# Architecture

An automated essay scorer for a 1-6 rubric, evaluated by Quadratic Weighted Kappa, plus the
teacher review UI that lets a human audit and correct what it produced.

Per-ticket notes live in `architecture/`. This file folds their diagrams into one running picture.
It starts at ticket 05 — earlier tickets are documented by `teacher_ui/decisions_log.md` and their
issue files, and are deliberately not backfilled here.

## The system, end to end

```
  personal_training_set.csv           essay text + the human rater's gold score
            │
            ▼
  aes_qwk_system/grading/             the scoring pipeline (frozen for the UI ladder)
  ─────────────────────────
  grade_essays.py  ──▶ predictions_v9.csv     per-trait system_* scores
  aggregator_v9.json                          3 fitted OLS coefficients + 5 cut points
            │
            |   annotation_v6_runB/           per-trait comments and quoted spans
            │            │
            ▼            ▼
  aes_qwk_system/teacher_ui/build_review.py   ◀── overrides.json  (append-only audit ledger)
  ==========================================      gold_reveals.json (one record per disclosure)
  THE SINGLE SEAM. Joins predictions, annotation, essay text and override
  records into one artifact. Span anchoring, batch validation, the join,
  holistic recomputation and override application all sit below this
  boundary, which leaves the HTTP layer with no logic worth testing (ui_6).
            │
            ├── anchor.py       resolves each quoted span to offsets in the text
            ├── override_state  folds a teacher's records latest-wins PER SECTION (ui_12)
            └── gold.py         withholds the rater's score until a reveal is ledgered (ui_4)
            │
            ▼
  aes_qwk_system/teacher_ui/app.py             the served pages and the JSON API
  ---------------------------------
  Rebuilds the artifact per request — nothing is cached, so a hand edit to
  overrides.json shows up on the next page load.
            │
            ├── render.py          essay text with per-criterion span marks
            ├── SCORE_NARRATION    one row per state; each row decides the score head,
            |                      its sentence and the formation panel together (ui_18)
            └── overrides.py       writes one correction, through the same seam (ui_13)
            │
            ▼
  static/app.js + static/app.css               the browser half
  ------------------------------
  Pins evidence to a trait, gathers corrections, POSTs, reloads. Computes no
  score: there is no client-side aggregator, by decision (ui_13).
```

## Ticket 05 — Trait override, recompute, and persistence

Full diagram: [`architecture/05-trait-override-and-persistence.md`][t05].

[t05]: architecture/05-trait-override-and-persistence.md

Added the write path, and the state the page reads back from it.

```
  static/app.js ──POST /api/override/{id}──▶ app.py ──▶ overrides.record_correction()
                                                             │
                                        build #1 over existing records → standing score
                                        build #2 with the record appended → recomputed
                                        holistic (never a second implementation of the
                                        fitted map — ui_13)
                                                             │
                                                             ▼
                                                    append() → overrides.json
                                                    atomic: temp file, os.replace()
                                                             │
                    load_overrides() reads it at call time, through the ONE binding
                    of OVERRIDES_FILE, so redirecting that name moves every reader
                    and every writer at once
                                                             │
                                                             ▼
                                        build_review → artifact → SCORE_NARRATION → page
```

Two guards define the stance: override records are validated as a set with every problem collected
and the offending value named (ui_7), and there is deliberately no direct holistic input — a
disagreement with the number itself is a *dissent*, a rationale and no number, stored against the
aggregator (ui_2).
