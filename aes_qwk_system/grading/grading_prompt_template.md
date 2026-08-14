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

## Why essays are read from disk rather than pasted into the prompt

Keeps the orchestrator simple (no need to escape/embed essay text into prompt strings) and lets
the grading agent see the exact same CSV a re-run would use. The tradeoff: the grading agent could
in principle glance at the `score` column since it's in the same file — this is mitigated by the
explicit "ignore the score column" instruction, and validated post-hoc by the bias/consistency
checks in `evaluation/compute_qwk.py` (a grader that was secretly reading the answer key would
produce suspiciously perfect agreement, which would itself be a flag to re-examine, not a result
to trust at face value).
