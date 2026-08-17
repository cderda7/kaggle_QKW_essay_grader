# v9 results — the fitted aggregator

**Headline: QWK 0.7392, leave-one-out. The first version to clear 0.70, and the first to beat v4.**

Every score is produced by a model fitted on the other 99 essays. The trait scores are v6 run B's,
carried through untouched and fidelity-checked, so the only thing that changed is the map from four
integers to one score.

| | QWK | Exact | Adjacent | MAE | Mean signed error |
|---|---|---|---|---|---|
| v4 (hand rules, weighted) | 0.6584 | 54% | 94% | 0.520 | +0.08 |
| v6 run B (hand rules) | 0.5954 | 48% | 95% | 0.570 | +0.41 |
| v8 (+ triage + length floor) | 0.6387 | 46% | 96% | 0.580 | +0.14 |
| **v9 (fitted aggregator)** | **0.7392** | **62%** | 95% | **0.430** | **+0.03** |

Exact agreement gains 14 points over v6 and 8 over v4. MAE falls a quarter. The bias that four
versions chased is gone: **+0.41 → +0.03.**

## 1. The protocol held — selection cost was zero

| | QWK |
|---|---|
| Un-nested LOO (features fixed to `wmean+len`) | 0.7392 |
| **Nested LOO (features re-selected on each fold's 99)** | **0.7392** |
| Selection cost | **0.0000** |

The candidate ladder was originally chosen by looking at CV on these same 100 essays, which is
contaminated. Re-running the selection inside every fold makes the number pay for that choice, and it
cost nothing: `wmean+len` was chosen on **96 of 100 folds**, and the four folds that picked
`traits+len+severity` produced identical predictions. The feature choice was not fitted to the
evaluation set.

For contrast, and as the record of why LOO rather than a holdout: across **200 random 50/50 splits
the same method returns mean 0.7231 with SD 0.052** — 10th–90th percentile [0.656, 0.793]. A single
split would have reported a draw from that distribution.

## 2. Both halves are load-bearing

Each row fitted identically, under LOO:

| | QWK | Exact | Bias |
|---|---|---|---|
| Rubric only (f1) | 0.6358 | 52% | +0.13 |
| Word count only (f2) | 0.6758 | 59% | +0.00 |
| **Both (v9)** | **0.7392** | **62%** | +0.03 |

The combination beats word count alone by +0.062 and the rubric alone by +0.103. Neither is
redundant — which is what the partial correlations predicted (argumentation's correlation with the
human score, after word count is removed, is 0.489).

**And this is a ranking gain, not just a calibration one.** Spearman: **v9 0.774**, against v6 run B
0.694, v4 0.680, v8 0.659. Every previous version was fighting over the discretization of a fixed
ranking whose ceiling was ~0.66. v9 moved the ranking.

Paired bootstrap, 4,000 reps:

| | ΔQWK | 95% CI | reps favouring v9 |
|---|---|---|---|
| v9 vs v6 run B | **+0.1431** | **[+0.034, +0.257]** | **99.7%** |
| v9 vs v8 | +0.1025 | [−0.011, +0.220] | 96.2% |
| v9 vs v4 | +0.0817 | [−0.012, +0.187] | 95.3% |
| v9 vs rubric-only | +0.1034 | [−0.014, +0.236] | 95.0% |
| v9 vs word-count-only | +0.0624 | [−0.034, +0.164] | 89.5% |

The v6 comparison clears zero outright — **the first interval in this project's history that does.**
v4 and v8 sit just inside it at 95–96%, which at n=100 and SE ≈ 0.053 is about as far as this corpus
can take a single comparison.

## 3. The distribution came back

| score | 1 | 2 | 3 | 4 | 5 | 6 |
|---|---|---|---|---|---|---|
| human | 9 | 25 | 36 | 28 | 2 | 0 |
| **v9** | **10** | 23 | 36 | 28 | 2 | 1 |
| v8 | 1 | 37 | 21 | 40 | 1 | 0 |
| v6 run B | 0 | 15 | 41 | 43 | 1 | 0 |

**v6, v7 and v8 could not assign a 1.** Two triage instruments were written to fix that and neither
fired. v9 assigns ten, four of them correctly, without any instrument at all — the distribution falls
out of matching the cuts to the fitting data's own distribution. Three of the versions' worth of
bottom-rung engineering is replaced by a quantile.

The remaining bottom-end error is now the opposite one: six essays humans scored 2 were given 1.

## 4. The cost, and it is not small

**v9 makes length a positive predictor, and overshoots.**

| | corr(word_count, score) |
|---|---|
| human raters | **0.688** ← the target |
| v4 | 0.513 |
| v6 run B | 0.474 |
| v8 | 0.459 |
| **v9** | **0.820** |

Every version through v8 used length *less* than the human raters did. v9 uses it **more**, and its
residual now correlates with length at **+0.242** (v8: −0.313) — it systematically over-scores long
essays. The anti-verbosity prohibition that governed v1–v7 was protecting against something real, and
v9 has overshot it in the other direction rather than landing on the human rate.

Two things follow:

- **The QWK is partly bought with a bias the rubric was built to avoid.** It is a real gain — the
  ablation shows the rubric contributes +0.062 that length cannot supply — but a system whose scores
  track length at 0.82 is not the grader a teacher would sign.
- **Generalisation is untested in the direction that matters.** β2 = 2.88 was fitted on 100 essays
  from one prompt mix. Length's relationship to quality is prompt-dependent; nothing here shows this
  coefficient transfers.

## 5. v10

1. **Constrain the length coefficient rather than deleting it.** The obvious form: penalise β2 until
   corr(word_count, system_score) lands at the human raters' 0.688 instead of overshooting to 0.820,
   and report what that costs in QWK. If the cost is small, v9's gain was mostly the fitted *mapping*
   rather than the length signal — which the rubric-only LOO number (0.6358 against v6's hand-ruled
   0.5954, same trait scores) already hints at: **+0.04 of v9's gain comes from replacing the rules
   alone, with no length at all.**
2. **`results_v6.md`'s priority 1 is still untouched after three versions.** Tightening rungs 2–3 on
   Organization, Development and Argumentation is now the only remaining lever on f1, and f1 is the
   half of v9 that is not length.
3. **Validate on essays this project has not seen.** The LOO estimate is honest for these 100 and
   says nothing about a new prompt. The constraint that only these 100 may be used for fitting does
   not prevent *checking* the fitted aggregator against held-out essays — that is a validation, not a
   fit, and it is the single most informative thing left to do.

Not attempted, deliberately: no cut points tuned against QWK, no re-selection after seeing the eval
number, no trait-weight fitting (tested, worse), no change to any rubric text.
