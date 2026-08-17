# AES Triage Instrument v7

A **first-impression sorting read**, run as its own pass, before and independently of any trait
scoring. It exists to answer one question — *is this essay so weak that careful trait analysis will
overstate it?* — and nothing else.

This file is the **entire** text handed to the triage pass. The triage reader never sees
`rubric_v6.md`, never sees a trait score, and never assigns one. Conversely the trait grader never
sees a triage label. That separation is the point: see `rubric_v7.md` for why.

---

## Why this pass exists

`evaluation/results_v6.md` §3 established that v6 ranks essays as well as v4 does (Spearman 0.694 vs
0.680) but sits ~0.4 of a point too high, because the bottom rungs of three trait ladders are too
easy to clear. The consequence is visible in one line: **under v6 the system never assigns a 1 at
all** — its lowest holistic score across 100 essays is 2, while the corpus contains nine essays a
human rater scored 1.

Two ways to fix that. Rewrite the bottom rungs of Organization, Development and Argumentation — the
route `results_v6.md` recommended — or add a separate judgment that is *allowed* to be holistic,
whose only job is the bottom of the scale. This instrument is the second. They are not exclusive;
this one is cheaper to measure and does not touch the four scales, which means v6's gains
(56/100 identical trait vectors, inter-trait correlation down to 0.48) are carried through
structurally rather than hoped for.

**What this is not.** It is not a return to holistic scoring. It is one-directional and bounded: the
label can only lower a score, never raise one, and it can only reach as far as 2. Everything from 3
up is decided exactly as v6 decided it.

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

## The ladder — climb from the bottom, stop at the last YES

Two rungs. Ask **A** first. Only if A is YES do you ask **B**.

| | Ask | If |
|---|---|---|
| **A** | Can you state, in your own words, **what position this writer takes** *and* **at least one reason they give for it** — without supplying either one yourself? | **NO → `very_bad`** |
| **B** | Did the **essay** do the work of getting you there, or did **you**? Answer this rung YES if **either** B1 or B2 holds. | **YES → `bad`** |
| | *(both rungs cleared)* | **`other`** |

**B1 — repair.** Getting to the position and its reason cost you real work: you had to go back over
a passage to recover the thread, or the connection between the reason and the claim is one you
supplied rather than one the essay made.

**B2 — assertion only.** Every reason stops where it starts. Nothing is explained, illustrated, or
applied to the claim; restating the claim in different words is assertion, not development. An essay
can be perfectly readable and still fail this rung.

`other` means *everything else* — mediocre, competent, and excellent all land here alike. This pass
does not distinguish among them and must not try.

---

## Decision rules

- **These are consequence questions, not presence questions.** That distinction is the whole lesson
  of `results_v6.md` §3: rungs phrased as *"does the essay contain X?"* are cheap to satisfy and
  collapsed v6's floors, while Conventions — whose rungs ask what the text **costs the reader** —
  retained 22 of its 37 twos. Rung A does not ask whether a thesis is *present*; it asks whether
  **you can state one**. Rung B does not ask whether reasons are *present*; it asks who did the work.

- **When you hesitate, answer `other`.** The rungs are not symmetric in cost. This label can only
  pull a score down, and the trait path underneath can still reach 2 on its own — so a miss here
  loses nothing that was not already lost, while a false alarm actively breaks an essay that the
  trait scales had right. Fire only when the call is easy. If you find yourself building a case for
  `bad`, the answer is `other`.

- **One read.** These rungs are defined at reading speed on purpose — rung B1 is *literally* about
  whether you had to go back. If you have re-read the essay three times to decide, B1 is answered.

- **Do not use length as a signal, in either direction.** [prohibition unchanged from v1] A short
  essay that states a position and reasons it is not `bad`. A long one that never gets past assertion
  is. If you notice yourself leaning on how substantial the essay *feels*, re-ask rungs A and B on
  what you can actually state.

- **Surface errors alone do not decide this.** Spelling, punctuation and grammar matter here only
  insofar as they stopped you from stating the position and reason (rung A) or made you go back
  (B1). Otherwise they belong to Conventions, which is scored elsewhere and independently.

- **Not your agreement.** Whether the position is one you hold, whether you would have argued it
  differently, and whether the writer picked the easy side are all irrelevant.

- **Not the shape.** No credit or penalty for having (or lacking) an introduction, five paragraphs,
  a conclusion, or transition words. `rubric_v6.md`'s research basis records that the conventional
  five-paragraph shape tops out mid-scale on organization; a well-shaped essay that never states a
  reasoned position still fails rung A.

- **Independently, per essay.** Do not let other essays in the batch calibrate this one. There is no
  target rate: however many of the ten in front of you are `very_bad` is however many there are.

---

## Output format

For each essay, output a JSON object with **exactly these four fields**:

```json
{
  "essay_id": "000d118",
  "triage_label": "other",
  "deciding_rung": "B_cleared",
  "triage_note": "position (school uniforms restrict expression) and two reasons statable on one read; reasons are applied to the claim, not just asserted"
}
```

- `triage_label` — exactly one of `very_bad`, `bad`, `other`.
- `deciding_rung` — which rung decided it: `A` (failed A → very_bad), `B1`, `B2`, `B1+B2` (→ bad),
  or `B_cleared` (→ other). This is the triage analog of v6's deciding-rung note, and it exists for
  the same reason: it makes a disagreement between two triage runs diagnosable instead of a bare
  label flip.
- `triage_note` — one clause. For `very_bad` or `bad`, say what you could not state, or what work
  you had to do. For `other`, state the position and reason you were able to recover — that is the
  evidence rung A was cleared.

**Do not output a holistic score, trait scores, a gate decision, or a `SCORES` field.** None of them
are yours to assign, and `grade_essays.py` refuses to assemble a triage batch that contains any of
them.
