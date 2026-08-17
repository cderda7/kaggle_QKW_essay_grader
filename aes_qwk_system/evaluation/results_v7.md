# v7 results — the triage cap

**Headline: the cap moves QWK the right way and fails its own pre-registered test.** v7 scores
**0.6180** against v6 run B's 0.5954 and v4's 0.6584. `rubric_v7.md` §4.1 committed, before the run,
to "QWK recovers past v4's 0.658, anything less and the cap is not earning a second pass." It did
not. §4.3's validity check also fails, and fails harder than the headline does — **a rule that caps
the shortest essays, using no reading at all, scores 0.682.**

Reporting it in that order because the second finding is the one that decides what v8 does.

Setup: trait scores carried through from `predictions_v6_runB.csv` byte-identical (fidelity check
passes — recomputing them reproduces every holistic score and gate exactly), plus one new blind pass
against `rubric_v7_triage.md` returning `very_bad` / `bad` / `other`, combined by
`min(cap(label), category_holistic)`. The triage pass read a projection of the source CSV containing
only `essay_id` and `full_text`, so it never had a gold score to ignore.

## 1. Headline metrics

| | QWK | Exact | Adjacent | MAE | Mean signed error | corr(wc, system) |
|---|---|---|---|---|---|---|
| v4 | **0.6584** | 54% | 94% | 0.520 | +0.08 | 0.513 |
| v6 run B (= v7 pre-cap) | 0.5954 | 48% | 95% | 0.570 | +0.41 | 0.474 |
| **v7** | **0.6180** | 48% | 95% | 0.570 | **+0.31** | 0.483 |

Paired bootstrap, 4,000 reps:

| | ΔQWK | 95% CI | reps favouring |
|---|---|---|---|
| v7 vs v6 run B | **+0.0228** | [−0.015, +0.064] | 87.2% |
| v7 vs v4 | **−0.0406** | [−0.115, +0.032] | 13.7% |

Both intervals straddle zero. The honest statement is that v7 is **probably** better than v6 and
**probably** worse than v4, and that a 100-essay corpus cannot resolve either at this size — the same
SE ≈ 0.053 constraint `decisions_log.md` #54 established. The bias number is the one real
improvement: **+0.41 → +0.31**, which is the mechanism working as designed, just not far enough.

**§4.2 (trait-side properties preserved) is met by construction, not by measurement.** The trait
scores are the same integers; trait agreement and inter-trait correlation are v6 run B's, unchanged.
That was the point of deriving rather than re-grading, and the fidelity check is what licenses saying
so.

## 2. What the cap actually did

Labels: **`very_bad` 1, `bad` 20, `other` 79.** Corpus base rates for comparison — which the triage
reader was deliberately not told — are 9 human 1s and 25 human 2s.

The cap **bound on only 10 of the 100 essays**, because most flagged essays were already at 2 in the
trait path. That gap is the finding:

| | n | of which human ≤2 | precision |
|---|---|---|---|
| Flagged (`bad` or `very_bad`) | 21 | 15 | **71%** |
| **Of those, cap actually binding** | **10** | **5** | **50%** |

**The flags are accurate where they change nothing and a coin flip where they act.** This is not a
coincidence: an essay whose flag binds is by definition one where the trait path disagreed, and
disagreement selects for the hard cases. Any future version of this design has to be evaluated on the
binding subset, not the flag set — the flag-set precision of 71% is the number that looks good and
means least.

The ten essays that moved: five human 2s→ correct, five human 3s → wrong, one of the five correct
being the sole `very_bad` (human 1, 2 → 1). Recall on the essays that needed help: **15 of 34** human
≤2 flagged at all.

## 3. Rung A is mis-set — and it is v6's disease in a new instrument

**Of the 9 essays a human scored 1, the triage called one `very_bad`, five `bad`, and three
`other`.** Eight of nine cleared rung A.

Rung A asks whether you can state the writer's position and one reason without supplying either
yourself. That defines `very_bad` as **unintelligible**. The human 1s in this corpus are not
unintelligible — they are intelligible and empty. They state a position, give something reason-shaped,
and stop. So they clear rung A comfortably, and the only label left for them is `bad`, which caps at
2, which is where the trait path had already put most of them.

This is exactly the failure `results_v6.md` §3 diagnosed — *"the ladders' bottom rungs are too easy
to clear"* — reproduced in an instrument written specifically to avoid it. The rung was phrased as a
consequence question, which was the right lesson, but the consequence chosen (*can you understand
it?*) sits below where human raters put the 1/2 boundary (*is there anything here?*). Consequence
phrasing is necessary and not sufficient; the consequence has to be the one the boundary is actually
made of.

Rung-level detail:

| Deciding rung | n | mean human score |
|---|---|---|
| A → very_bad | 1 | 1.00 |
| B1 (repair) → bad | 9 | 2.00 |
| B2 (assertion only) → bad | 5 | 2.20 |
| B1+B2 → bad | 6 | 2.17 |
| B_cleared → other | 79 | 3.11 |

Every firing rung separates cleanly from `B_cleared`. **The instrument discriminates; it just does
not reach low enough.**

## 4. The validity check fails: this is largely a length detector

`rubric_v7.md` §4.3 required this to be reported whatever it said.

| Word-count quartile | fire rate |
|---|---|
| Q1 (shortest) | **48%** |
| Q2 | 16% |
| Q3 | 12% |
| Q4 (longest) | 8% |

corr(fired, word_count) = **−0.328**. Mean length of flagged essays 264 words, unflagged 377.

That alone would be suggestive rather than damning — short essays really are worse on average, and
the corpus correlates word count with human score at 0.688. The damning number is the baseline:

| Rule | QWK |
|---|---|
| No cap (v6 run B) | 0.5954 |
| **Triage cap (21 flagged, 10 binding)** | **0.6180** |
| Cap the 10 shortest essays at 2 — no reading at all | 0.6451 |
| Cap the 21 shortest essays at 2 | **0.6820** |
| Cap the 34 shortest essays at 2 | 0.7208 |

**A word-count threshold outperforms the semantic read at every matched budget.** And within the
shortest quartile the triage separates nothing: of the 25 shortest essays, 11 of the 12 it flagged
were human ≤2 — and so were 12 of the 13 it did not flag.

Two things this does **not** mean:

- **It is not a proposal.** The k in "k shortest" is chosen with hindsight on the same 100 essays,
  which is precisely the in-sample tuning #54's 1,688-variant sweep exists to warn about, and the
  rule is a pure verbosity-bias machine — the bias this project has refused by explicit instruction
  since v1 and measures every run. Adopting it would raise QWK by making the system wrong in the way
  the corpus is wrong.
- **It does not mean the triage read is length in disguise.** It means the read did not extract
  enough beyond length to beat it. Those are different claims and only the second is supported.

One more number in the wrong direction: corr(word_count, system_score) rose **0.474 → 0.483** and the
residual correlation moved **−0.464 → −0.356**. The cap made the system slightly *more* length-coupled,
not less.

## 5. Headroom, so the size of the remaining prize is on the record

An oracle cap — same mechanism, same `min()`, labels assigned with knowledge of the gold scores —
reaches **0.8488** on v6 run B's trait scores. The mechanism is not the limit. **The instrument is.**

## 6. Read together, and what v8 should do

v7 is a **partial success reported as a failure of its own test**, which is the right way round. The
architecture works: a blind holistic pass, capped, one-directional, ablatable from a column, with the
trait scores provably untouched. It cost 0.023 QWK of movement in the right direction and it left
0.23 on the table.

What went wrong is one rung, and it is diagnosed rather than guessed:

1. **Re-cut rung A at "is there anything here", not "can I understand it".** The 1/2 boundary in this
   corpus is emptiness, not unintelligibility. A candidate phrasing to argue with, not to adopt
   unexamined: *after one read, is there anything you could quote back to this student as their own
   thinking — a reason they gave, an example they chose — or only the prompt returned to you in
   different words?* Eight of nine human 1s should fail that. This is a rewrite of one table row.
2. **Re-run and evaluate on the binding subset.** Flag-set precision is a vanity metric here; §2 is
   the reason.
3. **Report the length quartile table again.** If a fixed rung A raises QWK while fire rate stays
   concentrated in Q1, the gain still has not been shown to be about reading.
4. **`results_v6.md`'s priority 1 remains open and untouched** — tightening rungs 2–3 on
   Organization/Development/Argumentation. v7 deliberately did not attempt it. It is now the more
   attractive of the two, because it fixes the floors where they broke rather than adding a second
   instrument that has to find the same floor from outside.

Not attempted, deliberately: no gate-threshold change, no aggregation sweep, no re-tuning of the caps
after seeing these numbers. The cap values 1 and 2 are the ones the design specified before the run.
