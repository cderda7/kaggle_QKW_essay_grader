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

- [ ] Two further essays from the frozen sample are annotated; three total
- [ ] All eight guards are enforced: exact coverage against the frozen manifest, no forbidden or unknown field, every quote anchors, minimum quote length, maximum span length, 1–4 spans per criterion, criterion and polarity in range, and comments/overview present with no numeric score token in the overview
- [ ] The `no_evidence_reason` path is accepted when a criterion's spans are empty, and rejected when spans are empty and no reason is given
- [ ] Every guard failure names the essay and the specific offending value
- [ ] The build produces one artifact holding, per essay: the response text, the four trait scores, the holistic, the overview, each trait's comment, every span resolved to offsets with its criterion and polarity, and the score-formation values
- [ ] The gold score is absent from the artifact
- [ ] Building twice from identical inputs produces an identical artifact
- [ ] Holistic values are produced by the existing aggregator code path, not a reimplementation
- [ ] A test suite exists and runs, with one test per guard asserting it fires and that its message identifies the essay
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
