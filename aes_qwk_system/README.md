# AES QWK Grading System

An automated essay grading system for `personal_training_set.csv` (100 essays from the Learning
Agency Lab / PERSUADE "Automated Essay Scoring 2.0" data), validated against the human gold scores
using Quadratic Weighted Kappa (QWK), the competition's own metric. Built as versioned, diffable
runs — v1 is the original implementation, v2 is a rubric revision — so each change's effect on QWK
is directly comparable rather than overwriting prior results.

**Latest result: v2 QWK = 0.640** (substantial agreement; v1 was 0.594, moderate). Full
interpretation in `evaluation/results_v2.md`; v1's is preserved in `evaluation/results_v1.md`.

## How this was built (short version)

1. A fixed rubric (`rubric_v1.md` / `rubric_v2.md`) walks the grader through evidence extraction →
   sub-scores (v1: Organization, Development, Conventions; v2 adds Argumentation, with a rule that
   Argumentation=1 caps the holistic score at 3) → a holistic 1–6 score, with an explicit
   instruction not to use essay length as a scoring signal in either direction.
2. `personal_training_set.csv`'s 100 essays were split into 10 batches of 10
   (`grading/batches.json`, reused across versions so runs are essay-for-essay comparable) and
   graded in parallel by 10 independent Claude subagents per version, each reading the rubric and
   the source CSV directly, blind to the `score` column, and writing its results to
   `grading/batch_results/batch_NN.json` (v1) or `grading/batch_results_v2/batch_NN.json` (v2).
3. `grading/grade_essays.py --assemble --version v1|v2` merges and validates those batch results
   into `grading/predictions_v1.csv` / `predictions_v2.csv` (one row per essay: human score, system
   holistic + sub-scores, word count, rationale). It also checks version-specific rules, like v2's
   Argumentation-caps-holistic rule, and flags any violations.
4. `evaluation/compute_qwk.py --version v1|v2` computes QWK, a confusion matrix, agreement rates,
   a random-shuffle baseline (is the QWK distinguishable from chance?), and — specifically because
   you flagged verbosity bias as a concern — correlations between word count and (a) human score,
   (b) system score, (c) the system-minus-human residual, so the bias question is answered
   empirically each run rather than assumed away. Output: `results_<version>.json` (numbers) and
   `results_<version>.md` (narrative interpretation).

## Folder / file map

```
aes_qwk_system/
  README.md                          — this file
  decisions_log.md                    — every judgment call made across all versions, with rationale
  rubric_v1.md                        — original grading rubric (3 sub-scores)
  rubric_v2.md                        — your revised rubric: teacher persona, hypothesize-prompt
                                         instruction, + Argumentation sub-score with a cap rule
  grading/
    grading_prompt_template.md        — exact prompt shape used per batch, and why essays are read
                                         from disk rather than pasted inline
    batches.json                      — the 10 batches of 10 essay_ids, shared by every version
    batch_results/batch_00..09.json   — raw v1 grading output (one array of 10 objects each)
    batch_results_v2/batch_00..09.json — raw v2 grading output
    grade_essays.py                   — version-aware orchestration: assembles + validates batch
                                         results into predictions_<version>.csv; docstring documents
                                         the two ways to make this fully headless (real API call vs.
                                         this run's in-session subagent grading)
    predictions_v1.csv                — v1 per-essay results
    predictions_v2.csv                — v2 per-essay results (adds system_argumentation column)
  evaluation/
    compute_qwk.py                    — version-aware: computes QWK + all diagnostics from any
                                         predictions_<version>.csv
    results_v1.json / results_v1.md   — v1 metrics + narrative interpretation (preserved, unchanged)
    results_v2.json / results_v2.md   — v2 metrics + narrative interpretation, including a
                                         side-by-side comparison against v1 and whether the rubric
                                         change fixed the specific gap that motivated it
  tracker_log.json                    — structured log of iteration commits (QWK, ∆, rationale)
                                         that the tracker agent reads/writes; canonical source for
                                         the Google Doc commit tracker
  tracker/
    run_tracker.py                    — the agent's git-log-parsing half: run on your Mac, updates
                                         tracker_log.json from new commits
    build_tracker_doc.js              — the agent's doc-building half: run by Claude, turns
                                         tracker_log.json into a .docx matching the tracker Doc's
                                         table layout, for upload to Google Drive
    README.md                         — how the tracker agent works and how to run a sync
```

`personal_training_set.csv` itself is **not duplicated** here — everything reads it from its
existing location in the project folder, so there's a single source of truth.

## Re-running / extending

- To re-assemble predictions from existing batch results:
  `cd grading && python3 grade_essays.py --assemble --version v1` (or `v2`)
- To recompute metrics: `cd evaluation && python3 compute_qwk.py --version v1` (or `v2`)
- For a v3 (or any future rubric change): add `rubric_v3.md`, grade into a new
  `batch_results_v3/`, then run both scripts with `--version v3` — no other code should need to
  change. `decisions_log.md` documents this as the intended delta workflow.

See `decisions_log.md` for every place a judgment call was made instead of an objectively-correct
choice, and why — including how the v1→v2 transition itself was handled (entries 13–18) and how
the Commit Tracker agent works around this environment's real constraints (entries 19–25).

## Commit Tracker agent

`tracker/` turns your structured commit messages (`<label> ; QWK: ... ; Delta: ... ; rationale:
...`) into the Google Doc tracking table you built by hand in `Template GitHub Commit Tracker`. It
runs on-demand (ask Claude to "run the commit tracker") rather than automatically in the
background — see `tracker/README.md` for why, and exactly what each run does.
