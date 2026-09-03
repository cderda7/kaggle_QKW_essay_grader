# v9 validated on held-out essays — `personal_testing_set_1.csv`

**Headline: QWK 0.7501 on all 500 held-out essays, against 0.4889 for the hand-written rules it
replaced — on identical trait scores.**

This is a **validation, not a fit.** `aggregator_v9.json` was fitted on the 100 essays of
`personal_training_set.csv` and applied here frozen: same three coefficients
(`s = −6.7826 + 0.6827·f1 + 2.8834·f2`), same five cut points, no re-estimation, no re-cutting, no
re-selection. The constraint that only those 100 may be used for *fitting* is untouched. Zero overlap
between the two sets. The 500 were graded blind — the trait pass read a projection of the CSV
containing only `essay_id` and `full_text`.

## 1. The result

| | QWK | Exact | Adjacent | MAE | Bias |
|---|---|---|---|---|---|
| **v9 frozen aggregator** | **0.7501** | 61% | 97% | 0.418 | +0.08 |
| v3–v8 hand rules, identical trait scores | 0.4889 | 41% | 92% | 0.678 | +0.42 |
| rubric only (β2 = 0, fitted on the 100) | 0.5926 | 47% | 90% | 0.638 | +0.15 |
| word count only (β1 = 0, fitted on the 100) | 0.6231 | 51% | 95% | 0.562 | +0.13 |

Paired bootstrap, 3,000 reps:

| | ΔQWK | 95% CI | reps favouring v9 |
|---|---|---|---|
| v9 vs hand rules | **+0.2615** | **[+0.207, +0.315]** | **100.0%** |
| v9 vs rubric only | +0.1575 | [+0.106, +0.212] | 100.0% |
| v9 vs word count only | +0.1275 | [+0.080, +0.177] | 100.0% |

Every interval clears zero by a wide margin. At n=500 the SE ≈ 0.053 problem that made every
comparison from v1 to v8 unresolvable is gone — this is the first result in the project that needs no
caveat about sample size.

## 2. It transferred; the hand rules did not

| | training 100 | held-out 500 | change |
|---|---|---|---|
| v9 QWK | 0.7392 (leave-one-out) | **0.7501** | **+0.011** |
| hand-rules QWK | 0.5954 | 0.4889 | −0.107 |
| v9 Spearman | 0.774 | 0.752 | −0.022 |
| hand-rules Spearman | 0.694 | 0.575 | −0.119 |

**This is the finding.** The fitted map gave up 0.02 of Spearman moving to unseen essays; the hand
rules gave up 0.12 and lost a tenth of a QWK point. The gate, the bands and the weight-mass test were
tuned by hand against those 100 essays across six versions, and most of what they were worth turns out
to have been specific to them. The three-parameter fitted map generalised better than six versions of
hand-reasoned rules — and it is worth being clear that this says nothing bad about the reasoning
behind those rules, only that hand-placed thresholds on 100 examples are fitted parameters whether or
not anyone calls them that.

`rubric_v9.md` §4 flagged the risk that β2 = 2.88 was fitted on one prompt mix and might not travel.
It travelled.

## 3. The distribution

| score | 1 | 2 | 3 | 4 | 5 | 6 |
|---|---|---|---|---|---|---|
| human | 32 | 132 | 195 | 118 | 19 | 4 |
| **v9** | **34** | 106 | 197 | 146 | 12 | 5 |
| hand rules | 5 | 44 | 226 | 213 | 12 | 0 |

The hand rules assign five 1s where there are 32, no 6s at all, and pile 88% of the corpus into 3–4.
v9 tracks the real distribution closely at both ends. This reproduces, at 5× the sample, exactly what
the 100 showed: the quantile-matched cuts recover the score distribution that three versions of
purpose-built bottom-rung engineering (v6's ladders, v7's triage, v8's floor) could not.

## 4. The cost, still present, smaller than on the training set

| | corr(word_count, score) |
|---|---|
| human raters | 0.650 |
| **v9** | **0.772** |
| v9 residual vs word count | **+0.164** |

Still overshooting: the system leans on length more than the human raters do and over-scores long
essays. But less than on the 100 (0.820, residual +0.242), which suggests part of that overshoot was
fitted to that particular slice rather than intrinsic.

This remains the honest liability in the design, and `results_v9.md` §5 item 1 still stands as v10's
first job — constrain β2 until the coupling lands near the human rate and report what it costs. The
gap to close is now **0.772 → 0.650**.

## 5. What this establishes, and what it doesn't

Established, at n=500 with 100% bootstrap support:

1. **The aggregation replacement is real**, not a 100-essay artifact. +0.26 QWK.
2. **Both features are load-bearing out of sample.** Rubric alone 0.593, length alone 0.623, together
   0.750 — the combination beats the better single feature by +0.127.
3. **Hand-written rules degrade badly off their tuning set.** 0.595 → 0.489. The strongest argument
   in this project's history against ever hand-writing them again.

Not established: that the length coefficient is safe on a **different prompt mix**. Both the 100 and
the 500 are drawn from the same PERSUADE pool, so they share prompt distribution, genre and rater
pool. A corpus from a different source is the next real test, and until it is run, β2 = 2.88 should be
treated as calibrated to this corpus rather than to essay quality in general.

## Method note

500 essays, 50 batches of 10, each graded by an independent pass over `rubric_v6.md` — the trait
instrument unchanged since v6. Batches 45–49 were graded in a second sitting after a session limit
interrupted the first; the instrument, the prompt and the blind CSV were identical across both, and
batch assignment follows `essay_id` sort order, which is arbitrary with respect to content.
