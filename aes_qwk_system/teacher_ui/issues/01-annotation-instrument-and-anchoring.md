# 01: Annotation instrument, proven by anchoring one real essay

**What to build:** An annotation instrument that a model reads as its complete instructions for
producing student-facing feedback and evidence spans over an already-graded essay — and proof that
the spans it produces can actually be found in the essay. One essay from the frozen sample is
annotated against the instrument, and a command re-locates every quote to character offsets in the
source text and prints the resolved text back for comparison.

This ticket exists to answer the project's largest unknown before anything is built on top of it:
whether a model asked to quote student writing verbatim reproduces it faithfully enough to anchor,
given real essays contain irregular spacing, typos and odd punctuation. If the answer is no, the
instrument gets revised here rather than after an application has been built around the assumption.

The instrument is a sibling of the existing triage instrument in style and stance: it is the whole
prompt, it names its own output format, and it is validated mechanically rather than by trust.

Per decision D1, a trait with nothing citable is a finding rather than a failure. The criterion
object shape that encodes this (from the spec, adjusted by D1):

```json
"argumentation": {
  "comment": "student-facing feedback for this trait",
  "spans": [ { "quote": "verbatim text", "occurrence": 1, "polarity": "strength" } ],
  "no_evidence_reason": "required only when spans is empty"
}
```

**Blocked by:** None (can start immediately).

**Status:** ready-for-agent

- [x] An annotation instrument exists and is the annotator's complete instructions: the four traits, the criterion object shape above, `polarity` required on every span and one of strength/weakness, 1–4 spans per criterion, a minimum quote length of three words, a maximum span length, and the `no_evidence_reason` path when a trait has nothing citable
- [x] The instrument forbids emitting any score field and forbids stating a numeric score in the overview or comments, and says why
- [x] One essay from the frozen sample is annotated against the instrument and stored as a batch result keyed to the trait run it explains, not to a `ui_` version
- [x] A command re-locates every quote to character offsets in the source essay and prints, per span, the quote the annotator wrote alongside the text those offsets actually select
- [x] Matching succeeds despite whitespace differences between the quote and the source (collapsed runs, line breaks), and the resolved offsets index the original text rather than the normalised projection
- [x] A quote that does not occur in the essay, or an `occurrence` beyond the number of matches, fails loudly and names the essay and the quote
- [x] The anchoring outcome is recorded in the ticket's closing note: how many spans anchored on the first attempt, and what any failures looked like — this number sizes the risk for every later ticket

## Closing note — anchoring outcome

**14 of 14 spans anchored on the first attempt (100%)** across the one annotated essay (`0079938`,
four traits, 3–4 spans each). Verified failure and tolerance behaviour alongside it:

- A **silently corrected typo** — quoting `"building"` where the student wrote `"buliding"` — fails
  rather than anchoring somewhere plausible. This is the realistic failure mode and the one that
  matters, because a corrected quote would otherwise land a highlight on text the annotator never
  actually cited.
- An `occurrence` beyond the number of matches fails and reports how many matches exist.
- `occurrence: 2` correctly selects the second appearance of a repeated phrase.
- A quote re-wrapped with newlines and doubled spaces still anchors, and the returned offsets index
  the **original** text, not the normalised projection.
- A curly apostrophe folds to the straight one the student typed.
- Multiple bad quotes in one essay are collected and reported together, not one per run.

**Read this rate with care.** The annotation was produced in the same context that had just read the
essay, which is the best case for verbatim reproduction. A real batch run — a separate reader working
from disk over ten essays — is where the rate that matters gets measured, in ticket 07. Ticket 02's
two additional essays are the first meaningful check on whether 100% holds.
