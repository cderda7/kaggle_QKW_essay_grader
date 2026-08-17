# v6 results — per-trait scales

**Headline: the pre-registered hypothesis was confirmed, and QWK fell.** Both are real, and the
second is not noise. Reporting them in that order because #54 established which one this project
should be optimising.

Two independent gradings of the same 100 essays under `rubric_v6.md` (run A, run B), same
`batches.json`, same prompt template, same harness as v1–v4. v6's `VERSION_CONFIG` entry is
byte-identical to v5's apart from the paths, so the only variable is the rubric text.

## 1. Primary metric — run-to-run trait agreement (the #54 metric)

`rubric_v6_research_basis.md` §7 committed, before the run, to this being v6's primary test, and
predicted that **conventions and argumentation would improve most** because #53 identified them as
the two traits hardest to isolate from a whole-essay anchor.

| Trait | #54 baseline | v6 A-vs-B | Δ |
|---|---|---|---|
| Conventions | 61% | **85%** | **+24** |
| Argumentation | 62% | **82%** | **+20** |
| Development | 74% | **91%** | +17 |
| Organization | 80% | **85%** | +5 |
| **Identical trait vectors** | **33/100** | **56/100** | **+23** |

Adjacent agreement is **100% on all four traits** — no essay moved more than one band between runs.
Identical holistic scores: 93/100.

**The prediction held in both direction and rank order.** The two traits named in advance as most
in need of a dedicated scale gained most; organization, already the strongest, gained least. That
ordering is the part that would have been hard to get right by accident.

Two secondary effects, both in the intended direction:

- **Halo down sharply.** Mean pairwise inter-trait correlation falls **0.738 (v3 graded) → 0.482
  (run A) / 0.520 (run B)**. Under v3 the four traits were close to one trait scored four times;
  under v6 they carry substantially independent information.
- **Length coupling down.** corr(word_count, system_score) falls **0.513 (v4) → 0.427 / 0.474**.
  Human scores correlate with word count at 0.688, so this was always going to cost agreement —
  see §3.

## 2. QWK — down, and outside noise

| | QWK | LWK | Exact | Adjacent | MAE | Mean signed error |
|---|---|---|---|---|---|---|
| v3 (graded) | 0.6447 | 0.4977 | 54% | 93% | 0.530 | +0.09 |
| v4 (derived) | 0.6584 | 0.5053 | 54% | 94% | 0.520 | +0.08 |
| **v6 run A** | **0.5566** | 0.4035 | 49% | 93% | 0.580 | **+0.40** |
| **v6 run B** | **0.5954** | 0.4205 | 48% | 95% | 0.570 | **+0.41** |

Paired bootstrap, 4,000 reps, v6 run A vs v4: **ΔQWK = −0.102, 95% CI [−0.188, −0.012]**, with only
**1.5%** of reps favouring v6. This is a real regression, not a noise excursion, and it should not be
softened. Per #54's own standard — SE ≈ 0.053 — the drop is roughly 2 SE.

## 3. Diagnosis: the ranking is intact, the calibration is not

| | Spearman (rank) | best monotone relabel QWK |
|---|---|---|
| v4 | 0.680 | 0.6651 |
| v6 run A | 0.658 | 0.6265 |
| v6 run B | 0.694 | **0.6615** |

**v6 orders the essays as well as v4 does** — run B actually ranks better (0.694 vs 0.680). Under an
optimal monotone relabel run B recovers to 0.6615 against v4's ceiling of 0.6651, i.e. essentially
all of the gap. So this is a **shift, not a loss of discrimination**.

The mechanism is visible in one number: **the gate fires on 32/100 essays under v6, against 49/100
under v3.** v6 stopped assigning trait scores of 2, the gate is triggered by any trait ≤2, and
without it the compensatory floor guarantees a 3. Everything moved up ~0.4 of a point.

Where the 2s went — v3 essays scored 2 on a trait, and what v6 gave them:

| Trait | v3 count at 2 | → v6 kept 2 | → 3 | → 4 |
|---|---|---|---|---|
| Organization | 24 | 5 | 18 | 1 |
| Development | 27 | 6 | 17 | 4 |
| Argumentation | 31 | 9 | 12 | **10** |
| Conventions | 37 | **22** | 15 | 0 |

**The ladders' bottom rungs are too easy to clear.** "Does the text divide into parts that do
different jobs?", "Does the essay offer any support?", "Is a position stated at all?" are passed by
nearly every essay in this corpus, so the floor of each scale collapsed into 3–4. Argumentation is
the worst case: ten essays v3 called a 2 were given a **4**, which means rung 4 ("at least one reason
is actually reasoned") is also clearing too readily.

**Conventions is the exception, and it is the template for the fix.** It retained 22 of its 37 twos —
by far the best floor retention — and its rungs are the only ones anchored to a *reader consequence*
("do you never have to guess?", "do you never have to re-read?") rather than to the presence of a
textual feature. Presence questions are cheap to satisfy; consequence questions are not.

## 4. What was ruled out

**Re-tuning the gate threshold does not fix it** — tested in-sample only, reported as a negative
result rather than as a tuned score:

| | QWK | exact | bias | gate fires |
|---|---|---|---|---|
| gate ≤2 (current), run A / B | 0.557 / 0.595 | 49% / 48% | +0.40 / +0.41 | 32/100 |
| gate ≤3, run A / B | 0.477 / 0.548 | 41% / 48% | −0.27 / −0.21 | 84/100 / 80/100 |

Moving the gate to ≤3 overshoots hard — it fires on 80–84% of the corpus and flips the bias
negative. The problem is not where the gate sits; it is that v6's trait distribution no longer
matches the distribution the gate was calibrated against. **Fix the scales, not the threshold.**

No aggregation-rule search was run, deliberately: #54 already showed a 1,688-variant sweep picked on
one half of the data scoring *negative* on the other.

## 5. Read together

v6 buys a **markedly more self-consistent and less halo-driven grader at unchanged ranking quality**,
and pays for it with a **calibration regression** caused by scale floors that are too permissive. That
is a better position to be in than the reverse: run-to-run variance is the thing #54 identified as the
real headroom and it is the thing that got fixed, whereas the calibration failure is localized,
diagnosed, and cheap to attack.

**v7, in priority order:**

1. **Tighten rungs 2–3 on Organization, Development and Argumentation, and rung 4 on
   Argumentation**, rewriting them as *consequence* questions on the Conventions model rather than
   *presence* questions. Target: restore the trait-2 rate to roughly v3's without touching the upper
   rungs, which are working.
2. **Re-measure both numbers.** The 56/100 vector agreement and the 0.48 inter-trait correlation are
   the properties to preserve; QWK is the one to recover.
3. Do **not** tune the gate, and do **not** sweep aggregation rules.

The v6 rubric text, its ladders, and the research basis for each band are unchanged by this result —
what failed is where four specific rungs sit, not the decomposition.
