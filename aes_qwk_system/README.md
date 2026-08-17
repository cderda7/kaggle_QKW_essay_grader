# AES QWK Grading System

An automated essay grading system for `personal_training_set.csv` (100 essays from the Learning
Agency Lab / PERSUADE "Automated Essay Scoring 2.0" data), validated against the human gold scores
using Quadratic Weighted Kappa (QWK), the competition's own metric. Built as versioned, diffable
runs — v1 is the original implementation, v2–v4 are rubric revisions — so each change's effect
on QWK is directly comparable rather than overwriting prior results.

**Latest result: v4 QWK = 0.658** (v3: 0.645, v2: 0.640, v1: 0.594). v4 makes the trait weighting
explicit and unequal — argumentation 0.35, organization 0.25, development 0.25, conventions 0.15 —
by replacing v3's "at least 3 of the 4 traits at/above X" test with "traits carrying at least 0.75
of the total weight." Those are the same rule under equal weights, so nothing moves except what the
weights say should move. **Exactly one essay of 100 does**, and the +0.0137 QWK delta is 0.14
random-baseline standard deviations — inside noise. v4's case is that the rule now encodes the
intended weighting, not that the metric improved. It's also the first version *derived* rather than
graded: `evaluation/results_v4.md` has the fidelity check that justifies that, plus why the
footprint is one essay. Full reasoning in `decisions_log.md` #45–49.

Prior versions preserved unchanged in `evaluation/results_v1.md` / `results_v2.md` /
`results_v3.md` — but note the header on `results_v3.md`: it narrates an iteration that was
superseded before v4, and `decisions_log.md` #43 explains which artifact is which.

## How this was built (short version)

1. A fixed rubric (`rubric_v1.md` … `rubric_v4.md`) walks the grader through
   evidence extraction → sub-scores (v1: Organization, Development, Conventions; v2 adds
   Argumentation, with a rule that Argumentation=1 caps the holistic score at 3; v3 keeps the same
   4 sub-scores, now grounded in the verbatim official PERSUADE rubric, and replaces the single-field
   cap with a general severe-weakness gate — any sub-score ≤2 caps the essay in a disjunctive 1–3
   band, otherwise it must jointly clear multiple traits to reach a compensatory band; v4 keeps all
   of that and weights the four traits unequally, so the compensatory test becomes weight mass
   rather than a head count) → a holistic 1–6 score, with an explicit instruction not to use essay
   length as a scoring signal in either direction.
   **From v5 the split changes:** the rubric still defines all of the above, but the grader is only
   asked for the four trait scores — every rule that combines them runs in `grade_essays.py`. That
   makes the pipeline portable to models that can't reliably follow a seven-step conditional, and
   removes the grader-didn't-follow-the-gate failure mode entirely (decisions_log.md #50).
2. `personal_training_set.csv`'s 100 essays were split into 10 batches of 10
   (`grading/batches.json`, reused across versions so runs are essay-for-essay comparable) and
   graded in parallel by 10 independent Claude subagents per version, each reading the rubric and
   the source CSV directly, blind to the `score` column, and writing its results to
   `grading/batch_results/batch_NN.json` (v1), `grading/batch_results_v2/batch_NN.json` (v2), or
   `grading/batch_results_v3_iter3/batch_NN.json` (v3 — see decisions_log.md #43 on the name).
3. `grading/grade_essays.py --assemble --version v1|v2|v3` merges and validates those batch results
   into `grading/predictions_<version>.csv` (one row per essay: human score, system holistic +
   sub-scores, word count, rationale). It also checks version-specific rules — v2's
   Argumentation-caps-holistic rule, v3's full disjunctive/compensatory gate via
   `validate_v3_gate()` — and flags any violations (hard) or ambiguous edge cases (soft).
   **v4 skips steps 2–3 entirely**: it changes only how the four trait scores aggregate, so
   `--derive --version v4` recomputes holistic scores from `predictions_v3.csv` with the trait
   scores carried through untouched, after verifying that the same code reproduces v3's graded
   scores exactly under equal weights.
4. `evaluation/compute_qwk.py --version v1|v2|v3|v4` computes QWK, a confusion matrix, agreement rates,
   a random-shuffle baseline (is the QWK distinguishable from chance?), and — specifically because
   you flagged verbosity bias as a concern — correlations between word count and (a) human score,
   (b) system score, (c) the system-minus-human residual, so the bias question is answered
   empirically each run rather than assumed away. Output: `results_<version>.json` (numbers) and
   `results_<version>.md` (narrative interpretation).

## Folder / file map

```
aes_qwk_system/
  README.md                          — this file
  decisions_log.md                    — every judgment call made across all versions, with rationale
  rubric_v1.md                        — original grading rubric (3 sub-scores)
  rubric_v2.md                        — your revised rubric: teacher persona, hypothesize-prompt
                                         instruction, + Argumentation sub-score with a cap rule
  rubric_v3.md                        — graded (all 100 essays): restructures scoring into a
                                         disjunctive 1–3 band (one severe trait weakness caps the
                                         essay) vs. compensatory 4–6 band (requires jointly clearing
                                         multiple traits), grounded in the verbatim official
                                         PERSUADE rubric (rubric_official_persuade.md) rather than
                                         the reconstructed proxy v1/v2 used — see decisions_log.md
                                         #27–40. Later edited in place to widen the compensatory
                                         band to 3–6 and force holistic 1 on two traits at 1; the
                                         re-grade against that edit is what predictions_v3.csv holds
  rubric_v4.md                        — v3 plus explicit unequal trait weights (argumentation .35 /
                                         organization .25 / development .25 / conventions .15).
                                         Compensatory bands test weight mass >= 0.75 instead of
                                         counting 3 of 4 traits; the gate's four-trait average
                                         becomes weighted. NOT handed to a grader — v4 was derived
                                         from v3's trait scores, see decisions_log.md #45-49
  rubric_v5.md                        — v4 with steps 6-7 REMOVED: the grader's job stops at the
                                         four trait scores, and the gate/band/weight logic runs in
                                         code instead. Same scoring rules, same weights — only who
                                         executes them changed. Output schema is six fields
                                         (essay_id, evidence_notes, 4 traits). See decisions_log.md
                                         #50-53
  rubric_official_persuade.md         — verbatim official PERSUADE 2.0 rubric (Independent +
                                         Source-based variants), sourced from the corpus repo;
                                         supersedes the "reconstructed proxy" caveat from decision #2
  grading/
    grading_prompt_template.md        — exact prompt shape used per batch, and why essays are read
                                         from disk rather than pasted inline
    batches.json                      — the 10 batches of 10 essay_ids, shared by every version
    batch_results/batch_00..09.json   — raw v1 grading output (one array of 10 objects each)
    batch_results_v2/batch_00..09.json — raw v2 grading output
    batch_results_v3_iter3/batch_00..09.json — raw grading output from the ITERATION-3 v3 run
                                         (includes gate_applied/gate_rationale); each object leads
                                         with a post-hoc "SCORES": "<human> vs. <system>" line —
                                         see below. NOT the generation predictions_v3.csv describes:
                                         rubric_v3.md was edited and re-graded afterwards, and that
                                         iteration's batch JSONs were never saved. Renamed to say so
                                         — decisions_log.md #43
    batch_results_v3_iter3/_scores_annotation.json — generated manifest backing that field's leakage
                                         guard; do not hand-edit
    grade_essays.py                   — version-aware orchestration: assembles + validates batch
                                         results into predictions_<version>.csv; docstring documents
                                         the two ways to make this fully headless (real API call vs.
                                         this run's in-session subagent grading); validate_v3_gate()
                                         is the v3-specific disjunctive/compensatory rule checker;
                                         annotate_scores()/strip_scores() manage the SCORES field
    predictions_v1.csv                — v1 per-essay results
    predictions_v2.csv                — v2 per-essay results (adds system_argumentation column)
    predictions_v3.csv                — v3 per-essay results (adds system_gate_applied column)
    predictions_v4.csv                — v4 per-essay results, derived from predictions_v3.csv with
                                         identical trait scores; adds system_weighted_mean and
                                         system_decisive_mass so each band decision is auditable
  evaluation/
    compute_qwk.py                    — version-aware: computes QWK + all diagnostics from any
                                         predictions_<version>.csv
    results_v1.json / results_v1.md   — v1 metrics + narrative interpretation (preserved, unchanged)
    results_v2.json / results_v2.md   — v2 metrics + narrative interpretation, including a
                                         side-by-side comparison against v1 and whether the rubric
                                         change fixed the specific gap that motivated it
    results_v3.json / results_v3.md   — v3 metrics + narrative interpretation: the never-assigns-1
                                         fix confirmed, and the new "all-3s dead zone" cost it traded
                                         against (decisions_log.md #38-40). NOTE: the .json holds
                                         the current (iteration-4) v3 numbers while the .md narrates
                                         iteration 3 — see the header on the .md, decisions_log #43
    results_v4.json / results_v4.md   — v4 metrics + narrative: the one essay that moved and why,
                                         the equal-weight fidelity check behind deriving rather than
                                         re-grading, and why the weighting's footprint is structural
  tracker_log.json                    — structured log of iteration commits (QWK, ∆, rationale)
                                         for this project; canonical source for its Google Doc
                                         commit tracker. The AGENT ITSELF (run_tracker.py,
                                         build_tracker_doc.js) now lives outside this project, at
                                         projects/claude-agents/commit-tracker/ — see below — so it
                                         can be reused across projects rather than copied per-repo.
```

`personal_training_set.csv` itself is **not duplicated** here — everything reads it from its
existing location in the project folder, so there's a single source of truth.

## The `SCORES` field, and why the grader never writes it

From v3 on, every object in `batch_results_v3_iter3/*.json` leads with a one-line score comparison, so
reading a batch file tells you where the system agreed with the teacher before you read a single
rationale:

```json
{
  "SCORES": "3 vs. 2",

  "essay_id": "000d118",
  "evidence_notes": "...",
  ...
}
```

Left number is the human gold score, right is the system's `holistic_score`. **The grader does not
produce this field.** It's injected afterwards by `grade_essays.py --annotate-scores`, which reads
the gold scores from `personal_training_set.csv` — the same file the assembler already reads.

That ordering is the whole point, not an implementation detail. Asking the grader to emit
`"3 vs. 2"` would mean handing it the 3 first, which contradicts the "IGNORE the `score` column"
instruction the run's blindness depends on and would make QWK a measure of the model's willingness
to copy a number it was given. The failure wouldn't look like a failure, either — agreement would
*improve*. So three guards enforce the ordering mechanically rather than by convention:

- **Leakage detection.** `_scores_annotation.json` records every essay this script annotated. A
  `SCORES` field it can't account for aborts `--assemble` with an explanation, on the assumption
  that a grader produced it.
- **`--strip-scores`.** The inverse operation. Run it before showing prior batch results to any
  model — e.g. a v4 that compares itself against v3 — so gold scores never enter a grader's
  context. `--out-dir <dir>` writes blind copies and leaves the originals annotated.
- **CSV cross-check.** `SCORES` comes from the batch JSONs while every reported metric comes from
  `predictions_<version>.csv`; annotation warns if the two disagree, so the comparison you read is
  never quietly describing a different run than the headline QWK does.

Enabled for v3 and later only — v1/v2 batch results stay frozen. Future versions opt in with
`"annotate_scores": True` in `VERSION_CONFIG`. Full reasoning in `decisions_log.md` #41.

> **Resolved (decisions_log.md #43, closing #42):** the cross-check above fired the first time it
> ran, because `batch_results_v3/` and `predictions_v3.csv` described two different v3 generations.
> `tracker_log.json` settles which is which: entry 4 records **QWK 0.6446754** — the CSV's exact
> number — together with the rubric delta that produced it ("4-6 compensatory band now 3-6…
> 2 traits = 1 → holistic = 1"), and both of those rules are in `rubric_v3.md` and
> `validate_v3_gate()` as they stand. Entry 3 records 0.6381990, the batch files' number. Only
> 33/100 trait vectors and 4/100 rationales match across the two, so the CSV is a **later, separate
> grading run**, not a recompute — iteration 4, whose batch JSONs were never saved. The CSV is
> therefore authoritative and the batch directory is the stale artifact, which is the reverse of
> what #42 assumed. It has been renamed `batch_results_v3_iter3/` to say so; nothing was
> regenerated or overwritten. `--assemble --version v3` still works but reproduces iteration-3
> numbers.

## Re-running / extending

- To re-assemble predictions from existing batch results:
  `cd grading && python3 grade_essays.py --assemble --version v1` (or `v2`, `v3`) — note this
  needs `PERSONAL_TRAINING_SET_CSV=<path to personal_training_set.csv>` set in the environment if
  it isn't sitting two directories up from `grading/` (see the script's `--source-csv`/env-var
  handling).
  For v3 this also refreshes the `SCORES` fields in the batch results; add `--no-annotate` to leave
  those files byte-identical.
- To refresh `SCORES` without rebuilding the CSV:
  `cd grading && python3 grade_essays.py --annotate-scores --version v3`
- To produce blind (SCORES-free) copies before showing batch results to a model:
  `cd grading && python3 grade_essays.py --strip-scores --version v3 --out-dir /tmp/blind_v3`
- To assemble v5 once a grading run exists: grade against `rubric_v5.md` into
  `grading/batch_results_v5/`, then `cd grading && python3 grade_essays.py --assemble --version v5`.
  The grader supplies only `essay_id`, `evidence_notes` and the four trait scores; the holistic
  score, gate and gate rationale are computed during assembly. Assembly refuses a batch containing
  `holistic_score` / `gate_applied` / `gate_rationale`, since the v5 grader was never asked for them
  (decisions_log.md #51).
- To rebuild v4 from v3's trait scores (no grading run needed — v4 is a pure aggregation change):
  `cd grading && python3 grade_essays.py --derive --version v4`. This runs the equal-weight
  fidelity check first and aborts if the recompute no longer reproduces v3's graded scores exactly.
- To recompute metrics: `cd evaluation && python3 compute_qwk.py --version v1` (or `v2`, `v3`, `v4`)
- For a v5 (or any future change): if it changes only how trait scores *aggregate*, follow v4's
  pattern — add a `VERSION_CONFIG` entry with `"derived_from"` and a weights/rule block, then
  `--derive`. If it changes what a grader is asked to *judge*, it needs a real grading run: add
  `rubric_v5.md`, grade into `batch_results_v5/`, add a `VERSION_CONFIG` entry with a
  `batch_results_dir`, then `--assemble --version v5`.
  Two concrete candidates, both flagged in `results_v4.md`: (a) re-grade against `rubric_v4.md` to
  find out whether *telling* a grader that argumentation is weighted 0.35 also shifts how it assigns
  trait scores — a separate effect this derived version can't measure; (b) make the severe-weakness
  gate and the band floors weight-aware, so a low-weight trait can be compensated for. (b) is a
  change of standard rather than a generalisation and needs the official rubric's disjunctive
  "ONE OR MORE" language argued with directly — see decisions_log.md #48.

See `decisions_log.md` for every place a judgment call was made instead of an objectively-correct
choice, and why — including how the v1→v2 transition itself was handled (entries 13–18), the v3
rubric redesign and grading run (entries 27–40), and how the Commit Tracker agent works around this
environment's real constraints (entries 19–25).

## Commit Tracker agent

Turns this project's structured commit messages (`<label> ; QWK: ... ; Delta: ... ; rationale:
...`) into the Google Doc tracking table you built by hand in `Template GitHub Commit Tracker`.
**Moved out of this project** on 2026-08-14 to `projects/claude-agents/commit-tracker/` so it's
reusable for any project, not just this one — see that folder's README for how it works, and
`projects/claude-agents/README.md` for the catalog of every such shared agent. Only
`tracker_log.json` (this project's data) stays here; the agent itself does not. It runs on-demand
(ask Claude to "run the commit tracker for this project") rather than automatically in the
background — see the agent's own README for why.
