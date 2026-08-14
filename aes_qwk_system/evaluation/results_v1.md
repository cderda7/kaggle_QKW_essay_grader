# Results v1 — QWK interpretation

Run against all 100 essays in `personal_training_set.csv`. Full numbers in `results_v1.json`;
this file is the narrative interpretation.

## Headline number

**QWK = 0.594**

## Is this agreement, disagreement, or randomness?

**Real, moderate agreement — clearly not randomness, not full agreement either.**

To ground "clearly not randomness" empirically rather than by assertion: I computed what QWK looks
like if the system's actual 100 scores are randomly re-paired with the human scores (same score
distribution, no real correspondence) — 2,000 random shuffles average **QWK ≈ 0.00 (sd 0.10,
range -0.40 to +0.34)**. A grader with zero real signal would land in that band. Our system's 0.594
is roughly six standard deviations above that random-pairing baseline. It's also far above the
QWK=0 floor you'd get from a degenerate strategy like always guessing the modal score (3). So the
system is clearly reading and responding to real essay-quality signal, not noise.

It is not, however, tight agreement. Using the standard kappa bands (Landis & Koch, the
conventional reference for interpreting weighted kappa):

| Band | Range |
|---|---|
| slight | 0.0–0.20 |
| fair | 0.21–0.40 |
| **moderate** | **0.41–0.60** |
| substantial | 0.61–0.80 |
| almost perfect | 0.81–1.00 |

0.594 sits at the top of "moderate," just under "substantial." In plain terms: the system's
overall sense of essay quality tracks the human rater's reasonably well — it's not confusing good
essays for bad ones — but it disagrees on the precise score often enough that you wouldn't yet
trust it as a drop-in replacement for the human rater on an individual essay.

## Supporting agreement metrics

- **Exact agreement: 53%** — the system picks the identical score to the human just over half the
  time.
- **Adjacent agreement (within ±1): 95%** — the system is almost never off by more than one point.
  Nearly all of the disagreement is "close but not exact," not wild misses.
- **MAE: 0.54**, **mean signed error: +0.22** — the system skews slightly generous on average
  (about a fifth of a point higher than the human rater, on this 1–5 observed range).

## Confusion matrix (rows = human score, cols = system score)

```
            system=1  system=2  system=3  system=4  system=5
human=1         0         8         0         0         1
human=2         0        17         5         3         0
human=3         0         5        21        10         0
human=4         0         0         8        15         5
human=5         0         0         1         1         0
```

**The single clearest pattern: the system never assigned a score of 1**, even though 9 of the 100
essays were human-rated 1. Every human-1 essay got bumped to a 2 (8 of 9 cases) or, in one
striking outlier, a 5. The system's score distribution is shifted right relative to the human
rater's — it's reluctant to use the bottom of the scale. That's consistent with the +0.22 mean
signed error above and is the main systematic disagreement pattern in this run, not random noise.

## Verbosity-bias check (this was the specific concern you flagged)

Recall from data recon: **human scores correlate with word count at r = 0.688** in this file —
some of that is legitimate (more developed essays tend to be longer), so the bar isn't "zero
correlation," it's "not more biased toward length than the human rater was."

- corr(word_count, **human** score): **0.688** (baseline)
- corr(word_count, **system** score): **0.471**
- corr(word_count, residual = system − human): **−0.298**

**Verdict: no evidence the system amplified verbosity bias — if anything it leans the other way.**
The system's own scores correlate with length *less* than the human rater's do (0.47 vs. 0.69),
and the residual's negative correlation with length means that, if anything, the system is
*relatively less generous to longer essays and relatively more generous to shorter ones* than the
human rater was — the opposite of the classic "LLM judge rewards length" failure mode. This is
worth treating as a genuinely useful result of the rubric's explicit anti-length instruction and
forced sub-score structure (see `rubric_v1.md`), rather than assuming it worked — the numbers
support it. It does NOT mean the system ignores length entirely (0.47 is still a real positive
correlation) — just that it isn't the dominant signal, and it's weaker here than in the ground
truth itself.

## Sanity-check spot review (largest disagreements, read in full)

I read the full text of the two largest-gap essays to confirm the disagreement is substantive and
not a pipeline bug (wrong essay_id lookup, off-by-one parsing, etc.):

- **`01267d1`** — human=1, system=5 (largest single miss in the dataset). Reading it: the essay is
  structurally clean (clear intro/body/conclusion, topic sentences, a real citation habit), which
  is exactly what the rubric's Organization/Development traits reward — but it is almost entirely
  strung-together quotations from the source text ("the text states...") with very little of the
  student's own paraphrase, analysis, or synthesis. My best read: the human rubric likely penalizes
  "restates the source without original analysis" much more heavily than `rubric_v1.md` currently
  does. This looks like a real gap in the proxy rubric, not a bug — and a concrete, actionable
  candidate fix for v2 (see `decisions_log.md`).
- **`016010c`** — human=5, system=3 (largest miss in the other direction). Reading it: also
  genuinely well-organized and clearly written; the system's rationale cites "reasoning stays
  fairly surface-level," which is a defensible but harsher read than the human rater's. This one
  reads more like ordinary grader variance than a rubric gap.

Both cases confirm the pipeline is working correctly (right essay, right text, right score
recorded) — the disagreement is about grading judgment, which is the real thing QWK is meant to
surface.

## Bottom line

This is a real, moderate-agreement essay grader — not random, not yet essay-by-essay reliable. Its
main failure mode is a reluctance to use the bottom of the 1–6 scale (never assigns 1) rather than
a verbosity problem. The verbosity-bias check came back clean relative to the human baseline.
