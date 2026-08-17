# v8 results — the length floor, and a read that still isn't earning its place

**Headline: QWK 0.6387 — the best since v4, still below v4, and essentially all of the gain comes
from the floor rather than the read.**

| | QWK | Exact | Adjacent | Mean signed error | corr(wc, system) |
|---|---|---|---|---|---|
| v4 | **0.6584** | 54% | 94% | +0.08 | 0.513 |
| v6 run B | 0.5954 | 48% | 95% | +0.41 | 0.474 |
| v7 | 0.6180 | 48% | 95% | +0.31 | 0.483 |
| **v8** | **0.6387** | 46% | **96%** | **+0.14** | 0.459 |

v8 changes two things against v7, both in the triage instrument, with the trait scores identical in
both (carried through from v6 run B, fidelity-checked): **rung A re-cut** from *unintelligible* to
*empty*, and **rung A0 added** — a mechanical word-count floor applied in code.

## 1. The ablation, and it is the whole story

All four rows below come from the same run — `predictions_v8.csv` records `system_floor_cap` and
`system_cap_source` per essay, so the counterfactuals are column arithmetic, not re-runs.

| | QWK |
|---|---|
| Neither (v6 run B) | 0.5954 |
| **Floor only — no reading at all** | **0.6341** |
| Read only — no floor | 0.6177 |
| **v8 — floor + read** | **0.6387** |

- **The read adds +0.0046 on top of the floor.** Paired bootstrap v8 vs floor-only: **+0.0030, 95% CI
  [−0.081, +0.082], 54.4% of reps favouring v8.** That is a coin flip. On this corpus the semantic
  triage read contributes nothing measurable once the floor is in place.
- **The floor adds +0.0210 on top of the read**, and it does so by checking one integer.

Against the other versions: v8 vs v7 **+0.0207** (CI [−0.072, +0.114]); v8 vs v6 run B **+0.0434**
(CI [−0.052, +0.137]); v8 vs v4 **−0.0193** (CI [−0.127, +0.085], 35.9% favouring v8). Every interval
straddles zero — the SE ≈ 0.053 ceiling from #54 has not moved.

The bias number is the clean win: **+0.41 → +0.14**, the closest to calibrated any version has been
apart from v4 itself.

## 2. Rung A: the rewrite half-worked, in an informative way

v7's rung A defined *very bad* as unintelligible and sent eight of nine human 1s past it. v8 re-cut
it as a possession test — *is there anything here you could quote back to this student as their own
thinking?*

**All nine human 1s are now flagged, up from six.** That is the rewrite working.

**But rung A itself still fires exactly once, and on a human 2.** The nine 1s were caught at rung B,
labelled `bad`, capped at 2. So:

| | v7 | v8 |
|---|---|---|
| Human 1s flagged at all | 6 / 9 | **9 / 9** |
| Human 1s reaching a holistic 1 | 1 | **0** |
| Essays the system scores 1 | 1 | 1 |

**The system still cannot produce a 1.** Two instruments, written seven days and one full diagnosis
apart, both refuse to fire their bottom rung. That is now a pattern rather than a bug in one
phrasing, and it is the finding v9 should act on: the 1-vs-2 distinction may not be recoverable from
a single first-impression read at all. If the system should ever assign 1, the trait path's own
"two traits at 1" rule is the more plausible route.

Headroom, for scale: had rung A caught exactly the nine human 1s and nothing else, v8 would score
**0.7255**.

## 3. The read now over-fires, which is the opposite of v7's problem

`bad` labels went 20 → 35. Thirteen essays were capped to 2 that humans scored 3 (ten) or 4 (three).
Removing just those thirteen would put v8 at **0.7155**.

Binding-subset precision — the number `results_v7.md` §2 argued is the only one that matters:

| | n | human ≤2 | precision |
|---|---|---|---|
| v7, triage-bound | 10 | 5 | 50% |
| v8, triage-bound | 23 | 11 | **48%** |
| **v8, floor-bound** | **3** | **3** | **100%** |

**Two instruments, two coin flips.** The instrument was rewritten between them and the binding
precision did not move. Meanwhile the floor is 3-for-3 — small n, but it is *derived* precision: the
threshold's held-out violation rate was 1.92%, and the observed rate is consistent with it.

Reading §2 and §3 together: v8 tightened rung A and loosened rung B, and the second effect was not
asked for. The instrument's "when you hesitate, answer `other`" rule was retained for rung B and
explicitly suspended for rung A — the reader appears to have generalised the loosening across both.
That is a real hazard of instruments written in prose and a reason to prefer mechanical rules where
one is available.

## 4. The length floor, and the standard it changes

```
word_count < 175  ->  cap 2      held-out violation rate 1.92%  (14 of 729)
word_count < 225  ->  cap 3      held-out violation rate 0.00%  (0 of 2,928)
```

Derived on the 17,207 essays of `train.csv` not in the evaluation set. The 225/cap-3 tier is free:
across 2,928 held-out essays under 225 words, not one was scored above 3 by a human.

This reverses, in a scoped way, the absolute anti-verbosity prohibition every rubric v1–v7 carries.
The scope is exact and worth stating plainly, since the prohibition was load-bearing for four
versions:

- **The trait pass is untouched and still completely length-blind.** The trait grader never receives
  a word count and its rubric's prohibition is unchanged.
- **Every reading rung of the triage instrument is still length-blind**, and the triage reader is
  told not to estimate length.
- **What is now permitted** is a code-side, one-directional, out-of-sample-derived cap. It never
  rewards length, never separates a 300-word essay from a 600-word one, and cannot raise a score.

`decisions_log.md` #67 has the argument. One number for the standing worry that the prohibition had
become an overcorrection: **corr(word_count, human_score) = 0.688 while v8's
corr(word_count, system_score) = 0.459.** The system uses length *less* than the human raters do,
and did so under the strict prohibition too (v6 run B: 0.474). Whatever else is true, the system was
not over-using length.

## 5. Read together, and v9

v8 is the strongest version since v4 on QWK and the best-calibrated on bias, and it gets there with a
component that does no reading. The triage read has now been given two instruments and has produced
the same 50% binding precision under both, while adding +0.003 (CI straddling zero) over a rule that
checks one integer.

**v9, in priority order:**

1. **Stop paying for the read in its current form.** Either drop it — floor-only is 0.6341 for one
   line of code and no grading pass — or change what it is *asked for*. The most promising variant:
   don't ask for a label at all. Ask only for *the one thing you could quote back to this student*,
   and derive the label mechanically from whether the answer is empty or is a restatement of the
   prompt. That converts a judgment into an extraction, which is the kind of task the smaller models
   this project targets are actually reliable at, and it removes the calibration drift visible in §3.
2. **`results_v6.md`'s priority 1 is still untouched after two versions** — tightening rungs 2–3 on
   Organization, Development and Argumentation as consequence questions. v7 and v8 both went around
   the trait scales rather than into them. The gate fires on 32/100 under v6 against 49/100 under v3,
   and that is where the +0.14 residual bias still lives.
3. **Do not chase a holistic 1 through the triage.** Two instruments have declined to fire it. If the
   distinction is recoverable, it is more likely recoverable per-trait.

Not attempted, deliberately: no gate-threshold change, no aggregation sweep, no re-tuning of the
floor thresholds or the cap values after seeing these numbers. The floor is exactly the rule the
held-out derivation produced before any of it was applied to the evaluation set.
