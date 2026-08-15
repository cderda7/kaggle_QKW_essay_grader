# AES QWK Grading System

An automated essay grading system for `personal_training_set.csv` (100 essays from the Learning
Agency Lab / PERSUADE "Automated Essay Scoring 2.0" data), validated against the human gold scores
using Quadratic Weighted Kappa (QWK), the competition's own metric. Built as versioned, diffable
runs — v1 is the original implementation, v2 and v3 are rubric revisions — so each change's effect
on QWK is directly comparable rather than overwriting prior results.

**Latest result: v3 QWK = 0.638** — essentially tied with v2 (0.640; v1 was 0.594). Not a clean
"win": v3 fixed a real structural failure (the system never assigned a holistic score of 1 in
v1/v2; it does now, correctly, 3 of 9 times) but introduced a different one (a rubric gap inflates
~14% of essays, concentrated in the largest human-score cohort, worsening exact agreement 51%→43%
and MAE 0.54→0.65). Full breakdown and the tradeoff discussion in `evaluation/results_v3.md`; v1/v2
preserved unchanged in `evaluation/results_v1.md` / `results_v2.md`.

## How this was built (short version)

1. A fixed rubric (`rubric_v1.md` / `rubric_v2.md` / `rubric_v3.md`) walks the grader through
   evidence extraction → sub-scores (v1: Organization, Development, Conventions; v2 adds
   Argumentation, with a rule that Argumentation=1 caps the holistic score at 3; v3 keeps the same
   4 sub-scores, now grounded in the verbatim official PERSUADE rubric, and replaces the single-field
   cap with a general severe-weakness gate — any sub-score ≤2 caps the essay in a disjunctive 1–3
   band, otherwise it must jointly clear multiple traits to reach a compensatory 4–6 band) → a
   holistic 1–6 score, with an explicit instruction not to use essay length as a scoring signal in
   either direction.
2. `personal_training_set.csv`'s 100 essays were split into 10 batches of 10
   (`grading/batches.json`, reused across versions so runs are essay-for-essay comparable) and
   graded in parallel by 10 independent Claude subagents per version, each reading the rubric and
   the source CSV directly, blind to the `score` column, and writing its results to
   `grading/batch_results/batch_NN.json` (v1), `grading/batch_results_v2/batch_NN.json` (v2), or
   `grading/batch_results_v3/batch_NN.json` (v3).
3. `grading/grade_essays.py --assemble --version v1|v2|v3` merges and validates those batch results
   into `grading/predictions_<version>.csv` (one row per essay: human score, system holistic +
   sub-scores, word count, rationale). It also checks version-specific rules — v2's
   Argumentation-caps-holistic rule, v3's full disjunctive/compensatory gate via
   `validate_v3_gate()` — and flags any violations (hard) or ambiguous edge cases (soft).
4. `evaluation/compute_qwk.py --version v1|v2|v3` computes QWK, a confusion matrix, agreement rates,
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
  rubric_v3.md                        — graded (all 100 essays): restructures scoring into a
                                         disjunctive 1–3 band (one severe trait weakness caps the
                                         essay) vs. compensatory 4–6 band (requires jointly clearing
                                         multiple traits), grounded in the verbatim official
                                         PERSUADE rubric (rubric_official_persuade.md) rather than
                                         the reconstructed proxy v1/v2 used — see decisions_log.md
                                         #27–40
  rubric_official_persuade.md         — verbatim official PERSUADE 2.0 rubric (Independent +
                                         Source-based variants), sourced from the corpus repo;
                                         supersedes the "reconstructed proxy" caveat from decision #2
  grading/
    grading_prompt_template.md        — exact prompt shape used per batch, and why essays are read
                                         from disk rather than pasted inline
    batches.json                      — the 10 batches of 10 essay_ids, shared by every version
    batch_results/batch_00..09.json   — raw v1 grading output (one array of 10 objects each)
    batch_results_v2/batch_00..09.json — raw v2 grading output
    batch_results_v3/batch_00..09.json — raw v3 grading output (includes gate_applied/gate_rationale);
                                         each object now leads with a post-hoc
                                         "SCORES": "<human> vs. <system>" line — see below
    batch_results_v3/_scores_annotation.json — generated manifest backing that field's leakage
                                         guard; do not hand-edit
    grade_essays.py                   — version-aware orchestration: assembles + validates batch
                                         results into predictions_<version>.csv; docstring documents
                                         the two ways to make this fully headless (real API call vs.
                                         this run's in-session subagent grading); validate_v3_gate()
                                         is the v3-specific disjunctive/compensatory rule checker;
                                         annotate_scores()/strip_scores() manage the SCORES field
    predictions_v1.csv                — v1 per-essay results
    predictions_v2.csv                — v2 per-essay results (adds system_argumentation column)
    predictions_v3.csv                — v3 per-essay results (adds system_gate_applied column)
  evaluation/
    compute_qwk.py                    — version-aware: computes QWK + all diagnostics from any
                                         predictions_<version>.csv
    results_v1.json / results_v1.md   — v1 metrics + narrative interpretation (preserved, unchanged)
    results_v2.json / results_v2.md   — v2 metrics + narrative interpretation, including a
                                         side-by-side comparison against v1 and whether the rubric
                                         change fixed the specific gap that motivated it
    results_v3.json / results_v3.md   — v3 metrics + narrative interpretation: the never-assigns-1
                                         fix confirmed, and the new "all-3s dead zone" cost it traded
                                         against (decisions_log.md #38-40)
  tracker_log.json                    — structured log of iteration commits (QWK, ∆, rationale)
                                         for this project; canonical source for its Google Doc
                                         commit tracker. The AGENT ITSELF (run_tracker.py,
                                         build_tracker_doc.js) now lives outside this project, at
                                         projects/claude-agents/commit-tracker/ — see below — so it
                                         can be reused across projects rather than copied per-repo.
```

`personal_training_set.csv` itself is **not duplicated** here — everything reads it from its
existing location in the project folder, so there's a single source of truth.

## The `SCORES` field, and why the grader never writes it

From v3 on, every object in `batch_results_v3/*.json` leads with a one-line score comparison, so
reading a batch file tells you where the system agreed with the teacher before you read a single
rationale:

```json
{
  "SCORES": "3 vs. 2",

  "essay_id": "000d118",
  "evidence_notes": "...",
  ...
}
```

Left number is the human gold score, right is the system's `holistic_score`. **The grader does not
produce this field.** It's injected afterwards by `grade_essays.py --annotate-scores`, which reads
the gold scores from `personal_training_set.csv` — the same file the assembler already reads.

That ordering is the whole point, not an implementation detail. Asking the grader to emit
`"3 vs. 2"` would mean handing it the 3 first, which contradicts the "IGNORE the `score` column"
instruction the run's blindness depends on and would make QWK a measure of the model's willingness
to copy a number it was given. The failure wouldn't look like a failure, either — agreement would
*improve*. So three guards enforce the ordering mechanically rather than by convention:

- **Leakage detection.** `_scores_annotation.json` records every essay this script annotated. A
  `SCORES` field it can't account for aborts `--assemble` with an explanation, on the assumption
  that a grader produced it.
- **`--strip-scores`.** The inverse operation. Run it before showing prior batch results to any
  model — e.g. a v4 that compares itself against v3 — so gold scores never enter a grader's
  context. `--out-dir <dir>` writes blind copies and leaves the originals annotated.
- **CSV cross-check.** `SCORES` comes from the batch JSONs while every reported metric comes from
  `predictions_<version>.csv`; annotation warns if the two disagree, so the comparison you read is
  never quietly describing a different run than the headline QWK does.

Enabled for v3 and later only — v1/v2 batch results stay frozen. Future versions opt in with
`"annotate_scores": True` in `VERSION_CONFIG`. Full reasoning in `decisions_log.md` #41.

> **Open discrepancy (decisions_log.md #42):** the cross-check above fired the first time it ran.
> `batch_results_v3/` and the checked-in `predictions_v3.csv` currently describe two different v3
> generations — re-assembling from the batch files changes 69 of 100 rows and moves the metrics from
> QWK 0.6447 / 54% exact (what `results_v3.json` holds) to QWK 0.6382 / 43% (what this README's
> headline and decision #40 report). Nothing has been regenerated to resolve it; see #42.

## Re-running / extending

- To re-assemble predictions from existing batch results:
  `cd grading && python3 grade_essays.py --assemble --version v1` (or `v2`, `v3`) — note this
  needs `PERSONAL_TRAINING_SET_CSV=<path to personal_training_set.csv>` set in the environment if
  it isn't sitting two directories up from `grading/` (see the script's `--source-csv`/env-var
  handling).
  For v3 this also refreshes the `SCORES` fields in the batch results; add `--no-annotate` to leave
  those files byte-identical.
- To refresh `SCORES` without rebuilding the CSV:
  `cd grading && python3 grade_essays.py --annotate-scores --version v3`
- To produce blind (SCORES-free) copies before showing batch results to a model:
  `cd grading && python3 grade_essays.py --strip-scores --version v3 --out-dir /tmp/blind_v3`
- To recompute metrics: `cd evaluation && python3 compute_qwk.py --version v1` (or `v2`, `v3`)
- For a v4 (or any future rubric change): add `rubric_v4.md`, grade into a new `batch_results_v4/`,
  add a `"v4"` entry to `VERSION_CONFIG` in `grade_essays.py`, then run both scripts with
  `--version v4`. A concrete, already-identified v4 candidate: close the "all-3s dead zone" gap
  found in v3 (decisions_log.md #38) — e.g. widen the severe-weakness trigger or add an explicit
  tie-break rule for flat-3 trait profiles.

See `decisions_log.md` for every place a judgment call was made instead of an objectively-correct
choice, and why — including how the v1→v2 transition itself was handled (entries 13–18), the v3
rubric redesign and grading run (entries 27–40), and how the Commit Tracker agent works around this
environment's real constraints (entries 19–25).

## Commit Tracker agent

Turns this project's structured commit messages (`<label> ; QWK: ... ; Delta: ... ; rationale:
...`) into the Google Doc tracking table you built by hand in `Template GitHub Commit Tracker`.
**Moved out of this project** on 2026-08-14 to `projects/claude-agents/commit-tracker/` so it's
reusable for any project, not just this one — see that folder's README for how it works, and
`projects/claude-agents/README.md` for the catalog of every such shared agent. Only
`tracker_log.json` (this project's data) stays here; the agent itself does not. It runs on-demand
(ask Claude to "run the commit tracker for this project") rather than automatically in the
background — see the agent's own README for why.
