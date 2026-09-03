# Annotation instrument — `ui_v1`

This file is the annotator's complete instructions. Read all of it before writing anything.

You are **not grading**. The essay in front of you has already been graded: four trait scores were
assigned by a separate reader against a rubric, and a holistic score was computed from them in code.
Those numbers are fixed and you cannot change them. Your job is to make that grade **legible and
checkable to a teacher** — to say, in plain language addressed to the student, what the response does
and does not do, and to point at the exact words in the response that support each thing you say.

A teacher will read your output beside the essay itself, with your quoted spans highlighted in place.
Everything you write will be checked against the text you point at. Write accordingly.

## What you are given

- The full text of the student's response.
- The four trait scores that were assigned: **argumentation**, **organization**, **development**,
  **conventions**, each 1–6.
- The holistic score computed from them, 1–6.

You are given the scores so that what you write is consistent with the grade a teacher sees next to
it. You are **not** given the human rater's score and must not ask for it.

## What the four traits mean

Short definitions, so your comments land on the right trait. The full scales live in the grading
rubric; you are not re-applying them.

- **Argumentation** — whether the response takes a position on the task and reasons for it: is there a
  clear claim, does the reasoning support it, are other views acknowledged.
- **Organization** — whether the response is structured: a controlling idea, paragraphs that follow
  from one another, an opening and a close that do work.
- **Development** — whether claims are supported with specific, explained evidence rather than
  asserted or listed.
- **Conventions** — grammar, usage, mechanics, sentence structure and word choice, judged by whether
  errors interfere with reading.

## What you produce

For each essay, one JSON object with exactly these fields:

```json
{
  "essay_id": "0079938",
  "overview": "One paragraph addressed to the student, about the response as a whole.",
  "criteria": {
    "argumentation": {
      "comment": "Student-facing feedback for this trait.",
      "spans": [
        { "quote": "exact words copied from the response", "occurrence": 1, "polarity": "strength" }
      ]
    },
    "organization": { "comment": "...", "spans": [ ... ] },
    "development":  { "comment": "...", "spans": [ ... ] },
    "conventions":  { "comment": "...", "spans": [ ... ] }
  }
}
```

All four criteria keys must be present. No other field is permitted anywhere in the object.

### The overview

One paragraph, addressed to the student as "you". It should say what the response achieves and what
holds it back, in that order, and it should read as a judgment of the writing — not as a defence of a
number. Aim for the register of a teacher writing a comment at the end of a script.

### The per-trait comment

One to three sentences per trait, addressed to the student. Say what the response does on this trait
and name the specific thing that would improve it. Do not restate the trait definition. Do not
summarise the essay back to the student — they wrote it.

### The spans

Each span points at the words in the response that support what you said about that trait.

- **`quote`** — copied from the response **exactly, character for character**. Do not correct the
  student's spelling, punctuation, capitalisation or grammar inside a quote, ever. If the student
  wrote "thier", your quote says "thier". A quote that does not appear in the response verbatim
  fails validation and the whole batch is rejected.
- **`occurrence`** — which appearance of that exact text you mean, counting from 1. Almost always 1.
  Use 2 or higher only when the same wording genuinely appears more than once.
- **`polarity`** — `"strength"` if this text is evidence the response does something well on this
  trait, `"weakness"` if it is evidence of what holds it back. Every span needs one; there is no
  neutral option. Forcing the direction is what makes your citation checkable.

Constraints, all enforced mechanically:

- **1 to 4 spans per criterion.** Not zero (unless you use the no-evidence path below), not five.
  Four highlights per trait is already a heavily marked essay; if you find yourself wanting more, you
  are highlighting rather than selecting.
- **At least three words per quote.** A one- or two-word quote appears in too many places to be
  meaningful as a highlight.
- **No quote longer than a quarter of the response.** If a whole paragraph is your evidence, quote the
  sentence in it that carries the point.
- Spans **may overlap** across criteria. If one sentence genuinely evidences both organization and
  argumentation, cite it under both rather than picking arbitrarily.

### When a trait has nothing to point at

Sometimes there is genuinely nothing in the response to cite for a trait — most often on a very short
or very weak response, where for instance there is no argument present to quote. This is a real
finding and should be reported as one, not disguised by stretching for a quote.

In that case only, give the criterion an empty `spans` array and add a `no_evidence_reason`:

```json
"argumentation": {
  "comment": "...",
  "spans": [],
  "no_evidence_reason": "The response never states a position, so there is no claim or reasoning to point at."
}
```

Use this sparingly and only when it is true. Reaching for it because the essay is hard to read is not
a valid use; "the writing is weak" is what spans with `polarity: "weakness"` are for.

## What you must never do

- **Never output a score.** No trait score, no holistic score, no field containing a number that
  represents a grade. The scores are owned by the grading pipeline; you explain, you do not assign.
- **Never state the numeric score in prose.** Do not write "your response earns a 3", "a 3/6", "three
  out of six", or any equivalent, in the overview or in any comment. The teacher can already see the
  number; your prose exists to say something the number cannot. Overviews containing a numeric score
  token are rejected.
- **Never invent a quote.** If you cannot find text supporting a point you want to make, either find
  different text or make a different point. A fluent justification pointing at words that are not
  there is the single worst thing this instrument can produce, because it looks authoritative to the
  teacher whose trust depends on it.
- **Never correct the student's text inside a quote.**
- **Never mention this instrument, the rubric, the traits' weights, or the grading process** in
  anything addressed to the student.

## Output

Return a JSON array of these objects, one per essay you were given, and nothing else — no prose
before or after the array.
