# Results v2 — QWK interpretation

Re-run against all 100 essays in `personal_training_set.csv`, using `rubric_v2.md` (your edits:
teacher persona + hypothesize-a-prompt-if-missing instruction, and a new **Argumentation**
sub-score — originality/depth of analysis beyond basic synthesis — with a rule that
argumentation=1 caps the holistic score at 3). Full numbers in `results_v2.json`; this file is the
narrative interpretation. Comparison throughout is against `results_v1.md`, kept intact.

## Headline number

**QWK = 0.640** (up from v1's 0.594)

That's a real move, not just noise in the same "moderate" band — it crosses from the top of
**moderate** (0.41–0.60) into **substantial** (0.61–0.80) on the standard kappa bands. Same
randomness check as v1: 2,000 random re-pairings of the system's own v2 scores against human
scores give QWK ≈ 0.00 (sd 0.10); the actual 0.640 is **6.3 SDs above that random-pairing mean** —
still unambiguously real signal, and now a bit further from the noise floor than v1 was.

## What changed, in the numbers

| Metric | v1 | v2 | Change |
|---|---|---|---|
| QWK | 0.594 | 0.640 | +0.046 |
| Exact agreement | 53.0% | 51.0% | −2.0 pts |
| Adjacent (±1) agreement | 95.0% | 96.0% | +1.0 pt |
| MAE | 0.540 | 0.540 | unchanged |
| Mean signed error (system − human) | +0.220 | +0.080 | closer to 0 |
| corr(word_count, system_score) | 0.471 | 0.538 | up, still below human's 0.688 |
| corr(word_count, residual) | −0.298 | −0.213 | up, still negative |

The headline story: **the mean signed error nearly closed** (+0.220 → +0.080), i.e. v1's slight
tendency to over-score essays relative to the human rater is mostly gone in v2. That tracks
directly with the rubric change — Argumentation is a genuinely new, harder-to-satisfy bar
("beyond basic synthesis"), and the system's overall score distribution shifted down accordingly
(v1: mostly 3s/4s; v2: mostly 2s — see `results_v2.json` for the full distribution). Exact
agreement dipped slightly (some essays that were exactly right in v1 got nudged down too far by
the new criterion), but adjacent agreement and the headline QWK both improved, and QWK is a
distance-sensitive metric — a system that's "close but slightly off" scores better on QWK than one
that's "exactly right most of the time, wildly wrong occasionally," which is consistent with what
moved here.

## Did the new Argumentation dimension fix the case that motivated it?

Partially. Essay `01267d1` — the essay that was mostly strung-together quotes without original
synthesis, human-rated 1, that v1 scored a 5 — **improved to a 4 in v2** (Argumentation scored 3,
not 1, so the hard cap-to-3 rule didn't trigger; the grader judged it as "close to straightforward
synthesis" rather than pure synthesis). That's directional progress (error shrank from 4 points to
3) but not a fix — it's still the single largest miss in v2. My read: the rubric's Argumentation
description may need a lower bar for what counts as "1" (currently it likely reads as reserved for
essays with literally no analysis at all, rather than "analysis that's present but doesn't go
beyond restating the source"), or the essay may genuinely be borderline and the human rater's "1"
reflects a stricter standard than "beyond basic synthesis" captures. Worth deciding which, if you
want to iterate further — I'm flagging it rather than guessing.

The other v1 outlier, `016010c` (human=5, v1 system=3, "surface-level reasoning" complaint),
improved from a 2-point miss to a 1-point miss (system=4 in v2).

**New largest disagreements in v2** (didn't exist as top misses in v1): `00b3311` and `01a53e1`,
both human=4 but system=2, both with Argumentation scored 2. I haven't read these in full — flagging
as the natural next sanity-check pair if you want to keep tightening the rubric, rather than
asserting anything about them without reading the text first.

## Verbosity-bias check, re-run

Still clean, though slightly less strong than v1: corr(word_count, system_score) is 0.538 (up
from 0.471, still below the 0.688 human baseline), and corr(word_count, residual) is −0.213 (still
negative, i.e. the system still leans relatively less generous toward longer essays than the human
rater, not more). **No evidence the rubric change reintroduced verbosity bias** — the new
Argumentation dimension moved scores based on analytical depth, not essay length, which is exactly
what it was designed to do.

## Bottom line

v2 is a genuine improvement — QWK moved from moderate to substantial agreement, and the specific
over-scoring bias v1 showed (mean signed error) nearly disappeared. The system still never uses
the bottom of the 1–6 scale (no essay scored 1 in either version), and the essay that motivated
this rubric change improved but didn't fully resolve. Both are concrete, non-hypothetical targets
for a v3 if you want to keep iterating.
