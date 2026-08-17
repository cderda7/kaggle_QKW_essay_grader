# AES Triage Instrument v8

A **first-impression sorting read**, run as its own pass, before and independently of any trait
scoring. v8 revises v7 in two places and leaves everything else alone:

1. **Rung A0 is new** — a mechanical word-count floor, applied in code, documented here.
2. **Rung A is re-cut.** v7 defined *very bad* as **unintelligible**. That was wrong for this corpus
   and the run proved it: eight of the nine essays a human scored 1 cleared v7's rung A. v8 defines
   it as **empty**.

Rungs B1 and B2 are unchanged from v7. This file remains the entire text handed to the triage pass;
the pass still never sees `rubric_v6.md`, a trait score, or a holistic rule.

---

## Why this pass exists

`results_v6.md` §3: v6 ranks essays as well as v4 (Spearman 0.694 vs 0.680) but sits ~0.4 of a point
high, because the bottom rungs of three trait ladders clear too easily — **across 100 essays v6 never
assigns a 1 at all**, against nine in the corpus. `results_v7.md`: a triage cap recovered part of
that (0.5954 → 0.6180) and failed its own test, for one diagnosable reason given above.

**What this is not.** Not a return to holistic scoring. The label can only lower a score, never raise
one, and cannot reach above 2. Everything from 3 up is decided exactly as v6 decided it.

---

## Task given to the triage reader

You are a high school english teacher with 10 years experience. Before you mark a stack of essays
carefully, you read each one straight through once — the sorting read, the one that tells you which
ones you are going to have to talk to the student about. That read is what this task asks for.

Read the essay **once, straight through, at reading speed**. Then answer the ladder below. You are
not scoring the essay, not assigning traits, and not writing feedback.

If a prompt is not visible, infer what the essay set out to do from the essay itself and judge it
against that.

---

## The ladder

**Rung A0 runs before you and is not your job** — see the section below. Your job starts at rung A.
Ask **A** first. Only if A is NO do you ask **B**.

| | Ask | If |
|---|---|---|
| **A** | Is there **anything here you could quote back to this student as their own thinking** — a reason they actually gave, an example they actually chose, a distinction they actually drew? Or is it the prompt returned to you in different words? | **NOTHING → `very_bad`** |
| **B** | There is something. Did the **essay** do the work of connecting it to the claim, or did **you**? Answer YES if **either** B1 or B2 holds. | **YES → `bad`** |
| | *(both cleared)* | **`other`** |

**B1 — repair.** Getting to the position and its reason cost you real work: you had to go back over
a passage to recover the thread, or the connection between the reason and the claim is one you
supplied rather than one the essay made.

**B2 — assertion only.** Every reason stops where it starts. Nothing is explained, illustrated, or
applied to the claim; restating the claim in different words is assertion, not development.

`other` means *everything else* — mediocre, competent and excellent all land here alike. This pass
does not distinguish among them and must not try.

---

## Rung A, in detail — read this before judging anything

This is the rung v7 got wrong, so it gets the space.

**v7 asked: can you state the writer's position and one reason?** That defines *very bad* as
unintelligible — and the essays human raters score 1 in this corpus are **not** unintelligible. They
are intelligible and **empty**. The archetype, named exactly:

> The essay states a position, gives something **reason-shaped** — a sentence that occupies the
> grammatical position of a reason without carrying any content the writer supplied — and stops.

Every one of those clears "can you state a position and a reason?" comfortably. That is why v7 sent
eight of nine human 1s past this rung.

**So rung A now asks a possession question, not a comprehension one: is any of this thinking the
student's own?** Concretely, an essay fails rung A — is `very_bad` — when everything in it is one or
more of:

- **The prompt, returned.** The claim restated in synonyms, the question turned into a sentence.
- **Reason-shaped filler.** *"This is important because it is very important to many people."*
  *"There are many reasons why this is a good idea."* The connective is there, the content is not.
- **Assertion of the general.** *"Some people think X. Others think Y. It depends on the person."*
  Nothing chosen, nothing committed to.
- **A single idea, restated to length.** One point, three times, in different words.

An essay passes rung A on **one** genuine possession — a single reason the writer supplied, one
example they picked, one distinction they drew — even if it is poorly expressed, badly spelled, or
wrong. **Rung A is not about quality.** Something thin and clumsy still passes; something fluent and
empty does not. If it passes on exactly one such thing and nothing more, that is very often a `bad`
at rung B2, which is where it belongs.

**The test that decides hard calls:** could you write a two-sentence note back to this student that
quotes something they wrote and responds to *its content*? If everything you could quote is the
prompt or filler, the answer is `very_bad`.

---

## Rung A0 — the word-count floor (mechanical, not yours)

**Applied in code, before your read, and stated here so the instrument is complete.** You are not
asked to count words and must not try to estimate length — see the prohibition below, which still
binds every rung you *do* answer.

```
word_count < 175  ->  label `too_short`, caps the holistic score at 2
word_count < 225  ->                     caps the holistic score at 3
```

Derived on the **17,207 essays of `train.csv` that are not in the 100-essay evaluation set**, never
on the evaluation set:

| Rule | essays it touches | times it would be wrong |
|---|---|---|
| cap at 2 below 175 words | 729 | 14 — **1.92%** |
| cap at 3 below 225 words | 2,928 | 0 — **0.00%** |

The 225/cap-3 tier is free: across 2,928 held-out essays under 225 words, **not one** was scored
above 3 by a human.

**Why this is a cap and not a score.** Nothing here says a short essay is a 2. Below 175 words, 98%
of held-out essays are ≤2 but only 24% are 1s, so "short" carries no information about the 1-vs-2
distinction and the floor deliberately does not pretend otherwise — rung A does that work. And a cap
is one-directional: it never rewards length, never separates a 300-word essay from a 600-word one,
and cannot raise anything.

**This is a change of standard and is recorded as one.** Every rubric v1–v7 carries an absolute
prohibition on using length as a scoring signal. That prohibition is now **scoped**: it binds the
trait pass entirely and unchanged — the trait grader remains completely apathetic to word count and
never learns one — and it binds every reading rung in this file. What it no longer does is forbid a
code-side, one-directional, out-of-sample-derived floor at the cap layer. `decisions_log.md` #67.

---

## Decision rules

- **These are consequence questions, not presence questions.** `results_v6.md` §3's lesson, and v7's
  §3 correction to it: consequence phrasing is necessary and not sufficient — the consequence has to
  be the one the human 1/2 boundary is actually made of. Rung A asks what you could *quote back*,
  which is a possession test, because that is what separates the 1s here.

- **When you hesitate between `bad` and `other`, answer `other`.** The costs are asymmetric: the
  trait path underneath can still reach 2 on its own, so a miss loses little, while a false alarm
  breaks an essay the trait scales had right. In v7 the flags that *bound* were right only half the
  time. **This rule does not extend to rung A** — if an essay is genuinely empty, say so; v7's
  failure was under-firing there, not over-firing.

- **One read.** Rung B1 is literally about whether you had to go back. If you have re-read the essay
  three times to decide, B1 is answered.

- **Do not use length as a signal, in either direction, in any rung you answer.** [scoped as above]
  A short essay that gives one real reason of its own passes rung A. A long one that is entirely
  filler fails it. Length is handled mechanically at A0 and is not your business.

- **Surface errors alone do not decide this.** Spelling, punctuation and grammar matter here only
  insofar as they made you go back (B1). Otherwise they belong to Conventions, scored elsewhere.

- **Not your agreement, and not the shape.** Whether the position is one you hold is irrelevant. No
  credit or penalty for having an introduction, five paragraphs, a conclusion, or transition words.

- **Independently, per essay.** Do not let other essays in the batch calibrate this one. There is no
  target rate.

---

## Output format

For each essay, output a JSON object with **exactly these four fields**:

```json
{
  "essay_id": "000d118",
  "triage_label": "other",
  "deciding_rung": "B_cleared",
  "triage_note": "quotable: chooses the Vauban example and says what it shows about parking policy — not prompt restatement"
}
```

- `triage_label` — exactly one of `very_bad`, `bad`, `other`. (`too_short` is assigned by code at
  rung A0; never emit it.)
- `deciding_rung` — `A` (→ very_bad), `B1`, `B2`, `B1+B2` (→ bad), or `B_cleared` (→ other). It must
  agree with the label. This is what makes a disagreement between two triage runs diagnosable
  instead of a bare label flip.
- `triage_note` — one clause. For `very_bad`, say what you looked for and did not find. For `bad`,
  say what work you had to do. For `other`, **quote or name the thing you could give back to the
  student** — that is the evidence rung A was cleared.

**Do not output a holistic score, trait scores, a word count, a gate decision, or a `SCORES` field.**
None of them are yours to assign, and `grade_essays.py` refuses to assemble a triage batch containing
any of them.
