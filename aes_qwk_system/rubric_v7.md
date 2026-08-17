# AES Grading Rubric v7 — the triage cap

v7 is **not a rewrite of v6**. It is v6 plus one new, separately-run judgment, combined in code.
This file is the spec; it deliberately contains no trait-scale text, because none changed.

```
v7  =  rubric_v6.md          (trait pass — UNCHANGED, byte for byte)
     + rubric_v7_triage.md   (triage pass — NEW, run blind and separately)
     + the cap rule below    (combination — in code, in grade_essays.py)
```

---

## 1. What the two passes are

**Trait pass.** Exactly v6. A grader reads the essay against `rubric_v6.md`'s four 1–6 ladders and
returns `evidence_notes` plus four trait scores. `v4_holistic()` turns those into a *category
holistic score* by the same weighted gate/band rules used since v4. Nothing in this path knows a
triage pass exists.

**Triage pass.** A separate reader, a separate call, `rubric_v7_triage.md` as its entire prompt,
returning one label per essay: `very_bad`, `bad`, or `other`. Nothing in this path knows the trait
scales, the trait scores, or the holistic rules.

Neither pass sees the other's output. Neither sees the human `score` column — the triage pass is run
against a **projection of the source CSV containing only `essay_id` and `full_text`**, so its
blindness is structural rather than instructional (`decisions_log.md` #62–66).

## 2. The cap rule

```
holistic = min(cap(triage_label), category_holistic)

cap(very_bad) = 1
cap(bad)      = 2
cap(other)    = 6      # i.e. no constraint
```

Three properties this shape has, all of them load-bearing:

- **One-directional.** The triage label can only *lower* a score. `other` is not a floor — it says
  nothing, and an essay the triage pass waved through can still be sent to 1 or 2 by the trait path's
  own severe-weakness gate. That is exactly the "still possible to get a 2 even if it isn't flagged"
  requirement, and it falls out of `min()` rather than needing a rule of its own.
- **Non-inverting.** `min()` never raises an essay the traits scored lower. A `bad` flag on an essay
  whose four traits force a holistic 1 leaves it at 1. A hard assignment (`bad → exactly 2`) would
  have raised it, which would mean a coarse impression overruling a fine-grained judgment in the one
  direction where the fine-grained one is more likely right.
- **Ablatable.** `predictions_v7.csv` records `system_category_holistic` (pre-cap) beside
  `system_holistic_score` (post-cap), so the counterfactual "what would v7 have scored without the
  triage pass" is a column, not a re-run. It is by construction identical to v6 run B.

## 3. Why the triage pass is allowed to be holistic

v5 and v6 moved this project steadily away from asking a model for whole-essay judgments: v5 took the
aggregation rules out of the grader (`decisions_log.md` #50), v6 replaced whole-essay score-band
anchors with per-trait scales (#53, #55–61). A first-impression read is a whole-essay judgment. This
is a real tension and it is recorded, not glossed:

- The decomposition was adopted to fix **run-to-run trait variance** (#54), and it did — 33/100 →
  56/100 identical trait vectors. That machinery is untouched here; the trait pass is byte-identical
  v6. Whatever the triage pass's own stability turns out to be, it cannot degrade the trait scores,
  because it is not in their context.
- What decomposition *cost* was calibration at the bottom (`results_v6.md` §3), and the specific
  failure — never assigning a 1 — is one that a whole-essay read is well suited to catch and a
  bottom-rung analysis is not, since each individual ladder's floor can be cleared by an essay that
  fails as a whole.
- The judgment is bounded to two labels at the bottom of the scale and cannot reach above 2. It is a
  triage, in the medical sense: a cheap sort that decides who gets seen first, never the diagnosis.

The honest summary: v7 buys back the bottom of the distribution with a holistic judgment, and pays
for it with a second stochastic component whose own run-to-run stability has to be measured, not
assumed. §4 says how.

## 4. What v7 has to demonstrate

Stated before the run, in the manner of `rubric_v6_research_basis.md` §7.

1. **QWK recovers past v4's 0.658.** Anything less and the cap is not earning a second pass. The
   headroom is real — the corpus has 9 human 1s and 25 human 2s that v6 scores at 2–3 and 2–4
   respectively — but so is the risk, since a false `bad` on a human 3 or 4 costs quadratically.
2. **The trait-side properties survive unchanged.** Trait vector agreement and inter-trait
   correlation must be *identical* to v6 run B, not merely close — the trait scores are carried
   through untouched, so any difference means the pipeline leaked.
3. **The cap is not a length detector.** The corpus correlates word count with human score at 0.688,
   so a triage pass that fires on short essays would raise QWK for a reason that has nothing to do
   with reading quality. Report corr(fires, word_count) and the fire rate by length quartile; a cap
   that fires only in the bottom quartile is a failure even if QWK improves.
4. **Precision reported before recall.** Of the essays capped to 1, how many did a human score 1? Of
   those capped to 2, how many scored ≤2? A cap that fires often and correctly is good; a cap that
   fires often and loosely is v6's problem with the sign flipped.

**No target fire rate is given to the triage reader**, and none was tuned. The 9%/25% base rates of
the corpus are known to this file and were deliberately kept out of `rubric_v7_triage.md`: handing a
grader the answer key's distribution is a softer version of handing it the answer key.
`results_v7.md` reports the realized rates against those base rates as a *finding*.

## 5. What v7 explicitly does not do

- **Does not touch the gate threshold.** Still ≤2. `results_v6.md` §4 tested ≤3 and it overshot to
  84/100; the conclusion there was "fix the scales, not the threshold," and a cap is not a threshold
  change.
- **Does not sweep aggregation rules.** #54's 1,688-variant sweep scored negative out of sample.
- **Does not rewrite the trait ladders.** `results_v6.md`'s priority-1 recommendation — tightening
  rungs 2–3 on Organization/Development/Argumentation as consequence questions — remains open and
  unattempted. It is a genuine alternative to this version, not a complement that was done first.
  If v7 works, the honest reading is that *some* mechanism had to restore the bottom of the
  distribution, and this one is measurable in a single new pass while a ladder rewrite is not.

## 6. Output format

Trait pass: unchanged from v6 — six fields, see `rubric_v6.md`.
Triage pass: four fields, see `rubric_v7_triage.md`.
Neither grader emits a holistic score. `grade_essays.py --derive --version v7` combines them.
