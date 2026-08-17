# AES Rubric v9 — the fitted aggregator

**No grader reads this file, and no grader reads anything new.** `rubric_v6.md` is unchanged, the
trait pass is unchanged, and the trait grader still never learns a word count. v9 replaces only the
code that turns four trait scores into one holistic score.

```
v9  =  rubric_v6.md      (trait pass — UNCHANGED, byte for byte)
     + the aggregator below   (replaces the gate, the bands and the weight-mass test)
```

Like v4, v9 is **derived, not graded**: the four trait scores come through from `predictions_v6_runB.csv`
untouched, so a v6-vs-v9 diff isolates the aggregation and nothing else.

---

## 1. Why the rules are being replaced rather than repaired

Since v3 the traits have been combined by hand-written rules: a severe-weakness gate at any trait
≤2, a disjunctive 1–3 band, a compensatory 3–6 band, and a weight-mass test at 0.75. v7 and v8 both
tried to fix the result by adding machinery *around* those rules — a triage cap, then a length floor —
and both landed short of v4 (0.6180 and 0.6387 against 0.6584).

The rules are where the loss is. **v6 run B scores 0.5954, but the best QWK that any monotone
thresholding of its own weighted trait mean could reach is 0.6609.** That gap is created entirely by
the discretization: same trait scores, different mapping, +0.07. Hand-writing where the bands fall is
a fitting problem being solved by hand, and badly.

## 2. The aggregator, whole

**Step 1 — weighted trait mean.** The existing V4 weights, **fixed, not fitted**:

```
f1 = 0.35·argumentation + 0.25·organization + 0.25·development + 0.15·conventions
```

Fitting these weights was tested and is *worse* — 5-fold CV gives 0.6922 with regression-fitted
weights against 0.7233 with the hand-chosen ones. At n=100 the hand weights win, so they stay.

**Step 2 — length, entering continuously:**

```
f2 = log10(word_count)
```

**Step 3 — one continuous score, three coefficients by OLS against the human score:**

```
s = β0 + β1·f1 + β2·f2
```

Fitted values on all 100: `s = −6.7826 + 0.6827·f1 + 2.8834·f2`.

**Step 4 — five cut points, by distribution matching, not by maximising QWK:**

```
c_i   = Quantile(s_fit, P(y_fit ≤ i))          i = 1..5
score = 1 + #{ i : s ≥ c_i }
```

Fitted values: `[1.7352, 2.5160, 3.3482, 4.1925, 4.5817]`.

That is all of it: **three coefficients and five derived cuts.** Deliberately a far smaller
hypothesis class than the 1,688-variant rule sweep `decisions_log.md` #54 found scored *negative*
out of sample — and unlike that sweep, no cut point here is chosen against the metric.

**Deleted from the scoring path:** the severe-weakness gate, the disjunctive and compensatory bands,
the weight-mass test, the v7 triage read, and the v8 length floor (subsumed — length is continuous
now). `v4_holistic()`, `LENGTH_FLOOR` and `load_triage()` remain in `grade_essays.py` so v3–v8 still
reproduce exactly; v9 does not call them.

## 3. How it is evaluated, and why leave-one-out

The project constraint is that **only the 100 essays of `personal_training_set.csv` may be used for
fitting.** So the fitting data and the evaluation data are the same 100 essays, and the only question
is how to keep each prediction honest.

**Every score in `predictions_v9.csv` comes from a model fitted on the other 99 essays.** No essay
contributes to the model that scores it.

Leave-one-out was chosen over a 50/50 holdout on measurement grounds, recorded here because the
alternative is the obvious one: across **200 random 50/50 splits the same method returns mean 0.7231
with SD 0.052** — a single split can hand back anything from 0.64 to 0.81, so the headline would
mostly report which split was drawn. LOO fits on 99 rather than 50, evaluates on all 100 (keeping it
directly comparable to v4 and v8 on the same essays), and is **deterministic — no seed, one number,
reproducible forever**, which is the same preference that removed stochastic rule-following from the
grader in v5.

**The feature set is re-selected inside every fold.** The candidate ladder in `FEATURE_SETS` was
originally chosen by looking at CV on these same 100, which is contaminated; under nested LOO the
inner selection re-runs on each fold's 99, so the reported number pays for the choice. Result:
nested and un-nested both give **0.7392**, selection cost **0.0000**, with `wmean+len` chosen on 96 of
100 folds. The feature choice was not fitted to the evaluation set.

`aggregator_v9.json` stores coefficients fitted on all 100 — the best estimate for scoring a *new*
essay — and records the LOO number in `performance_estimate` rather than an in-sample score, which
would flatter it every time anyone read the file.

## 4. What this costs, stated plainly

**v9 makes essay length a positive predictor of the score.** v1–v7 prohibited using length as a
signal in either direction; v8 permitted a one-directional cap; v9 puts length in the model with a
positive coefficient. This is the largest standard change in the project's history and
`decisions_log.md` #74 argues it rather than assuming it.

The measurable cost is already visible: **corr(word_count, system_score) = 0.820, against the human
raters' 0.688.** The system is now *more* length-driven than the humans it is imitating, and its
residual correlates with length at +0.242 — it over-scores long essays. That is a real validity
problem and it is the first thing v10 should attack; `results_v9.md` §4 has the detail. What the
prohibition was protecting against was never imaginary, and v9 has now overshot it in the other
direction.

The trait pass remains completely length-blind. Length enters this system at exactly one line,
`aggregator_features()`, in the aggregation layer.
