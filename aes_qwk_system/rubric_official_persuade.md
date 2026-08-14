# Official Holistic Scoring Rubric — PERSUADE 2.0 / Kaggle AES 2.0

**Provenance.** Kaggle's competition pages for *Learning Agency Lab — Automated Essay Scoring 2.0*
do not publish a rubric; the Data tab only states that essays were scored 1–6. The essays come from
the **PERSUADE 2.0 corpus**, and the rubric the human raters actually used is published in the
corpus repo: https://github.com/scrosseye/persuade_corpus_2.0

Two variants, matching the corpus's two task types (`task` column in PERSUADE: *Independent* vs
*Text dependent*). They are identical except that the source-based version requires evidence drawn
from the provided source text(s).

- `sat_rubric_only_indy.pdf` — independent writing
- `sat_rubric_only_source_based.pdf` — source-based writing
- `argumentation_effectiveness_rubric.pdf` — separate rubric, scores *discourse elements*
  (Ineffective / Adequate / Effective), not the 1–6 holistic score. Not the competition target.

License on the corpus: CC BY-NC-SA 4.0.

Both are SAT-style holistic rubrics. Shared preamble:

> After reading each essay and completing the analytical rating form, assign a holistic score based
> on the rubric below. For the following evaluations you will need to use a grading scale between 1
> (minimum) and 6 (maximum). As with the analytical rating form, the distance between each grade
> (e.g., 1-2, 3-4, 4-5) should be considered equal.

Note the explicit **equal-interval** assumption — that is the justification for treating the target
as ordinal-with-equal-spacing (regression + threshold rounding) rather than plain multiclass.

---

## A. Independent writing (verbatim)

**SCORE OF 6:** An essay in this category **demonstrates clear and consistent mastery**, although it
may have a few minor errors. A typical essay effectively and insightfully develops a point of view
on the issue and demonstrates outstanding critical thinking, using clearly appropriate examples,
reasons, and other evidence to support its position; the essay is well organized and clearly
focused, demonstrating clear coherence and smooth progression of ideas; the essay exhibits skillful
use of language, using a varied, accurate, and apt vocabulary and demonstrates meaningful variety in
sentence structure; the essay is free of most errors in grammar, usage, and mechanics.

**SCORE OF 5:** An essay in this category **demonstrates reasonably consistent mastery**, although
it will have occasional errors or lapses in quality. A typical essay effectively develops a point of
view on the issue and demonstrates strong critical thinking, generally using appropriate examples,
reasons, and other evidence to support its position; the essay is well organized and focused,
demonstrating coherence and progression of ideas; the essay exhibits facility in the use of
language, using appropriate vocabulary demonstrates variety in sentence structure; the essay is
generally free of most errors in grammar, usage, and mechanics.

**SCORE OF 4:** An essay in this category **demonstrates adequate mastery**, although it will have
lapses in quality. A typical essay develops a point of view on the issue and demonstrates competent
critical thinking, using adequate examples, reasons, and other evidence to support its position; the
essay is generally organized and focused, demonstrating some coherence and progression of ideas
exhibits adequate; the essay may demonstrate inconsistent facility in the use of language, using
generally appropriate vocabulary demonstrates some variety in sentence structure; the essay may have
some errors in grammar, usage, and mechanics.

**SCORE OF 3:** An essay in this category **demonstrates developing mastery**, and is marked by ONE
OR MORE of the following weaknesses: develops a point of view on the issue, demonstrating some
critical thinking, but may do so inconsistently or use inadequate examples, reasons, or other
evidence to support its position; the essay is limited in its organization or focus, or may
demonstrate some lapses in coherence or progression of ideas displays; the essay may demonstrate
facility in the use of language, but sometimes uses weak vocabulary or inappropriate word choice
and/or lacks variety or demonstrates problems in sentence structure; the essay may contain an
accumulation of errors in grammar, usage, and mechanics.

**SCORE OF 2:** An essay in this category **demonstrates little mastery**, and is flawed by ONE OR
MORE of the following weaknesses: develops a point of view on the issue that is vague or seriously
limited, and demonstrates weak critical thinking, providing inappropriate or insufficient examples,
reasons, or other evidence to support its position; the essay is poorly organized and/or focused, or
demonstrates serious problems with coherence or progression of ideas; the essay displays very little
facility in the use of language, using very limited vocabulary or incorrect word choice and/or
demonstrates frequent problems in sentence structure; the essay contains errors in grammar, usage,
and mechanics so serious that meaning is somewhat obscured.

**SCORE OF 1:** An essay in this category **demonstrates very little or no mastery**, and is
severely flawed by ONE OR MORE of the following weaknesses: develops no viable point of view on the
issue, or provides little or no evidence to support its position; the essay is disorganized or
unfocused, resulting in a disjointed or incoherent essay; the essay displays fundamental errors in
vocabulary and/or demonstrates severe flaws in sentence structure; the essay contains pervasive
errors in grammar, usage, or mechanics that persistently interfere with meaning.

---

## B. Source-based writing (verbatim)

Identical in structure; the italicized clauses below are the only substantive differences.

**SCORE OF 6:** An essay in this category **demonstrates clear and consistent mastery**, although it
may have a few minor errors. A typical essay effectively and insightfully develops a point of view
on the issue and demonstrates outstanding critical thinking; the essay uses clearly appropriate
examples, reasons, and other evidence *taken from the source text(s)* to support its position; the
essay is well organized and clearly focused, demonstrating clear coherence and smooth progression of
ideas; the essay exhibits skillful use of language, using a varied, accurate, and apt vocabulary and
demonstrates meaningful variety in sentence structure; the essay is free of most errors in grammar,
usage, and mechanics.

**SCORE OF 5:** An essay in this category **demonstrates reasonably consistent mastery**, although
it will have occasional errors or lapses in quality. A typical essay effectively develops a point of
view on the issue and demonstrates strong critical thinking; the essay generally using appropriate
examples, reasons, and other evidence *taken from the source text(s)* to support its position; the
essay is well organized and focused, demonstrating coherence and progression of ideas; the essay
exhibits facility in the use of language, using appropriate vocabulary demonstrates variety in
sentence structure; the essay is generally free of most errors in grammar, usage, and mechanics.

**SCORE OF 4:** An essay in this category **demonstrates adequate mastery**, although it will have
lapses in quality. A typical essay develops a point of view on the issue and demonstrates competent
critical thinking; the essay using adequate examples, reasons, and other evidence *taken from the
source text(s)* to support its position; the essay is generally organized and focused, demonstrating
some coherence and progression of ideas exhibits adequate; the essay may demonstrate inconsistent
facility in the use of language, using generally appropriate vocabulary demonstrates some variety in
sentence structure; the essay may have some errors in grammar, usage, and mechanics.

**SCORE OF 3:** An essay in this category **demonstrates developing mastery**, and is marked by ONE
OR MORE of the following weaknesses: develops a point of view on the issue, demonstrating some
critical thinking, but may do so inconsistently or use inadequate examples, reasons, or other
evidence *taken from the source texts* to support its position; the essay is limited in its
organization or focus, or may demonstrate some lapses in coherence or progression of ideas displays;
the essay may demonstrate facility in the use of language, but sometimes uses weak vocabulary or
inappropriate word choice and/or lacks variety or demonstrates problems in sentence structure; the
essay may contain an accumulation of errors in grammar, usage, and mechanics.

**SCORE OF 2:** An essay in this category **demonstrates little mastery**, and is flawed by ONE OR
MORE of the following weaknesses: develops a point of view on the issue that is vague or seriously
limited, and demonstrates weak critical thinking; the essay provides inappropriate or insufficient
examples, reasons, or other evidence *taken from the source text* to support its position; the essay
is poorly organized and/or focused, or demonstrates serious problems with coherence or progression
of ideas; the essay displays very little facility in the use of language, using very limited
vocabulary or incorrect word choice and/or demonstrates frequent problems in sentence structure; the
essay contains errors in grammar, usage, and mechanics so serious that meaning is somewhat obscured.

**SCORE OF 1:** An essay in this category **demonstrates very little or no mastery**, and is
severely flawed by ONE OR MORE of the following weaknesses: develops no viable point of view on the
issue, or provides little or no evidence to support its position; the essay is disorganized or
unfocused, resulting in a disjointed or incoherent essay; the essay displays fundamental errors in
vocabulary and/or demonstrates severe flaws in sentence structure; the essay contains pervasive
errors in grammar, usage, or mechanics that persistently interfere with meaning.

---

## Notes for our grading prompts

1. The rubric is **compensatory at 4–6** ("a typical essay...") but **disjunctive at 1–3** ("marked
   by ONE OR MORE of the following weaknesses"). A single severe weakness caps an essay low even if
   other dimensions are fine. Worth encoding explicitly — an LLM grader tends to average instead.
2. Four dimensions recur at every score point: (a) point of view / critical thinking, (b) evidence
   and support, (c) organization / coherence, (d) language — vocabulary, sentence variety, grammar
   and mechanics.
3. Note the sic errors in the source PDFs ("progression of ideas exhibits adequate", "the essay
   generally using"). Preserved verbatim above; clean them up if pasting into a prompt.
4. The AES 2.0 train set does not carry the PERSUADE `task` column, so we can't cleanly split
   independent vs source-based per essay. The differences are minor enough that a merged rubric
   with a conditional evidence clause is probably the right move for grading.
