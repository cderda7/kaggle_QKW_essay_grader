# Ticket 05 — Trait override, recompute, and persistence

A teacher disagrees with the AI's trait scores; the holistic is recomputed through the frozen v9
aggregator; every correction lands in an append-only audit record that survives restart.

## Files touched

`teacher_ui/overrides.py` — **new.** Writes one correction to the ledger. Owns validation
ordering and obtaining a record's `recomputed_holistic` by building the artifact that would
result from storing it.

`teacher_ui/ledger.py` — **new.** Owns how either ledger reaches disk: a reentrant per-path lock
to be held across the whole read-modify-write, and an atomic replace through a pending file named
for the writing process and thread. Imported by `overrides.py` and `gold.py` alike, so the
invariant has one home rather than a copy in each (ui_19).

`teacher_ui/gold.py` — pre-existing, and now writes through `ledger.py` too. Its "one record per
essay" check is a read-modify-write with the same exposure, and it truncated the real file in
place, so an interrupted write lost every reveal already recorded rather than only the new one.

`teacher_ui/build_review.py` — the single seam. Gains `load_overrides` (path resolved at call
time), the collect-all override guards, `override_state` (the per-section latest-wins fold), and
the override-derived fields on each essay.

`teacher_ui/app.py` — gains `POST /api/override/{essay_id}` and the `SCORE_NARRATION` state table
that decides the score head, its sentence, and whether the formation panel opens itself.

`teacher_ui/static/app.js` — gathers the trait selects and the reason, POSTs, reloads. Computes
no score: there is no client-side aggregator.

`teacher_ui/static/app.css` — styles for the editable trait control, the corrected score head,
and the override and dissent forms.

`teacher_ui/overrides.json` — **new, generated.** The append-only ledger. Hand-editable and
diffable by design, which is why the guards name the offending value.

## How it connects

```
  ┌──────────────────────────────────────────────────────────────────────┐
  │  FROZEN INPUTS — ticket 05 changes none of these                     │
  │                                                                      │
  │  aggregator_v9.json          3 OLS coefficients + 5 cut points       │
  │  predictions_v9.csv          per-trait system_* scores               │
  │  annotation_v6_runB/         batches, comments, quoted spans         │
  │  personal_training_set.csv   essay text; the gold score stays here   │
  │                              and never enters the artifact (ui_4)    │
  └───────────────────────────────────┬──────────────────────────────────┘
                                      │
                                      ▼
  ┌───────────────────────────────────┴──────────────────────────────────┐
  │  build_review.build_review()  —  THE SINGLE SEAM (ui_6)              │
  │                                                                      │
  │  Override records are an INPUT here, not a mutation applied          │
  │  downstream. Joins predictions, annotation, essay text and override  │
  │  records; anchors spans via anchor.resolve_spans(); applies the      │
  │  frozen aggregator; emits the artifact.                              │
  │                                                                      │
  │    load_overrides()          reads overrides.json at CALL time,      │
  │                              through the ONE binding of              │
  │                              OVERRIDES_FILE                          │
  │    check_override_records()  hard errors, collected, naming the      │
  │                              essay and the offending value (ui_7)    │
  │    override_state()          folds one essay's records LATEST-WINS   │
  │                              PER SECTION (ui_12) — and again one     │
  │                              record short, which is what "what did   │
  │                              this save do" is measured against       │
  └───────────────────────────────────┬──────────────────────────────────┘
                                      │
                                      ▼
  ┌───────────────────────────────────┴──────────────────────────────────┐
  │  artifact essay dict                                                 │
  │                                                                      │
  │    ai_traits / traits                overridden / reviewed           │
  │    ai_holistic / holistic            score_unchanged_vs_ai           │
  │    holistic_before_latest_record     score_unchanged_by_latest_record│
  │    latest_record_kind                score_formation                 │
  │    latest_record_changed_traits      override_trail                  │
  └───────────────────────────────────┬──────────────────────────────────┘
                                      │
                                      ▼
  ┌───────────────────────────────────┴──────────────────────────────────┐
  │  app.py — the HTTP layer, holding no logic worth testing             │
  │                                                                      │
  │  GET  /essay/{id}      narration_state() picks one SCORE_NARRATION   │
  │                        row; that row decides ALL THREE of the score  │
  │                        head, its sentence, and whether the formation │
  │                        panel opens itself (ui_16 → ui_18).           │
  │                        render.py marks up the response text; gold.py │
  │                        withholds the rater score until a reveal is   │
  │                        ledgered (ticket 04).                         │
  │                                                                      │
  │  POST /api/override/{id}                                             │
  │                        membership-checks the essay against           │
  │                        annotated_ids(), then delegates to            │
  │                        overrides.record_correction().                │
  └───────────────────────────────────┬──────────────────────────────────┘
                                      │
                                      ▼
  ┌───────────────────────────────────┴──────────────────────────────────┐
  │  static/app.js — the browser half                                    │
  │                                                                      │
  │  Gathers the trait selects and the reason, POSTs, then RELOADS.      │
  │  Computes no score: predicting which cut point a continuous score    │
  │  lands in is exactly where a correction most often does nothing,     │
  │  so a local preview would discredit the instrument at the moment     │
  │  it is being audited (ui_13).                                        │
  └───────────────────────────────────┬──────────────────────────────────┘
                                      │
                                      ▼
  ┌───────────────────────────────────┴──────────────────────────────────┐
  │  overrides.record_correction()                                       │
  │                                                                      │
  │  1. guards run on the RAW values, before any coercion                │
  │  2. build #1 over the existing records → the standing score          │
  │  3. build #2 with the prospective record appended → THE recomputed   │
  │     holistic. Never a second implementation of the fitted map: a     │
  │     direct apply_aggregator() call would drift, and the place it     │
  │     would surface is the panel built to be audited (ui_13).          │
  │  4. re-fold the trail so the POST response matches a later GET       │
  │  5. append() — through ledger.write_json: a pending file named for   │
  │     this process and thread, then os.replace(), so a half-written    │
  │     ledger is never left behind and two writers cannot interleave    │
  │     into one truncated file                                          │
  │                                                                      │
  │  Steps 1-5 run under ledger.lock(path). The lock has to span the two │
  │  builds, not just the append: original_holistic and score_unchanged  │
  │  are formed from the records as they stood when the save BEGAN, so a │
  │  save landing in between would make them describe a ledger that      │
  │  never existed (ui_19).                                              │
  └───────────────────────────────────┬──────────────────────────────────┘
                                      │
                                      ▼
  ┌───────────────────────────────────┴──────────────────────────────────┐
  │  overrides.json — the append-only audit ledger                       │
  │                                                                      │
  │  Hand-editable and diffable by design, which is why the guards       │
  │  name the offending value rather than quietly re-scoring an essay.   │
  │  Read back by load_overrides() on the very next build: the ledger    │
  │  is both an output of this path and an input to the seam above.      │
  └──────────────────────────────────────────────────────────────────────┘
```

## The four things worth knowing

**One binding owns the ledger path.** `build_review.OVERRIDES_FILE` (env-overridable via
`TEACHER_UI_OVERRIDES_FILE`) is read at call time by every reader and every writer. A second copy
would let a test redirect one and leave the app appending to the committed audit record.

**One lock spans the whole read-modify-write.** `record_override` is a sync `def`, so FastAPI
runs it on anyio's threadpool and two tabs really do save at once. Nothing is lost even unlocked
— `append` re-reads under its own lock — but the record's account of ITSELF is formed before that
re-read, so without the outer lock a record reports moving from a score another record had
already superseded. `gold.record_reveal` holds the same lock across its own check and write.

**The recomputed holistic comes from the build, not from arithmetic.** Two builds per correction is
the deliberate cost (ui_13). A direct `apply_aggregator` call would be a second implementation of a
fitted map, and the place its drift would surface is the score-formation panel that exists to be
audited.

**The narration is a table, not a chain of conditionals.** `SCORE_NARRATION` has one row per state,
and each row decides the head, the sentence and the panel together. Deriving them separately let
the page contradict itself in four successive review rounds (ui_18).
