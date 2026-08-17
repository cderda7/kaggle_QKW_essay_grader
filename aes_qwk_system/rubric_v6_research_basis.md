# Research basis for `rubric_v6.md`

Companion to `rubric_v6.md`. This file explains where every design decision in the four trait scales
came from, what the evidence for it actually is, and — where the evidence is weaker than the rubric's
confident tone implies — says so.

**Verification key used throughout:**
**✅ verified** — quoted from a primary or official source fetched during this research pass.
**⚠️ secondhand** — reported via a secondary source, or the fetch returned a summary rather than
verbatim text.
**❌ unverified** — the source exists and is cited correctly, but the claim attributed to it could
not be confirmed in this pass. Treat as a lead, not a citation.

---

## 0. The problem v6 exists to solve

v1–v5 assigned four trait scores on a 1–6 scale without ever defining what any trait score meant.
A grader writing `conventions: 4` and `development: 4` was resolving both against the *same* holistic
band ("adequate mastery… lapses in quality") plus its own priors. `rubric_v5.md` names this as a known
limitation and `decisions_log.md` #53 calls the fix "the next planned change"; v6 is that change.

**The project's own measurements already say this is where the problem is.** #54 reports run-to-run
trait agreement between the iteration-3 and iteration-4 gradings — two runs whose rubrics differed
*only* in aggregation, so the trait scores should have been identical — at **33/100 identical
vectors**, and per-trait agreement of **conventions 61%, argumentation 62%, organization 80%,
development 74%**. #54's conclusion: "that variance, not the aggregation rule, is where the remaining
headroom is," supported by the finding that a sweep of 1,688 aggregation-rule variants scored
*negative* out of sample and the best possible monotone relabel of v4's scores tops out at 0.665
against v4's 0.658.

**So the two weakest traits are exactly the two whose official clauses are hardest to isolate from a
whole-essay descriptor**, which is what #53 predicted. That is the specific, measured target v6 aims
at, and §7 states the prediction before the run.

Two general consequences follow from undefined traits.

The first is a validity problem. Popham (1997) names three ways rubrics fail, and the middle one is
exactly this: **hypergeneral criteria**, rubrics so vague they only say that *"really good student
responses to the task are, well, really good. And… really bad student responses are — you guessed it
— really bad."* ✅ ([ASCD](https://www.ascd.org/el/articles/whats-wrong-and-whats-right-with-rubrics))
Brookhart puts the positive version: *"The genius of rubrics is that they are descriptive and not
evaluative"* ✅ — and warns that replacing substantive description with "Excellent, Good, Fair, Poor"
produces a grading scale, not a rubric ([full
text](https://www.geocities.ws/bdktraining/pdfkur/How%20to%20Create%20and%20Use%20Rubrics%20for%20Formative%20Assessment%20and%20Grading%20(%20PDFDrive%20).pdf)).

The second is a reliability problem. Undefined traits collapse into each other. Lai, Wolfe & Vickers
(2015) find *"evidence of illusory halo when raters assign multiple analytic scores to a single
student response"* and that *"at best, only two factors seem to be distinguishable in analytic
writing scores assigned to expository essays"* ⚠️
([EPM](https://journals.sagepub.com/doi/abs/10.1177/0013164414530990)). A many-facet Rasch study of
criterion order found rater-criterion difficulty spreads of *"at most, 0.50 point"* on a 7-point
scale, with Content/Organization rated near-identically and Vocabulary/Language Use likewise ✅
([Language Testing in Asia](https://link.springer.com/article/10.1186/s40468-020-00115-0)).

So: four undefined traits are, measurement-wise, close to one trait scored four times. v6's job is to
give each scale a different question to answer.

**Caveat stated up front.** Decomposition is not free. Across the holistic-vs-analytic literature,
per-trait reliability is typically *worse* than holistic reliability — a G-study of L2 writing found
*"rater reliability was lower for the component scores than for the overall level"*, needing **four**
raters to reach .90 on individual traits versus **two** for the holistic score ⚠️
([Language Testing in Asia](https://link.springer.com/article/10.1186/s40468-015-0014-4)). A German
large-scale study (1,365 8th-graders, 14 trained raters) found analytic criteria in the language
domain at kappa **.28–.61** and concluded *"many of the analytic criteria were not reliable enough
for individual feedback"* even while the composite was fine ⚠️
([PDF](https://d-nb.info/1349386553/34)). **The expected v6 outcome is better-defined traits, not
automatically a better QWK.** See §7.

### 0.1 The constraint v5 imposed, and how v6 satisfies it

`decisions_log.md` #50 moved the holistic rule into code because the project's goal restricts it to
**sub-120B models**, which will not reliably execute a seven-step conditional. That constraint binds
v6 too: a per-trait rubric that requires the grader to score four sub-criteria and then combine them
would reintroduce exactly the arithmetic #50 deleted.

So v6's decision procedure per trait is a **ladder of five yes/no questions, climbed from the bottom,
stopping at the last YES**. No arithmetic, no branching, no sub-scores to combine, and — because the
ladder is total and ordered — no essay that fits no band. The four sub-criteria still structure the
written bands, because that is what makes adjacent bands discriminable (§1.1, §1.3), but they are
reference material for hard calls rather than steps the grader executes.

This is directly supported by the AES literature, which converges on the same shape from two
directions:

- **Reflect-and-Revise** let an LLM iteratively rewrite rubrics against held-out QWK. The refined
  rubrics converged on *"boldface emphasis, brief summary tables, and **conditional rules of the form
  'if X is observed, assign score s'**"* — clarity via conditional logic rather than longer
  descriptions — with gains up to **+0.47 QWK (ASAP)** and **+0.19 (TOEFL11)** ✅
  ([arXiv 2510.09030](https://arxiv.org/html/2510.09030)). A climb-the-ladder table is that form.
- **Rulers** compiles the rubric into a fixed checklist of *"granular decision items requiring
  discrete choices"* and reports **ASAP 2.0 QWK 0.7276** against Multi-Trait Specialization's 0.5566.
  Its most relevant robustness result: when criterion order was reversed, direct holistic scoring
  collapsed while *"Rulers exhibits minimal variance"* ✅
  ([arXiv 2601.08654](https://arxiv.org/html/2601.08654v1)). An order-invariant checklist is the
  mechanical fix for the position/halo effects the Rasch literature identified (§1.5).

There is one finding that cuts the other way and should be held in view: for **analytic** scoring
specifically, *"concise keyword-based prompts generally outperform longer rubric-style prompts in
multi-trait analytic scoring"* ✅ ([arXiv 2604.00259](https://arxiv.org/html/2604.00259)). v6 is long.
The ladders are the concession to that finding — they are the operative instrument and could be
extracted as a one-page grader card — and the full bands are the fallback. **The natural v7 experiment
is A/B-ing ladders-only against the full file on the same 100 essays**, which the harness supports
for free since neither changes the output schema.

---

## 1. Design principles applied to all four scales

### 1.1 Fixed sub-criteria, repeated in the same order at every band

Every scale in v6 has four sub-criteria (a)–(d) that appear at all six bands. Brookhart's parallel
construction rule: *"If part of the description of proficiency is that a student 'states the problem
in terms of its mathematical requirements,' then each level of that criterion should have a
description of the way students do that."* ✅ The UF rubric guide says it operationally: *"if your
descriptors include quantity, clarity, and details, make sure that each of these outcome expectations
is included in each performance level descriptor"* ✅
([PDF](https://www.assessment.aa.ufl.edu/media/assessmentaaufledu/faculty-resources/Writing-Effective-Rubrics-2025.pdf)).

Structural model taken from **6+1 Trait Writing** (Education Northwest), whose 3–12 rubric decomposes
each trait into lettered sub-criteria restated at every band ✅
([rubric PDF](https://educationnorthwest.org/sites/default/files/resources/traits-rubrics-3-12.pdf))
and from **ACT Writing**, whose four analytic domains map near-1:1 onto ours ✅
([ACT rubric](https://www.act.org/content/dam/act/unsecured/documents/Writing-Test-Scoring-Rubric.pdf)):

| ACT domain | v6 trait |
|---|---|
| Ideas and Analysis | Argumentation |
| Development and Support | Development |
| Organization | Organization |
| Language Use and Conventions | Conventions |

**What we did *not* take from ACT.** ACT's adjacent bands are differentiated almost entirely by one
adverb: *"an argument that **critically** engages"* (6) / *"**productively** engages"* (5) /
*"engages"* (4) ✅. That is maximally parallel and maximally hypergeneral — the exact wording style
Popham criticizes and the one an LLM grader will resolve inconsistently. v6 borrows ACT's *trait
decomposition* and IELTS/TOEFL's *band-boundary wording*.

### 1.2 Band boundaries stated as observable contrasts, not quantifiers

The two best-worded operational rubrics found:

- **Smarter Balanced, Evidence/Elaboration 4 vs 3** ✅: evidence *"integrated, relevant, and
  **specific**"* versus *"integrated and relevant, **yet may be general**"*
  ([official PDF](https://portal.smarterbalanced.org/library/en/performance-task-writing-rubric-argumentative.pdf)).
  The lower band names the exact failure it tolerates.
- **TOEFL iBT Integrated, 5 vs 4** ✅: language errors at 5 *"do not result in inaccurate or imprecise
  presentation of content"*; at 4, *"more frequent or noticeable minor language errors, as long as
  such usage and grammatical structures do not result in anything more than an occasional lapse of
  clarity"* ([ETS](https://www-stg-sp.es.ets.org/pdfs/toefl/toefl-ibt-writing-rubrics.pdf)).
  The boundary is a **consequence test**, not a count.

v6 uses the consequence-test pattern wherever possible: Organization's *interchangeability test*,
Development's *listed-vs-explained* line, Conventions' *what do the errors cost* ladder, and
Argumentation's *does the essay get somewhere new*.

IELTS Task 2's four repeating axes — **range, control/accuracy, coverage, consequence** — were used
as a drafting checklist for each ladder ⚠️ (quoted from a third-party mirror of the public band
descriptors, not from ielts.org; [mirror](https://www.ielts-mentor.com/files/ielts-writing-task2-band-description.pdf) —
**verify before quoting IELTS wording anywhere public**).

### 1.3 One dimension moves per band step; sub-criteria that vary independently stay separate

Stanford SCALE's rubric checklist states the anti-conflation rule: *"Indicators should not be grouped
together within a single performance level if student performance on those indicators often
varies."* ✅
([PDF](https://www.bates.edu/research/files/2018/07/SCALE-Quality-Rubric-Checklist.docx.pdf)) This is
why Organization separates *controlling idea*, *frame*, *progression*, and *unity* rather than
bundling them into "well organized" — real essays vary independently across those.

The AP English Language Argument rubric (Row B) shows the technique at the top boundary ✅
([2025 scoring guidelines](https://apcentral.collegeboard.org/media/pdf/ap25-sg-english-language-set-1.pdf)):
3 points = *"Explains how some of the evidence supports a line of reasoning"*; 4 points = the
identical evidence requirement, with *"**Consistently** explains…"*. Evidence is held constant;
only commentary consistency moves. v6's Development 4/5 boundary copies this move directly.

### 1.4 Presence-focused at bands 2–6; absence language reserved for band 1

UF: *"Focus your descriptions on the presence of the quantity and quality that you expect, rather
than on the absence of them. However, at the lowest level, it would be appropriate to state that an
element is 'lacking' or 'absent.'"* ✅

### 1.5 Structural alignment is a known halo risk, and v6 accepts it knowingly

Humphry & Heldsinger (2014) argue that the near-universal rubric grid — every criterion with the same
number of levels, aligned side by side — is itself a validity threat: alignment *"makes it
cognitively easier for raters to assign uniform scores rather than differentiate performance across
distinct competencies"* ✅ ([*Educational Researcher*](https://journals.sagepub.com/doi/10.3102/0013189X14542154)).
Smarter Balanced breaks alignment deliberately: Organization/Purpose 0–4, Evidence/Elaboration 0–4,
**Conventions 0–2** ✅.

**v6 cannot break alignment** — four traits × 1–6 is fixed by the gate, the weights, and the output
schema, and changing it would make v6 incomparable to v1–v5. So v6 mitigates instead, with the two
interventions the halo literature supports:

- **Independent scoring per trait.** The MFRM criterion-order study found that **random criterion
  order** raised rater separation to **6.44** versus **4.68 / 4.36** for standard and reverse order,
  and that *"successive presentation of conceptually related criteria (content–organization;
  vocabulary–language use) intensified similarity perceptions"* ✅.
- **Self-contained trait blocks.** Each scale in v6 is written to be extractable into its own
  grader call. This is the Multi-Trait Specialization pattern (§6.2), which exists precisely to
  *"isolat[e] trait-specific scoring criteria from rubric guidelines that mix multiple traits as a
  whole"* ✅ ([arXiv 2404.04941](https://arxiv.org/html/2404.04941v2)).

This is recorded as an accepted, mitigated risk rather than a solved problem.

### 1.6 Cross-trait firewalls

Rezaei & Lovorn (2010) engineered two essays with inverted strengths — one mechanically polished and
content-thin, one content-complete and error-riddled — and found *"raters were significantly
influenced by mechanical characteristics of students' writing rather than the content **even when
they used a rubric**"* ✅ ([ERIC EJ881105](https://eric.ed.gov/?id=EJ881105)). A rubric alone does not
stop the bleed; explicit negative instructions are required. Hence the numbered firewall list in v6.

Smarter Balanced provides institutional precedent for treating conventions as construct-independent:
since 2022–23, an **off-purpose** essay is scored on **Conventions only** ✅
([scoring specs](https://technicalreports.smarterbalanced.org/scoring_specs/_book/scoringspecs.html)).

---

## 2. Organization — where each band came from

**Official anchors** are the organization clause of each PERSUADE holistic band, verbatim (see
`rubric_official_persuade.md`). The official 5-vs-6 difference is the words *"clearly"* and
*"smooth"*. Everything below is the extension that makes that difference decidable.

### 2.1 Bands 1–3: presence and placement of the controlling idea

A 2025 study of **17,451 essays from grades 6–8** on a US state summative assessment ran a latent
class analysis over seven annotated structural elements and recovered **eight structural patterns,
monotonically ordered by rubric score** ✅
([*Frontiers in Education*](https://www.frontiersin.org/journals/education/articles/10.3389/feduc.2025.1569529/full)):

| Pattern | % | Organization mean (0–4 scale) |
|---|---|---|
| Body only, no controlling idea | 4.7 | 1.29 |
| Controlling-idea-only introduction | 9.4 | 1.61 |
| No intro/conclusion, controlling idea buried in body | 22.2 | 1.65 |
| Controlling idea with introductory remarks | 22.5 | 1.78 |
| Standard structure, controlling idea missing/hidden | 6.5 | 1.97 |
| Standard structure, controlling idea deferred to conclusion | 4.3 | 2.08 |
| Multiple introductions | 3.5 | 2.22 |
| **Conventional intro–body–conclusion** | **26.8** | **2.24** |

The ordering is driven almost entirely by **presence and placement of the controlling idea** and
**presence of framing paragraphs** — which is exactly the (a)/(b) ladder in v6's bands 1–3, and the
warrant for the **controlling-idea test at the 2/3 boundary** (*is the position stated in the essay's
own words, or must the reader assemble it from the body?*).

Bamberg's holistic coherence scale (1983/1984) would have been the ideal additional anchor. ❌ **Its
actual level descriptors could not be located** — the best available secondhand account is Knoch
(2007), which characterizes only Level 2 and lists the criterion set: topic identification, setting
of context, cohesive devices, appropriate conclusion, discourse flow, errors ⚠️
([Knoch via Academia](https://www.academia.edu/5597017/)). Recovering Bamberg verbatim needs
*RTE* 18(3) via JSTOR/NCTE. The criterion set is consistent with v6's sub-criteria; the wording is
not borrowed from it.

### 2.2 Band 4 is the conventional-structure ceiling

The same LCA is the cleanest empirical statement of the five-paragraph theme as a developmental
waypoint rather than a ceiling-breaker: the **conventional intro–body–conclusion pattern tops out at
2.24 on a 0–4 organization rubric** ✅ — the *middle*, not the top, and the highest of the eight
patterns. So a scale whose top bands can be reached by executing the standard shape cleanly has no
room left to discriminate 5 from 6.

Hence v6's explicit rule: **the conventional five-paragraph frame caps at 4**, and 5–6 require
something the standard shape does not buy. 6+1 Traits independently marks the same boundary with the
words *"formulaic"* and *"predictable"* at its band 4 ✅.

### 2.3 Bands 5–6: motivated sequence and structure-as-argument

What sits above conventional structure had to come from somewhere. Two sources:

- **6+1 Traits, Organization**, sub-criterion "Sequencing": 4 = *"logical sequencing of ideas"*;
  5 = *"sequencing that builds connections to create a unified whole"*; 6 = *"highly effective
  sequencing, making best choices"* ✅ (short excerpts; the fetch tool declined full reproduction on
  © grounds — © 2021 Education Northwest). v6's **interchangeability test** is an operationalization
  of the 4→5 step: *builds connections* means later parts depend on earlier ones, which means the
  order cannot be permuted freely.
- **Smarter Balanced Organization/Purpose 4**: *"a clear and effective organizational structure,
  creating a sense of unity and completeness"* with *"logical progression with strong connections"* ✅.

### 2.4 The rule against scoring transition words

This is the most counterintuitive rule in v6 and it has the strongest evidence behind it.

Crossley & McNamara found cohesion indices correlating **negatively** with expert quality ratings —
content word overlap **r = −0.279**, positive logical connectives **r = −0.227**, LSA given/new
**r = −0.265** (all p < .001) — concluding *"increased cohesion was characteristic of essays scored
lower"* and *"how human raters construct a coherent mental representation does not correlate with the
cohesive devices reported by Coh-Metrix"* ⚠️
([Academia copy](https://www.academia.edu/104603107/Understanding_expert_ratings_of_essay_quality_Coh_Metrix_analyses_of_first_and_second_language_writing)).

The TAACO work resolves the paradox by level ✅
([*Behavior Research Methods* 2016](https://link.springer.com/article/10.3758/s13428-015-0651-7)):
**local** cohesion (adjacent-sentence overlap, connectives) is a negative or null predictor;
**global** cohesion (paragraph-to-paragraph overlap, cross-segment semantic similarity) **positively**
predicts both coherence judgments and essay quality, with paragraph-level overlap indices the
strongest predictors (R² = .22–.27).

**Design consequence, stated bluntly:** a grader instructed to reward "uses transitional phrases such
as *furthermore*, *in conclusion*" will actively anti-correlate with expert quality judgment. v6
therefore describes progression in terms of **relations between paragraphs' ideas**, never signposting.

Topical structure analysis (Lautamatti; Witte) was considered as an alternative operationalization
and rejected. ❌ Witte's (1983) quantitative link between progression type and holistic quality could
not be verified, and the same surface-feature critique that sinks connective counts applies to
progression-type counts. The usable residue is qualitative and is what v6 uses: *paragraph-internal
unity = every sentence's topic is recoverably related to the paragraph's controlling topic.*

### 2.5 Why the top band is functional, not stylistic

Morris, Crossley, Holmes & Suh Choi (2025) analysed **4,170 highly-rated PERSUADE essays** and found
**four distinct high-scoring profiles** ✅ ([*JoWR*](https://www.jowr.org/jowr/article/download/1491/1000/6213)):
Structural (32.4%, high cohesion and formal organization), Academic (22%, phrasal complexity and
lexical sophistication), **Reportive (25%, source-based, *lower* cohesion indices)**, and
**Conversational (20.6%, high-frequency spoken language, personal pronouns)**. Verbatim: *"writers can
employ a variety of writing profiles to successfully write an argumentative essay."*

**There is no single linguistic signature of a 6 in this corpus.** A top band written in stylistic
terms ("formal, cohesive, academic register") would systematically under-score the ~46% of
high-scoring essays that are Reportive or Conversational. Every v6 top band is therefore written in
terms of *what the text accomplishes*, and Organization carries an explicit rule saying so.

### 2.6 Known risk

Organization is historically the **least reliable** analytic trait — the L2 G-study found "structure"
lowest among five components ⚠️, and the MFRM order study found Organization the **most
order-sensitive** criterion ✅. If any v6 trait fails to stabilize, expect this one.

---

## 3. Development — where each band came from

### 3.1 The core decision: depth over count

The best single study found splits elaboration into two orthogonal dimensions and finds them very
unequal ✅ ([*JoWR*](https://www.jowr.org/jowr/article/download/850/932/2449)):

- **Elaboration breadth** = number of distinct top-level topics / primary arguments.
- **Elaboration depth** = amount of supporting detail within each.
- **Depth dominates**: largest predictive effect on text quality across genres, **b = 0.516**;
  breadth's contribution genre-dependent and negligible in descriptive writing. Coding κ = .75.

Three independent corroborations:

- Crossley, Tian & Wan (2022) on PERSUADE-lineage data: raw counts of argumentation elements are weak
  predictors — **evidence/data count r = .188**, concluding-summary count r = .193 — while
  **hierarchical (superordinate–subordinate) relation counts reach r = .309–.323**. Verbatim: *"it is
  not the presence of argumentation features that is predictive of writing quality but rather the
  relationships between superordinate and subordinate features."* ✅
  ([*JoWR*](https://www.jowr.org/jowr/article/download/831/872/1032))
- Du & List (2021): evidence-related processing strategies **did not predict the *quantity* of
  evidence but did predict its *quality*** ⚠️ ([*RRQ*](https://ila.onlinelibrary.wiley.com/doi/abs/10.1002/rrq.366)).
- The Response-to-Text Assessment work (Correnti, Rahimi, Litman — source-based, grades 5–8, the
  closest analogue to our task) found **specificity alone was the most predictive automated feature
  group, approaching full-model performance by itself** ⚠️
  ([IJAIED](https://link.springer.com/article/10.1007/s40593-017-0143-2)).

Hence v6's first and most emphatic Development rule: **depth, not count.**

**Counter-precedent, recorded honestly:** the RTA rubric *itself* includes a raw "number of pieces of
evidence" sub-criterion (<2 lowest, 3+ higher) ⚠️. Its own authors caveat that they *"have yet to
examine construct validity at the feature level."* v6 declines to follow it.

### 3.2 The listed-vs-explained line (bands 3/4) and the consistency line (4/5)

Two published operationalizations, used directly:

**AP English Language, Row B** ✅ — the cleanest published statement of listed vs. explained:

| Pts | Evidence | Commentary |
|---|---|---|
| 1 | "Provides evidence that is mostly general." | "Summarizes the evidence but does not explain how the evidence supports the argument." |
| 2 | "Provides some specific, relevant evidence." | "Explains how some of the evidence relates to the student's argument, but no line of reasoning is established…" |
| 3 | "Provides specific evidence to support all claims in a line of reasoning." | "Explains how some of the evidence supports a line of reasoning." |
| 4 | *(identical to 3)* | "**Consistently** explains how the evidence supports a line of reasoning." |

**Smarter Balanced Evidence/Elaboration** ✅ supplies the degradation vocabulary at the low end:
score 2 = *"weakly integrated, imprecise, repetitive, vague, and/or copied"*; score 1 = *"minimal,
irrelevant, absent, incorrectly used, or predominantly copied"*. The explanatory variant adds a
directly usable 2/3 separator: *"development may consist primarily of source summary"* ✅ — which is
v6's Development band 2, sub-criterion (d).

**Texas STAAR** ✅ confirms the specificity ladder: SP3 *"Evidence is specific, well chosen, and
relevant"*; SP2 *"Evidence is limited and may include some irrelevant information"*; SP1 *"Evidence
is insufficient and/or mostly irrelevant"*
([PDF](https://tea.texas.gov/sites/default/files/tx-staar-arg-opinion-rubric-g6-e2.pdf)).

### 3.3 Relevance as a gate, sufficiency as a gradient

Operational rubrics split on whether these are separable. CCSS W.9-10.2b names them separately
(*"relevant, and sufficient"*) ✅; STAAR collapses them (*"insufficient **and/or** mostly
irrelevant"*) ✅; Smarter Balanced never names sufficiency, embedding it in
*comprehensive / adequate / uneven, cursory / minimal* ✅. Encoding relevance as a **precondition**
and sufficiency as the **gradient** matches every operational rubric examined and avoids the counting
trap.

### 3.4 The rule against ranking evidence by provenance

Smarter Balanced states it explicitly in a rubric footnote ✅:
> Argumentative: *"Elaborative techniques may include the use of personal experiences that support the
> argument(s)."*

The qualifier is **relevance to the claim**, not where the evidence came from. Its annotated student
samples make the same move: a 1-point sample fails not because it is anecdotal but because it relies
on *"anecdotal observation … without substantive analysis"* ⚠️
([WestEd samples](https://understandingproficiency.wested.org/wp-content/uploads/2015/11/Gr8_E-E_Unscored_Samples.pdf)).
And the elaboration-depth research (§3.1) locates quality in development, not source type.

⚠️ **Honest gap:** no study was found directly testing whether human raters score personal-experience
evidence lower *after controlling for specificity*. The additional equity argument — that a provenance
hierarchy would import unequal access to external evidence (background knowledge, prior schooling, ELL
status) — is **reasoned, not cited**. It is presented in v6 as a design commitment.

### 3.5 Copying and patchwriting

- **Plakans & Gebril (2013):** source-use features explained **>50% of score variance**, and
  **verbatim source use correlated *negatively* with score** ⚠️
  ([Academia](https://www.academia.edu/3727957/)).
- **Smarter Balanced** treats *"weakly integrated… and/or copied"* as score 2, *"predominantly
  copied"* as score 1, and reserves the non-scorable code for wholesale copying ✅. **TOEFL Integrated**
  scores 0 for a response that *"merely copies sentences from the reading"* ⚠️.
- **Patchwriting** as a *developmental stage* of source engagement rather than misconduct is
  well-attested in secondary sources ⚠️ but Howard's exact framing was **not fetched**
  ([Citation Project](http://www.citationproject.net/wp-content/uploads/2018/03/Howard-Plagiarism-Pentimento.pdf)).

v6 follows the SB pattern: predominantly copied → 1; patchwriting caps the trait at 3.

### 3.6 Why length neutrality is stated hardest here

Length contamination is **trait-specific**, and this is the single most actionable finding from the
research pass:

- *Frontiers in Psychology* (2020): text length explained an **additional 24% of variance** in quality
  ratings beyond measured proficiency (β = 0.41, p < .01), and citing Pohlmann-Rother et al. (2016),
  length correlated **r = 0.62 with semantic-pragmatic (content) dimensions but r = 0.09 with
  language mechanics** — *"no meaningful relationship between text length and language mechanics."* ✅
  ([full text](https://www.frontiersin.org/journals/psychology/articles/10.3389/fpsyg.2020.562462/full))
- Kobrin, Deng & Shaw (College Board), 2,820 SAT essays: **r = .62 between word count and essay
  score** ✅ ([PDF](https://www.testpublishers.org/assets/documents/Volume_8_issue_1Does_quantity_equal.pdf)).
- Perelman reports the timed/untimed gradient: 25-minute essays **40–60%** shared variance with
  length; 1-hour **≈20%**; 72-hour **≈10%**; untimed undergraduate essays on familiar topics **1.7%**
  ⚠️ (polemical source; [WAC Clearinghouse](https://wacclearinghouse.org/docs/books/wrab2011/chapter7.pdf)).
  PERSUADE/ASAP are timed standardized-test writing — the high-confound end.

So v4's blanket anti-verbosity instruction was correct but undirected. v6 keeps it and adds where it
bites: **hardest on Development, nearly inert on Conventions.**

> ⚠️ **Complication worth knowing before "fixing" this.** On ASAP 2.0, human scores correlate with
> length at **r = 0.71** while an LLM grader showed a *weaker* correlation (**r = 0.47**) ✅
> ([arXiv 2604.00259](https://arxiv.org/html/2604.00259)). Length bias is partly baked into the ground
> truth. De-biasing the grader can therefore *lower* QWK against human labels. That is a legitimate
> validity-vs-metric tradeoff and should be an explicit decision, not an accident — see §7.

---

## 4. Conventions — where each band came from

### 4.1 The impedance ladder is native to the official rubric, not imported

Worth stating clearly, because it is the strongest provenance claim in v6. The official PERSUADE
bands already ladder on consequence:

| Band | Official phrase |
|---|---|
| 4 | "may have **some errors** in grammar, usage, and mechanics" |
| 3 | "may contain an **accumulation of errors**" |
| 2 | "errors… so serious that **meaning is somewhat obscured**" |
| 1 | "**pervasive errors**… that **persistently interfere with meaning**" |

v6 does not introduce impedance banding; it *finishes* it, by supplying the two upper steps the
official text leaves as "generally free of most errors" (5) and "free of most errors" (6), and by
naming what the 4/3 boundary means operationally.

### 4.2 Operational precedent

**Texas STAAR** is the cleanest published statement of impedance banding ✅
([PDF](https://tea.texas.gov/sites/default/files/tx-staar-arg-opinion-rubric-g6-e2.pdf)):
> 2: *"Few errors, but those errors do not impact the clarity."*
> 1: *"Several errors, but the reader can understand the writer's thoughts."*
> 0: *"Many errors, and these errors impact the clarity of the writing."*

**6+1 Traits Conventions (1–6)** is the closest 6-point structural precedent, and puts the impedance
threshold at exactly the 4/3 boundary ✅: 4 = *"grade level appropriate correct conventions with some
minor errors"* → 3 = *"inconsistency in use of correct conventions which **may impair readability**"*;
2 = *"many errors that make text difficult to read"*; 1 = *"errors that make text unreadable or
distracting"*.

**Smarter Balanced's scoring gloss** supplies the three-way frame v6 uses implicitly ✅
([scoring guide](https://portal.smarterbalanced.org/library/en/scoring-guide-for-ela-full-writes.pdf)):
> *"**Variety:** A range of errors includes sentence formation, punctuation, capitalization, grammar
> usage, and spelling; **Severity:** Basic errors are more heavily weighted than higher-level errors;
> **Density:** The proportion of errors to the amount of writing done well. This includes the ratio of
> errors to the length of the piece."*

Note density is **normalized by length**, not raw count — an institutional precedent that pure
counting is inadequate.

### 4.3 The rule against enumerating error types — and the honest caveat

v6 forbids building an error taxonomy. Two reasons, of unequal strength.

**The strong reason (empirical).** ETS's investigation of e-rater's 36 grammar/usage/mechanics/style
microfeatures found that *"a single microfeature or a small number of microfeatures are responsible
for most of the variability"* in each group — **spelling dominates mechanics** (r = 0.53, the
strongest and most stable feature) — that **ten microfeatures had >95% zero scores** (no
discriminating power at all), and that **three microfeatures correlate *positively* with human
scores** (missing commas, hyphen errors, passive voice) ✅
([ERIC EJ1168485](https://files.eric.ed.gov/fulltext/EJ1168485.pdf)). Fine-grained error taxonomies
mostly add noise, and "more error flags = worse" is not even monotonic.

**The equity reason (a design commitment, not a finding).** Hairston (1981) surveyed 84 professionals
on 65 sentences and produced a severity hierarchy whose **most severe tier is nonstandard verb forms
("he brung," "has went"), double negatives, and objective pronouns as subjects** — 79 of 80 objected
to "brung" ⚠️ ([PDF](https://teaching.berkeley.edu/sites/default/files/not_all_errors_are_created_equal.pdf)).

> **Read that carefully, because it cuts against the received wisdom.** Hairston's hierarchy is driven
> by **social stigma and dialect marking, not comprehension impedance**. "He brung" is perfectly
> comprehensible and ranks *most* severe. These are features of stigmatized varieties of English
> (AAVE, Appalachian, Southern vernaculars) as much as of L2 interlanguage. **This is evidence that
> raters key on prestige-dialect deviation** — which means an impedance-anchored rubric is a
> deliberate *departure* from documented rater behaviour, not a description of it.

Santos (1988) found professors judged NNS errors *"highly comprehensible, generally unirritating, but
academically unacceptable"* ⚠️ — comprehensibility and acceptability dissociate. And a systematic
review of 31 error-gravity studies (1969–1999) concludes that *"evidence for a 'universal hierarchy of
errors' remains inconclusive"*, with rankings varying across studies and native-speaker raters
consistently more lenient than non-native ones ⚠️
([review PDF](https://www.nepjol.info/index.php/mrj/article/download/73470/56240/213760)).

> **So the honest framing, which v6 adopts:** "band on whether errors impede meaning, not on error
> count or error type" is a **well-motivated normative commitment with strong operational precedent
> (STAAR, 6+1 Traits, TOEFL, and the official PERSUADE rubric's own 2/1 language)** — but it is *not*
> a settled empirical finding about how raters behave. The gravity literature suggests raters key on
> dialect prestige at least as much as on comprehension. **v6 is choosing comprehension deliberately,
> and this may cost QWK against human labels.** That is a validity decision; log it as one.

❌ **Verification gaps here, listed so nobody cites them from memory:** Connors & Lunsford (1988) error
frequency table; Lunsford & Lunsford (2008) top-20 error list and the ~2.3-errors-per-100-words
stability claim; Vann, Meyer & Lorenz (1984) primary; Burt & Kiparsky's global/local error
definitions. All four exist and are correctly cited as sources, but **none of their specific findings
was verified in this pass.**

### 4.4 The rule against rewarding syntactic complexity

Beers & Nagy (2009) — and this reverses by genre, which is why it matters here ✅
([*Reading and Writing*](https://link.springer.com/article/10.1007/s11145-007-9107-5)):

- **Words per clause**: positively correlated with quality **in persuasive essays**; no significant
  correlation in narratives.
- **Clauses per T-unit**: positively correlated **in narratives**; ***negatively* correlated with
  quality in persuasive essays.**

PERSUADE/ASAP are argumentative. **In this genre, clause density is a negative signal.** So v6 says
*variety and control* and never *subordination* or *complex sentences* — following 6+1 Traits'
Sentence Fluency, which describes *"varied sentences that are usually technically correct and flow
smoothly"* without prescribing subordination ✅.

### 4.5 Scope decision: vocabulary lives in Conventions

This follows **NAEP** (whose "Language Facility and Conventions" dimension covers *"Sentence structure
and sentence variety," "Word choice," "Voice and tone," "Grammar, usage, and mechanics"* ✅) and
**6+1 Traits**, and diverges from **Smarter Balanced**, which puts vocabulary and style inside
Evidence/Elaboration and keeps Conventions to *"sentence formation, punctuation, capitalization,
grammar usage, and spelling"* ✅.

It also follows the official PERSUADE rubric, which is decisive: its language clause bundles
vocabulary, sentence structure, and mechanics into one strand at every band. **Do not cite Smarter
Balanced's Conventions descriptors as covering vocabulary.**

One consequence, flagged in v6: on **source-based** prompts, sophisticated vocabulary may be lifted
from the source rather than produced by the writer — and verbatim borrowing predicts score
*negatively* (§3.5). Judge the writer's own sentences.

❌ NAEP's actual 6-level descriptors sit in Appendices C1–C3 of the 2011 framework and were **not
retrieved** ([framework PDF](https://www.cde.state.co.us/sites/default/files/documents/assessment/documents/naep/writing_framework_2011.pdf)).

### 4.6 A widely-repeated claim that did *not* survive checking

The assumption that **conventions is the highest-agreement trait** is plausible, commonly asserted,
and **could not be substantiated in this pass**. The L2 G-study found *"differences among components
were quite small"* with no component clearly highest ⚠️; Lai, Wolfe & Vickers found analytic writing
scores collapse to ~2 distinguishable factors ⚠️.

**What can be defended instead** — and what v6 relies on — is a *validity* argument, not a reliability
one: length confounds content traits at r ≈ .62 and mechanics at r ≈ .09 ✅ (§3.6). Conventions is
distinctive because it measures something length does not proxy for, whether or not it is also the
most reliable.

---

## 5. Argumentation — where each band came from

### 5.1 The corpus's own argumentation rubric, used as a mid-band definition

PERSUADE ships a companion rubric scoring discourse elements Effective / Adequate / Ineffective ✅
(`argumentation_effectiveness_rubric.pdf` in
[the corpus repo](https://github.com/scrosseye/persuade_corpus_2.0); full descriptor text fetched).
Its **Adequate** band is consistently characterized by *restatement without advancement*:

- Position, Adequate: *"addresses the topic but generally **repeats the prompt's stance**."*
- Claim, Adequate: *"relates to the position but **may simply repeat part of the position** or state a
  claim without support."*
- Concluding Summary, Adequate: *"**merely copies the claims** or may restate only part of the claims."*

That is a **corpus-native definition of the mid band**: *present but restating* versus *present and
advancing*. It is the source of v6's most important Argumentation rule — **restatement is not
development** — and of the specific band-2 language ("what look like reasons are restatements of the
position in other words").

The recurring axis across every element of that rubric is **relevance + specificity + validity**,
which v6's (a)–(d) sub-criteria track.

Also verbatim from that rubric, and directly usable: **Rebuttal, Effective** = *"directly answers and
refutes the counterclaim"*; **Counterclaim, Effective** = *"reasonable and relevant… a valid objection
to the position."*

### 5.2 The developmental ladder for bands 4–6

**Deane et al. (2015), ETS learning progression "The Key Practice, Discuss and Debate Ideas"** ✅
([ERIC full text](https://files.eric.ed.gov/fulltext/EJ1109288.pdf)) — the only published ordinal
argumentation progression found that is US, standards-aligned, grade-appropriate, and free:

| Level | Verbatim |
|---|---|
| 1 | "Understands the idea that positions may need to be supported with reasons that will be convincing" |
| 2 | "Recognizes, generates and elaborates on reasons in writing, with some awareness of the need for evidence" |
| 3 | "Understands use of evidence and clearly grasps the need to provide evidence and reasons that are directly relevant" |
| 4 | "Understands the role of critique and rebuttal and is able to reason about and respond to counterevidence" |
| 5 | "Builds systematic mental models of entire debates, and uses that model to frame one's own attempts" |

Note where rebuttal sits: **Level 4 of 5**, and the top level is *modelling the debate itself* — which
is the warrant for v6's band 6 being "does something the prompt did not hand it" rather than simply
"has a rebuttal."

⚠️ Caveat: Deane's strand tables are written largely in comprehension/interpretation voice, since the
progression covers reading and writing jointly. v6 converts to production voice.

### 5.3 Why counterargument is one route to 5 and not the requirement

This was the most consequential judgment call in the whole rubric, and the evidence points both ways.

**For making it a high-band marker:**

- **Wolfe, Britt & Butler (2009):** essays that **rebut** opposing arguments were rated higher in
  quality than myside-biased essays ⚠️
  ([*Written Communication*](https://journals.sagepub.com/doi/abs/10.1177/0741088309333019)). Their
  three-way schema is the key nuance: other-side information can be **omitted**, **mentioned/conceded**,
  or **rebutted** — and **only rebuttal reliably raises quality.** Mere acknowledgment is not clearly
  better than omission. This is why v6 says *acknowledging without answering does not by itself reach 5.*
- **Nussbaum & Kardash (2005)** give the useful three-way typology of what a rebuttal *does* — shows the
  counterargument (a) is invalid, (b) carries less force, or (c) rests on a false assumption ⚠️
  ([Academia](https://www.academia.edu/4387838/)). v6 band 6 uses this verbatim in substance.
- **Felton & Kuhn (2001):** adults vs. adolescents, counter-argument utterances **20.42% vs 8.51%**,
  rebuttal sequences **5.02 vs 1.07** (both p<.001) ✅
  ([PDF](https://www.tc.columbia.edu/faculty/dk100/faculty-profile/files/001_Thedevelopmentofaugumentivediscourseskills.pdf)) —
  it is developmentally discriminating.

**Against making it the requirement:**

- **Knudson (1992),** analysing argumentative writing across four grade levels: *"Few children in any
  grade used features of opposition or response to opposition."* ⚠️ ([ERIC EJ456314](https://eric.ed.gov/?id=EJ456314))
- **Nussbaum & Kardash:** *unprompted college students* averaged **0.15 rebuttals per essay** ⚠️.
  In grades 6–12, unprompted, expect near-zero.
- **Ferretti & Graham (2019):** only about **25% of student essays provide strong reasoning while
  considering counterarguments** ⚠️
  ([*Reading and Writing*](https://link.springer.com/article/10.1007/s11145-019-09950-x)).
- **The official rubric never mentions counterargument.** The word appears nowhere in the PERSUADE
  holistic text ✅. Making it a gate would be *adding* a criterion the gold labels were not produced
  against — decorrelating from the target.

**Resolution:** counterargument-with-rebuttal is **one of three sufficient routes to band 5**,
alongside **explicit warranting** and **appropriate qualification**. The warranting route is supported
by the Toulmin-perspective study that found **Warrant-Backing 1.27 vs 0.38 (p = .001)** between
fourth-year and first-year writers, alongside argument **depth** (2.27 vs 1.78, p < .001) and **width**
(2.83 vs 2.34, p = .012), while *"counterarguments and rebuttals were too rare in **both** groups to
differentiate"* ✅
([PDF](https://www.tesolunion.org/attachments/files/ANDLHBN2MW4ZGY2AZDJLAMWQ54NDVM9Y2Y1AYZHH6MTKYAMJGW9M2ZK3NTHJ6ZDGY3ZTVL5ZGNH9YMQ29MZEXBM2QY5LJM2EOTK25NTMZALMVI.pdf)).
Explicit warranting is a genuine upper-band marker that is *more attainable* in a grades 6–12 corpus
than rebuttal.

⚠️ **Qualification/hedging as an upper-band marker is the weakest link in v6.** No study was found
establishing hedging or qualification as an ordinal quality band in US adolescent argumentative
writing. It is included as one of three alternative routes rather than a gate specifically because the
evidence is thin. If v6's band-5 distribution looks wrong, this is the first clause to cut.

❌ **Stapleton & Wu (2015)** — "Assessing the quality of arguments in students' persuasive writing"
(*JEAP* 17) — is the highest-value unretrieved source. Its thesis (presence of Toulmin elements is
largely decoupled from argument quality — students fill the counterargument slot with something
worthless) is exactly what this scale needs, and it likely contains a per-element ordinal quality
rubric. Paywalled; recommend chasing via institutional access before v6.

### 5.4 A structural warning about this trait and Organization

The PERSUADE raters' own analytic form scored **ten dimensions on a 1–6 scale** before assigning the
holistic score — *effective lead, clear purpose, clear plan, topic sentences, paragraph transitions,
organization, unity, perspective, conviction, grammar/mechanics* — and PCA collapsed them into **three
components** ✅ ([Crossley, Tian & Wan 2022](https://www.jowr.org/jowr/article/download/831/872/1032)):

1. **Argument Strength and Organization** (unity, perspective, conviction, topic sentences, paragraph
   transitions, organization)
2. **Introductory Elements** (effective lead, clear purpose, clear plan)
3. **Grammar and Mechanics**

**The corpus's own factor structure does not separate argumentation from organization** — they load
together. So expect v6's Argumentation and Organization scores to correlate heavily even when scored
independently, and do not read that correlation as a rubric failure. If the traits must be
restructured in a future version, the empirically-supported split is *Introductory Elements /
Argument+Organization / Language / Conventions*, which would be a genuine departure from the
four-trait scheme and its own version.

❌ **Highest-value unretrieved source overall:** the per-level 1–6 descriptors for those ten analytic
dimensions. The PERSUADE rubric PDF's own preamble references them — *"After reading each essay and
completing the **analytical rating form**…"* — but the form's text is not in the repo and is not
reproduced in any accessible paper. **Recommend contacting Scott Crossley directly.** If obtained, it
would supersede large parts of §5 and §2 with the actual instrument the gold labels came from.

---

## 6. Notes specific to running this with an LLM grader

### 6.1 What the AES literature says explicit decision rules buy

- **Reflect-and-Revise** (iterative rubric refinement optimized on QWK) found refined rubrics
  converged on *"boldface emphasis, brief summary tables, and **conditional rules of the form 'if X is
  observed, assign score s'**"* — clarity via conditional logic rather than longer descriptions — with
  gains up to **+0.47 QWK (ASAP)** and **+0.19 (TOEFL11)** ✅
  ([arXiv 2510.09030](https://arxiv.org/html/2510.09030)). This is the direct warrant for v6's
  *decision rules* blocks.
- **Rulers** (locked rubric + evidence-anchored scoring) reports **ASAP 2.0 QWK 0.7276** vs
  Multi-Trait Specialization's 0.5566, using a fixed taxonomy, an operational checklist of granular
  discrete-choice items, and **deterministic evidence rules requiring verbatim quotes**, with a score
  cap when evidence is missing ✅ ([arXiv 2601.08654](https://arxiv.org/html/2601.08654v1)). Notably it
  is **order-invariant**: reversing criterion order collapsed direct holistic scoring but left Rulers
  essentially unchanged.

### 6.2 Trait decomposition works — with a specific implementation

**Multi-Trait Specialization** runs *"several independent conversations, one per trait"*, each
(1) retrieving *"quotes relevant to the trait"*, (2) giving verbal evaluations per quote, (3) scoring
against predefined criteria. Reported QWK gains: **TOEFL11 0.025 → 0.462**; **ASAP 0.205 → 0.560** ✅
([arXiv 2404.04941](https://arxiv.org/html/2404.04941v2)). The independent-conversation detail *is*
the halo firewall.

This is the strongest available argument for the harness change suggested in v6's operational note —
one trait per call, self-contained scale in context.

### 6.3 Two findings that cut against v6's design, recorded rather than buried

1. **More traits can mean worse per-trait agreement.** On the same study, six-trait ELLIPSE topped out
   at **QWK 0.321** while holistic ASAP 2.0 reached **0.601** ✅
   ([arXiv 2604.00259](https://arxiv.org/html/2604.00259)). Four traits is a reasonable middle ground;
   this is a reason not to decompose further.
2. **For analytic scoring specifically, longer rubric prose has been found to *underperform* concise
   keyword prompts** — *"concise keyword-based prompts generally outperform longer rubric-style
   prompts in multi-trait analytic scoring"* ✅ (same paper). v6 is long. That is a real, testable risk,
   and it is the natural v6 experiment: a keyword-condensed variant of the same four scales, scored
   against the same 100 essays.

Popham's third failure mode — **dysfunctional detail**, rubrics so elaborate that *"busy teachers won't
have anything to do with them"* ✅ — is the human-facing version of the same objection. v6 is at four
criteria (inside Popham's recommended 3–5) but well past his one-to-two-page guidance.

### 6.4 Expected artifacts to check for in `predictions_v5.csv`

- **Central-tendency compression.** *"Model-assigned scores exhibit consistently lower standard
  deviations than human annotations for nearly all traits"* ✅. Compare trait-score SDs against the v3
  graded run.
- **Conventions harshness.** Models systematically under-score grammar/conventions traits — a bias of
  **−1.04** on ELLIPSE with keyword prompting ✅. If v6's conventions distribution shifts down versus
  v3, suspect the grader before the rubric.
- **Trait-score uniformity.** If all four traits agree on most essays, halo has won; try the
  one-trait-per-call harness (§6.2).

### 6.5 On QWK as the acceptance metric

Worth knowing before reading any v6-vs-v4 delta as real. A 2023 evaluation of QWK for AES documents
five failure modes ✅ ([EDM 2023 PDF](https://scholarlypublications.universiteitleiden.nl/access/item:3665152/download)):
score-resolution sensitivity (0.784 vs 0.720 on identical rater data depending on the combination
rule); the kappa paradox (99.8% raw agreement can fall below a 0.7 threshold); prevalence effects
(identical 0.66 percent agreement yielding QWK 0.599–0.765); position sensitivity (0.599 → 0.855 by
rearranging where on the diagonal agreements fall); and inapplicability beyond two raters. Its
recommendation is to report **linear weighted kappa** alongside, and Krippendorff's α for multi-rater
settings.

A companion paper's illustration is worth pinning up: for one identical set of predictions with a
systematic one-point offset, *"unweighted, linear-weighted, and quadratic-weighted κ are −3/13, 1/3,
and 5/7"* ✅ ([arXiv 2606.00093](https://arxiv.org/html/2606.00093)).

This does not change the project's metric — QWK is the competition's own — but v6's evaluation should
report **exact and adjacent agreement, LWK, and MAE** alongside it, as the existing harness already
partly does. Reference points for calibration: human exact agreement on analytic writing traits sits
around **55–75%**, with within-one-point agreement **>90%** ✅ (Jonsson & Svingby 2007,
[ERIC EJ796733](https://eric.ed.gov/?id=EJ796733)).

---

## 7. What to expect from v6, stated before running it

Recording the prediction in advance so the result can't be narrated after the fact — consistent with
how #49 handled v4's one-essay delta and #54 handled the noise floor.

### The primary hypothesis is not QWK

#54 established that the remaining headroom is **trait-score variance**, not aggregation: 33/100
identical trait vectors across two runs that should have produced identical ones, a 1,688-variant
aggregation sweep that scored negative out of sample, and a monotone-relabel ceiling of 0.665 against
v4's 0.658. It also established the noise floor: bootstrap 95% CI on v4's QWK is **[0.542, 0.749]**,
SE ≈ 0.053, so the entire v1→v4 gain of +0.064 is 1.2 SE.

**So the v6 result to report is run-to-run trait agreement, and QWK is secondary.** The measurement is
cheap and is the one that can actually detect the intended effect: **grade the same 100 essays twice
under v6 and compare trait vectors**, exactly as #54 did for v3-vs-v4.

**Stated prediction.** v6 should raise per-trait run-to-run agreement, and should raise it **most on
conventions (61%) and argumentation (62%)** — the two traits #53 identifies as hardest to isolate from
a whole-essay anchor, and therefore the two with the most to gain from a dedicated scale. Organization
(80%) and development (74%) should move less. **If conventions and argumentation do not improve, v6's
core claim is wrong**, regardless of what QWK does, and the ladders for those two traits are the first
thing to re-examine — most likely Conventions rung 5 (the sentence-variety requirement, which is the
newest constraint in that scale) and Argumentation rung 5 (the three-route disjunction, which is the
most complex single rung in the file).

A secondary prediction, cheaper still: **`evidence_notes` should now name a rung**, so any two runs
that disagree on a trait can be diffed at the rung level. Under v5 a 4-vs-3 conventions split is
untraceable; under v6 it should localize to a specific question. If the disagreements do *not*
localize — if two runs cite the same rung and still differ — the problem is the rung's wording, not
the scale's structure, and that is a much more actionable finding than a QWK delta.

### QWK is uncertain, and three specific things could push it down

1. **The gate is coarse and absorbs half the corpus.** 49 of 100 essays are decided by the
   severe-weakness gate before any weighting is consulted (#48). Better-defined traits change *which*
   essays trip it, but the gate's coarseness limits how far trait-level refinement can propagate to
   the holistic score. A large trait-level change with a small holistic footprint is a plausible and
   *expected* outcome — and per #54, comparing on shared trait scores gives a ΔQWK CI four times
   narrower than re-grading does, so a re-graded v5-vs-v6 delta will be very hard to call.
2. **v6 deliberately departs from documented rater behaviour in two places.** Impedance-based rather
   than stigma-based conventions banding (§4.3), and hard length-neutrality on Development (§3.6)
   against a ground truth that itself correlates with length at r ≈ .71. Both are validity choices
   that can cost agreement with the humans who produced the labels. They are made knowingly; see #61.
3. **Rubric length is a live risk for analytic LLM scoring** (§0.1, §6.3) — and more so under the
   sub-120B constraint than it was for the frontier model that produced every number in the repo so
   far.

### Suggested additions to `evaluation/results_v6.md`

Beyond the existing harness:

- **Run-to-run trait agreement, per trait**, v6 vs. the #54 baseline (61/62/80/74). This is the
  headline number.
- **Rung-level diff of disagreeing essays**, from `evidence_notes` — where two runs disagree, do they
  cite the same rung?
- **Inter-trait correlation matrix**, v5 and v6 side by side. Falling correlation with agreement held
  is a win even if QWK does not move (§0, halo).
- **Per-trait score distributions** vs. v5's run — watch for central-tendency compression and for
  conventions harshness, both documented LLM-grader artifacts (§6.4).
- **Count of essays whose trait vector changed versus whose holistic score changed.** These will
  differ a lot, and the difference should be visible rather than inferred.
- **Bootstrap CI on any QWK delta**, per #54, so a within-noise result is reported as within noise.

---

## 8. Proposed `decisions_log.md` entries (#55–61)

Drafted in the log's existing voice; #50–54 are taken by v5.

55. **v6 replaces the holistic score-band anchors with four per-trait scales, which is the change #53
    named as next.** v5 left the grader asking for trait scores while giving it whole-essay
    descriptors to decompose on every judgment. v6 decomposes them once, in the file, and quotes the
    exact official clause each band came from. **Nothing about the grader's job otherwise changes** —
    the task still stops at four trait scores, the gate and the holistic score still run in
    `v4_holistic()`, and the output schema is still v5's six fields. v6 gives the grader no new rule to
    execute; it replaces the reference material it reads.

56. **The decomposition is a re-projection of the official rubric, not a new instrument.** The official
    text already lists the same four dimensions in the same order at every score point, separated by
    semicolons; v6 reads that table column-wise instead of row-wise. Every band carries the verbatim
    source clause, sic errors preserved, so the anchoring is auditable rather than asserted. Three
    structural facts came out of doing this and are recorded because they are not obvious on a first
    read: the language clause is *two* clauses at every band (facility, then errors) — which is why
    Conventions has separate word-choice, sentence-structure and error sub-criteria; the point-of-view
    and evidence clauses are **fused and disjunctive at score 1 only** ("develops no viable point of
    view… **or** provides little or no evidence"), so Argumentation 1 and Development 1 share a source
    clause; and the official 5-to-6 difference in organization is three word insertions ("clear**ly**
    focused", "**clear** coherence", "**smooth** progression"), which is precisely why extension was
    needed and why every extended clause is marked `[ext]`.

57. **Each trait's decision procedure is a five-rung yes/no ladder, because #50's constraint binds
    here too.** A per-trait rubric that asked the grader to score four sub-criteria and combine them
    would reintroduce exactly the arithmetic #50 deleted from the prompt. So the operative instrument
    is a ladder climbed from the bottom, stopping at the last YES: no arithmetic, no branching, no
    sub-scores, and — because the ladder is total and ordered — no essay that fits no band. The four
    sub-criteria still structure the written bands, since that is what makes adjacent bands
    discriminable, but they are reference for hard calls rather than steps. Two AES results support
    the shape: rubric-refinement experiments converge on conditional "if X is observed, assign s"
    rules, and checklist-compiled rubrics are measurably order-invariant where free-form rubric
    scoring is not.

58. **The primary v6 metric is run-to-run trait agreement, not QWK — and the prediction is stated
    before the run.** #54 showed the headroom is trait variance, not aggregation, and that QWK's SE
    (≈0.053) swallows any single-iteration delta. v6 should raise per-trait agreement **most on
    conventions and argumentation** (61% and 62%), the two traits #53 identified as hardest to isolate
    from whole-essay anchors, and less on organization and development (80%, 74%). If those two do not
    improve, v6's core claim is wrong regardless of QWK. Measurement is a double-grade of the same 100
    essays, as #54 did.

59. **`evidence_notes` now names the deciding rung, which makes disagreement diagnosable.** Additive,
    no schema change, parses under the existing reader. The point is that a 4-vs-3 conventions split
    between two runs is currently untraceable; naming the rung localizes it. If two runs cite the *same*
    rung and still differ, the problem is that rung's wording rather than the scale's structure —
    a more actionable finding than any aggregate metric.

60. **Three rules in v6 contradict what an untrained grader would do, and each has evidence behind
    it.** (a) *Do not score transition words* — local cohesion indices correlate **negatively** with
    expert quality ratings (content-word overlap r = −0.279, logical connectives r = −0.227) while
    global paragraph-to-paragraph cohesion predicts positively; a grader rewarded for "furthermore"
    anti-correlates with expert judgment. (b) *Do not count evidence* — elaboration depth predicts
    quality at b = 0.516 while raw evidence counts manage r = .188, and on PERSUADE-lineage data it is
    the hierarchical *relations* between argument elements (r = .309–.323) rather than their presence
    that tracks quality. (c) *Do not reward syntactic complexity* — clauses per T-unit correlates
    **negatively** with quality in persuasive writing specifically (Beers & Nagy 2009), which is our
    genre. Also recorded: the conventional five-paragraph shape caps Organization at 4, on the
    strength of an LCA over 17,451 grade 6–8 essays where conventional intro–body–conclusion tops out
    at 2.24 on a 0–4 organization rubric — the middle of the scale, and the *highest* of eight
    structural patterns, so a scale whose upper bands are reachable by executing the standard shape
    has nothing left to discriminate 5 from 6.

61. **Two v6 choices knowingly depart from how human raters behave, and may cost QWK.** First,
    Conventions bands on **comprehension**, not error type. The impedance ladder is native to the
    official rubric — its own bands run "some errors" → "an accumulation" → "meaning somewhat
    obscured" → "persistently interfere with meaning" — so v6 finishes it rather than importing it.
    But the error-gravity literature shows raters keying on **prestige-dialect deviation** at least as
    much as on comprehension: Hairston's most-severe tier is nonstandard verb forms and double
    negatives, which are perfectly comprehensible and are features of stigmatized varieties of English.
    Choosing comprehension is a validity commitment with an equity rationale, made knowing it may
    disagree with the labels. Second, **counterargument is one route to the upper Argumentation bands,
    never the requirement** — for it, rebuttal sits at level 4 of 5 in ETS's argumentation progression
    and only *answered* (not merely acknowledged) counterarguments raise rated quality; against it, the
    official rubric never mentions counterargument, unprompted college writers average 0.15 rebuttals
    per essay, and "few children in any grade" use opposition features at all, so gating on it would
    empty the band and decorrelate from the gold labels. The alternative routes are explicit warranting
    and appropriate qualification; **the qualification route is the least evidenced of the three and is
    the first clause to cut if band 5 misbehaves.**

---

## 9. Verification status — read before citing anything from this file

**✅ Verified (primary or official text obtained):** PERSUADE argumentation effectiveness rubric (all
21 cells); both PERSUADE SAT holistic rubrics; Deane et al. 2015 progression tables; Felton & Kuhn
2001 figures; Crossley, Tian & Wan 2022 (ten analytic dimensions, PCA, correlations); the 2025
Frontiers LCA; TAACO local/global cohesion findings; Morris et al. 2025 four writing profiles;
Smarter Balanced argumentative/explanatory/conventions rubrics and scoring gloss; AP Lang 2025 Row B;
STAAR argumentative rubric; TOEFL iBT rubrics; ACT writing rubric band lead sentences; Beers & Nagy
2009; the elaboration depth/breadth study; e-rater GUM microfeature findings; Frontiers 2020 length
study; Kobrin/Deng/Shaw; Popham 1997; Brookhart 2013/2018; Humphry & Heldsinger 2014; Jonsson &
Svingby 2007; the MFRM criterion-order study; SCALE and UF rubric guidance; NAEP framework dimension
names; MTS / Rulers / Reflect-and-Revise / QWK-critique AES papers.

**⚠️ Secondhand or partially verified:** IELTS Task 2 descriptors (third-party mirror — **verify
before quoting publicly**); 6+1 Traits (short excerpts only; full reproduction declined on copyright
grounds); Crossley & McNamara Coh-Metrix correlations; Plakans & Gebril; Du & List; RTA rubric
criteria; Wolfe/Britt/Butler; Nussbaum & Kardash; Knudson; Ferretti & Graham; Hairston; Santos;
Perelman's length gradient; Howard on patchwriting; Bamberg via Knoch.

**❌ Not verified — cited as leads only:** Bamberg's actual coherence-scale level descriptors;
**Stapleton & Wu (2015)** argument-quality rubric (highest-value gap for Argumentation); Kuhn (1991)
coding categories; Witte (1983) topical-structure/quality correlations; Connors & Lunsford (1988) and
Lunsford & Lunsford (2008) error data; Vann, Meyer & Lorenz (1984) primary; Burt & Kiparsky
global/local definitions; NAEP Appendix C 6-level descriptors; Jacobs et al. (1981) cell wording;
Lu (2011) findings; Kyle & Crossley source-based lexical findings; the LLM-ELL-bias
mechanistic-interpretability paper; **the PERSUADE analytical rating form's per-level 1–6 descriptors
for its ten dimensions** (highest-value gap overall — recommend contacting Scott Crossley directly).

---

## Sources

**Rubric design and measurement**
[Popham 1997, What's Wrong—and What's Right—with Rubrics](https://www.ascd.org/el/articles/whats-wrong-and-whats-right-with-rubrics) ·
[Brookhart 2013, How to Create and Use Rubrics](https://www.geocities.ws/bdktraining/pdfkur/How%20to%20Create%20and%20Use%20Rubrics%20for%20Formative%20Assessment%20and%20Grading%20(%20PDFDrive%20).pdf) ·
[Brookhart 2018, Appropriate Criteria: Key to Effective Rubrics](https://www.frontiersin.org/journals/education/articles/10.3389/feduc.2018.00022/full) ·
[Jonsson & Svingby 2007 (ERIC)](https://eric.ed.gov/?id=EJ796733) ·
[Dawson 2017, Assessment rubrics: towards clearer and more replicable design (ERIC)](https://eric.ed.gov/?id=EJ1129724) ·
[Humphry & Heldsinger 2014, Common structural design features of rubrics](https://journals.sagepub.com/doi/10.3102/0013189X14542154) ·
[Rezaei & Lovorn 2010 (ERIC)](https://eric.ed.gov/?id=EJ881105) ·
[Lai, Wolfe & Vickers 2015, Illusory and True Halo in Writing Scores](https://journals.sagepub.com/doi/abs/10.1177/0013164414530990) ·
[Rating criteria order and halo (MFRM)](https://link.springer.com/article/10.1186/s40468-020-00115-0) ·
[Holistic vs analytic rater reliability (G-study)](https://link.springer.com/article/10.1186/s40468-015-0014-4) ·
[Analytic vs holistic large-scale assessment (German, PDF)](https://d-nb.info/1349386553/34) ·
[SCALE Quality Rubric Checklist](https://www.bates.edu/research/files/2018/07/SCALE-Quality-Rubric-Checklist.docx.pdf) ·
[UF Writing Effective Rubrics 2025](https://www.assessment.aa.ufl.edu/media/assessmentaaufledu/faculty-resources/Writing-Effective-Rubrics-2025.pdf) ·
[WIDA Writing Scoring Rubric technical report](https://wida.wisc.edu/sites/default/files/resource/Technical-Report-Development-New-WIDA-Writing-Scoring-Rubric-Grades-1-12.pdf) ·
[Diederich, French & Carlton 1961 (ERIC)](https://eric.ed.gov/?id=ED002172)

**Operational rubrics**
[Smarter Balanced Argumentative Rubric, Gr 6–11](https://portal.smarterbalanced.org/library/en/performance-task-writing-rubric-argumentative.pdf) ·
[Smarter Balanced Explanatory Rubric](https://portal.smarterbalanced.org/library/en/performance-task-writing-rubric-explanatory.pdf) ·
[Smarter Balanced Scoring Guide for ELA Full Writes](https://portal.smarterbalanced.org/library/en/scoring-guide-for-ela-full-writes.pdf) ·
[Smarter Balanced Scoring Specifications](https://technicalreports.smarterbalanced.org/scoring_specs/_book/scoringspecs.html) ·
[Understanding Proficiency, Gr 8 Evidence/Elaboration samples](https://understandingproficiency.wested.org/wp-content/uploads/2015/11/Gr8_E-E_Unscored_Samples.pdf) ·
[AP English Language Scoring Guidelines 2025](https://apcentral.collegeboard.org/media/pdf/ap25-sg-english-language-set-1.pdf) ·
[STAAR Argumentative/Opinion Rubric Gr 6–English II](https://tea.texas.gov/sites/default/files/tx-staar-arg-opinion-rubric-g6-e2.pdf) ·
[ACT Writing Test Scoring Rubric](https://www.act.org/content/dam/act/unsecured/documents/Writing-Test-Scoring-Rubric.pdf) ·
[TOEFL iBT Writing Rubrics (ETS)](https://www-stg-sp.es.ets.org/pdfs/toefl/toefl-ibt-writing-rubrics.pdf) ·
[6+1 Trait Rubrics, Grades 3–12](https://educationnorthwest.org/sites/default/files/resources/traits-rubrics-3-12.pdf) ·
[IELTS Task 2 band descriptors (third-party mirror — verify)](https://www.ielts-mentor.com/files/ielts-writing-task2-band-description.pdf) ·
[NAEP 2011 Writing Framework](https://www.cde.state.co.us/sites/default/files/documents/assessment/documents/naep/writing_framework_2011.pdf) ·
[CCSS Writing, Grades 9–10](https://www.thecorestandards.org/ELA-Literacy/W/9-10/)

**Corpus and its own instruments**
[PERSUADE Corpus 2.0 (GitHub)](https://github.com/scrosseye/persuade_corpus_2.0) ·
[ASAP 2.0 Corpus (GitHub)](https://github.com/scrosseye/ASAP_2.0) ·
[Crossley, Tian & Wan 2022, Argumentation Features and Essay Quality (JoWR)](https://www.jowr.org/jowr/article/download/831/872/1032) ·
[Morris et al. 2025, Distinguishing Effective Writing Styles in the PERSUADE Corpus (JoWR)](https://www.jowr.org/jowr/article/download/1491/1000/6213) ·
[Kaggle: Feedback Prize — Evaluating Student Writing](https://www.kaggle.com/competitions/feedback-prize-2021) ·
[Kaggle: Feedback Prize — Predicting Effective Arguments](https://www.kaggle.com/competitions/feedback-prize-effectiveness)

**Organization and coherence**
[Frontiers in Education 2025, LCA of essay structure (17,451 essays)](https://www.frontiersin.org/journals/education/articles/10.3389/feduc.2025.1569529/full) ·
[Crossley, Kyle & McNamara 2016, TAACO (Behavior Research Methods)](https://link.springer.com/article/10.3758/s13428-015-0651-7) ·
[Crossley & McNamara, Coh-Metrix analyses of essay quality](https://www.academia.edu/104603107/Understanding_expert_ratings_of_essay_quality_Coh_Metrix_analyses_of_first_and_second_language_writing) ·
[Knoch 2007, comparison of two coherence rating scales](https://www.academia.edu/5597017/) ·
[Lee, Helping Students Develop Coherence (English Teaching Forum)](https://americanenglish.state.gov/files/ae/resource_files/02-40-3-i.pdf)

**Argumentation**
[Deane et al. 2015, Discuss and Debate Ideas learning progression (ERIC)](https://files.eric.ed.gov/fulltext/EJ1109288.pdf) ·
[Felton & Kuhn 2001, Development of Argumentive Discourse Skill (PDF)](https://www.tc.columbia.edu/faculty/dk100/faculty-profile/files/001_Thedevelopmentofaugumentivediscourseskills.pdf) ·
[Nussbaum & Kardash 2005, Goal Instructions and Counterargument Generation](https://www.academia.edu/4387838/) ·
[Wolfe, Britt & Butler 2009, Argumentation Schema and the Myside Bias](https://journals.sagepub.com/doi/abs/10.1177/0741088309333019) ·
[Knudson 1992, Development of Written Argumentation (ERIC)](https://eric.ed.gov/?id=EJ456314) ·
[Ferretti & Graham 2019, Argumentative writing: theory, assessment, instruction](https://link.springer.com/article/10.1007/s11145-019-09950-x) ·
[Crowhurst, argumentative writing development (ERIC ED299596)](https://files.eric.ed.gov/fulltext/ED299596.pdf) ·
[Stapleton & Wu 2015 (JEAP — paywalled, unretrieved)](https://www.sciencedirect.com/science/article/abs/pii/S1475158514000824)

**Development and evidence**
[Elaboration and contextualization moves (JoWR)](https://www.jowr.org/jowr/article/download/850/932/2449) ·
[Rahimi, Litman, Correnti et al., RTA (IJAIED)](https://link.springer.com/article/10.1007/s40593-017-0143-2) ·
[Du & List 2021, Evidence Use in Argument Writing (RRQ)](https://ila.onlinelibrary.wiley.com/doi/abs/10.1002/rrq.366) ·
[Plakans & Gebril 2013, Source text use as a predictor of score](https://www.academia.edu/3727957/) ·
[Howard, A Plagiarism Pentimento (Citation Project)](http://www.citationproject.net/wp-content/uploads/2018/03/Howard-Plagiarism-Pentimento.pdf)

**Conventions and language**
[Beers & Nagy 2009, Syntactic complexity as a predictor of adolescent writing quality](https://link.springer.com/article/10.1007/s11145-007-9107-5) ·
[Hairston 1981, Not All Errors Are Created Equal (PDF)](https://teaching.berkeley.edu/sites/default/files/not_all_errors_are_created_equal.pdf) ·
[Santos 1988, Professors' Reactions to NNS Academic Writing](https://onlinelibrary.wiley.com/doi/abs/10.2307/3587062) ·
[A Systematic Review of Error Gravity Articles (1969–1999)](https://www.nepjol.info/index.php/mrj/article/download/73470/56240/213760) ·
[e-rater GUM microfeatures investigation (ERIC EJ1168485)](https://files.eric.ed.gov/fulltext/EJ1168485.pdf) ·
[Crossley & Kim, Linguistic Features of Writing Quality and Development (JWA)](https://wacclearinghouse.org/docs/jwa/vol6/crossley-kim.pdf) ·
[Measuring Lexical Diversity: The Twofold Length Problem (arXiv)](https://arxiv.org/pdf/2307.04626) ·
[CCCC Statement on Second Language Writing and Multilingual Writers](https://cccc.ncte.org/cccc/resources/positions/secondlangwriting/)

**Length bias**
[Is a Long Essay Always a Good Essay? (Frontiers in Psychology)](https://www.frontiersin.org/journals/psychology/articles/10.3389/fpsyg.2020.562462/full) ·
[Kobrin, Deng & Shaw, Does Quantity Equal Quality? (PDF)](https://www.testpublishers.org/assets/documents/Volume_8_issue_1Does_quantity_equal.pdf) ·
[Perelman, Construct Validity, Length, Score, and Time (WAC Clearinghouse)](https://wacclearinghouse.org/docs/books/wrab2011/chapter7.pdf)

**AES and LLM grading**
[Multi-Trait Specialization (arXiv 2404.04941)](https://arxiv.org/html/2404.04941v2) ·
[RMTS, rationale-augmented multi-trait scoring (NAACL Findings 2025)](https://aclanthology.org/2025.findings-naacl.322.pdf) ·
[Rulers: Locked Rubrics and Evidence-Anchored Scoring (arXiv 2601.08654)](https://arxiv.org/html/2601.08654v1) ·
[Reflect-and-Revise rubric refinement (arXiv 2510.09030)](https://arxiv.org/html/2510.09030) ·
[LLM Essay Scoring Under Holistic and Analytic Rubrics (arXiv 2604.00259)](https://arxiv.org/html/2604.00259) ·
[Evaluating QWK as the Standard AES Metric (EDM 2023)](https://scholarlypublications.universiteitleiden.nl/access/item:3665152/download) ·
[Agreement Measurement for Rubric-based LLM Judges (arXiv 2606.00093)](https://arxiv.org/html/2606.00093) ·
[Ke & Ng, Automated Evaluation of Writing — 50 Years and Counting (ACL 2020)](https://aclanthology.org/2020.acl-main.697.pdf)
