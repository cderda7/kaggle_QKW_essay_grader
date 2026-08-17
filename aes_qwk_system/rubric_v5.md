# AES Grading Rubric v5

Scale: **1 (lowest) to 6 (highest)**, matching the official PERSUADE / Learning Agency Lab AES 2.0 scale.

> **v5 changes what the grader is asked to do, not how essays are scored.** The scoring rules are
> unchanged from v4 — same four traits, same weights, same severe-weakness gate, same band
> thresholds. What changed is *who executes them*: **the grader's job now stops at the four trait
> scores.** The gate, the band placement, the weighted mean and the threshold tests have moved into
> `grading/grade_essays.py` (`v4_holistic()`), which computes the holistic score from the traits.
> Steps 6–7 of the v4 rubric are therefore absent from this file by design — not omitted by
> accident. See `decisions_log.md` #50.

> **Why.** v3/v4 asked the grader to run a seven-step conditional: count traits at ≤2, branch on
> how many are exactly 1, compute a weighted mean, round half up, clamp to a band, then test three
> threshold rules. Claude followed it perfectly — the v4 fidelity check found 100/100 compliance —
> but that is a frontier-model result, and this project's goal constrains it to sub-120B models
> that will not follow it reliably. Moving the rule into code deletes the hardest part of the task
> from the model's job and leaves it doing the thing smaller models are genuinely competent at:
> applying trait descriptions to text and emitting four integers. It also removes a whole class of
> bug rather than validating around it — decisions #38–39 (essays where the rubric's ambiguity was
> resolved two different ways) and #42 (the drift between two generations) were both
> grader-executing-rules failures, and a rule the grader never runs cannot be run wrongly.

## Trait weights (applied in code, not by the grader) [v4, unchanged]

| Trait | Official rubric dimension | Weight |
|---|---|---|
| Argumentation | point of view and critical thinking | **0.35** |
| Organization | organization / coherence | 0.25 |
| Development | evidence and support | 0.25 |
| Conventions | language | **0.15** |

**The grader does not use this table.** It is here so a reader of this file knows what happens to
the four scores downstream, and to make explicit that no trait should be inflated or deflated in
anticipation of its weight. Score each trait on its own merits; the weighting is applied once,
afterwards, by `v4_holistic()`.

## Task given to the grader

You are a high school english teacher with 10 years experience. You are grading your students' assignments by determining the extent to which they align with your standards, as outlined on the provided rubric. You are scoring a student argumentative/source-based essay written in response to a prompt. The prompt may not be visible to you. If no prompt is available, generate a hypothesis prompt so that you may grade the essay against what it set out to do. If the essay draws on a provided source text or texts, evidence should be evaluated against how well it's drawn from those sources; if it doesn't (an independent-writing prompt), evaluate evidence and reasoning on their own merits. Then, score the essay on its own internal merits: point of view and critical thinking, use of evidence/support, organization/coherence, and use of language.

## Required process (in this order — do not skip steps, and do not score a trait before step 1)

**These five steps are the whole task.** Earlier versions of this rubric had a step 6 and a step 7
that combined the four trait scores into a single holistic score. Those steps now run in code. Stop
after step 5.

1. **Evidence extraction.** Identify 2–3 concrete pieces of evidence of the essay's argumentative
   quality: the main claim, key supporting reasons/evidence (noting whether they're drawn from a
   provided source text, if one exists), and how directly they connect to the claim. Write these
   down before scoring anything.

2. **Organization (1–6).** Maps to the official rubric's *organization / coherence* dimension:
   structure, focus, coherence, and progression of ideas from intro to conclusion.

3. **Development / Evidence & Support (1–6).** Maps to the official rubric's *evidence and
   support* dimension: how appropriate and sufficient the examples, reasons, and evidence are —
   drawn from the source text(s) when the essay is source-based — in supporting its position.
   *This is about how well-supported and precise the argument is, not how much text there is.* A
   short essay that makes a precise, well-evidenced point should score as well here as a long
   essay that makes the same point with padding or repetition.

4. **Conventions / Language (1–6).** Maps to the official rubric's *language* dimension, which is
   broader than grammar alone: vocabulary (appropriate vs. weak/incorrect word choice), sentence
   variety and structure, and grammar/usage/mechanics. Score what's actually on the page; do not
   infer this from length or topic complexity alone.

5. **Point of View / Argumentation (1–6).** Maps to the official rubric's *point of view and
   critical thinking* dimension: how insightfully and originally the essay develops and argues its
   position on the issue — this goes beyond basic synthesis of the evidence gathered in step 3.

**Stop here.** Return the four trait scores and your evidence notes. Do not combine them.

## Provenance note (superseding v1/v2's)

v1 and v2 used a *reconstructed proxy* rubric because the real one couldn't be fetched in that
environment. `rubric_official_persuade.md` resolved that — it's the verbatim **official PERSUADE
2.0 scoring rubric**, sourced from the corpus repo
(https://github.com/scrosseye/persuade_corpus_2.0), covering both task variants (Independent /
Source-based writing, which are identical apart from an evidence-from-source clause). The trait
definitions above and the score-band anchors below are grounded directly in that verbatim text —
see `decisions_log.md` #27 for what changed as a result and how the two task variants were merged.

## Explicit anti-verbosity-bias instruction

**Do not use essay length as a scoring signal, in either direction.** A concise, well-argued essay
should score as well as or better than a long, repetitive, or padded one making the same points.
Conversely, do not penalize a short essay for being short if its argument is complete and precise.
If you notice yourself inclined to raise or lower a score primarily because an essay "feels
substantial" or "feels thin" due to its length, stop and re-ground the score in the Organization /
Development / Conventions / Point-of-View judgments above instead.

## Score-band anchors — verbatim official rubric (merged Independent + Source-based variants)

> **[v5] Read these as calibration context for the trait scores, not as a score to assign.** You are
> not producing a holistic score, so these six descriptors are here to anchor what each *level* of
> quality looks like. Each one describes all four dimensions at once — find the clause that matches
> the trait you are scoring and use it to place that trait. For example, a level-6 essay "exhibits
> skillful use of language, using varied, accurate, and apt vocabulary" — that clause is your
> Conventions-at-6 anchor.
>
> **Known limitation, being fixed next:** this is an awkward instrument for the job. These anchors
> describe whole essays, so scoring a single trait against them requires you to mentally decompose
> them every time — and run-to-run agreement is measurably worst on exactly the two traits whose
> anchors are hardest to isolate (conventions 61%, argumentation 62%, against organization 80% and
> development 74%). Rewriting these as four per-trait scales of six levels each, extracted from the
> same official text, is the next planned change to this file.

Bracketed clauses apply when the essay draws on a provided source text; omit them for
independent-writing prompts. Lightly cleaned up from the source PDFs' own minor phrasing slips,
as the source material's own notes invite for prompt use — content unchanged.

**6 — Compensatory.** Demonstrates clear and consistent mastery, although it may have a few minor
errors. A typical essay effectively and insightfully develops a point of view on the issue and
demonstrates outstanding critical thinking, using clearly appropriate examples, reasons, and other
evidence [taken from the source text(s)] to support its position; is well organized and clearly
focused, demonstrating clear coherence and smooth progression of ideas; exhibits skillful use of
language, using varied, accurate, and apt vocabulary and meaningful variety in sentence structure;
and is free of most errors in grammar, usage, and mechanics.

**5 — Compensatory.** Demonstrates reasonably consistent mastery, although it will have occasional
errors or lapses in quality. A typical essay effectively develops a point of view on the issue and
demonstrates strong critical thinking, generally using appropriate examples, reasons, and other
evidence [taken from the source text(s)] to support its position; is well organized and focused,
demonstrating coherence and progression of ideas; exhibits facility in the use of language, using
appropriate vocabulary and demonstrating variety in sentence structure; and is generally free of
most errors in grammar, usage, and mechanics.

**4 — Compensatory.** Demonstrates adequate mastery, although it will have lapses in quality. A
typical essay develops a point of view on the issue and demonstrates competent critical thinking,
using adequate examples, reasons, and other evidence [taken from the source text(s)] to support
its position; is generally organized and focused, demonstrating some coherence and progression of
ideas; may demonstrate inconsistent facility in the use of language, using generally appropriate
vocabulary and demonstrating some variety in sentence structure; and may have some errors in
grammar, usage, and mechanics.

**3 — Disjunctive.** Demonstrates developing mastery, and is marked by ONE OR MORE of the
following weaknesses: develops a point of view on the issue demonstrating some critical thinking,
but may do so inconsistently or use inadequate examples, reasons, or other evidence [taken from
the source text(s)] to support its position; is limited in its organization or focus, or may
demonstrate some lapses in coherence or progression of ideas; may demonstrate facility in the use
of language, but sometimes uses weak vocabulary or inappropriate word choice and/or lacks variety
or has problems in sentence structure; or contains an accumulation of errors in grammar, usage,
and mechanics.

**2 — Disjunctive.** Demonstrates little mastery, and is flawed by ONE OR MORE of the following
weaknesses: develops a point of view on the issue that is vague or seriously limited, and
demonstrates weak critical thinking, providing inappropriate or insufficient examples, reasons, or
other evidence [taken from the source text(s)] to support its position; is poorly organized and/or
focused, or demonstrates serious problems with coherence or progression of ideas; displays very
little facility in the use of language, using very limited vocabulary or incorrect word choice
and/or frequent problems in sentence structure; or contains errors in grammar, usage, and
mechanics so serious that meaning is somewhat obscured.

**1 — Disjunctive.** Demonstrates very little or no mastery, and is severely flawed by ONE OR MORE
of the following weaknesses: develops no viable point of view on the issue, or provides little or
no evidence to support its position; is disorganized or unfocused, resulting in a disjointed or
incoherent essay; displays fundamental errors in vocabulary and/or severe flaws in sentence
structure; or contains pervasive errors in grammar, usage, or mechanics that persistently
interfere with meaning.

## Output format

For each essay, output a JSON object with **exactly these six fields**:

```json
{
  "essay_id": "000d118",
  "evidence_notes": "one or two sentences",
  "organization": 3,
  "development": 3,
  "conventions": 3,
  "argumentation": 3
}
```

**Do not output a holistic score, a gate decision, or a gate rationale.** They are not yours to
assign — `grade_essays.py` computes all three from the four trait scores above, and it will refuse
to assemble a batch that contains them, on the grounds that their presence means the batch was
graded against an older prompt. There is also no `rationale` field: in v1–v4 the rationale explained
the holistic score, and you are no longer assigning one. Put whatever justifies your trait scores
into `evidence_notes`.

Note: the four JSON field names (`organization`, `development`, `conventions`, `argumentation`)
are kept identical to v1–v4 for pipeline continuity, even though their definitions above are
grounded in the official rubric's four dimensions (organization/coherence, evidence and support,
language, and point of view/critical thinking respectively) rather than v1/v2's proxy definitions.
See `decisions_log.md` #27 for this mapping and why it wasn't also a field-rename.

Score every essay independently on its own merits. Do not compare essays in the same batch to each other, do not let earlier essays in the batch anchor later scores, and do not adjust for where you guess the average score "should" land.
