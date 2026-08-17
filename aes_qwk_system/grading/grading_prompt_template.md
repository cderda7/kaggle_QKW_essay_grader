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

## v7 adds a second prompt shape: the triage pass

v7 runs **two** passes over the same essays, and this file now describes both.

**The trait pass is unchanged.** Same template as above, `{RUBRIC}` = `rubric_v6.md`. v7 did not
re-run it at all — the trait scores are carried through from `predictions_v6_runB.csv` by
`--derive --version v7`.

**The triage pass has its own prompt**, and its `{RUBRIC}` is `rubric_v7_triage.md` — the whole of
it, and nothing else. The triage reader never sees a trait scale, a trait score, or a holistic rule,
because a first impression contaminated by the trait ladders is no longer a first impression.

```
You are performing a first-impression TRIAGE READ of student essays.

Read {TRIAGE_INSTRUMENT} in full first. It is your complete instructions for how to judge.
Follow it exactly — especially the two-rung ladder, the "when you hesitate, answer other" rule,
the length prohibition, and the output format.

The essays are in {BLIND_CSV_PATH}, which has exactly two columns: essay_id and full_text.
Read the essay text for these essay_ids and no others: {ESSAY_IDS}

Read each essay yourself, in full, one at a time. Judge each essay independently — do not let the
other essays in this batch calibrate it, and do not aim for any particular number of very_bad or
bad labels.

Write your results as a JSON array of objects — one per essay_id, in the order listed above — to
{OUT_PATH}. Each object has exactly the four fields the instrument's Output format section
specifies: essay_id, triage_label, deciding_rung, triage_note. Do not add any other field.
```

Three differences from the trait prompt, each deliberate:

- **`{BLIND_CSV_PATH}`, not the source CSV.** The triage pass reads a projection containing only
  `essay_id` and `full_text`, produced by `grade_essays.py --make-blind-csv`. Every earlier run kept
  the grader off the gold score by instruction while the column sat in the file it opened; this one
  removes the column. `decisions_log.md` #62 — and it is why the "IGNORE the `score` column"
  sentence is absent from the prompt above rather than merely repeated.
- **"do not aim for any particular number."** The corpus's base rates (9 human 1s, 25 human 2s) are
  known to `rubric_v7.md` and were deliberately kept out of the instrument and out of this prompt.
  Handing a grader the answer key's distribution is a softer version of handing it the answer key.
- **The reader writes the file.** Ten batches in parallel, each writing
  `batch_results_v7_triage/batch_NN.json` directly, rather than returning JSON through the
  orchestrator to be re-serialised.

`load_triage()` validates the result: labels in range, `deciding_rung` present and *consistent with
the label*, no forbidden field (trait scores, holistic score, gold score, `SCORES`), and exact
coverage of `batches.json`. All hard errors — a triage pass is one label per essay, so there is no
partially-usable one.
