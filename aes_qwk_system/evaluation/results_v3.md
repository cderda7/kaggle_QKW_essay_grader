# v3 results — disjunctive/compensatory gate, grounded in the official PERSUADE rubric

**QWK = 0.6382** (substantial agreement, Landis & Koch). Essentially tied with v2 (0.6400) — a
difference of 0.0018, far smaller than the random-shuffle baseline's own standard deviation
(~0.099), i.e. not a meaningful change in QWK. But the aggregate number hides two real, opposite
shifts underneath it. Read this alongside `results_v1.md` and `results_v2.md`.

| Metric | v1 | v2 | v3 | v3 vs v2 |
|---|---|---|---|---|
| QWK | 0.594 | 0.640 | 0.638 | flat (Δ0.002, within noise) |
| Exact agreement | 53% | 51% | **43%** | worse |
| Adjacent (±1) agreement | 95% | 96% | **92%** | worse |
| MAE | 0.54 | 0.54 | **0.65** | worse |
| Mean signed error (system − human) | +0.22 | +0.08 | +0.15 | worse (partial reversion toward v1) |
| corr(word_count, residual) | −0.298 | −0.213 | −0.214 | flat |
| QWK, SDs above random-pairing mean | 6.11 | 6.31 | 6.49 | flat/slightly up (real signal, not noise, in all three) |

## The headline win: the "never assigns a 1" finding (decisions_log.md #10, #17) is resolved

v1 and v2 never once output a holistic score of 1, across 100 essays each, despite 9 essays being
human-rated 1 in both runs. v3's confusion matrix:

```
              system:  1   2   3   4   5
human=1 (n=9):         3   5   1   0   0
human=2 (n=25):        5  14   3   3   0
human=3 (n=36):        0   8  11  17   0
human=4 (n=28):        0   3   3  15   7
human=5 (n=2):         0   0   1   1   0
```

The system now assigns 1 eight times, matching 3 of the 9 true human=1 essays exactly and putting
5 more one point off (system=2). This directly confirms the hypothesis behind the whole v3 change
(decision #17's working theory, restated by you as the compensatory-averaging failure mode): the
grader wasn't structurally incapable of recognizing a genuinely weak essay — it was averaging a
severe weakness in one trait against three fine traits and landing in the middle. The severe-
weakness gate (rubric step 6) removes that averaging path entirely for the bottom of the scale, and
it worked exactly as designed there.

The known hard case (`01267d1`, decisions_log.md #11/#18, human=1) also kept improving:
v1 system=5 (4-pt miss) → v2 system=4 (3-pt miss) → **v3 system=3 (2-pt miss)**. Still not exact,
but the trend across all three rubric versions is monotonic in the right direction. In v3, only its
Argumentation trait triggered the gate (score 2 — "may demonstrate facility... but sometimes uses
weak vocabulary" was NOT the issue here; the essay's near-total reliance on strung-together
quotations without original synthesis is exactly what Argumentation/Point-of-View is meant to
catch) while Organization/Development/Conventions each independently landed at 3 — so gate
placement rules put it at the top of the 2-3 range rather than the bottom. That's a legitimate,
rubric-consistent outcome, not a bug; whether it's the *right* outcome for an essay a human called
a flat 1 is a separate, harder question the aggregate numbers below start to answer.

## The real cost: exact agreement and MAE both got worse, and it's traceable to a specific gap

Exact agreement dropped from 51% (v2) to 43% (v3); MAE rose from 0.54 to 0.65. This isn't diffuse
noise — it concentrates almost entirely in the human=3 cohort (36 essays, the largest and modal
group in this dataset): only 11 got matched exactly, while 17 were scored a 4, one point too high.

The cause, found empirically during assembly (not predicted in advance): the gate's "severe
weakness" trigger is a trait score ≤2, but a trait score of **exactly 3** ("developing mastery,"
the official rubric's own disjunctive-band language) is neither severe by that trigger *nor* able
to structurally clear the compensatory band's "≥3 of 4 traits at ≥4" threshold below it. 14 of the
100 essays fell into this gap — profiles like `{org:4, dev:3, conv:3, arg:3}` or all four traits at
a flat 3 — and graders resolved the ambiguity inconsistently, sometimes staying at 3 (following the
rubric's "default to the lower adjacent score" fallback) and more often rounding up to 4 (following
the general "typical essay... develops... organized... adequate" framing loosely). See
`decisions_log.md` #38 for the full mechanics and `grade_essays.py`'s `validate_v3_gate()` for how
this is now flagged (as a soft advisory, not a hard rule violation, since neither grader behavior
was actually wrong given what the rubric said) on every future v3 run.

Net effect: the essays most likely to land in this gap skew toward the human=3 cohort specifically
— exactly the essays whose profile is "solidly okay across the board, nothing severely wrong,
nothing clearly excellent either" — which is why the damage concentrates there rather than spreading
evenly. This is a **rubric design gap, not a grading-consistency problem**: `validate_v3_gate()`
found zero hard rule violations across all 100 essays once the 14 dead-zone cases were correctly
reclassified as ambiguous rather than wrong — every grader followed *some* defensible reading of
the rubric as written, which is exactly the problem (the rubric didn't specify only one).

## Verbosity-bias diagnostics — no material change from v2

`corr(word_count, residual)` = −0.214, essentially identical to v2's −0.213 (both well improved
from v1's −0.298). The rubric's anti-length instruction is holding steady; v3's changes didn't
touch this dimension one way or the other. `corr(word_count, system_score)` fell from 0.538 (v2) to
0.431 (v3) — closer to v1's 0.471 — but since `corr(word_count, human_score)` = 0.688 is a *real*
pattern in this corpus (longer essays are, in fact, human-rated higher on average, not just
padding), a system correlation below the human one isn't itself bias-free — it may mean v3 is
under-crediting length-linked substance in some cases. Flagging as a secondary, smaller-magnitude
observation, not a new bias finding on the scale of the two above.

## Bottom line

v3 traded one confirmed structural failure (never assigns 1) for a different, smaller-magnitude
one (a rubric gap that inflates the largest middle cohort by about one point in ~1 out of 7
essays), and the two roughly cancel out in QWK. Whether that's a net improvement depends on what
you care about more: if under-identifying genuinely weak essays (the v1/v2 failure) is the costlier
error for your use case, v3 is a real fix worth keeping. If precision in the middle of the scale
(where most of this dataset's essays live) matters more, v3 as written is a regression on that
front. The dead-zone gap itself (decision #38) looks like a clean, contained fix for a v4 delta —
e.g. extending the severe-weakness trigger or adding an explicit tie-break rule for flat-3 profiles
— rather than a reason to abandon the disjunctive/compensatory approach altogether, since the part
of it that was empirically testable (does removing the averaging path let genuinely weak essays
score low) worked.
