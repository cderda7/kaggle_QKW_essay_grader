# Ticket 05 — Trait override, recompute, and persistence

A teacher disagrees with the AI's trait scores; the holistic is recomputed through the frozen v9
aggregator; every correction lands in an append-only audit record that survives restart.

## Files touched

`teacher_ui/overrides.py` — **new.** Writes one correction to the ledger. Owns validation
ordering, the atomic append, and obtaining a record's `recomputed_holistic` by building the
artifact that would result from storing it.

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
                    ┌─────────────────────────────────────────────────────────┐
                    │  FROZEN INPUTS — ticket 05 changes none of these         │
                    │                                                          │
                    │  aggregator_v9.json     predictions_v9.csv               │
                    │  (3 OLS coefficients    (system_* trait scores)          │
                    │   + 5 cut points)                                        │
                    │  annotation_v6_runB/    personal_training_set.csv        │
                    │  (batches, comments,    (essay text; the gold score      │
                    │   quoted spans)          stays here — never in the       │
                    │                          artifact, decision ui_4)        │
                    └────────────────────────────┬─────────────────────────────┘
                                                 │
                                                 ▼
   overrides.json  ─────────────────────▶  build_review.build_review()
   (append-only     load_overrides()      ─────────────────────────────
    audit ledger)   reads it at CALL      THE SINGLE SEAM (ui_6).
          ▲         time, through the     Override records are an INPUT here,
          │         one binding of        not a mutation applied downstream.
          │         OVERRIDES_FILE        Joins predictions + annotation + text
          │                                + override records, anchors spans
          │                                via anchor.resolve_spans(), applies
          │                                the aggregator, emits the artifact.
          │                                        │
          │                                        │  calls
          │                                        ▼
          │                          check_override_records()   ← hard errors, collected,
          │                          ─────────────────────────    naming the essay and the
          │                          override_state()             offending value (ui_7)
          │                          ─────────────────────────
          │                          Folds one essay's records
          │                          LATEST-WINS PER SECTION (ui_12):
          │                          a dissent does not erase a
          │                          correction. Also yields the
          │                          fold one record short, which
          │                          is what "what did this save
          │                          do" is measured against.
          │                                        │
          │                                        ▼
          │                          ┌──────────────────────────────────┐
          │                          │ artifact essay dict              │
          │                          │  ai_traits / traits              │
          │                          │  ai_holistic / holistic          │
          │                          │  holistic_before_latest_record   │
          │                          │  latest_record_kind              │
          │                          │  latest_record_changed_traits    │
          │                          │  overridden / reviewed           │
          │                          │  score_unchanged_vs_ai           │
          │                          │  score_unchanged_by_latest_record│
          │                          │  score_formation / override_trail│
          │                          └───────────┬──────────────────────┘
          │                                      │
          │            ┌─────────────────────────┴───────────────────────┐
          │            ▼                                                 ▼
          │   app.py  GET /essay/{id}                      app.py  POST /api/override/{id}
          │   ───────────────────────                      ─────────────────────────────
          │   narration_state()  ──▶ SCORE_NARRATION       membership-checks the essay
          │     one row per state; the row decides         against annotated_ids(), then
          │     ALL THREE of the score head, its           delegates to overrides.py
          │     sentence, and whether the formation                    │
          │     panel opens itself (ui_16/ui_17/ui_18).                │
          │   render.py renders the marked-up response.                │
          │   gold.py withholds the rater score until                  │
          │     a POST reveal is ledgered (ticket 04).                 │
          │            │                                               │
          │            ▼                                               ▼
          │      HTML page ──▶ static/app.js                overrides.record_correction()
          │                    ───────────────              ─────────────────────────────
          │                    Gathers selects +            1. guards run on RAW values,
          │                    reason, POSTs, then             before any coercion
          │                    RELOADS. Computes no         2. build #1 over existing
          │                    score: predicting which         records → the standing score
          │                    cut point a continuous       3. build #2 with the prospective
          │                    score lands in is where        record appended → THE
          │                    a correction most often        recomputed holistic (ui_13:
          │                    does nothing (ui_13).           never a second implementation
          │                         │                          of the fitted map)
          │                         │                       4. re-fold the trail so the POST
          │                         │                          response matches a later GET
          │                         └──────POST────────────▶ 5. append()
          │                                                          │
          └──────────────────────────────────────────────────────────┘
                        atomic: write sibling temp file, os.replace()
```

## The three things worth knowing

**One binding owns the ledger path.** `build_review.OVERRIDES_FILE` (env-overridable via
`TEACHER_UI_OVERRIDES_FILE`) is read at call time by every reader and every writer. A second copy
would let a test redirect one and leave the app appending to the committed audit record.

**The recomputed holistic comes from the build, not from arithmetic.** Two builds per correction is
the deliberate cost (ui_13). A direct `apply_aggregator` call would be a second implementation of a
fitted map, and the place its drift would surface is the score-formation panel that exists to be
audited.

**The narration is a table, not a chain of conditionals.** `SCORE_NARRATION` has one row per state,
and each row decides the head, the sentence and the panel together. Deriving them separately let
the page contradict itself in four successive review rounds (ui_18).
