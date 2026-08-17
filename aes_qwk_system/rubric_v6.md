# AES Grading Rubric v6

Scale: **1 (lowest) to 6 (highest)**, matching the official PERSUADE / Learning Agency Lab AES 2.0 scale.

> **v6 is the change v5 said it was leaving for next.** `rubric_v5.md` closes with a known
> limitation: the score-band anchors are the six *holistic* descriptors, so a grader asked for four
> trait scores has to mentally decompose whole-essay text on every judgment — and run-to-run
> agreement is worst on exactly the two traits whose clauses are hardest to isolate (**conventions
> 61%, argumentation 62%**, against organization 80% and development 74%). v6 replaces those anchors
> with **four per-trait scales of six levels each, extracted from the same official text**, which is
> the fix `decisions_log.md` #53 names. See #55–61.

> **Everything v5 changed about the grader's job stays changed.** The grader's task still stops at
> the four trait scores. The severe-weakness gate, the band placement, the weighted mean and the
> threshold tests still run in `grading/grade_essays.py` (`v4_holistic()`), not here. The output
> schema is still six fields. **v6 does not give the grader a single new rule to execute** — it
> replaces the *reference material* the grader reads while assigning four integers, and nothing else.

> **v6 must be re-graded, not derived.** v4 could be derived from v3's trait scores because a weight
> change only touches aggregation (#46). v6 changes what a grader does *when assigning a trait
> score*, so `predictions_v6.csv` requires a genuine grading run. Any v6-vs-v5 comparison that
> reuses v5's trait scores measures nothing.

> **Designed for the model constraint that motivated v5.** #50 moved the holistic rule into code
> because sub-120B models will not follow a seven-step conditional. v6 respects the same
> constraint: each trait's decision procedure is a **ladder of five yes/no questions**, climbed from
> the bottom. There is no arithmetic, no branching, no sub-score to combine, and no case where an
> essay fits no band. The fuller band descriptions below the ladder are reference for hard calls,
> not additional steps.

## How v6 is anchored to the official rubric

Every band carries an **Official anchor** line quoting, verbatim, the clause the official
PERSUADE/SAT holistic rubric uses for *that dimension* at *that score point* — taken directly from
`rubric_official_persuade.md`, including the source PDFs' own grammatical slips, marked *[sic]*.
The anchors are the audit trail, so they are reproduced exactly rather than tidied.

Three structural facts about the official rubric made this decomposition possible, and are worth
stating because they are not obvious from reading it once:

1. **The official rubric already decomposes into exactly these four dimensions**, in the same order,
   at every score point — each band is a semicolon-separated list of clauses covering point of view /
   critical thinking, evidence, organization, and language. v6's four scales are that list read
   column-wise instead of row-wise. This is a re-projection of the official text, not a new instrument.
2. **The language clause is itself two clauses at every band** — *facility with language* (vocabulary
   and sentence structure) and *errors in grammar, usage, and mechanics* — which is why Conventions
   below separates word choice, sentence structure, and error accuracy.
3. **At score 1 only, the point-of-view and evidence clauses are fused and disjunctive**: *"develops
   no viable point of view on the issue, **or** provides little or no evidence to support its
   position."* So Argumentation 1 and Development 1 share a source clause, and either alone is
   sufficient for the official band 1. Both scales reflect this.

Where the official language runs out — and it does, badly, at the top: the entire official difference
between an organization 5 and a 6 is the insertions "clear**ly** focused", "**clear** coherence",
"**smooth** progression — the extension is drawn from the writing-assessment literature and cited in
`rubric_v6_research_basis.md`. **Where a band tightens or extends the official language rather than
restating it, it is marked [ext].** Nothing below reverses the official rubric's ordering; the
extensions decide cases it leaves open.

## Trait weights (applied in code, not by the grader) [v4, unchanged]

| Trait | Official rubric dimension | Weight |
|---|---|---|
| Argumentation | point of view and critical thinking | **0.35** |
| Organization | organization / coherence | 0.25 |
| Development | evidence and support | 0.25 |
| Conventions | language | **0.15** |

**The grader does not use this table.** It is here so a reader of this file knows what happens to the
four scores downstream, and to make explicit that no trait should be inflated or deflated in
anticipation of its weight. Score each trait on its own merits; the weighting is applied once,
afterwards, by `v4_holistic()`.

## Task given to the grader

You are a high school english teacher with 10 years experience. You are grading your students' assignments by determining the extent to which they align with your standards, as outlined on the provided rubric. You are scoring a student argumentative/source-based essay written in response to a prompt. The prompt may not be visible to you. If no prompt is available, generate a hypothesis prompt so that you may grade the essay against what it set out to do. If the essay draws on a provided source text or texts, evidence should be evaluated against how well it's drawn from those sources; if it doesn't (an independent-writing prompt), evaluate evidence and reasoning on their own merits. Then, score the essay on its own internal merits: point of view and critical thinking, use of evidence/support, organization/coherence, and use of language.

## Required process

**These five steps are the whole task.** The gate and the holistic score run in code. Stop after
step 5.

Do step 1 first. **Steps 2–5 may be done in any order** — and if the harness supports it, should be
presented in a randomized order across essays, for the reason given under *Cross-trait firewalls*.

1. **Evidence extraction.** Identify 2–3 concrete pieces of evidence of the essay's argumentative
   quality: the main claim, key supporting reasons/evidence (noting whether they're drawn from a
   provided source text, if one exists), and how directly they connect to the claim. Write these down
   before scoring anything.

2. **Organization (1–6).** Score against the **Organization scale**.
3. **Development / Evidence & Support (1–6).** Score against the **Development scale**.
4. **Conventions / Language (1–6).** Score against the **Conventions scale**.
5. **Point of View / Argumentation (1–6).** Score against the **Argumentation scale**.

**Stop here.** Return the four trait scores and your evidence notes. Do not combine them, do not
assign a holistic score, and do not decide a gate.

---

# The four trait scales

## How to score a trait

Each scale opens with a **ladder**: five yes/no questions. **Start at 1 and climb. Your score is the
last rung you can answer YES to.** Once you hit a NO, stop — do not skip a rung because a higher one
also looks true.

Below each ladder, the same six bands are written out in full against four fixed sub-criteria
**(a)–(d)** that appear at every band in the same order and always ask the same question. **The
ladder decides the score; the full bands are reference for hard calls.** They agree by construction —
each rung is the thing that separates its band from the one below.

Two reading rules:

- **Descriptors are floors, not descriptions.** An essay that *exceeds* a band still satisfies it.
  Bands are separated by what the **higher** band adds, never by what the lower band tolerates. "Most
  support is specific" at band 3 does not exclude an essay whose support is specific throughout.
- **Score each trait against its own scale only.** Do not let a judgment made under one trait carry
  into another — see *Cross-trait firewalls*. Each scale is self-contained so it can be extracted and
  used on its own.

---

## Trait 1 — ORGANIZATION (organization / coherence)

### Ladder — climb from 1, stop at the last YES

| Reach | Ask |
|---|---|
| **2** | Does the text divide into parts that do different jobs? |
| **3** | Is a controlling idea stated somewhere, in the essay's own words? |
| **4** | Is it stated early and held, with an opening and a closing present, and does every body part relate to it? |
| **5** | Is there **no** pair of body parts that could swap places without loss? |
| **6** | Does the sequence itself make an argumentative move you can name — concession before rebuttal, weakest to strongest, principle then hard case, objection then answer? |

**Sub-criteria used in the full bands:**
**(a) Controlling idea** — is a position governing the whole text, and where is it stated?
**(b) Frame** — do the opening and closing do work, or merely occupy the slots?
**(c) Progression between parts** — do the parts stand in a recoverable relation to each other and
to the controlling idea?
**(d) Unity within parts** — does each idea-unit do one job?

### 6
> **Official anchor:** *"the essay is well organized and clearly focused, demonstrating clear coherence and smooth progression of ideas"*

(a) A controlling idea governs every part; nothing sits outside it.
(b) The opening establishes what is at stake and what the essay will do; the closing lands the
argument somewhere the opening did not already put it.
(c) **[ext]** The sequence carries an argumentative move the reader can name. The order is not merely
defensible; it is *doing* something.
(d) Every idea-unit does one identifiable job and finishes it.

### 5
> **Official anchor:** *"the essay is well organized and focused, demonstrating coherence and progression of ideas"*

(a) A controlling idea is stated early and holds throughout.
(b) Opening and closing both do work; the closing does more than restate the opening in new words.
(c) **[ext]** The order is **motivated**: parts build, later material depends on earlier material,
and no pair of body parts could swap places without loss.
(d) Idea-units are unified.

### 4
> **Official anchor:** *"the essay is generally organized and focused, demonstrating some coherence and progression of ideas exhibits adequate"* [sic — the source PDF's own truncation]

(a) A controlling idea is stated early and holds.
(b) A frame is present: an opening that orients and a closing that closes, however conventionally.
The closing may add little.
(c) **[ext]** Every body part relates to the controlling idea, but at least one pair could swap places
without loss. The essay is a set of supports rather than a sequence.
(d) Idea-units are unified; at most one wanders and returns.

### 3
> **Official anchor:** *"the essay is limited in its organization or focus, or may demonstrate some lapses in coherence or progression of ideas displays"* [sic]

(a) A controlling idea is stated but **weakly located** — late, buried mid-essay, or drifting far
enough by the end that the position has moved.
(b) The frame is incomplete or perfunctory: an opening with no orientation, a closing that stops
rather than closes, or one of the two missing.
(c) Most parts relate to the controlling idea, but at least one does not — a digression, or a part
that repeats an earlier one without adding to it.
(d) Unity breaks at least once: an idea-unit starts one job and finishes another.

### 2
> **Official anchor:** *"the essay is poorly organized and/or focused, or demonstrates serious problems with coherence or progression of ideas"*

(a) A controlling idea is present but the reader has to assemble it — only inferable from the body, or
contradicted elsewhere.
(b) No functioning frame: the essay begins mid-argument, ends without closing, or both.
(c) Parts follow each other without a recoverable relation; the reader rereads to work out how one
part bears on the last.
(d) Idea-units do not hold together — a single unit carries several unrelated jobs.

### 1
> **Official anchor:** *"the essay is disorganized or unfocused, resulting in a disjointed or incoherent essay"*

(a) No controlling idea is recoverable anywhere.
(b) No frame.
(c) The text does not divide into parts serving distinct functions; order is arbitrary.
(d) No idea-unit is internally coherent.

### Decision rules — Organization

- **Do not score transition words.** Do not raise a score because the essay uses *furthermore*,
  *in conclusion*, *first/second/third*, or repeats key terms across sentences; do not lower one for
  their absence. Local cohesive devices are, in this corpus lineage, characteristic of *lower*-scoring
  essays. Judge whether **each part's ideas bear on the previous part's and on the controlling idea**
  — a relation you could state — not whether the connection is signposted.
- **Executing the conventional shape cleanly is a 4, not a 5.** An introduction, three on-topic
  supports and a conclusion, done competently, is a complete description of a 4. The five-paragraph
  form is **not itself a cap**: such an essay reaches 5 if no two body parts could swap, and 6 if the
  sequence makes a nameable argumentative move. What caps at 4 is *interchangeable supports*, not
  *five paragraphs*.
- **Paragraphing is a formatting fact, not an organization fact.** Do not lower anything because the
  essay is unparagraphed or oddly paragraphed. Where paragraph breaks exist, use them as the
  idea-units; where they do not, use the idea-units the text actually has.
- **Do not score length or paragraph count.** A three-part essay whose parts build scores 5. A
  six-part essay of interchangeable supports does not.
- **Do not score style or register.** Formal, academic, source-reporting and conversational essays all
  reach 6 by the same route: the reader can always say why each part is where it is.

---

## Trait 2 — DEVELOPMENT (evidence and support)

> **Before climbing: discard irrelevant support.** Set aside any support that does not bear on the
> claim it is attached to, and score what remains. **If everything is discarded this way, the score
> is 1.** Relevance never earns partial credit at any band, so it is handled once, here, rather than
> repeated in the bands.

### Ladder — climb from 1, stop at the last YES

| Reach | Ask |
|---|---|
| **2** | Does the essay offer any support for its position? |
| **3** | Is at least one piece of support **specific** — a named case, a particular, a figure, a realized example? |
| **4** | Does the essay **state the connection** between support and claim for at least some of its support? |
| **5** | Is the support specific throughout, **and** is most of it explained in a way that adds something the support alone did not say? |
| **6** | Is **every** piece of support specific **and** explained that way? |

**Sub-criteria used in the full bands:**
**(a) Sufficiency** — does every claim that needs support have it?
**(b) Specificity** — is the support named and concrete, or a general gesture?
**(c) Elaboration** — is the connection from support to claim *stated*, and does stating it add
anything the support alone did not say?
**(d) Attribution and transformation** — where the essay uses language or facts it did not originate
(a provided source, a quoted authority, a named study), is that material transformed and put to work,
or reproduced? *If the essay uses no borrowed material, (d) does not apply.*

### 6
> **Official anchor:** *"using clearly appropriate examples, reasons, and other evidence to support its position"* — source-based variant: *"the essay uses clearly appropriate examples, reasons, and other evidence taken from the source text(s) to support its position"*

(a) Every claim that needs support has it.
(b) Support is specific — named cases, concrete particulars, figures, fully realized examples.
(c) **[ext]** **Every** piece of support is explained, and each explanation does interpretive work:
it says what the support shows and why that bears on the position, rather than restating the support.
(d) Borrowed material is paraphrased or quoted deliberately and sits inside the writer's own
sentences; the writer's argument governs the source, not the reverse.

### 5
> **Official anchor:** *"the essay generally using appropriate examples, reasons, and other evidence… to support its position"* [sic]

(a) Every claim that needs support has it.
(b) Support is specific.
(c) **[ext]** **Most** support is explained, and the explanations add something the support alone does
not say. One or two pieces may be left to speak for themselves.
(d) Borrowed material is transformed into the writer's own phrasing and connected to the writer's
claims.

### 4
> **Official anchor:** *"using adequate examples, reasons, and other evidence to support its position"*

(a) The main claims have support; one may be left unsupported.
(b) Support is specific.
(c) **[ext]** The connection is stated for **some** support but not consistently — and where stated,
the explanation tends to **restate the support in other words** rather than interpret it. The essay
says *this happened, which shows my point*, without saying how.
(d) Borrowed material is used and marked in some way, but sits alongside the writer's sentences
rather than inside them.

*(Bands 6, 5 and 4 hold **specificity constant** and move only **elaboration**. What separates the
top three bands is how consistently the essay explains its support, not how concrete the support is.)*

### 3
> **Official anchor:** *"use inadequate examples, reasons, or other evidence to support its position"*

(a) Some claims go unsupported.
(b) At least one piece of support is specific; most is general — "studies show", "many people",
"it can be dangerous".
(c) Support is **listed, not explained**. The reader supplies the connection.
(d) **[ext]** Borrowed material is **patchwritten** — source phrasing stitched together with little
transformation — or paraphrased so loosely that it no longer says what the source said.

### 2
> **Official anchor:** *"providing inappropriate or insufficient examples, reasons, or other evidence to support its position"*

(a) Support is thin: most claims go unsupported.
(b) Support is **general throughout** — no named case, no concrete particular anywhere.
(c) No explanation of how any support bears on the position; **or** what is offered as support
restates the claim it is meant to support (circular).
(d) **[ext]** Borrowed material stands in for the argument: the essay reports what a source says
instead of arguing from it.

### 1
> **Official anchor:** *"provides little or no evidence to support its position"* — fused disjunctively with the point-of-view clause at score 1 in the official text

(a) No support is offered, or all of it was discarded as irrelevant.
(b) Nothing specific enough to assess.
(c) None.
(d) The response is **predominantly copied**.

### Decision rules — Development

- **Depth, not count.** Do not raise a score because an essay offers more pieces of support. Rate how
  far each piece is taken. Three supports each explained beat six listed. This is the most important
  rule in this scale and the one most likely to be violated by accident.
- **Relevance is a precondition, sufficiency is a gradient.** Handle relevance once, before climbing,
  per the box above. Do not average irrelevant support in as partial credit.
- **The 3/4 rung is the listed/explained line.** If the reader is doing the work of connecting support
  to claim, the essay has not reached 4. If the essay states the connection, even weakly, it has.
- **The 4/5 rung is consistency of explanation, with specificity held constant.** Both bands have
  specific support. A 5 explains most of it in a way that adds something; a 4 explains some of it and
  mostly by restatement. The 5/6 rung is *most* becoming *every*.
- **Do not rank support by where it came from.** A specific, explained personal experience counts
  exactly as much as a specific, explained statistic. The criterion is whether the support is concrete
  and whether the essay says what it shows — never whether it is "academic". Ranking by provenance
  imports differences in background knowledge and prior schooling this trait is not measuring.
- **Length neutrality, and why it is stated here.** This is the trait where length bias enters: word
  count correlates with content-trait ratings at roughly r ≈ .6 and with mechanics ratings at roughly
  r ≈ .1. A short essay with two specific, explained supports scores higher than a long one with five
  general ones. If you find yourself moving this score because the essay "feels substantial", stop and
  count how many supports are actually *explained*.
- **Copying and patchwriting** fire on **observing borrowed phrasing**, not on knowing whether the
  prompt was source-based — which you often cannot know. *Predominantly* copied → 1. Patchwriting —
  borrowed phrasing lightly stitched — caps the trait at 3; it is a developmental stage of source use,
  not a floor.
- **Do not score errors here.** Grammar, spelling and sentence problems belong to Conventions.

---

## Trait 3 — CONVENTIONS (language: vocabulary, sentence structure, grammar/usage/mechanics)

The official rubric's language strand is two clauses at every band — *facility with language*
(vocabulary and sentence structure) and *errors in grammar, usage, and mechanics*. Sub-criteria
(a)–(b) take the first, (c) the second, and (d) is the consequence axis both clauses ladder on in the
official text.

### Ladder — climb from 1, stop at the last YES

Rungs 2–4 are a **reader-consequence** ladder. Ask what the errors cost *you*, reading it once.

| Reach | Ask |
|---|---|
| **2** | Can you generally parse the sentences — is meaning mostly recoverable? |
| **3** | Do you never have to **guess** what was meant? (Re-reading to repair a sentence is fine here.) |
| **4** | Do you never have to **re-read**? Errors are visible, but nothing needs repair. |
| **5** | Do sentences vary in length and shape and stay under control, with errors only occasional and minor? |
| **6** | Is word choice **apt** rather than merely correct, and the sentence variety purposeful — does the language do positive work? |

**Sub-criteria used in the full bands:**
**(a) Word choice** — is it accurate and fitted to what the writer means?
**(b) Sentence structure** — are sentences under control, and do they vary?
**(c) Grammar, usage, mechanics** — how much is wrong?
**(d) Consequence to the reader** — what do the errors *cost*?

### 6
> **Official anchor:** *"the essay exhibits skillful use of language, using a varied, accurate, and apt vocabulary and demonstrates meaningful variety in sentence structure"* + *"the essay is free of most errors in grammar, usage, and mechanics"*

(a) Word choice is **apt**, not merely correct — words are chosen for precision, and the essay says
what it means rather than something near it.
(b) Sentence variety is **meaningful**: length and shape track what each sentence is doing.
(c) Errors are rare enough to read as lapses.
(d) **[ext]** The language does positive work — precision of wording and sentence shape carry part of
the meaning, rather than merely not obstructing it.

### 5
> **Official anchor:** *"the essay exhibits facility in the use of language, using appropriate vocabulary demonstrates variety in sentence structure"* [sic] + *"the essay is generally free of most errors in grammar, usage, and mechanics"*

(a) Word choice fits consistently; the reader is never wrong-footed by a word.
(b) Sentences vary in length and shape and stay under control at every length.
(c) Errors are occasional and minor.
(d) **[ext]** Nothing in the language costs the reader anything — no re-reading, no repair.

### 4
> **Official anchor:** *"the essay may demonstrate inconsistent facility in the use of language, using generally appropriate vocabulary demonstrates some variety in sentence structure"* [sic] + *"the essay may have some errors in grammar, usage, and mechanics"*

(a) Word choice is generally appropriate, with occasional words that are approximately rather than
exactly right.
(b) Some variety in sentence structure, but control is **inconsistent** — longer sentences occasionally
lose their grip.
(c) Errors occur but do not accumulate.
(d) **[ext]** Errors are visible, but **the reader never re-reads**: nothing has to be repaired to get
the meaning.

### 3
> **Official anchor:** *"the essay may demonstrate facility in the use of language, but sometimes uses weak vocabulary or inappropriate word choice and/or lacks variety or demonstrates problems in sentence structure"* + *"the essay may contain an accumulation of errors in grammar, usage, and mechanics"*

(a) Word choice is sometimes weak or wrong for the context.
(b) Sentences run to one pattern, or break down when they get long.
(c) Errors **accumulate** across the piece.
(d) **[ext]** Meaning stays recoverable throughout, but **the reader re-reads** in places to repair a
sentence.

### 2
> **Official anchor:** *"the essay displays very little facility in the use of language, using very limited vocabulary or incorrect word choice and/or demonstrates frequent problems in sentence structure"* + *"the essay contains errors in grammar, usage, and mechanics so serious that meaning is somewhat obscured"*

(a) Vocabulary is very limited, or words are used incorrectly in ways that change what is said.
(b) Frequent problems in sentence structure — run-ons, fragments, sentences that do not resolve.
(c) Errors are frequent.
(d) **Meaning is somewhat obscured**: at least once the reader has to **guess** what was intended
rather than repair it.

### 1
> **Official anchor:** *"the essay displays fundamental errors in vocabulary and/or demonstrates severe flaws in sentence structure"* + *"the essay contains pervasive errors in grammar, usage, or mechanics that persistently interfere with meaning"*

(a) Fundamental errors in vocabulary — intent is often unrecoverable.
(b) Severe flaws in sentence structure; sentences frequently cannot be parsed.
(c) Errors are pervasive.
(d) Errors **persistently interfere with meaning** — reading is a decoding exercise.

### Decision rules — Conventions

- **Band on consequence, not on count.** The official rubric's own ladder is a consequence ladder —
  *some errors* (4) → *an accumulation* (3) → *meaning somewhat obscured* (2) → *persistently
  interfere with meaning* (1). Two essays with the same number of errors can and should differ by two
  bands if one's errors cost the reader nothing and the other's cost comprehension. The rungs are:
  **reader decodes (1) → guesses (2) → re-reads (3) → never re-reads (4) → nothing costs anything
  (5) → language does positive work (6)**.
- **A flat but clean essay is not a 5 or a 6.** If every sentence is the same shape, rung 5 fails —
  the official band-5 clause requires *variety in sentence structure*, not merely absence of error.
  Correctness alone does not reach the top bands. This is the most common way this trait gets
  over-scored.
- **Do not enumerate or hunt error types.** Do not tally subject–verb agreement, article use, comma
  splices or any other category, and do not weight categories against each other. Enumeration is the
  mechanism by which prestige-dialect and second-language penalties enter a conventions score:
  features of stigmatized varieties of English are highly comprehensible and would rank as severe
  under any type-based hierarchy. Ask only what the errors cost the reader.
- **Do not reward syntactic complexity.** Score **variety and control**, never subordination or clause
  density. In argumentative writing specifically, clause density is not a positive quality signal. Do
  not write off simple sentences doing their job, and do not credit a long sentence that survives only
  by luck.
- **Do not reward sophisticated vocabulary as such** — score whether the word is *right*. Where the
  essay uses borrowed phrasing, that phrasing is not the writer's word choice; judge the writer's own
  sentences.
- **Do not lower this score because the ideas are thin, and do not lower any other trait because of
  errors.** A mechanically polished essay with nothing to say gets a high Conventions score and a low
  Development score. That is the correct result, not a contradiction.

---

## Trait 4 — ARGUMENTATION (point of view and critical thinking)

### Ladder — climb from 1, stop at the last YES

| Reach | Ask |
|---|---|
| **2** | Is a position stated at all? |
| **3** | Is the position clear and committed — the writer's, not the prompt's wording handed back? |
| **4** | Is **at least one reason actually reasoned** — does the essay say *why* it follows, not only that it does? |
| **5** | **At least one of:** an opposing position is acknowledged **and answered**; the position is qualified where the issue warrants it; the governing principle is made explicit. **And** the essay reaches a conclusion the prompt's framing does not already imply. |
| **6** | Does the essay answer the **strongest** objection (showing it invalid, outweighed, or resting on a false assumption), **or** change the terms of the prompt's framing — reframe the question, or mark where its position holds and where it does not? |

**Sub-criteria used in the full bands:**
**(a) Position** — is there a stance, is it the writer's, and does it hold?
**(b) Reasoning** — is the *why* connecting reason to position stated, or assumed?
**(c) The other side** — omitted, mentioned, conceded, or answered?
**(d) Advance** — measured against **the prompt** at every band: how far past the prompt's own framing
does the essay get?

### 6
> **Official anchor:** *"A typical essay effectively and insightfully develops a point of view on the issue and demonstrates outstanding critical thinking"*

(a) A clear position, held throughout, that is the writer's own rather than the prompt's returned to
sender.
(b) **[ext]** The essay states not just its reasons but **why those reasons count** — the principle
connecting reason to position is on the page.
(c) **[ext]** **At least one of:** the essay answers the **strongest** opposing consideration rather
than a convenient weak one — showing it invalid, outweighed, or resting on a false assumption; or it
makes its governing principle explicit and applies it to a case that tests it.
(d) **[ext]** The essay **changes the terms of the prompt's framing** — reframes the question, or
establishes a boundary condition marking where its position holds and where it does not.

### 5
> **Official anchor:** *"A typical essay effectively develops a point of view on the issue and demonstrates strong critical thinking"*

(a) A clear position, held throughout.
(b) **[ext]** Reasons are genuinely reasoned — the connection from each reason to the position is
stated, not assumed.
(c) **[ext]** **At least one of:** an opposing position is acknowledged *and answered*; the position is
qualified where the issue warrants it; or the governing principle is made explicit rather than left
implied.
(d) **[ext]** The essay reaches a conclusion **the prompt's framing does not already imply**.

### 4
> **Official anchor:** *"A typical essay develops a point of view on the issue and demonstrates competent critical thinking"*

(a) A clear position, held throughout.
(b) **[ext]** **At least one reason is actually reasoned** — the essay says why it follows, not only
that it does. Others may be asserted.
(c) The other side may be absent, or mentioned without being engaged.
(d) **[ext]** The essay reaches a conclusion **the prompt's framing implies** — it does more than hand
the prompt back, but gets no further than its own supporting reasons.

### 3
> **Official anchor:** *"develops a point of view on the issue, demonstrating some critical thinking, but may do so inconsistently"*

(a) A position is clear — held throughout, **or** held inconsistently (drifting, or with later claims
that do not sit under it).
(b) Reasoning is **asserted, not shown**: the essay says *that* something is so, never *why*.
(c) Absent.
(d) The essay circles its position — later parts restate the opening in different words.

### 2
> **Official anchor:** *"develops a point of view on the issue that is vague or seriously limited, and demonstrates weak critical thinking"*

(a) A position is stated but **vague or so limited it barely engages the issue** — or it is the
prompt's own wording handed back with no commitment added.
(b) What look like reasons are **restatements of the position** in other words.
(c) Absent.
(d) None.

### 1
> **Official anchor:** *"develops no viable point of view on the issue"* — fused disjunctively with the evidence clause at score 1 in the official text

(a) **No viable position**: no stance is recoverable, or the essay states positions that contradict
each other so that no stance can be attributed to it.
(b) None.
(c) Absent.
(d) None.

### Decision rules — Argumentation

- **Restatement is not development.** Repeating the position in new words, or handing back the
  prompt's framing, does not climb a rung at any level. This is the most common way a weak essay looks
  stronger than it is.
- **Rung 3 is commitment; rung 4 is reasoning.** A position stated with commitment but never justified
  stops at 3 — holding-consistency stops mattering above band 3, which is why band 3(a) admits both
  the consistent and the drifting case. One reason genuinely reasoned reaches 4.
- **A real rebuttal implies reasoning.** An essay that refutes a counterargument by showing it invalid,
  outweighed, or resting on a false assumption has, in doing so, shown reasoning — it passes rung 4 by
  that alone. Do not fail it on rung 4 and then credit it at rung 6.
- **Counterargument is one route, never the requirement — at 5 or at 6.** Acknowledging the other side
  *without answering it* does not satisfy rung 5; mere mention is not reliably better than omission.
  But making the governing principle explicit, and qualifying the position appropriately, are equally
  valid routes at both rungs. This matters practically: in student argumentative corpora,
  counterargument and rebuttal are rare at every grade level, and gating the upper bands on rebuttal
  alone would empty them.
- **(d) is always measured against the prompt**, never against the essay's own introduction — internal
  progression is Organization's (c), not this. The ladder is: hands the prompt back (2) → circles (3)
  → reaches what the prompt implies (4) → reaches what it does not imply (5) → changes its terms (6).
- **Do not score whether you agree.** A well-reasoned position you find wrong scores high. A position
  you share, asserted without reasoning, scores low.
- **Do not score evidence quality here.** Whether the supporting facts are specific and explained is
  Development. The two traits will correlate; score them separately anyway.
- **Do not score errors, length, or vocabulary here.**

---

## Cross-trait firewalls

Raters using a rubric are demonstrably influenced by mechanical polish when scoring content. These
**six** instructions exist to block that and the other known bleed paths. They are binding.

1. **Errors stay in Conventions.** Do not lower Organization, Development or Argumentation because of
   grammar, spelling, punctuation or sentence problems.
2. **Ideas stay out of Conventions.** Do not lower Conventions because the argument is thin, the
   evidence weak, or the structure loose.
3. **Development and Argumentation ask different questions of the same sentence.** Development asks
   whether the *support* is concrete and whether the essay says **what it shows**. Argumentation asks
   whether the *principle* linking that showing to the position is **on the page**. One sentence can
   satisfy one and not the other: "Test scores fell 12% after the ban, which shows phones hurt
   learning" is specific and explained (Development rung 4–5) while leaving its warrant entirely
   implicit (Argumentation stops at rung 4). Score each question separately.
4. **Structure stays in Organization.** Do not raise Argumentation or Development because the essay is
   well organized, and do not lower Organization because the argument is weak. Internal progression is
   Organization's (c); distance from the prompt is Argumentation's (d).
5. **Score each trait against its own scale, in isolation.** Assign all four before looking at them
   together. Do not adjust one trait to be consistent with another — four scores that disagree are
   information, not an error.
6. **Do not score agreement, topic or prompt difficulty.** Score what this essay does, not whether you
   share its position or think the prompt was easy.

**Operational note.** Trait scores assigned in one pass tend to collapse toward each other (illusory
halo). The firewalls are more reliable if each trait is scored in a **separate call, with only that
trait's scale in context**, and steps 2–5 are presented in a randomized order across essays. Each
scale above is self-contained for exactly this reason. This is a harness change, not a rubric change,
and is not required for v6 conformance — but if v6's trait scores come back suspiciously uniform
across traits, it is the first thing to try. It is also the natural companion to #50's small-model
goal: four short single-trait prompts are a much easier ask of a sub-120B model than one long
four-trait prompt.

---

## Explicit anti-verbosity-bias instruction [prohibition unchanged from v1]

**Do not use essay length as a scoring signal, in either direction.** A concise, well-argued essay
should score as well as or better than a long, repetitive, or padded one making the same points.
Conversely, do not penalize a short essay for being short if its argument is complete and precise. If
you notice yourself inclined to raise or lower a score primarily because an essay "feels substantial"
or "feels thin" due to its length, stop and re-ground the score in the Organization / Development /
Conventions / Argumentation scales above instead.

**[v6] The prohibition is absolute for all four traits.** What varies is only how *hard it is to
obey*: length contaminates content-trait ratings far more than language-trait ratings (r ≈ .6 versus
r ≈ .1). Be most vigilant on **Development**, then Argumentation, then Organization. Length bias is
least likely to arise in Conventions — but the prohibition applies there identically, and a longer
essay is not a better-written one.

---

## Provenance note (superseding v1/v2's)

v1 and v2 used a *reconstructed proxy* rubric because the real one couldn't be fetched in that
environment. `rubric_official_persuade.md` resolved that — it's the verbatim **official PERSUADE 2.0
scoring rubric**, sourced from the corpus repo (https://github.com/scrosseye/persuade_corpus_2.0),
covering both task variants (Independent / Source-based writing, which are identical apart from an
evidence-from-source clause). The four trait scales above are grounded directly in that verbatim
text — each band's *Official anchor* line is the clause it decomposes. See `decisions_log.md` #27 for
the dimension mapping and #55–61 for the decomposition.

**A known tension, recorded rather than silently resolved.** The official rubric's band-3
*organization* clause ("limited in its organization or focus…") is **disjunctive at the holistic
level** — an essay with that weakness alone is a holistic 3. In v6 that same clause defines
**Organization 3**, which does not trip the gate in `v4_holistic()` (it fires at ≤2), so an essay with
Organization 3 and other traits at 5 lands at holistic 4. This is inherited from v4's gate threshold,
not introduced by v6 — but v6 is the version that makes it visible, because it is now possible to see
which official clause a trait score corresponds to. Whether the gate should fire at trait = 3 for the
disjunctive dimensions is a real open question, it lives in code now, and it needs its own version;
see #48 for why the threshold was left alone.

---

## Output format [v5 — unchanged]

For each essay, output a JSON object with **exactly these six fields**:

```json
{
  "essay_id": "000d118",
  "evidence_notes": "one or two sentences",
  "organization": 3,
  "development": 3,
  "conventions": 3,
  "argumentation": 3
}
```

**Do not output a holistic score, a gate decision, or a gate rationale.** They are not yours to
assign — `grade_essays.py` computes all three from the four trait scores above, and it will refuse to
assemble a batch that contains them, on the grounds that their presence means the batch was graded
against an older prompt. There is no `rationale` field either: in v1–v4 the rationale explained the
holistic score, and you are no longer assigning one.

**[v6] Put the deciding rung into `evidence_notes`.** For each trait, name the highest ladder rung you
answered YES to and why it stopped there — e.g. *"org 4 (body parts swap freely); dev 3 (one specific
example, listed not explained); conv 4 (visible errors, never re-read); arg 4 (one reason reasoned, no
opposing view)."* This is the only change to the field's use, it is additive, and
`predictions_v6.csv` parses under the existing reader. It is also what makes a disagreement between
two runs diagnosable — under v5 a 4-vs-3 split on conventions is untraceable; under v6 it names the
rung the two runs answered differently.

The four JSON field names are kept identical to v1–v5 for pipeline continuity, even though their
definitions are now grounded in the official rubric's four dimensions rather than v1/v2's proxy
definitions. See `decisions_log.md` #27 for this mapping and why it wasn't also a field-rename.

Score every essay independently on its own merits. Do not compare essays in the same batch to each other, do not let earlier essays in the batch anchor later scores, and do not adjust for where you guess the average score "should" land.
