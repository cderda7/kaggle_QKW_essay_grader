# v4 results — explicit trait weighting (argumentation 0.35, conventions 0.15)

**QWK = 0.6584**, up from v3's 0.6447. Read the delta carefully: **+0.0137 is 0.14 standard
deviations of the random-shuffle baseline (SD ≈ 0.099)**, which is well inside noise. This version
should be justified on the grounds that the rule now encodes the weighting you asked for, not on
the grounds that QWK moved. Read alongside `results_v3.md` (but see the note at the top of that
file — it narrates the superseded iteration-3 run, not the v3 numbers below).

| Metric | v2 | v3 | v4 | v4 vs v3 |
|---|---|---|---|---|
| QWK | 0.640 | 0.6447 | **0.6584** | +0.0137 (0.14 baseline SDs — noise) |
| Exact agreement | 51% | 54% | 54% | unchanged |
| Adjacent (±1) agreement | 96% | 93% | 94% | +1pt |
| MAE | 0.54 | 0.530 | **0.520** | −0.010 |
| Mean signed error (system − human) | +0.08 | +0.090 | +0.080 | marginally less lenient |
| corr(word_count, residual) | −0.213 | −0.244 | −0.232 | flat |
| QWK, SDs above random-pairing mean | 6.31 | 6.48 | 6.62 | flat (real signal in all three) |

## What changed: one essay

`0105e2e` — organization 4, development 4, conventions 4, argumentation 3 — moves from holistic 4
to 3. Under v3 it cleared the band-4 bar because 3 of its 4 traits were at ≥4. Under v4 those three
traits carry 0.25 + 0.25 + 0.15 = **0.65** of the total weight, below the 0.75 threshold, so it
falls to the compensatory floor. Its human score is **2**, so the move is toward the human rater.

That is the entire diff. Every other essay scores identically to v3, and every trait score in
`predictions_v4.csv` is byte-identical to `predictions_v3.csv` — only the aggregation changed.

## Why the footprint is one essay, and why that was predictable

This is structural, not a sign the weights were applied weakly:

1. **Half the corpus never reaches the weighted rule.** 49 of 100 essays are decided by the
   severe-weakness gate, which is deliberately unweighted — any trait at ≤2 gates the essay
   regardless of that trait's weight (`rubric_v4.md` step 6, `decisions_log.md` #48). Of the 51
   that do reach the compensatory bands, one moved.
2. **The mass rule differs from the count rule for exactly one trait subset.** "At least 3 of 4
   traits" and "traits carrying ≥0.75 of the weight" agree on every subset of the four traits
   except {organization, development, conventions}, which carries 0.65. So the only profile that
   can move is one where **argumentation is the sole trait below the threshold** — which is
   precisely the semantic you asked for, expressed at its narrowest.
3. **A weighted mean would not have helped.** Across all 100 essays the weighted and unweighted
   means differ by at most 0.20 and by 0.054 on average; rounded to integers they disagree on only
   3 essays. On a 1–6 integer scale, a 0.35/0.25/0.25/0.15 split is simply not far enough from
   0.25/0.25/0.25/0.25 to move many scores by any aggregation method.

An alternative that would have moved ~22 essays — using the weighted mean as the placement engine
inside each band instead of the threshold tests — was simulated and rejected: it scored *worse*
(QWK 0.630), and it reintroduces exactly the averaging behaviour `decisions_log.md` #33 added the
counting rule to prevent. See #45.

## Confusion matrix

```
              system:  1   2   3   4   5   6
human=1 (n=9):         3   4   2   0   0   0
human=2 (n=25):        1  16   7   1   0   0
human=3 (n=36):        0   7  22   7   0   0
human=4 (n=28):        0   1   9  13   4   1
human=5 (n=2):         0   0   1   1   0   0
human=6 (n=0):         0   0   0   0   0   0
```

Identical to v3's except one essay shifting from the human=2 / system=4 cell to human=2 / system=3.
The v3-era structural properties all hold: the system still assigns 1 (4 times, 3 of them on true
human=1 essays — the fix from v3 that resolved the v1/v2 "never assigns a 1" failure), and the
human=3 cohort, this dataset's largest at 36 essays, is still the best-matched band at 22 exact.

## The fidelity check, and why v4 was derived rather than re-graded

v1–v3 each re-graded all 100 essays with 10 parallel subagents. v4 did not, because a weight change
only touches how trait scores aggregate — the grader's job (reading essays, assigning four trait
scores) is unaffected by it.

The claim that the aggregation is fully mechanical is not assumed, it is **tested before every
derivation**. `check_v4_fidelity()` runs the v4 scoring function over all 100 v3 trait vectors with
*equal* weights — i.e. v3's own rules — and compares against what v3's graders actually wrote:

```
Fidelity check passed: recomputing v3 under equal weights reproduces every graded
holistic_score and gate_applied exactly
```

100/100 on both fields, and the check raises rather than warns on any mismatch. Two consequences:

- v3's iteration-4 grading run was **completely rule-compliant** — no drift between the rubric as
  written and the scores as assigned, which is a meaningful result about v3 in its own right and a
  notable contrast with the iteration-3 run (`decisions_log.md` #38–39, where 14 essays resolved a
  rubric ambiguity two different ways).
- Because the recompute reproduces the graded scores exactly under equal weights, **the entire
  v3→v4 diff is attributable to the weights** and nothing else. A re-grade would have added grader
  variance on top of a one-essay signal, making the change unmeasurable.

The cost of this choice, stated plainly: v4 has no `batch_results_v4/` and no per-essay grader
rationales of its own — `predictions_v4.csv` carries generated rationales describing which rule
fired, not a reader's judgment. And `rubric_v4.md` documents a rule no grader was ever run against.
If you want to know whether *telling* a grader that argumentation is weighted 0.35 also changes how
it assigns trait scores — a plausible and separate effect — that requires a real re-grade, and it
would be a different version.

## Verbosity bias

Unchanged, as expected from a one-essay diff. `corr(word_count, residual)` = −0.232 (v3: −0.244),
and `corr(word_count, system_score)` = 0.513 against a human baseline of 0.688. The system still
tracks length somewhat less than human raters do, which as `results_v3.md` notes is not
automatically bias-free, since length correlates with real substance in this corpus.

## Bottom line

v4 does what was asked: argumentation now carries more weight than the other traits, conventions
less, and the rule that implements it is a strict generalisation of v3's — identical under the old
weights, so nothing established was disturbed. The measurable effect on this 100-essay set is one
essay and a QWK move inside noise.

If you want the weighting to bite harder, the obvious lever is the wrong one. Making the **gate**
weight-aware — so that conventions at 0.15 can no longer cap an essay on its own — was simulated
and changes **zero** essays, because the "no trait below 3" floor on band 4 catches exactly the
same essays the gate was catching and holds them at 3 anyway. The floors are the real binding
constraint. Dropping them as well moves 2 more essays. Neither is a generalisation of the existing
rules the way the mass threshold is; both are changes of standard — they decide that a severe
weakness in a low-weight dimension can be compensated for, which the official rubric's disjunctive
1/2/3 language argues against. Worth doing deliberately as its own version, with that argument
addressed head-on, rather than folded into a weighting change.
