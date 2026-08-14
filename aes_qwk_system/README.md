# AES QWK Grading System — v1

An automated essay grading system for `personal_training_set.csv` (100 essays from the Learning
Agency Lab / PERSUADE "Automated Essay Scoring 2.0" data), validated against the human gold scores
using Quadratic Weighted Kappa (QWK), the competition's own metric.

**Headline result: QWK = 0.594** (moderate agreement, ~6 standard deviations above a random-pairing
baseline — real signal, not noise, but not yet essay-by-essay reliable). Full interpretation in
`evaluation/results_v1.md`.

## How this was built (short version)

1. A fixed rubric (`rubric_v1.md`) walks the grader through evidence extraction → three sub-scores
   (Organization, Development, Conventions) → a holistic 1–6 score, with an explicit instruction
   not to use essay length as a scoring signal in either direction.
2. `personal_training_set.csv`'s 100 essays were split into 10 batches of 10
   (`grading/batches.json`) and graded in parallel by 10 independent Claude subagents, each reading
   the rubric and the source CSV directly, blind to the `score` column, and writing its results to
   `grading/batch_results/batch_NN.json`.
3. `grading/grade_essays.py --assemble` merges and validates those batch results into
   `grading/predictions_v1.csv` (one row per essay: human score, system holistic + sub-scores,
   word count, rationale).
4. `evaluation/compute_qwk.py` computes QWK, a confusion matrix, agreement rates, and — specifically
   because you flagged verbosity bias as a concern — correlations between word count and (a) human
   score, (b) system score, (c) the system-minus-human residual, so the bias question is answered
   empirically rather than assumed away. Output: `evaluation/results_v1.json` (numbers) and
   `evaluation/results_v1.md` (narrative interpretation, including a random-shuffle baseline to
   show the agreement is real and not statistical noise).

## Folder / file map

```
aes_qwk_system/
  README.md                          — this file
  decisions_log.md                    — every judgment call made building v1, with rationale
  rubric_v1.md                        — the grading rubric given to every grader subagent
  grading/
    grading_prompt_template.md        — exact prompt shape used per batch, and why essays are read
                                         from disk rather than pasted inline
    batches.json                      — the 10 batches of 10 essay_ids used for parallel grading
    batch_results/batch_00.json..09.json
                                       — raw per-batch grading output (one array of 10 objects each)
    grade_essays.py                   — orchestration: assembles + validates batch_results into
                                         predictions_v1.csv; also documents (in its docstring) the
                                         two ways to make this fully headless for a v2 (real API
                                         call vs. this run's in-session subagent grading)
    predictions_v1.csv                — the actual per-essay result: essay_id, human_score,
                                         system_holistic_score, system_organization,
                                         system_development, system_conventions, word_count,
                                         rationale
  evaluation/
    compute_qwk.py                    — computes QWK + all diagnostics from predictions_v1.csv
    results_v1.json                   — machine-readable metrics (for diffing against v2/v3 later)
    results_v1.md                     — narrative interpretation: what the QWK means, agreement vs.
                                         disagreement vs. randomness, the verbosity-bias verdict,
                                         and a manual sanity-check read of the two largest misses
```

`personal_training_set.csv` itself is **not duplicated** here — everything reads it from its
existing location in the project folder, so there's a single source of truth.

## Re-running / extending

- To re-assemble predictions from the existing batch results:
  `cd grading && python3 grade_essays.py --assemble`
- To recompute metrics: `cd evaluation && python3 compute_qwk.py`
- To actually re-grade (v2, a rubric change, etc.), this whole system is designed to be forked:
  bump the version suffix (`rubric_v2.md`, `predictions_v2.csv`, `results_v2.md`/`.json`) so prior
  runs stay intact and diffable rather than overwritten.

See `decisions_log.md` for every place a judgment call was made instead of an objectively-correct
choice, and why.
