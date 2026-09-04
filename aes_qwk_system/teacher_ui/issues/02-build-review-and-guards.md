# 02: `build_review` and its guards, over three essays

**What to build:** The single seam this whole feature rests on — a function that takes graded
predictions, annotation batches, essay text and override records, and returns one validated review
artifact. Two further essays are annotated so it runs over three, and every guard in the spec is
enforced, each aborting the build at the command line with a message that names the essay and the
offending value rather than failing vaguely.

Override records are an **input** to this function, not a mutation applied to its output. That is
what collapses span anchoring, batch validation, the join, holistic recomputation and override
application below one testable boundary and leaves the HTTP layer with no logic worth testing. If
that boundary erodes later, the test suite loses most of its value.

Holistic values must come from the same aggregator code path that produced the original score —
imported, not reimplemented — so a recomputed score is provably the same function as the original.

This ticket also establishes the first automated test suite in this repository. The prior art for
its stance is the existing triage loader and fidelity checks: hard failure, named cause, no
partially-usable run.

**Blocked by:** 01.

**Status:** ready-for-agent

- [x] Two further essays from the frozen sample are annotated; three total
- [x] All eight guards are enforced: exact coverage against the frozen manifest, no forbidden or unknown field, every quote anchors, minimum quote length, maximum span length, 1–4 spans per criterion, criterion and polarity in range, and comments/overview present with no numeric score token in the overview
- [x] The `no_evidence_reason` path is accepted when a criterion's spans are empty, and rejected when spans are empty and no reason is given
- [x] Every guard failure names the essay and the specific offending value
- [x] The build produces one artifact holding, per essay: the response text, the four trait scores, the holistic, the overview, each trait's comment, every span resolved to offsets with its criterion and polarity, and the score-formation values
- [x] The gold score is absent from the artifact
- [x] Building twice from identical inputs produces an identical artifact
- [x] Holistic values are produced by the existing aggregator code path, not a reimplementation
- [x] A test suite exists and runs, with one test per guard asserting it fires and that its message identifies the essay
- [x] Anchoring is tested for exact matches, whitespace-irregular matches, correct selection among repeated occurrences, and offsets isolating the intended text in the original string

## Note — anchoring tests landed early

The anchoring half of this ticket's test suite was pulled forward and is already committed: 20 tests
covering exact and whitespace-irregular matches, occurrence selection, offsets indexing the original
string, typographic folding, deliberate case-strictness, the collected-failures path, and the
no-evidence path, plus an integration test that every span in every real annotation batch anchors
exactly. Mutation-tested — removing folding, returning normalised offsets, finding only the first
occurrence, or dropping whitespace collapse each makes the suite fail.

What remains for this ticket is the **guard** tests: one per guard, each asserting it fires and names
the essay. Extend the existing suite rather than starting a second one.

## Closing note

Built over three essays (`0079938`, `0105e2e`, `019e8c3`), 40 spans, **40/40 anchored first pass**.

**The artifact reproduces `predictions_v9.csv` exactly** — holistic, continuous score, band and
weighted trait mean all match for every essay, which is the check that the aggregator is imported
rather than reimplemented. Two builds of identical inputs are byte-identical. No gold score reaches
the artifact.

**64 tests**, all passing, covering one test per guard plus the artifact's observable contents.
Mutation-verified: disabling the grade-language check, the span cap, coverage, the forbidden-field
check, minimum and maximum quote length, the polarity check, build-time anchoring, or override
application each makes the suite fail (9 mutations, 9 caught).

### Two things for later tickets

**The no-evidence path (ui_8) has not been exercised by a real essay.** All three annotated essays
had citable evidence for all four traits, so the path is covered only by a test fixture. The
159-word `0105e2e` was chosen as the most likely candidate and still did not need it. Ticket 07
should note whether any of the remaining seven do — if none ever do, ui_8 is a guard against a case
that does not occur in this corpus, which is worth knowing.

**Annotator contamination, disclosed.** The human gold scores for these three essays were visible in
this session before annotation (they were printed while computing the sample distribution and the
override-sensitivity table). Annotation is not scoring, and no score in the artifact comes from the
annotator — but comment severity plausibly shifts when the annotator knows the human disagreed with
the system. This is the same class of contamination ui_4 guards against on the teacher's side, via a
route ui_4 does not cover. Ticket 07's remaining seven should be annotated without the gold scores
in context, and the write-up should say whether the first three read differently from the rest.

### Notable case for ticket 03

`0105e2e` scores traits 4/4/4/3 — a weighted mean of 3.85, the strongest of the three — and lands a
holistic of **2**, because it is 159 words. It sits 0.32 below the next band up. This is the clearest
possible demonstration of why the score-formation panel is not optional polish, and it should be the
first essay opened when the review page exists.
