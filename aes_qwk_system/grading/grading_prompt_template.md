# Grading prompt template (v1)

This is the exact prompt shape used for each batch of essays. `{RUBRIC}` is the full contents of
`rubric_v1.md`. `{ESSAY_IDS}` is the list of essay_ids in this batch. `{CSV_PATH}` is the path to
the source CSV the grader agent reads directly (essay text is NOT pasted inline into the prompt —
the agent reads it from disk so the orchestrator doesn't have to duplicate essay content).

```
You are grading student essays using the rubric below. Read the essays yourself from the CSV file
at {CSV_PATH} — it has columns essay_id, full_text, score. IGNORE the `score` column entirely; it
is the human rater's answer and must not influence or leak into your grading. Grade only these
essay_ids from that file: {ESSAY_IDS}

<rubric>
{RUBRIC}
</rubric>

For each essay_id listed above, follow the rubric's required process and produce one JSON object
in the exact output format the rubric specifies. Return a JSON array of these objects, one per
essay_id, and nothing else — no prose before or after the array. Grade each essay independently;
do not let other essays in this batch influence any score.
```

## What the grader is asked for changed in v5

Through v4 the grader produced a `holistic_score` (plus `gate_applied` / `gate_rationale`) by
executing the rubric's steps 6–7 itself. **From v5 the grader's job stops at the four trait
scores.** `rubric_v5.md` has no steps 6–7, and its output schema is exactly six fields: `essay_id`,
`evidence_notes`, and the four traits. `grade_essays.py` computes the holistic score, the gate and
the gate rationale from those traits via `v4_holistic()`.

The prompt shape above needs no change — it already says only "follow the rubric's required process
and produce one JSON object in the exact output format the rubric specifies," and the rubric now
specifies a shorter one. This template never names the fields, which is why it survived the schema
change untouched.

`assemble --version v5` hard-errors if a batch object contains `holistic_score`, `gate_applied` or
`gate_rationale`, on the grounds that the v5 grader was never asked for them — their presence means
the batch was graded against an older prompt, or the model kept going past its instructions. Same
style of guard as the `SCORES` check below: mechanical, and it fails loudly rather than quietly
assembling a run that isn't what the CSV would claim.

## The `SCORES` field is never part of this prompt

From v3 on, each object in `batch_results_v3_iter3/*.json` leads with a `"SCORES": "<human> vs. <system>"`
field. **Do not add it to the output format this prompt asks for, and do not mention it here.** It
is injected after grading by `grade_essays.py --annotate-scores`, which reads the gold scores from
`personal_training_set.csv`. Asking the grader to emit it would require handing the grader the
human score — the exact thing the "IGNORE the `score` column" instruction above exists to prevent —
and the resulting QWK would measure only the model's willingness to copy a number it was given.

`grade_essays.py` enforces this: an annotation manifest records every `SCORES` field the script
wrote, and any `SCORES` field it can't account for aborts assembly as suspected leakage. If you ever
need to show prior batch results to a model (say, a v4 run comparing itself against v3), generate a
blind copy first with `--strip-scores --out-dir <dir>` and pass that instead.

## Why essays are read from disk rather than pasted into the prompt

Keeps the orchestrator simple (no need to escape/embed essay text into prompt strings) and lets
the grading agent see the exact same CSV a re-run would use. The tradeoff: the grading agent could
in principle glance at the `score` column since it's in the same file — this is mitigated by the
explicit "ignore the score column" instruction, and validated post-hoc by the bias/consistency
checks in `evaluation/compute_qwk.py` (a grader that was secretly reading the answer key would
produce suspiciously perfect agreement, which would itself be a flag to re-examine, not a result
to trust at face value).
