# AES Grading Rubric v4

Scale: **1 (lowest) to 6 (highest)**, matching the official PERSUADE / Learning Agency Lab AES 2.0 scale.

> **v4 is v3 with the trait weighting made explicit and unequal.** Every rule below is v3's, with
> two changes, both marked **[v4]** where they appear: the compensatory bands test *weight mass*
> rather than a head count of traits, and the gate's four-trait average becomes a *weighted* mean.
> Nothing else about the process, the anchors, or the output schema differs from `rubric_v3.md`.

> **Provenance note — v4 was derived, not graded.** v1–v3 were each produced by re-grading all 100
> essays. v4 was not. A weight change only affects how the four trait scores aggregate into a
> holistic score, so v4's scores were recomputed from v3's trait scores by
> `grade_essays.py --derive --version v4`, leaving every trait score untouched. That recompute is
> gated on a fidelity check: running the same code with equal weights reproduces all 100 of v3's
> graded holistic scores and `gate_applied` values exactly, so the aggregation is provably
> mechanical and the entire v3→v4 diff is attributable to the weights. **This file therefore
> documents the aggregation rule in force for v4, but was never handed to a grader.** If a future
> version re-grades against it, that is a new run and should be versioned as such. See
> `decisions_log.md` #43–49.

## Trait weights [v4]

| Trait | Official rubric dimension | Weight |
|---|---|---|
| Argumentation | point of view and critical thinking | **0.35** |
| Organization | organization / coherence | 0.25 |
| Development | evidence and support | 0.25 |
| Conventions | language | **0.15** |

v1–v3 weighted these equally at 0.25 each without ever saying so — the gate fires on *any* trait,
and the compensatory bands ask "are at least 3 of the 4 traits at/above X," both of which treat the
four traits as interchangeable. v4 states the weighting and makes it unequal: argumentation is the
dimension the score should turn on most, conventions the least.

> **Provenance note (superseding v1/v2's):** v1 and v2 used a *reconstructed proxy* rubric because
> the real one couldn't be fetched in this environment. `rubric_official_persuade.md` (found
> already present in this project folder) has since resolved that — it's the verbatim **official
> PERSUADE 2.0 scoring rubric**, sourced from the corpus repo
> (https://github.com/scrosseye/persuade_corpus_2.0), covering both task variants (Independent /
> Source-based writing, which are identical apart from an evidence-from-source clause). This
> version's process and score-band anchors are grounded directly in that verbatim text — see
> `decisions_log.md` #27 for exactly what changed as a result and how the two task variants were
> merged into one rubric.

## Task given to the grader

You are a high school english teacher with 10 years experience. You are grading your students' assignments by determining the extent to which they align with your standards, as outlined on the provided rubric. You are scoring a student argumentative/source-based essay written in response to a prompt. The prompt may not be visible to you. If no prompt is available, generate a hypothesis prompt so that you may grade the essay against what it set out to do. If the essay draws on a provided source text or texts, evidence should be evaluated against how well it's drawn from those sources; if it doesn't (an independent-writing prompt), evaluate evidence and reasoning on their own merits. Then, score the essay on its own internal merits: point of view and critical thinking, use of evidence/support, organization/coherence, and use of language.

## Required process (in this order — do not skip steps or jump straight to a holistic number)

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

6. **Severe-weakness gate (disjunctive check — do this before assigning a holistic score).**
   The official rubric's own score-of-1/2/3 language is explicit about this: scores of 1, 2, and 3
   are each defined as "flawed/marked by **ONE OR MORE** of the following weaknesses" across the
   four dimensions above — meaning a single severe weakness in any one dimension is sufficient to
   place the whole essay in that band, regardless of how the other three dimensions look. Scores
   of 4–6, by contrast, describe "a typical essay" jointly clearing multiple dimensions at once —
   nothing in the official language suggests averaging a weak dimension against strong ones.

   Look at the four trait scores from steps 2–5. A trait score of **1 or 2** counts as a *severe
   weakness* in that trait — this is just checking the numbers you already assigned, not a new
   judgment.

   - **If none of the four traits scored ≤2:** no severe weakness — proceed to step 7 and place
     the essay in the 3–6 band.
   - **If one or more traits scored ≤2:** the essay is gated into the **1–3 band**, regardless of
     how strong its other traits are. Placement within the band:
     - **Two or more** traits scored **1** → holistic score is **1**, no matter what the other
       traits are. Multiple severe failures overrides everything else.
     - **Exactly one** trait scored **1** → compute the **weighted average** of all four trait
       scores **[v4]** — that is, `0.25·organization + 0.25·development + 0.15·conventions +
       0.35·argumentation`, rather than the plain average v3 used.
       - If that weighted average is **below 2** → holistic score is **1**.
       - Otherwise → holistic score is that **weighted average, rounded to the nearest whole
         number** (round .5 up), capped at **3** since this essay is still gated into the 1–3 band.
         This lets one severe weakness alongside otherwise-solid traits land higher than a flat 1,
         without escaping the band entirely.
     - **Two or more** traits scored **2** (and none scored 1) → holistic score is **2**, full
       stop. Do not drift up to 3 because "only two traits were bad."
     - Exactly **one** trait scored **2** (nothing lower, nothing else ≤2) → holistic score is
       **2 or 3**. v3 left this to grader discretion; v4 resolves it with the same weighted
       average, rounded half up and clamped to the 2–3 range **[v4]**. This is a formalisation
       rather than a change of standard — it reproduces what v3's graders actually did on all 17
       such essays under both weightings (`decisions_log.md` #47).
   - **The gate trigger itself is deliberately unweighted.** *Any* trait at ≤2 gates the essay,
     including conventions at its 0.15 weight. Weights govern how traits *aggregate*; they do not
     govern whether a severe weakness counts as severe. The official rubric's 1/2/3 language is
     disjunctive — "flawed by ONE OR MORE of the following weaknesses" — and it draws no
     distinction between which dimension the weakness falls in. Same reasoning applies to the
     "two or more traits at 1 → 1" and "two or more traits at ≤2 → 2" rules above, which count
     severe failures rather than weighing them.
   - This gate takes priority over step 7. If the gate triggers, the holistic score comes from
     this step, not step 7.

7. **Holistic score (1–6) — compensatory placement, only reached if step 6 found no severe
   weakness.** The official rubric's 3–6 descriptions each open with "a typical essay... [does
   several things at once]" — jointly meeting multiple dimension criteria, not averaging a couple
   of strong traits against a couple of middling ones.

   **[v4] The threshold test is weight mass, not a head count.** v3 asked "are at least 3 of the 4
   traits at/above X." v4 asks "do the traits at/above X carry at least **0.75** of the total
   weight." Under equal weights these are the same question — 3 of 4 equally-weighted traits carry
   exactly 0.75 — so this is a strict generalisation of v3's rule, not a new one. Under v4's
   weights, one trait subset behaves differently: {organization, development, conventions} carries
   0.65 and no longer clears the bar. That is the intended effect. An essay whose only weak
   dimension is argumentation no longer reaches the higher band on the strength of the other three.

   Concretely, where *mass(X)* is the summed weight of the traits scoring at/above X:
   - **3** — no severe weakness by the gate, and the essay fails the bar for 4. (This is the
     compensatory floor: clearing the gate guarantees at least a 3.)
   - **4** — *mass(4)* ≥ 0.75, and no trait is below 3.
   - **5** — *mass(5)* ≥ 0.75, and no trait is below 4.
   - **6** — all 4 traits are ≥5, and at least 2 of the 4 are 6. **Unweighted by design**: this
     band requires every trait to clear the bar, so there is no subset for a weight to select
     between.
   - The "none is below 3 / below 4" floors are likewise unweighted membership tests — a trait
     below the floor blocks the band no matter how little weight it carries.
   - If neither threshold is met (traits middling across the board with no subset clearing a level
     by weight), default to the lower of the two adjacent scores rather than rounding up.

   This is your single overall judgment of essay quality, synthesizing the traits above under the
   rule that governs the band you landed in (steps 6–7) — not a free-floating impression, and not
   a simple average of the four trait scores.

## Explicit anti-verbosity-bias instruction

**Do not use essay length as a scoring signal, in either direction.** A concise, well-argued essay
should score as well as or better than a long, repetitive, or padded one making the same points.
Conversely, do not penalize a short essay for being short if its argument is complete and precise.
If you notice yourself inclined to raise or lower a score primarily because an essay "feels
substantial" or "feels thin" due to its length, stop and re-ground the score in the Organization /
Development / Conventions / Point-of-View judgments above instead.

## Score-band anchors — verbatim official rubric (merged Independent + Source-based variants)

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

For each essay, output a JSON object:

```json
{
  "essay_id": "000d118",
  "evidence_notes": "one or two sentences",
  "organization": 3,
  "development": 3,
  "conventions": 3,
  "argumentation": 3,
  "gate_applied": "disjunctive",
  "gate_rationale": "one sentence: which trait(s), if any, triggered the severe-weakness gate, or 'none' if the essay reached the compensatory band",
  "holistic_score": 3,
  "rationale": "one sentence explaining the holistic score, referencing the traits and the gate outcome above, not length"
}
```

Note: the four JSON field names (`organization`, `development`, `conventions`, `argumentation`)
are kept identical to v1/v2 for pipeline continuity, even though their definitions above are now
grounded in the official rubric's four dimensions (organization/coherence, evidence and support,
language, and point of view/critical thinking respectively) rather than v1/v2's proxy definitions.
See `decisions_log.md` #27 for this mapping and why it wasn't also a field-rename.

**[v4] The output schema is unchanged from v3.** The weights change how a holistic score is
computed from the four traits, not what a grader reports. Because v4 was derived rather than
graded, its per-essay results live only in `grading/predictions_v4.csv`, which adds two audit
columns — `system_weighted_mean` and `system_decisive_mass` — recording the quantity each essay's
band decision actually turned on. `system_decisive_mass` is blank for gated essays and for band-6
essays, since both are decided by counting rules where no mass was consulted.

Score every essay independently on its own merits. Do not compare essays in the same batch to each other, do not let earlier essays in the batch anchor later scores, and do not adjust for where you guess the average score "should" land.
