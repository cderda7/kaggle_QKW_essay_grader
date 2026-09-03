# Teacher Review UI — `ui_v1` spec

Status: ready to build. Written 2026-09-03, from the `/grill-me` session that settled it (21 questions,
3 rounds). This is the first entry in a **new version ladder** — `ui_v1`, `ui_v2`, … — deliberately
separate from the `v1`–`v9` QWK ladder. QWK versions answer *was the number right*; `ui_` versions
answer *is the stated reasoning right, and can a teacher correct it*.

Supersedes `../planning/teacher_override_ui_handoff.md`, which describes a different design
(override → few-shot steering as the primary feature). That handoff's Open Question 1 is resolved
here in favour of trait-level override; its few-shot bank is explicitly out of scope for `ui_v1`.

---

## Problem Statement

The grading system produces a number and nothing a human can check. For each essay it emits four
trait scores and a single `evidence_notes` blob of marker's shorthand — *"org 3 (controlling idea
buried mid-essay, closing stops rather than closes)"* — and then `aggregator_v9.json` turns those
four integers plus the essay's word count into a 1–6 holistic score. A teacher handed that output
faces three problems at once:

1. **They cannot see where a judgment came from.** `evidence_notes` asserts that the controlling
   idea is buried mid-essay. Which sentences? A teacher who wants to verify that claim has to
   re-read the entire essay hunting for what the model was looking at. The evidence exists only in
   the model's head and is unrecoverable after the run.

2. **They cannot give it to a student.** `evidence_notes` is written for whoever is auditing the
   pipeline. It is compressed, it names ladder rungs, and it is addressed to nobody. Turning a
   grading run into student feedback is currently a manual rewrite of every essay.

3. **They cannot disagree with it in any way the system records.** There is no override path at
   all. A teacher who thinks the model got Conventions wrong has a CSV they could hand-edit, which
   destroys the run's provenance and teaches the system nothing.

Underneath all three sits a fourth problem the current output actively hides:
`corr(word_count, system_score) = 0.820` against the human raters' 0.688. A third of the holistic
score is essay length. A teacher shown four trait scores and a `4/6` will reasonably conclude the
four traits produced the 4. They did not.

## Solution

A local, single-user web app that renders each AI-graded essay as a **review surface**: the student's
full response on the left with the exact spans the model used highlighted in place, and on the right
the score, an overview paragraph, and one card per rubric trait containing student-facing feedback —
each card colour-matched to its highlights, so every claim in the feedback is one glance away from
the text that produced it.

The teacher reads it, disagrees where they disagree, and corrects it: trait scores are editable and
the holistic recomputes through the existing frozen aggregator; individual highlights can be rejected
as unsupported; feedback text can be edited. Every correction is written to an append-only audit
record carrying what the AI said, what the teacher said, why, and which model versions were active.

Making this possible requires the pipeline to keep track of where information came from during
grading, which it currently does not. That is added as a **separate annotation pass** over frozen
trait scores — a second read that produces spans and prose but touches no score, in the same way v7
and v8 added a triage pass alongside the trait pass. See `../decisions_log.md` #78.

---

## User Stories

**Reviewing a grade**

1. As a teacher, I want to see the student's full response and the AI's assessment side by side, so that I can check the assessment against the text without switching context.
2. As a teacher, I want each trait's feedback in its own card, so that I can evaluate the AI's judgment one trait at a time rather than as a single verdict.
3. As a teacher, I want the exact words the AI relied on highlighted in the response, so that I can verify a claim instead of taking it on trust.
4. As a teacher, I want each highlight coloured to match the trait card it belongs to, so that I can tell at a glance which judgment a piece of text supports.
5. As a teacher, I want to know whether a highlight was cited as a strength or a weakness, so that I can tell whether the AI read a passage the way I do.
6. As a teacher, I want hovering a trait card to emphasise its own highlights and mute the others, so that I can isolate one line of reasoning in a densely marked essay.
7. As a teacher, I want hovering a highlight to surface which trait cited it, so that I can work from the text back to the judgment as well as forwards.
8. As a teacher, I want an overview paragraph summarising the response as a whole, so that I get the shape of the assessment before reading four separate cards.
9. As a teacher, I want each trait card to show that trait's own 1–6 score, so that I can see the numbers the AI actually produced rather than only the derived total.
10. As a teacher, I want the trait cards ordered by their weight in the final score, so that the trait that matters most is the one I read first.
11. As a teacher, I want the holistic score displayed as `N/6` in the same prominent position as a marker's total, so that the artefact reads like a marked script.
12. As a teacher, I want the essay's prompt or instructions shown above the response, so that I can judge relevance to the task and not just quality in the abstract.
13. As a teacher, I want long instructions collapsed by default with a way to expand them, so that the response stays the focus of the page.

**Understanding how the score was formed**

14. As a teacher, I want a way to see how the holistic score was computed from the traits, so that I am not asked to trust a number whose derivation is hidden.
15. As a teacher, I want to see the weighted trait mean, the word-count term, the continuous score and the band it fell into, so that I can locate exactly which step I disagree with.
16. As a teacher, I want to see how close the score was to the next band boundary, so that I know whether a small trait correction could move it.
17. As a teacher, I want the length contribution stated explicitly, so that I am not misled into thinking four trait cards explain a score that essay length substantially drove.
18. As a teacher, I want that panel collapsed by default, so that the everyday reading experience stays clean and the derivation is there when I want it.

**Correcting a grade**

19. As a teacher, I want to change any trait score, so that I can record a disagreement with the AI's actual judgment rather than with its arithmetic.
20. As a teacher, I want the holistic score to recompute immediately when I change a trait, so that I can see the consequence of my correction.
21. As a teacher, I want to see the before and after holistic score together, so that the effect of my correction is explicit.
22. As a teacher, I want to be told when my trait correction does **not** move the holistic score, so that I do not conclude the app is broken when the aggregator's cut points absorb the change.
23. As a teacher, I want to record that I disagree with the final score even when I agree with the traits, so that a disagreement the aggregator caused is captured as such and not laundered into a fake trait correction.
24. As a teacher, I want to write a short rationale for any correction, so that a later reader knows why I disagreed and not merely that I did.
25. As a teacher, I want to reject an individual highlight as unsupported, so that a hallucinated or misplaced citation is recorded as a specific defect.
26. As a teacher, I want to edit a trait's feedback text, so that I can fix wording that is wrong or unhelpful without discarding the assessment.
27. As a teacher, I want to edit the overview paragraph, so that the whole-response summary can be corrected too.
28. As a teacher, I want my span, feedback and score corrections stored separately from one another, so that "the AI scored it wrong" and "the AI explained it badly" stay distinguishable.
29. As a teacher, I want to change my mind and correct the same essay again, so that a first pass does not lock me in.
30. As a teacher, I want earlier corrections preserved rather than overwritten, so that the history of my own judgment is auditable alongside the AI's.
31. As a teacher, I want to see at a glance which essays I have already reviewed, so that I can work through a set without losing my place.
32. As a teacher, I want to clear a correction and return to the AI's original, so that a mistaken edit is recoverable.

**Blindness and integrity**

33. As a teacher, I want the human rater's gold score hidden by default, so that my own judgment is formed independently rather than anchored to the answer key.
34. As a teacher, I want to reveal the gold score deliberately when I want to compare, so that the tool supports research use after I have committed to a view.
35. As a researcher, I want any override recorded after the gold score was revealed to be flagged as such, so that anchored corrections can be excluded from anything that later steers the model.
36. As a researcher, I want every override record to carry the trait-run and aggregator version active when it was made, so that a correction against `v6_runB` traits is never silently reused against different ones.
37. As a researcher, I want a highlight that cannot be located in the essay to fail the build loudly, so that a misplaced highlight never reaches a teacher looking authoritative.
38. As a researcher, I want the annotation pass to be unable to emit a score, so that the artefact cannot carry a second, divergent copy of a number the aggregator owns.
39. As a researcher, I want the annotation pass to be forbidden from stating the numeric score in prose, so that the overview reads as a judgment rather than as a defence of a number already on screen.
40. As a researcher, I want the essay sample frozen to a committed manifest, so that re-running never silently annotates a different ten essays.

**Operating it**

41. As a researcher, I want to start the app with one command against local files, so that reviewing does not require standing up infrastructure.
42. As a researcher, I want a list page of all reviewable essays with their scores and review status, so that I can pick where to work.
43. As a researcher, I want the review artefact built and validated by a batch step before the server ever runs, so that a broken annotation batch is caught at the command line with an explanation rather than in a browser.
44. As a researcher, I want the built artefact to be a single inspectable file, so that I can diff and grep it like every other artefact in this project.
45. As a researcher, I want overrides stored in a diffable text file under version control, so that the history of corrections is visible in `git diff`.
46. As a researcher, I want the span acceptance rate computable from the override records, so that `ui_v2` has something concrete to improve on even though this ladder carries no headline metric.

---

## Implementation Decisions

### The annotation pass is additive and changes no score

Recorded in full as `../decisions_log.md` #78. The trait instrument (`rubric_v6.md`) and the trait
scores it produced (`v6_runB`) are frozen. Everything this feature needs — spans, per-trait
student-facing comments, the overview — comes from a **second pass** over the same essays, joined at
build time. Structurally identical to how v7 and v8 added a triage pass, and how v4 and v9 changed
aggregation with trait scores carried through untouched.

Consequences accepted: annotating a corpus costs a second full pass, and the annotator is shown a
score it did not assign, so its prose is post-hoc justification rather than independent judgment. The
mitigation is that its claims must be anchored to locatable text, so an unsupported justification
fails mechanically rather than reading as fluent.

### The annotation pass runs after derivation and sees the scores

Ordering is `assemble/derive → annotate → build-review`. The annotator is given the essay text, the
four trait scores, and the final holistic. It needs the holistic because the overview sits next to
that number on screen, and an overview written blind to it will contradict it. It is nonetheless
**forbidden from emitting any score field and from stating a numeric score in prose** — the
aggregator owns the number; the annotator explains the response.

### Annotation output schema

Per essay, exactly these fields — the schema is closed, and any additional field fails the batch:

```json
{
  "essay_id": "000d118",
  "overview": "one paragraph addressed to the student",
  "criteria": {
    "argumentation": {
      "comment": "student-facing feedback for this trait",
      "spans": [
        {
          "quote": "verbatim text copied exactly from the response",
          "occurrence": 1,
          "polarity": "strength"
        }
      ]
    },
    "organization": { "comment": "...", "spans": [ ... ] },
    "development":  { "comment": "...", "spans": [ ... ] },
    "conventions":  { "comment": "...", "spans": [ ... ] }
  }
}
```

`polarity` is one of `strength` | `weakness` and is **required** on every span — forcing the
direction is what makes a highlight reviewable. There is no neutral option.

### Spans anchor by verbatim quote, never by offset

The annotator emits the quoted text plus which occurrence of it it means; `build_review` re-locates
it to character offsets. Models cannot count characters, and a model-emitted offset that is silently
wrong is the worst failure mode available here, because a misplaced highlight looks authoritative.

Anchoring runs on a whitespace-normalised projection of both the essay and the quote (runs of
whitespace collapsed to a single space), with an index map back to original offsets, because student
text contains irregular spacing and line breaks that a model will not reproduce faithfully when
quoting.

### Anchoring and batch guards — all hard errors

`load_annotation()` takes the stance `load_triage()` already takes: a partially-usable annotation
pass is not a thing, so every one of these aborts the build with an explanation naming the essay and
the offending value.

1. **Coverage is exact** against the frozen essay manifest — every expected essay present, nothing
   extra, nothing graded twice.
2. **No forbidden field.** Trait scores, `holistic_score`, any gold/human score, `SCORES`, or any
   field not in the schema above. The annotator is *shown* the scores and must not *emit* them.
3. **Every quote anchors.** Zero matches in the normalised essay fails. An `occurrence` higher than
   the number of matches fails.
4. **Minimum quote length** of three words. A one- or two-word quote matches in many places, carries
   no information as a highlight, and makes `occurrence` load-bearing in a way no annotator will get
   right.
5. **Maximum span length** of 25% of the essay. An annotator permitted to highlight a whole paragraph
   will, and a mostly-highlighted essay conveys nothing.
6. **Span count per criterion is 1–4.** At least one, because a trait card with no evidence behind it
   is exactly the defect this feature exists to expose. At most four, because uncapped highlighting
   converges on highlighting everything.
7. **`polarity` and criterion key are in range.**
8. **`comment` and `overview` are present and non-empty**, and the overview contains no numeric score
   token (a bare digit 1–6, `/6`, `out of six`, and similar), enforcing the no-restating-the-number
   rule mechanically rather than by instruction.

### Overlapping spans are permitted

Two traits can legitimately cite the same sentence, and forcing the annotator to pick one makes an
arbitrary choice that is invisible to the teacher. Rendering resolves overlap by painting the
outermost span's fill and marking the nested one, rather than by striping — striped multi-colour text
is unreadable at body size.

### Highlight visual encoding

Colour encodes **criterion**, matching the trait card headers — four hues, one per trait. Polarity is
a **second, orthogonal channel**: solid fill for a strength, dotted underline for a weakness. Two
channels rather than eight colours, because eight low-saturation hues are not reliably
distinguishable as text backgrounds and the polarity distinction must survive whatever hue it lands
on. Palette constraint: all four hues must keep body text at accessible contrast as a background,
must remain distinguishable from one another at the low saturation the mock uses, and must not rely
on hue alone to carry meaning — the polarity channel plus card-hover emphasis provide the
non-colour redundancy.

### Four trait cards, showing their own scores, ordered by weight

Argumentation (0.35), Organization (0.25), Development (0.25), Conventions (0.15). The reference mock
shows no per-criterion mark because in the rubric it came from the criteria carry no separate marks;
in PERSUADE the trait scores *are* the AI's actual output, and hiding them would mean a teacher
reviews prose while the numbers driving everything stay invisible. Weight order rather than
alphabetical, so the trait with the largest influence is read first.

### The score-formation panel

Collapsed by default, preserving the mock's clean reading experience. Expanded, it shows the weighted
trait mean, `log₁₀(word_count)` and the raw word count, the continuous score `s`, the band `s` fell
into, and the distance to the nearest cut point. Every one of these values already exists per essay
in `predictions_v9.csv` (`system_weighted_mean`, `system_log10_wc`, `word_count`,
`system_continuous_score`, `system_band`) plus the cuts in `aggregator_v9.json` — the panel is a
presentation of stored values, not a recomputation.

This is the project's answer to its own most prominent open problem. `corr(word_count, system_score)`
is 0.820 against the human raters' 0.688, and `results_v9.md` §4–5 names constraining that coupling
as v10's first job. Presenting a holistic score in a review tool without its derivation would be the
first place in the project where a number appears without an audit trail.

### Override model

The teacher overrides **trait scores**. The holistic recomputes by calling the existing frozen
aggregator — the same `apply_aggregator` path used to produce the score in the first place, with the
same coefficients and cut points, never re-fit. A recomputation that lands on the same holistic is
shown as such explicitly, because a silent no-op reads as a broken control.

Direct holistic override is **not** offered. It cannot steer anything (the aggregator is three fitted
coefficients, not a promptable model), and it silently decouples the displayed score from the
evidence displayed beside it. Instead there is a distinct **score dissent flag**: a teacher can record
"I disagree with the final score but not with the traits", with a rationale and no number. That is
information about the aggregator, and it is stored as such rather than being disguised as a trait
correction.

Span verdicts (accept / reject-as-unsupported) and feedback-text edits are stored in their own
sections of the record, separate from score overrides — they are evidence about annotation quality,
not about scoring, and conflating them would make both unusable.

### Override storage

Append-only `overrides.json`: one record per correction event, never mutated in place, with the UI
reading the latest record per essay as current state. A teacher who changes their mind twice leaves a
trail. JSON rather than SQLite because this is a single local user over ten essays, and the file needs
to be diffable and greppable like every other artefact here — SQLite would buy concurrency and
indexing with no use for either, and would make the override history invisible to `git diff`.

Each record carries: essay id, timestamp, original trait scores and holistic, corrected trait scores,
recomputed holistic, span verdicts, feedback edits, rationale, `gold_revealed`, and the trait-run and
aggregator versions active. That last pair is what stops a correction made against `v6_runB` traits
from being silently reused against different ones.

### Gold score handling

The reviewable essays come from `personal_training_set.csv`, which contains the human rater's score.
It is **withheld from the review surface by default** and revealed only by a deliberate action, which
stamps the essay's subsequent override records `gold_revealed: true`.

This is a leakage control, not a UI preference. Overrides are intended to feed a few-shot bank later
(out of scope here, but the storage shape anticipates it), and an override anchored to the answer key
would launder gold labels into the grading prompt through a door the existing `SCORES` annotation
manifest and `--strip-scores` guards do not watch. The flag keeps anchored corrections identifiable
and excludable rather than banning comparison outright.

### Essay sample

Ten essays, drawn uniformly at random from the training 100 with a fixed, recorded seed, and frozen
to a committed manifest that also records the seed and the source run. Re-running reads the manifest;
it never re-draws. This mirrors `batches.json`, reused across every version so runs stay
essay-for-essay comparable.

**The draw has been made** (seed 20260903, frozen to `essays_ui_v1.json`) and its actual shape matters
more than the prediction that preceded it:

| human score | 1 | 2 | 3 | 4 | 5 | 6 |
|---|---|---|---|---|---|---|
| essays in sample | 1 | 5 | 3 | 1 | 0 | 0 |

Word counts run 159–507. So the sample is **bottom-heavy**, not centre-heavy: median human score 2,
nothing above 4. That is better than expected at the bottom — it includes one of the corpus's nine
score-1 essays, the band the system has historically failed hardest on — and empty at the top, so
nothing learned here describes how annotation reads on a strong essay. It also means the length range
is narrow and low, which limits what these ten can show about the word-count coupling the
score-formation panel exists to expose.

Accepted as-is for `ui_v1`, whose job is to get the surface built and looked at. Stratification is the
right move at the next scale-up, and the gap to close first is the 5–6 end.

### Build step, not request-time join

`--build-review` joins predictions, annotation batches, essay text and override records into a single
validated artefact that the server reads. Validation belongs in a batch step that can hard-fail with
an explanation, not in a request handler that has to render something. This is the same shape as the
existing `--assemble` / `--derive` / `--fit` commands.

Critically, **override records are an input to the build**, not a mutation applied downstream. The
artefact therefore represents review state *given* annotation and corrections, which collapses what
would otherwise be a second seam (override application) into the first.

### Application architecture

FastAPI serving a server-rendered page plus a small vanilla-JS layer; no Node toolchain, no SPA
framework. The interaction the design needs — hover a card, emphasise its spans; hover a span,
surface its card — is DOM attribute work over elements the server already emitted, not state
management. One language, one process, one command to run.

The HTTP surface is deliberately thin: read the built artefact; append an override record and rebuild.
Endpoints cover the essay list, a review page, the review JSON for an essay, override submission, and
gold-score reveal. No authentication, no multi-user concerns — this is a local single-user tool, as
established.

### Versioning and logging

This is `ui_v1` on its own ladder, with its own `decisions_log.md` and `tracker_log.json` under
`teacher_ui/`. Version identifiers carry the `ui_` prefix in filenames and commit messages, because
bare `v1` already means the original rubric and always will. Annotation output is keyed to the trait
run it explains (`annotation_v6_runB/`) rather than to a `ui_` version, because that annotation
belongs to trait scores which v7, v8 and v9 all share.

`../decisions_log.md` #78 stays in the QWK log rather than moving here: it is a decision about the
grading pipeline, and a reader checking why v9's numbers survive this feature needs to find it there.
It is cross-referenced from the new log.

Per-project convention, `ui_` commit messages **drop the metric segment** —
`<label> ; Delta: … ; rationale: …`. Span acceptance rate is computed and reported in the results
write-up regardless, so it is available if a later version wants it promoted to the headline.

---

## Testing Decisions

### What a good test looks like here

A good test in this feature asserts on **what a teacher or a downstream reader would observe** — the
built artefact's contents, whether a malformed batch is rejected and with what explanation, what the
holistic becomes after a trait correction — and never on how the join is implemented, what helper
functions exist, or the shape of intermediate state. Anchoring tests in particular should assert
*which text ends up highlighted*, not what the index map contains.

Fixtures are small hand-written essays and annotation batches, not copies of the real corpus, so that
a test naming a failure names it precisely and a rubric change does not break the suite.

### Prior art — and its absence

**This repository currently has no automated tests at all.** There is no `tests/` directory and no
`test_*.py` anywhere. What it has instead is a strong tradition of *in-pipeline validators that
hard-fail*, and those are the real prior art for the guards specified above:

- `load_triage()` — validates label range, rung/label agreement, forbidden fields, and exact
  coverage; every one a hard error, on the stated grounds that a partially-usable triage pass does
  not exist. `load_annotation()` should read as a sibling of this function.
- `check_v4_fidelity()` and the fidelity check in `derive_v7` — refuse to derive unless the same code
  reproduces the prior version's scores exactly, so a measured effect is never partly a bug.
- `cross_check_predictions()` and the `SCORES` annotation manifest — detect provenance divergence
  between two artefacts that should agree, and abort on unaccounted-for fields.
- `derive_v9`'s refusal to run against an aggregator whose feature list or `n` disagrees with config.

`ui_v1` should follow that tradition **and** establish the first genuine test suite, since the
standing project instruction is to write tests where none exist for the changed behaviour. The
guards live in the build step where they belong; the tests assert that each guard actually fires.

### What gets tested

Everything of consequence sits below the single seam, so the suite is aimed almost entirely at
`build_review` and the loader it calls:

- **Anchoring.** Exact match; whitespace-normalised match against irregular spacing and line breaks;
  correct selection among repeated occurrences; the returned offsets isolating the intended text in
  the original string.
- **Every guard rejects.** One test per guard in the list above, each asserting the build fails *and*
  that the message names the essay and the offending value. A guard that fires silently or fires with
  an unhelpful message is a defect.
- **The valid path.** A well-formed batch produces an artefact whose spans, comments, overview, trait
  scores, holistic and score-formation values are all present and correct.
- **Override behaviour.** A trait correction recomputes the holistic through the frozen aggregator; a
  correction that does not move the holistic is represented as such; a dissent flag records without a
  number; span rejections and feedback edits land in their own sections; repeated corrections to one
  essay preserve the earlier records and the latest wins.
- **Gold handling.** The artefact omits the gold score by default; a record made after reveal carries
  the flag.
- **Determinism.** Building twice from identical inputs produces an identical artefact.

An HTTP-level pass over the endpoints via FastAPI's test client covers wiring only — that the routes
return the artefact and that a posted override is persisted and reflected — because the logic beneath
them is already covered at the seam.

### End-to-end

Per standing project instruction, this is a UI a human clicks through, so correctness is confirmed in
a browser and not only by calling functions: open the app, read an essay, hover a card and see its
spans emphasise, expand the score-formation panel, change a trait, watch the holistic recompute,
reject a span, reload and find the correction still there. Any bug found during the build is
reproduced this way first, before it is diagnosed. Visual defects noticed along the way get fixed
along the way.

---

## Out of Scope

- **The few-shot steering bank.** Overrides are stored in a shape that can feed one — original and
  corrected scores, rationale, versions, and the `gold_revealed` flag are all recorded for exactly
  that purpose — but no bank is assembled, no examples are selected, and no grading prompt changes.
  Selection strategy (all vs. capped vs. similarity-matched), drift, and whether overrides
  retroactively re-score anything are unanswered modelling questions and belong to their own effort.
- **Live grading.** The app reviews essays that are already graded and annotated. It makes no model
  API call; nothing here depends on an API key the repo has never had.
- **Any change to trait scores, the aggregator, or QWK.** No rubric text changes, no coefficients
  move, no version in the `v1`–`v9` ladder is affected. Constraining β₂ toward the human coupling
  rate remains v10's job and is untouched here.
- **Multi-user concerns.** No authentication, no accounts, no concurrent editing, no deployment. One
  person, one machine, local files.
- **Other rubrics.** `ui_v1` renders PERSUADE: 1–6, four traits. The layout is drawn from a mock of a
  different marking scheme, and generalising to arbitrary rubrics is not attempted now.
- **Scaling the corpus.** Ten essays. Annotating the remaining 90, or the held-out 500, is a later
  decision that should follow a stratified sample rather than a uniform one.
- **Exporting student-facing reports.** The feedback is written to be student-facing; producing a
  document to hand a student is not part of this version.

---

## Further Notes

**The honest weakness of this design is the annotator's position.** It is shown a score it did not
assign and asked to explain it, which makes its output justification rather than judgment. It will
sometimes produce fluent support for a score that is wrong. The guards are what keep this from being
invisible: a justification has to be anchored in text that actually exists, at least one span per
trait, and the teacher sees the spans rather than only the prose. That converts "the model wrote
something plausible" into "the model pointed at these words", which is checkable. It does not
eliminate the problem, and `ui_v2` should look hard at whether span acceptance rate differs between
essays the system scored well and essays it scored badly.

**Span acceptance rate is the metric this ladder is refusing to name.** QWK cannot see explanation
quality at all — it is defined over numbers, and no number in this feature moves. The fraction of AI
spans a teacher accepts unedited is the natural analogue and falls out of the override records for
free. It is not the headline metric for `ui_v1` by decision, but it should be computed and reported,
with `n` attached, because at ten essays it will be extremely noisy and quoting it without the count
would overstate it.

**The build step is where this design's leverage is.** Making override records an input to
`build_review` rather than a mutation applied to its output is what reduces the whole feature to one
testable boundary. If that boundary erodes during implementation — if override application drifts
into the request handler, or anchoring gets called from the template layer — the test suite loses most
of its value. It is worth defending.

**Two facts that should not get lost.** First, the drawn sample tops out at human score 4 and has no
5s or 6s, so nothing learned from `ui_v1` describes how annotation reads on a strong essay — and its
narrow, low word-count range limits what it can show about the length coupling. Second, the
score-formation panel exists *because* the four trait cards do not explain the score; if that panel
gets cut for visual cleanliness, the UI becomes actively misleading rather than merely incomplete.

**The reference mock is directional, not a pixel target.** It sets the layout and the information
hierarchy — response left, score and overview and criterion cards right, highlights colour-matched to
cards — and that structure is the requirement. Exact spacing, hues and typography are not: the mock
comes from a /20 three-criterion marking scheme, so matching it precisely is not even coherent for a
1–6 four-trait rubric. Build the structure, fix what looks genuinely broken, and let the first render
be reacted to rather than pre-emptively polished.
