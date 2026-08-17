#!/usr/bin/env python3
"""
grade_essays.py — orchestration script for the AES QWK grading system.

WHAT THIS SCRIPT DOES ON ITS OWN:
  - Loads personal_training_set.csv
  - Assembles predictions_<version>.csv from per-batch grading results (JSON files) matching
    grading/batches.json (the batch/essay_id split is shared across rubric versions)
  - Validates schema (all essay_ids present, scores in [1,6], version-specific rules honored)
  - Annotates v3+ batch results with a post-hoc human-vs-system SCORES field (see below)

WHAT IT DELIBERATELY DOES NOT DO (documented judgment call, see decisions_log.md #1):
  This sandbox does not expose a usable ANTHROPIC_API_KEY to shell scripts, so this script does
  NOT itself call an LLM API to grade essays. Instead, `score_essay_batch()` below is a stub that
  raises NotImplementedError with instructions for both of the two real ways to fill it in:

    (a) Point it at a real Claude API call (recommended for a fully headless, repeatable version):
        pip install anthropic --break-system-packages
        client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        # send the prompt built from grading_prompt_template.md + rubric_<version>.md, parse the
        # returned JSON array, and return it.

    (b) What actually happened for every version run so far: a human operator (Claude, running
        interactively via the Agent tool in a Cowork session) read each batch's essays and rubric
        and produced the JSON output by hand-reasoning through each essay, batch by batch, in
        parallel subagent calls. Raw JSON outputs are saved in grading/batch_results[_<version>]/,
        and this script's job is just to assemble and validate them into predictions_<version>.csv.

THE `SCORES` ANNOTATION FIELD (v3+, see decisions_log.md #41):
  Each object in batch_results_v3_iter3/*.json leads with a human-readable comparison field:

      "SCORES": "5 vs. 4",     # <teacher/human gold score> vs. <system holistic_score>

  so a reviewer skimming a batch file sees the agreement or disagreement for each essay before
  reading its rationale, without cross-referencing predictions_v3.csv.

  CRITICAL -- THE GRADER NEVER WRITES THIS FIELD. The validity of this whole project rests on the
  grader being blind to the `score` column (README step 2). If the grading prompt asked a model to
  emit "N vs. M", the model would have to be handed the human score first, and QWK would then be
  measuring nothing but its ability to copy a number it was given. So `SCORES` is injected strictly
  AFTER grading, by annotate_scores() below, which reads the gold scores from
  personal_training_set.csv -- the same file assemble() already reads. The grader's output schema
  and prompt are unchanged, and grading_prompt_template.md must never mention this field.

  Three guards keep it that way:
    1. An annotation manifest (_scores_annotation.json, written next to the batch files) records
       which essay_ids this script annotated. If a batch file turns up carrying `SCORES` for an
       essay the manifest doesn't account for, that field came from something other than this
       script -- most likely a grader that could see the gold score -- so check_no_foreign_scores()
       hard-errors instead of quietly folding it into the results.
    2. `--strip-scores` is the inverse operation, for producing blind copies of batch results
       before feeding them back to any model (e.g. a v4 run that compares itself against v3
       output). Never hand an annotated file to a grader.
    3. cross_check_predictions() warns when the holistic scores in the batch JSONs disagree with
       predictions_<version>.csv, since SCORES is computed from the former while every reported
       metric comes from the latter -- if they drift apart, the comparison a reviewer reads is not
       the one the headline QWK describes.

VERSIONING:
  v1 rubric  -> 3 sub-scores (organization, development, conventions), no cap rule
               -> grading/batch_results/*.json           -> predictions_v1.csv
  v2 rubric  -> 4 sub-scores (+ argumentation), argumentation==1 caps holistic_score at 3
               -> grading/batch_results_v2/*.json         -> predictions_v2.csv
  v3 rubric  -> same 4 sub-scores, but a general severe-weakness GATE (see validate_v3_gate()):
               any sub-score <=2 gates the essay into holistic in {1,2,3} with severity-graduated
               placement; otherwise holistic in {4,5,6} requires a "3-of-4 traits at/above
               threshold" compensatory rule. This replaces v2's single-field cap_rule, which only
               ever checked argumentation==1. Output also carries gate_applied/gate_rationale
               (written through to predictions_v3.csv as system_gate_applied) so the gate's actual
               effect is auditable per-essay, not just in aggregate. See decisions_log.md #27-37.
               Also the first version to carry the SCORES annotation field (decisions_log.md #41).
               -> grading/batch_results_v3_iter3/*.json   -> predictions_v3.csv
               NOTE the directory name: it holds the *iteration-3* grading run, which is NOT the
               generation predictions_v3.csv describes. See decisions_log.md #43 (resolving #42).
  v4         -> NOT A GRADING RUN. Same rules as v3, but the four traits are weighted
               (argumentation .35 / organization .25 / development .25 / conventions .15) and the
               compensatory "3 of 4 traits at/above threshold" test becomes "traits carrying >=0.75
               of total weight at/above threshold". Derived deterministically from v3's trait
               scores by derive_v4() -- no batch results, no grader. See decisions_log.md #45-49.
               -> grading/predictions_v3.csv              -> predictions_v4.csv
  v5 rubric  -> A REAL grading run again, but the grader's job now STOPS at the four trait scores.
               rubric_v5.md drops steps 6-7: the gate, the band placement and the weighted mean are
               no longer executed by a model, they are computed here by v4_holistic(). The output
               schema shrinks to essay_id + evidence_notes + the four traits; holistic_score,
               gate_applied and gate_rationale become outputs of this script. Aggregation is
               byte-identical to v4, so a v4-vs-v5 diff isolates the prompt change.
               Consequences: no gate validator is needed (a rule the grader never runs cannot be
               run wrongly), and the pipeline stops depending on the grader being able to follow a
               seven-step conditional -- which is what makes it portable to the sub-120B models the
               project's goal requires. See decisions_log.md #50.
               -> grading/batch_results_v5/*.json         -> predictions_v5.csv
  v6 rubric  -> Same architecture as v5, different rubric text: four per-trait 1-6 scales instead of
               whole-essay score-band anchors. Config byte-identical to v5 apart from paths.
               -> grading/batch_results_v6/*.json         -> predictions_v6.csv
               (v6_runB is an independent second grading of the same essays under the same rubric,
               used to measure run-to-run trait agreement. Not a rubric version.)
  v7         -> NOT A NEW TRAIT GRADING RUN. v7 is v6's trait scores (carried through from
               v6_runB untouched) plus a SECOND, INDEPENDENT pass: a blind first-impression triage
               that returns one label per essay -- very_bad / bad / other -- against
               rubric_v7_triage.md, which is the entire prompt that pass sees. The label caps the
               holistic score the trait path computed:
                   holistic = min(TRIAGE_CAPS[label], category_holistic)
               so it can only lower a score, never raise one, and never reaches above 2. The
               pre-cap score is written to predictions_v7.csv as system_category_holistic, which
               makes the no-triage counterfactual a column rather than a re-run.
               Motivation: results_v6.md section 3 -- v6 ranks essays as well as v4 but never
               assigns a 1, against 9 human 1s in the corpus. See rubric_v7.md and
               decisions_log.md #62-65.
               -> grading/predictions_v6_runB.csv + grading/batch_results_v7_triage/*.json
                  -> predictions_v7.csv
  Same batches.json (essay_id split) is reused across versions so runs are directly comparable.

USAGE:
    python3 grade_essays.py --assemble --version v1
    python3 grade_essays.py --assemble --version v2
    python3 grade_essays.py --assemble --version v3   # regenerates ITERATION-3 numbers, see #43
    python3 grade_essays.py --annotate-scores --version v3   # annotate only, no CSV rebuild
    python3 grade_essays.py --assemble --version v3 --no-annotate
    python3 grade_essays.py --strip-scores --version v3 --out-dir /tmp/blind_v3
    python3 grade_essays.py --derive --version v4    # recompute v4 from predictions_v3.csv
    python3 grade_essays.py --derive --version v4 --check-fidelity   # + equal-weight self-check
    python3 grade_essays.py --assemble --version v5  # traits from the grader, holistic computed here
    python3 grade_essays.py --make-blind-csv --out-dir /tmp/blind   # essay_id + full_text only
    python3 grade_essays.py --derive --version v7    # v6_runB traits + triage labels -> capped
"""

import argparse
import csv
import json
import math
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BATCHES_FILE = os.path.join(HERE, "batches.json")

# Post-hoc reviewer annotation. Injected by this script only -- never emitted by a grader.
SCORES_FIELD = "SCORES"
ANNOTATION_MANIFEST = "_scores_annotation.json"

# --- v4 trait weighting (decisions_log.md #45) -------------------------------------------------
# v1-v3 weight the four traits equally without ever saying so: the gate fires on *any* trait <=2,
# and the compensatory bands ask "are >=3 of the 4 traits at/above X" -- both treat the traits as
# interchangeable, i.e. 0.25 each. v4 makes the weighting explicit and unequal.
V4_WEIGHTS = {
    "organization": 0.25,
    "development": 0.25,
    "conventions": 0.15,
    "argumentation": 0.35,
}
EQUAL_WEIGHTS = {k: 0.25 for k in V4_WEIGHTS}

# The compensatory bands become a weight-mass test rather than a head count. The threshold is 0.75
# precisely because 3 of 4 equally-weighted traits carry 0.75 -- so under EQUAL_WEIGHTS this rule is
# byte-for-byte v3's "3 of 4" rule, and the new weights are the only thing that can move a score.
# That equivalence is what makes v4 a strict generalization instead of a second, confounded change.
# It also means only one trait subset behaves differently under V4_WEIGHTS: {organization,
# development, conventions} carries 0.65, below the bar -- so the essays that move are exactly those
# where argumentation is the sole trait below the threshold. See decisions_log.md #45.
MASS_THRESHOLD = 0.75

# --- v7 triage cap (rubric_v7.md section 2) ----------------------------------------------------
# A separate, blind first-impression pass returns one label per essay. The label caps the holistic
# score the trait path computed; it never raises it, and it cannot reach above 2. `other` maps to 6,
# which is the same as no constraint -- written as a cap rather than special-cased so the whole rule
# is a single min() with no branch to get wrong.
TRIAGE_CAPS = {"very_bad": 1, "bad": 2, "other": 6}
TRIAGE_RUNGS = ("A", "B1", "B2", "B1+B2", "B_cleared")

# --- v8 rung A0: the word-count floor (rubric_v8_triage.md) ------------------------------------
# Mechanical, applied here rather than read by the triage model -- nothing should depend on an LLM
# counting words reliably, and the instrument's length prohibition still binds every rung the model
# DOES answer. One-directional like every other cap: it can only lower a score.
#
# Thresholds derived on the 17,207 essays of train.csv that are NOT in personal_training_set.csv,
# selected by held-out violation rate alone and never fitted to the evaluation set:
#     cap 2 below 175 words -- touches 729 held-out essays, wrong on 14 of them (1.92%)
#     cap 3 below 225 words -- touches 2,928 held-out essays, wrong on 0 of them (0.00%)
# Ordered longest-threshold-last; first match wins, so the tighter cap takes precedence.
#
# This reverses, in a scoped way, the absolute anti-verbosity-bias prohibition every rubric v1-v7
# carries. The prohibition still binds the trait pass entirely (the trait grader never sees a word
# count) and every reading rung of the triage instrument. decisions_log.md #67.
LENGTH_FLOOR = ((175, 2), (225, 3))

# --- v9: the fitted aggregator (rubric_v9.md) --------------------------------------------------
# v3-v8 turn four trait scores into a holistic score with hand-written rules: a gate at any trait
# <=2, a disjunctive 1-3 band, a compensatory 3-6 band, a weight-mass test at 0.75. Those rules are
# where the loss is. v6 run B scores 0.5954, but the best QWK ANY monotone thresholding of its own
# weighted trait mean could reach is 0.6609 -- the discretization throws away ~0.07 by itself.
#
# v9 replaces all of it with a fitted map over two features, and nothing else:
#     s     = b0 + b1*f1 + b2*f2      (OLS against the human score)
#     score = 1 + #{i : s >= c_i}     (five cuts)
# where f1 is the V4-weighted trait mean (weights FIXED -- fitting them is worse at n=100, 0.6922
# vs 0.7233 in 5-fold CV) and f2 is log10(word_count). The cuts come from distribution matching,
# NOT from maximising QWK: c_i is the quantile of s at the fitting data's P(y <= i).
#
# Three coefficients and five derived cuts is a far smaller hypothesis class than the 1,688-variant
# rule sweep decisions_log.md #54 found scored negative out of sample. decisions_log.md #71-74.
AGGREGATOR_FEATURES = ("weighted_trait_mean", "log10_word_count")

# The candidate ladder, re-selected inside every LOO fold so the reported number includes the cost
# of choosing. Names are stable so the fold-selection tally is readable.
FEATURE_SETS = {
    "wmean":              ("weighted_trait_mean",),
    "wmean+len":          ("weighted_trait_mean", "log10_word_count"),
    "traits+len":         ("organization", "development", "conventions", "argumentation",
                           "log10_word_count"),
    "traits+len+severity": ("organization", "development", "conventions", "argumentation",
                            "log10_word_count", "min_trait", "n_traits_le2"),
}


def length_floor_cap(word_count, floor=LENGTH_FLOOR):
    """Cap implied by rung A0 for an essay of this length. 6 (i.e. no constraint) if it clears."""
    for threshold, cap in floor:
        if word_count < threshold:
            return cap
    return 6

# Fields a triage reader must NOT emit. It is handed rubric_v7_triage.md and nothing else -- it has
# never seen a trait scale or a gate rule -- so any of these means the batch came from the wrong
# prompt, or from a model that kept going past its instructions. Same style of guard as
# MODEL_SIDE_ONLY_FIELDS, and it fails loudly for the same reason.
TRIAGE_FORBIDDEN_FIELDS = (
    "holistic_score", "gate_applied", "gate_rationale", "score", SCORES_FIELD,
    "organization", "development", "conventions", "argumentation",
)

VERSION_CONFIG = {
    "v1": {
        "batch_results_dir": os.path.join(HERE, "batch_results"),
        "predictions_file": os.path.join(HERE, "predictions_v1.csv"),
        "sub_score_fields": ["organization", "development", "conventions"],
        "cap_rule": None,
        "extra_fields": [],
    },
    "v2": {
        "batch_results_dir": os.path.join(HERE, "batch_results_v2"),
        "predictions_file": os.path.join(HERE, "predictions_v2.csv"),
        "sub_score_fields": ["organization", "development", "conventions", "argumentation"],
        # (field, value) that caps holistic_score at cap_value
        "cap_rule": {"field": "argumentation", "trigger_value": 1, "cap_value": 3},
        "extra_fields": [],
    },
    "v3": {
        # Holds the ITERATION-3 grading run. predictions_v3.csv is the *later* iteration-4 run,
        # whose batch JSONs were never saved -- so `--assemble --version v3` does not rebuild the
        # checked-in CSV, it regenerates the superseded iteration-3 numbers (QWK 0.638 / 43% exact
        # instead of 0.645 / 54%). Renamed from batch_results_v3/ to say so in the filename.
        # decisions_log.md #43 has the evidence and closes #42.
        "batch_results_dir": os.path.join(HERE, "batch_results_v3_iter3"),
        "predictions_file": os.path.join(HERE, "predictions_v3.csv"),
        "sub_score_fields": ["organization", "development", "conventions", "argumentation"],
        "cap_rule": None,  # superseded by validate_v3_gate() below
        "gate_rule": "v3_severe_weakness",
        # (json field, csv column header) pairs written straight through to the predictions CSV,
        # beyond the standard essay_id/human_score/holistic/sub-scores/word_count/rationale columns
        "extra_fields": [("gate_applied", "system_gate_applied")],
        # v3+ only: inject the post-hoc "<human> vs. <system>" SCORES field into the batch JSONs.
        # Deliberately NOT enabled for v1/v2 -- those runs are frozen historical artifacts whose
        # results are already reported, and rewriting them would dirty the diff for no analytical
        # gain (decisions_log.md #41). Future versions opt in by setting this flag.
        "annotate_scores": True,
    },
    "v4": {
        # No batch_results_dir and no grading run: v4 is DERIVED from v3's trait scores by
        # derive_v4(). A weight change only touches how trait scores aggregate, and an
        # equal-weight recompute reproduces all 100 of v3's holistic scores and gate_applied
        # values exactly (--check-fidelity), so re-grading would only add grader noise on top of a
        # rule change that is fully mechanical. decisions_log.md #46.
        "derived_from": "v3",
        "predictions_file": os.path.join(HERE, "predictions_v4.csv"),
        "sub_score_fields": ["organization", "development", "conventions", "argumentation"],
        "cap_rule": None,
        "gate_rule": "v4_weighted",
        "weights": V4_WEIGHTS,
        "extra_fields": [("gate_applied", "system_gate_applied")],
        # No SCORES annotation: no grader is involved in a derived version, so there is nothing to
        # keep blind, and human_score already sits beside system_holistic_score in the CSV.
        "annotate_scores": False,
    },
    "v5": {
        # A REAL grading run (unlike v4), but the grader's job stops at the four trait scores.
        # rubric_v5.md drops steps 6-7 entirely: the severe-weakness gate, the band placement, the
        # weighted mean and the threshold tests are no longer things a model executes -- they are
        # computed here by v4_holistic(). decisions_log.md #50.
        #
        # Why: v3/v4 asked the grader to run a seven-step conditional (count traits <=2, branch on
        # how many are exactly 1, weight-average, round half up, clamp to a band, then test three
        # thresholds). Claude followed it perfectly -- the v4 fidelity check found 100/100
        # compliance -- but that is a frontier-model result, and the project's goal constrains it to
        # sub-120B models that will not follow it reliably. Moving the rule into code removes the
        # hardest part of the task from the model and leaves it doing what small models are actually
        # good at: applying trait descriptions to text and emitting four integers.
        #
        # It also deletes a whole class of bug rather than validating around it. validate_v3_gate()
        # exists to catch a grader failing to follow the gate; decisions #38-39 (the dead-zone
        # essays resolved two ways) and #42 (the drift) were both grader-executing-rules problems.
        # A rule the grader never executes cannot be executed wrongly, so v5 needs no gate
        # validator -- only the check below that the grader did not emit the fields it was not asked
        # for, which would mean it is running an older prompt.
        "batch_results_dir": os.path.join(HERE, "batch_results_v5"),
        "predictions_file": os.path.join(HERE, "predictions_v5.csv"),
        "sub_score_fields": ["organization", "development", "conventions", "argumentation"],
        "cap_rule": None,
        "gate_rule": None,          # nothing for a grader to violate
        "holistic_source": "derived",
        "weights": V4_WEIGHTS,      # same aggregation as v4, so v4->v5 isolates the prompt change
        "extra_fields": [],
        # SCORES annotation is back on: v5 IS graded, so batch files are worth reading, and the
        # reviewer still wants the human-vs-system comparison at the top of each object. The
        # holistic half of that comparison is derived here rather than read from the grader.
        "annotate_scores": True,
    },
    "v6": {
        # A REAL grading run, same architecture as v5: the grader's job stops at the four trait
        # scores and v4_holistic() computes the rest. The ONLY difference from v5 is the rubric
        # text -- rubric_v6.md replaces v5's six holistic score-band anchors with four per-trait
        # 1-6 scales extracted from the same official rubric, which is the change decisions_log.md
        # #53 named as next. Config is byte-identical to v5 apart from the paths, so a v5-vs-v6
        # diff isolates the per-trait scales and nothing else.
        "batch_results_dir": os.path.join(HERE, "batch_results_v6"),
        "predictions_file": os.path.join(HERE, "predictions_v6.csv"),
        "sub_score_fields": ["organization", "development", "conventions", "argumentation"],
        "cap_rule": None,
        "gate_rule": None,
        "holistic_source": "derived",
        "weights": V4_WEIGHTS,
        "extra_fields": [],
        "annotate_scores": True,
    },
    "v6_runB": {
        # Independent second grading of the SAME essays under the SAME rubric_v6.md. Exists only
        # to measure run-to-run trait agreement, which decisions_log.md #54 identifies as where the
        # remaining headroom is and which rubric_v6_research_basis.md section 7 names as v6's
        # primary metric. Not a rubric version; never reported as one.
        "batch_results_dir": os.path.join(HERE, "batch_results_v6_runB"),
        "predictions_file": os.path.join(HERE, "predictions_v6_runB.csv"),
        "sub_score_fields": ["organization", "development", "conventions", "argumentation"],
        "cap_rule": None,
        "gate_rule": None,
        "holistic_source": "derived",
        "weights": V4_WEIGHTS,
        "extra_fields": [],
        "annotate_scores": True,
    },
    "v7": {
        # v6's trait scores + a blind triage pass, combined by min(). See rubric_v7.md.
        #
        # derived_from is v6_runB rather than v6: run B is the later of the two v6 gradings and the
        # one results_v6.md reports the ranking diagnosis against (Spearman 0.694, best monotone
        # relabel 0.6615 vs v4's ceiling of 0.6651). Picking the better of two runs as a baseline
        # would be cherry-picking if v7 were being compared against v6 -- it is not: v7's headline
        # comparison is against v4 (0.6584), and using run B makes the triage cap's measured effect
        # SMALLER than it would look against run A. The conservative choice, recorded here so the
        # choice is visible rather than incidental. decisions_log.md #63.
        #
        # NOT a trait grading run: the four trait scores are carried through byte-identical, which
        # is what makes "v7 without the triage" exactly equal to v6_runB and lets the ablation be a
        # column in the CSV (system_category_holistic) instead of a separate run.
        "derived_from": "v6_runB",
        "predictions_file": os.path.join(HERE, "predictions_v7.csv"),
        "sub_score_fields": ["organization", "development", "conventions", "argumentation"],
        "cap_rule": None,
        "gate_rule": None,
        "weights": V4_WEIGHTS,      # unchanged since v4, so the cap is the only new variable
        "triage_results_dir": os.path.join(HERE, "batch_results_v7_triage"),
        "triage_caps": TRIAGE_CAPS,
        "extra_fields": [("gate_applied", "system_gate_applied")],
        # No SCORES annotation anywhere in v7. Same reasoning as v4 for the derived CSV (no trait
        # grader ran, and human_score already sits beside system_holistic_score there). For the
        # triage batch files it is a stronger point: a "<human> vs. <system>" line written into
        # them would put a gold score in the same directory a triage reader is pointed at, and
        # load_triage() rejects a SCORES field outright rather than trying to account for it.
        "annotate_scores": False,
    },
    "v8": {
        # Same architecture as v7 -- same trait scores, same min() composition, same blind pass --
        # with two changes, both in rubric_v8_triage.md:
        #   1. rung A re-cut from "unintelligible" to "empty" (v7 sent 8 of 9 human 1s past it);
        #   2. rung A0 added: the mechanical LENGTH_FLOOR above.
        # Deriving from the same v6_runB trait scores as v7 is what makes v7 and v8 a clean pair:
        # the trait side is identical in both, so a v7-vs-v8 diff is the instrument and nothing
        # else. decisions_log.md #67-69.
        "derived_from": "v6_runB",
        "predictions_file": os.path.join(HERE, "predictions_v8.csv"),
        "sub_score_fields": ["organization", "development", "conventions", "argumentation"],
        "cap_rule": None,
        "gate_rule": None,
        "weights": V4_WEIGHTS,
        "triage_results_dir": os.path.join(HERE, "batch_results_v8_triage"),
        "triage_caps": TRIAGE_CAPS,
        "length_floor": LENGTH_FLOOR,
        "extra_fields": [("gate_applied", "system_gate_applied")],
        "annotate_scores": False,
    },
    "v9": {
        # Derived, not graded -- the same pattern as v4. The four trait scores come through from
        # v6_runB untouched and rubric_v6.md is unchanged, so a v6-vs-v9 diff isolates the
        # aggregation and nothing else. No triage pass, no length floor, no gate, no bands: the
        # whole scoring rule is fit_aggregator() + apply_aggregator(). See rubric_v9.md.
        #
        # Why v6_runB and not v8: v8's predictions already have the triage cap and length floor
        # applied, and v9 replaces both. What v9 needs is the raw trait scores, which is exactly
        # what v6_runB holds -- and it is the same source v7 and v8 derive from, so all three sit
        # on identical trait data and differ only in what happens after.
        "derived_from": "v6_runB",
        "predictions_file": os.path.join(HERE, "predictions_v9.csv"),
        "sub_score_fields": ["organization", "development", "conventions", "argumentation"],
        "cap_rule": None,
        "gate_rule": None,
        "weights": V4_WEIGHTS,          # used only to build feature f1, not to place a band
        "aggregator_file": os.path.join(os.path.dirname(HERE), "aggregator_v9.json"),
        "features": AGGREGATOR_FEATURES,
        "extra_fields": [],
        "annotate_scores": False,
    },
}


# Fields v5+ graders must NOT emit: the model is not asked for them, so their presence means the
# batch was produced by an older prompt (or a model improvising past its instructions) and the
# run is not what predictions_v5.csv would claim it is.
MODEL_SIDE_ONLY_FIELDS = ("holistic_score", "gate_applied", "gate_rationale")


def derived_item_fields(item, cfg):
    """Compute the holistic score, gate and rationale for a graded item whose grader didn't.

    Single source of truth for the v5+ path: assemble() and annotate_scores() both go through here
    so a batch file can never be annotated with one holistic score and assembled with another.
    """
    traits = {f: item[f] for f in cfg["sub_score_fields"]}
    return v4_holistic(traits, cfg.get("weights", V4_WEIGHTS))


def validate_v3_gate(item, sub_score_fields):
    """Check one graded essay against rubric_v3.md's step 6/7 gate logic (decisions_log.md #27-37).

    Returns a list of human-readable violation strings (empty if the essay is fully compliant).
    Checks three independent things:
      1. Band membership: does holistic_score fall in the band the trait scores imply?
      2. Severity-graduated placement *within* the 1-3 band, when gated.
      3. The compensatory "N of 4 traits at/above threshold" rule, when not gated.
    Also cross-checks the grader's own self-reported `gate_applied` field against what the trait
    scores actually imply, since that field exists specifically to be auditable (decision #35) --
    a grader that says "compensatory" while a trait is <=2 (or vice versa) is a real error, not
    just an inconsistency in the write-up.
    """
    traits = {f: item[f] for f in sub_score_fields}
    lowest = min(traits.values())
    holistic = item["holistic_score"]
    severe = lowest <= 2
    n_severe = sum(1 for v in traits.values() if v <= 2)
    violations = []

    reported_gate = item.get("gate_applied")
    expected_gate = "disjunctive" if severe else "compensatory"
    if reported_gate not in ("disjunctive", "compensatory"):
        violations.append(f"gate_applied missing/invalid: {reported_gate!r}")
    elif reported_gate != expected_gate:
        violations.append(
            f"gate_applied={reported_gate!r} but trait scores {traits} imply {expected_gate!r}"
        )

    if severe:
        n_ones = sum(1 for v in traits.values() if v == 1)
        if holistic > 3:
            violations.append(f"severe weakness present {traits} but holistic_score={holistic} > 3")
        elif n_ones >= 2:
            if holistic != 1:
                violations.append(
                    f"2+ traits scored 1 {traits} so holistic_score should be 1 no matter what, got {holistic}"
                )
        elif n_ones == 1:
            avg = sum(traits.values()) / 4
            if avg < 2:
                expected = 1
            else:
                expected = min(3, math.floor(avg + 0.5))  # round-half-up, capped at 3
            if holistic != expected:
                violations.append(
                    f"exactly one trait ==1 {traits} (avg={avg:.2f}) so holistic_score should be "
                    f"{expected} (1 if avg<2, else round-half-up avg capped at 3), got {holistic}"
                )
        elif n_severe >= 2:  # lowest == 2, two or more traits <=2, none ==1
            if holistic != 2:
                violations.append(
                    f"{n_severe} traits <=2 {traits} (none ==1) so holistic_score should be 2, got {holistic}"
                )
        else:  # exactly one trait == 2, nothing lower, nothing else <=2
            if holistic not in (2, 3):
                violations.append(
                    f"exactly one trait ==2 {traits} so holistic_score should be 2 or 3, got {holistic}"
                )
    else:
        # No severe weakness: compensatory band is now 3-6. Check threshold rules for each band.
        n_at_least = lambda t: sum(1 for v in traits.values() if v >= t)

        if holistic == 3 and not (n_at_least(3) >= 3 and lowest >= 3):
            violations.append(
                f"holistic_score=3 (compensatory floor) requires >=3 traits >=3 and none <3, got {traits}"
            )
        elif holistic == 4 and not (n_at_least(4) >= 3 and lowest >= 3):
            violations.append(
                f"holistic_score=4 requires >=3 traits >=4 and none <3, got {traits}"
            )
        elif holistic == 5 and not (n_at_least(5) >= 3 and lowest >= 4):
            violations.append(f"holistic_score=5 requires >=3 traits >=5 and none <4, got {traits}")
        elif holistic == 6 and not (n_at_least(5) == 4 and n_at_least(6) >= 2):
            violations.append(f"holistic_score=6 requires all traits >=5 and >=2 traits ==6, got {traits}")

    return violations


def weighted_mean(traits, weights):
    """Weighted mean of the four trait scores. Weights sum to 1.0, so no normalisation needed."""
    return sum(weights[k] * v for k, v in traits.items())


def weight_mass(traits, weights, threshold_score):
    """Total weight carried by traits scoring at/above threshold_score.

    Under EQUAL_WEIGHTS this is just (count / 4), which is why comparing it against MASS_THRESHOLD
    (0.75) reproduces v3's "at least 3 of the 4 traits" test exactly.
    """
    return sum(w for k, w in weights.items() if traits[k] >= threshold_score)


def v4_holistic(traits, weights=V4_WEIGHTS):
    """v3's scoring rules with the trait weighting made explicit. Pure function, no I/O.

    Returns (holistic_score, gate_applied, gate_rationale, audit) -- the first three are the same
    values a v3 grader emitted by hand, now computed. `audit` carries the two numbers the rules
    actually turn on, so the CSV can record which one decided each essay:
        weighted_mean  -- always defined; the quantity the disjunctive band uses
        decisive_mass  -- the weight mass at the threshold the compensatory decision turned on,
                          or None for gated essays and for band 6 (both decided by counting rules,
                          where no mass was consulted and printing one would invent a rationale)

    Every v3 rule is preserved; exactly two things are weighted:

      1. The compensatory bands (step 7) test weight mass >= 0.75 instead of counting 3 of 4
         traits. Identical under equal weights (see MASS_THRESHOLD).
      2. The gate's "exactly one trait ==1 -> average the four traits" (step 6) uses the weighted
         mean instead of the arithmetic one.

    Deliberately NOT weighted, because these are membership tests rather than aggregations and
    weighting them would be a second change riding along with this one (decisions_log.md #48):
      - the gate trigger itself (ANY trait <=2 gates, including conventions at 0.15);
      - "2+ traits at 1 -> 1" and "2+ traits <=2 -> 2", which count severe failures;
      - the "no trait below X" floors on bands 4 and 5, and band 6's "all four >=5, at least two
        at 6" -- all four traits must clear those regardless of weight.

    One v3 rule was not deterministic and had to be pinned down for a code path: "exactly one trait
    ==2 -> holistic is 2 or 3, at grader discretion". This uses the weighted mean, rounded half up,
    clamped to [2,3]. That reproduces the grader on all 17 such essays in predictions_v3.csv under
    both weightings, so it is a formalisation of what the graders actually did, not a rule change.
    See decisions_log.md #47.
    """
    lowest = min(traits.values())
    n_ones = sum(1 for v in traits.values() if v == 1)
    n_severe = sum(1 for v in traits.values() if v <= 2)
    wmean = weighted_mean(traits, weights)
    audit = {"weighted_mean": wmean, "decisive_mass": None}

    if lowest <= 2:
        if n_ones >= 2:
            return 1, "disjunctive", (
                f"{n_ones} traits scored 1; multiple severe failures force holistic 1"
            ), audit
        if n_ones == 1:
            if wmean < 2:
                return 1, "disjunctive", (
                    f"one trait scored 1 and the weighted mean is {wmean:.2f} (<2), so holistic 1"
                ), audit
            score = min(3, math.floor(wmean + 0.5))
            return score, "disjunctive", (
                f"one trait scored 1; weighted mean {wmean:.2f} rounds to {score} within the "
                f"1-3 band"
            ), audit
        if n_severe >= 2:
            return 2, "disjunctive", (
                f"{n_severe} traits scored <=2 (none at 1), which fixes holistic at 2"
            ), audit
        sole = next(k for k, v in traits.items() if v == 2)
        score = max(2, min(3, math.floor(wmean + 0.5)))
        return score, "disjunctive", (
            f"{sole} alone scored 2; weighted mean {wmean:.2f} places the essay at {score} "
            f"within the 2-3 range"
        ), audit

    n_at_least = lambda t: sum(1 for v in traits.values() if v >= t)
    if n_at_least(5) == 4 and n_at_least(6) >= 2:
        return 6, "compensatory", "all four traits >=5 with at least two at 6", audit
    for band, floor in ((5, 4), (4, 3)):
        mass = weight_mass(traits, weights, band)
        if mass >= MASS_THRESHOLD - 1e-9 and lowest >= floor:
            return band, "compensatory", (
                f"traits at/above {band} carry weight {mass:.2f} (>= {MASS_THRESHOLD}) and no "
                f"trait is below {floor}"
            ), {**audit, "decisive_mass": mass}
    # Fell through both bands: the essay sits at the compensatory floor. The decision that put it
    # there is the failed band-4 test, so that is the mass worth recording.
    mass4 = weight_mass(traits, weights, 4)
    return 3, "compensatory", (
        f"no severe weakness, but traits at/above 4 carry only weight {mass4:.2f} "
        f"(< {MASS_THRESHOLD}), so the essay stays at the compensatory floor of 3"
    ), {**audit, "decisive_mass": mass4}


def check_v4_fidelity(source_predictions, weights=EQUAL_WEIGHTS):
    """Prove v4_holistic() models the rules v3's graders actually applied, before trusting v4.

    Runs the function over every v3 trait vector with EQUAL weights -- i.e. v3's own rules -- and
    compares against what the graders wrote. Any disagreement means the derivation is not a
    faithful re-implementation and v4's numbers would be measuring a coding error rather than the
    weight change, so this raises instead of warning. decisions_log.md #46.
    """
    mismatches = []
    for row in read_predictions(source_predictions):
        holistic, gate, _, _ = v4_holistic(row["traits"], weights)
        if holistic != row["holistic"] or gate != row["gate_applied"]:
            mismatches.append(
                f"{row['essay_id']}: graded ({row['holistic']}, {row['gate_applied']}) vs "
                f"recomputed ({holistic}, {gate}) from {row['traits']}"
            )
    if mismatches:
        raise RuntimeError(
            f"Fidelity check FAILED on {len(mismatches)} of the source essays -- v4_holistic() "
            f"does not reproduce the graded scores under equal weights, so it is not a faithful "
            f"model of the rules v4 claims to be generalising. Fix it before trusting any v4 "
            f"number.\n  " + "\n  ".join(mismatches[:10])
            + (f"\n  ... and {len(mismatches) - 10} more" if len(mismatches) > 10 else "")
        )
    return True


def read_predictions(path):
    """Read a predictions_<version>.csv into dicts, pulling the four trait scores out as ints."""
    fields = ["organization", "development", "conventions", "argumentation"]
    rows = []
    with open(path, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            rows.append({
                "essay_id": r["essay_id"],
                "human_score": int(r["human_score"]),
                "holistic": int(r["system_holistic_score"]),
                "traits": {k: int(r[f"system_{k}"]) for k in fields},
                "gate_applied": r.get("system_gate_applied"),
                "word_count": int(r["word_count"]),
                "rationale": r["rationale"],
            })
    return rows


def derive_v4(version="v4", check_fidelity=True):
    """Recompute a version's holistic scores from an earlier version's trait scores.

    v4 is not a grading run (see VERSION_CONFIG["v4"]). The four trait scores are carried through
    untouched -- only the aggregation changes -- so any diff between predictions_v3.csv and
    predictions_v4.csv is attributable to the weighting and nothing else. The output CSV adds two
    audit columns -- system_weighted_mean and system_decisive_mass -- recording the quantity each
    essay's band decision actually turned on, so the weighting's effect is checkable per-essay
    rather than only in aggregate (the v4 analog of the gate_applied reasoning in
    decisions_log.md #35). system_decisive_mass is blank where no mass was consulted: gated essays
    and band-6 essays are decided by counting rules.
    """
    cfg = VERSION_CONFIG[version]
    source_version = cfg["derived_from"]
    source_file = VERSION_CONFIG[source_version]["predictions_file"]
    weights = cfg["weights"]

    if not os.path.exists(source_file):
        raise FileNotFoundError(
            f"{version} derives from {source_version}, but {source_file} does not exist"
        )

    if check_fidelity:
        check_v4_fidelity(source_file)
        print(f"Fidelity check passed: recomputing {source_version} under equal weights reproduces "
              f"every graded holistic_score and gate_applied exactly")

    rows = read_predictions(source_file)
    changed = []
    out = []
    for row in rows:
        holistic, gate, rationale, audit = v4_holistic(row["traits"], weights)
        if holistic != row["holistic"]:
            changed.append((row["essay_id"], row["traits"], row["holistic"], holistic))
        out.append({**row, "new_holistic": holistic, "new_gate": gate, "new_rationale": rationale,
                    "audit": audit})

    sub_score_fields = cfg["sub_score_fields"]
    with open(cfg["predictions_file"], "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "essay_id", "human_score", "system_holistic_score",
            *[f"system_{field}" for field in sub_score_fields],
            "system_gate_applied", "system_weighted_mean", "system_decisive_mass",
            "word_count", "rationale",
        ])
        for r in out:
            mass = r["audit"]["decisive_mass"]
            writer.writerow([
                r["essay_id"], r["human_score"], r["new_holistic"],
                *[r["traits"][field] for field in sub_score_fields],
                r["new_gate"], f"{r['audit']['weighted_mean']:.2f}",
                "" if mass is None else f"{mass:.2f}",
                r["word_count"], r["new_rationale"],
            ])

    print(f"Derived {len(out)} rows from {os.path.basename(source_file)} -> "
          f"{os.path.basename(cfg['predictions_file'])}")
    print(f"Weights: " + ", ".join(f"{k}={v}" for k, v in weights.items()))
    if changed:
        print(f"{len(changed)} holistic score(s) changed vs {source_version}:")
        for eid, traits, old, new in changed:
            print(f"  {eid}  {traits}  {old} -> {new}")
    else:
        print(f"No holistic scores changed vs {source_version}")
    return {"n": len(out), "changed": changed}


def make_blind_csv(source_csv_path, out_path):
    """Write a projection of the source CSV containing only essay_id and full_text.

    Every grading run so far kept the grader blind to the gold score by *instruction* -- the prompt
    says "IGNORE the `score` column" and the column is right there in the file the grader opens
    (grading_prompt_template.md is candid about this being the weak point of reading essays from
    disk). For v7's triage pass the column is simply not in the file. Structural rather than
    instructional: a reader cannot ignore what it was never given, and the guarantee no longer
    depends on a model's compliance.

    Not retrofitted to the trait passes: v1-v6 are graded, reported and frozen, and re-running them
    against a different input file would change the artifact rather than the method. Applied from
    v7 forward. decisions_log.md #62.
    """
    with open(source_csv_path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["essay_id", "full_text"])
        for r in rows:
            writer.writerow([r["essay_id"], r["full_text"]])
    print(f"Wrote {len(rows)} blind rows (essay_id, full_text only) to {out_path}")
    return out_path


def load_triage(cfg, expected_ids):
    """Read and validate a version's triage batch results into {essay_id: item}.

    Validates four things, all of them hard errors -- a triage pass is one label per essay, so
    there is no such thing as a partially-usable one:
      1. every label is one of TRIAGE_CAPS;
      2. deciding_rung is one of TRIAGE_RUNGS and AGREES with the label (a `bad` decided by rung
         `A` means the reader mislabelled or misreported, and either way the row is not evidence of
         what it claims);
      3. no forbidden field (trait scores, holistic score, gold score) is present;
      4. coverage is exact -- every expected essay_id present, nothing extra.
    """
    triage_dir = cfg["triage_results_dir"]
    if not os.path.isdir(triage_dir):
        raise FileNotFoundError(
            f"{triage_dir} does not exist. v7 needs a triage pass: grade the essays against "
            f"rubric_v7_triage.md into that directory as batch_00.json .. batch_09.json first."
        )

    rung_implies = {
        "A": "very_bad",
        "B1": "bad", "B2": "bad", "B1+B2": "bad",
        "B_cleared": "other",
    }

    triage = {}
    problems = []
    for fname in batch_filenames(triage_dir):
        with open(os.path.join(triage_dir, fname)) as f:
            items = json.load(f)
        for item in items:
            eid = item.get("essay_id")
            label = item.get("triage_label")
            rung = item.get("deciding_rung")
            present = [k for k in TRIAGE_FORBIDDEN_FIELDS if k in item]
            if present:
                problems.append(f"{fname}:{eid} carries fields the triage reader was never asked "
                                f"for: {present}")
            if label not in TRIAGE_CAPS:
                problems.append(f"{fname}:{eid} triage_label={label!r} not one of "
                                f"{sorted(TRIAGE_CAPS)}")
            elif rung not in TRIAGE_RUNGS:
                problems.append(f"{fname}:{eid} deciding_rung={rung!r} not one of {TRIAGE_RUNGS}")
            elif rung_implies[rung] != label:
                problems.append(f"{fname}:{eid} deciding_rung={rung!r} implies "
                                f"{rung_implies[rung]!r} but triage_label={label!r}")
            if eid in triage:
                problems.append(f"{fname}:{eid} graded twice")
            triage[eid] = item

    missing = sorted(set(expected_ids) - set(triage))
    extra = sorted(set(triage) - set(expected_ids))
    if missing:
        problems.append(f"no triage label for {len(missing)} essay(s): {missing}")
    if extra:
        problems.append(f"triage labels for essays not in the source set: {extra}")

    if problems:
        raise ValueError(
            f"Triage pass in {os.path.basename(triage_dir)} is not usable "
            f"({len(problems)} problem(s)):\n  " + "\n  ".join(problems[:12])
            + (f"\n  ... and {len(problems) - 12} more" if len(problems) > 12 else "")
        )
    return triage


def apply_triage_cap(category_holistic, label, caps=TRIAGE_CAPS, floor_cap=6):
    """The rule, whole: holistic = min(cap(label), floor_cap, category_holistic). Pure function.

    v7 had no floor and passes floor_cap=6, which is why this reproduces v7 exactly.

    Returns (holistic, source) where `source` attributes the move to `triage`, `floor`, `both` or
    `none`. Attribution is computed here, once, and written to the CSV, because every claim about
    either mechanism's contribution is made of it -- and because v7's central finding was that the
    flags which *bind* behave nothing like the flags overall. Keeping the two mechanisms separable
    per-essay is what lets floor-only / read-only / both be read off one file instead of three runs.
    """
    label_cap = caps[label]
    capped = min(label_cap, floor_cap, category_holistic)
    if capped == category_holistic:
        return capped, "none"
    by_label = label_cap < category_holistic
    by_floor = floor_cap < category_holistic
    return capped, "both" if (by_label and by_floor) else ("triage" if by_label else "floor")


def derive_v7(version="v7", check_fidelity=True):
    """Combine a trait version's scores with a triage pass, per rubric_v7.md.

    Structurally derive_v4()'s sibling: no grading run for the traits, which are carried through
    from `derived_from` untouched. The difference is that a second, independently-produced input
    (the triage labels) joins them at the last step.

    The fidelity check is the same idea as check_v4_fidelity() and just as load-bearing: recompute
    the source version's holistic scores from its own trait scores under its own weights, with no
    cap applied, and require all 100 to match the source CSV exactly. If that fails, the trait path
    is not being carried through faithfully and any measured effect of the triage cap would be
    partly a bug -- so it raises rather than warns. Passing it is also what licenses the claim in
    rubric_v7.md section 2 that system_category_holistic IS v6_runB, column for column.
    """
    cfg = VERSION_CONFIG[version]
    source_version = cfg["derived_from"]
    source_file = VERSION_CONFIG[source_version]["predictions_file"]
    weights = cfg["weights"]
    caps = cfg["triage_caps"]

    if not os.path.exists(source_file):
        raise FileNotFoundError(
            f"{version} derives its trait scores from {source_version}, but {source_file} does "
            f"not exist"
        )

    if check_fidelity:
        check_v4_fidelity(source_file, weights=weights)
        print(f"Fidelity check passed: recomputing {source_version} from its own trait scores "
              f"reproduces every holistic score and gate exactly, so system_category_holistic "
              f"below is {source_version} unchanged")

    rows = read_predictions(source_file)
    triage = load_triage(cfg, [r["essay_id"] for r in rows])

    length_floor = cfg.get("length_floor")
    out = []
    for row in rows:
        category, gate, rationale, audit = v4_holistic(row["traits"], weights)
        item = triage[row["essay_id"]]
        floor_cap = length_floor_cap(row["word_count"], length_floor) if length_floor else 6
        holistic, source = apply_triage_cap(category, item["triage_label"], caps, floor_cap)
        out.append({**row, "category": category, "holistic": holistic, "gate": gate,
                    "rationale": rationale, "audit": audit, "source": source,
                    "floor_cap": floor_cap,
                    "label": item["triage_label"], "rung": item["deciding_rung"],
                    "note": item.get("triage_note", "")})

    sub_score_fields = cfg["sub_score_fields"]
    with open(cfg["predictions_file"], "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "essay_id", "human_score", "system_holistic_score",
            *[f"system_{field}" for field in sub_score_fields],
            "system_gate_applied", "system_weighted_mean", "system_decisive_mass",
            # v7 additions. system_category_holistic is the pre-cap score -- i.e. exactly what
            # this pipeline would have produced without the triage pass -- so the ablation is a
            # column comparison, not a second run.
            "system_category_holistic", "system_triage_label", "system_triage_rung",
            "system_floor_cap", "system_cap_source",
            "word_count", "rationale", "triage_note",
        ])
        for r in out:
            mass = r["audit"]["decisive_mass"]
            writer.writerow([
                r["essay_id"], r["human_score"], r["holistic"],
                *[r["traits"][field] for field in sub_score_fields],
                r["gate"], f"{r['audit']['weighted_mean']:.2f}",
                "" if mass is None else f"{mass:.2f}",
                r["category"], r["label"], r["rung"],
                r["floor_cap"], r["source"],
                r["word_count"], r["rationale"], r["note"],
            ])

    counts = {label: sum(1 for r in out if r["label"] == label) for label in caps}
    moved = [r for r in out if r["source"] != "none"]
    by_source = {s: sum(1 for r in moved if r["source"] == s)
                 for s in ("triage", "floor", "both")}
    print(f"Derived {len(out)} rows from {os.path.basename(source_file)} + "
          f"{os.path.basename(cfg['triage_results_dir'])} -> "
          f"{os.path.basename(cfg['predictions_file'])}")
    print("Triage labels: " + ", ".join(f"{k}={counts[k]}" for k in caps))
    if length_floor:
        print("Length floor (rung A0): " + ", ".join(f"wc<{t} -> cap {c}" for t, c in length_floor))
    print(f"Cap binding on {len(moved)} of {len(out)} essays "
          + ", ".join(f"{v} by {k}" for k, v in by_source.items() if v) + ":")
    for r in moved:
        print(f"  {r['essay_id']}  {r['label']:<8} wc={r['word_count']:<4} "
              f"{r['category']} -> {r['holistic']}  by {r['source']:<7} (human {r['human_score']})")
    return {"n": len(out), "counts": counts, "moved": moved, "by_source": by_source}


# --- v9 aggregator internals ------------------------------------------------------------------
# Deliberately stdlib-only, matching the rest of this module. compute_qwk.py owns the reporting and
# may use sklearn; the fitting path here stays dependency-free and fully deterministic, which is
# what lets the LOO number be reproduced exactly by anyone with Python and the CSV.

def _qwk(a, b, n_labels=6):
    """Quadratic weighted kappa over labels 1..n_labels. Matches sklearn's cohen_kappa_score."""
    n = len(a)
    O = [[0] * n_labels for _ in range(n_labels)]
    for x, y in zip(a, b):
        O[x - 1][y - 1] += 1
    ha = [0] * n_labels
    hb = [0] * n_labels
    for x in a:
        ha[x - 1] += 1
    for y in b:
        hb[y - 1] += 1
    num = den = 0.0
    for i in range(n_labels):
        for j in range(n_labels):
            w = ((i - j) ** 2) / ((n_labels - 1) ** 2)
            num += w * O[i][j]
            den += w * ha[i] * hb[j] / n
    return 1.0 - num / den if den else 0.0


def _solve(A, b):
    """Gaussian elimination with partial pivoting. Small, exact enough, no numpy."""
    n = len(A)
    M = [row[:] + [b[i]] for i, row in enumerate(A)]
    for col in range(n):
        p = max(range(col, n), key=lambda r: abs(M[r][col]))
        if abs(M[p][col]) < 1e-12:
            raise ValueError("singular design matrix -- a feature is constant or collinear")
        M[col], M[p] = M[p], M[col]
        for r in range(n):
            if r == col:
                continue
            f = M[r][col] / M[col][col]
            for c in range(col, n + 1):
                M[r][c] -= f * M[col][c]
    return [M[i][n] / M[i][i] for i in range(n)]


def _ols(X, y):
    """Least squares with an intercept. Returns [b0, b1, ...] via the normal equations."""
    D = [[1.0] + list(row) for row in X]
    k = len(D[0])
    A = [[sum(D[r][i] * D[r][j] for r in range(len(D))) for j in range(k)] for i in range(k)]
    v = [sum(D[r][i] * y[r] for r in range(len(D))) for i in range(k)]
    return _solve(A, v)


def _quantile(values, p):
    """Linear-interpolation quantile, same convention as numpy's default."""
    s = sorted(values)
    if not s:
        raise ValueError("empty")
    if p <= 0:
        return s[0]
    if p >= 1:
        return s[-1]
    pos = p * (len(s) - 1)
    lo = int(math.floor(pos))
    hi = min(lo + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (pos - lo)


def aggregator_features(traits, word_count, names=AGGREGATOR_FEATURES, weights=V4_WEIGHTS):
    """Feature vector for one essay. Pure; the single place a feature name becomes a number.

    Note what is NOT here: nothing the trait grader sees. The grader produces four integers under
    rubric_v6.md and never learns a word count -- length enters the system for the first and only
    time at this line, in the aggregation layer. decisions_log.md #74.
    """
    out = []
    for name in names:
        if name == "weighted_trait_mean":
            out.append(weighted_mean(traits, weights))
        elif name == "log10_word_count":
            out.append(math.log10(max(word_count, 1)))
        elif name == "min_trait":
            out.append(float(min(traits.values())))
        elif name == "n_traits_le2":
            out.append(float(sum(1 for v in traits.values() if v <= 2)))
        elif name in traits:
            out.append(float(traits[name]))
        else:
            raise KeyError(f"unknown aggregator feature {name!r}")
    return out


def fit_aggregator(rows, names=AGGREGATOR_FEATURES):
    """Fit coefficients and cut points on `rows`. Pure -- no I/O, no globals, no randomness.

    Two halves, and only the first is fitted against the target:
      * OLS coefficients for s = b0 + sum(b_i * f_i), regressing the human score on the features;
      * five cut points by DISTRIBUTION MATCHING -- c_i is the quantile of s at the fitting data's
        P(y <= i). No cut is chosen to maximise QWK, which is what keeps the discretization from
        becoming a second fitted model on top of the first.
    """
    X = [aggregator_features(r["traits"], r["word_count"], names) for r in rows]
    y = [float(r["human_score"]) for r in rows]
    beta = _ols(X, y)
    s = [beta[0] + sum(b * f for b, f in zip(beta[1:], x)) for x in X]
    cuts = [_quantile(s, sum(1 for v in y if v <= k) / len(y)) for k in range(1, 6)]
    for i in range(1, len(cuts)):                     # ties are possible on small fitting sets
        cuts[i] = max(cuts[i], cuts[i - 1])
    return {"features": list(names), "beta": beta, "cuts": cuts, "n": len(rows)}


def apply_aggregator(params, traits, word_count):
    """Score one essay. Returns (holistic, s, band_label) -- the band label is for auditing."""
    f = aggregator_features(traits, word_count, params["features"])
    beta = params["beta"]
    s = beta[0] + sum(b * v for b, v in zip(beta[1:], f))
    score = 1 + sum(1 for c in params["cuts"] if s >= c)
    lo = params["cuts"][score - 2] if score >= 2 else None
    hi = params["cuts"][score - 1] if score - 1 < len(params["cuts"]) else None
    band = f"[{'-inf' if lo is None else f'{lo:.3f}'}, {'inf' if hi is None else f'{hi:.3f}'})"
    return score, s, band


def loo_predict(rows, names=AGGREGATOR_FEATURES):
    """Leave-one-out predictions: essay i is scored by a model fitted on the other 99.

    This is the honest estimate the project reports, and it is deterministic -- no seed, no shuffle,
    one number that reproduces forever. Chosen over a 50/50 holdout on measurement grounds: across
    200 random 50/50 splits the same method returns mean 0.7231 with SD 0.052, so a single split
    would report mostly which split was drawn. decisions_log.md #73.
    """
    preds = []
    for i in range(len(rows)):
        fit_rows = rows[:i] + rows[i + 1:]
        assert len(fit_rows) == len(rows) - 1 and rows[i] not in fit_rows
        params = fit_aggregator(fit_rows, names)
        preds.append(apply_aggregator(params, rows[i]["traits"], rows[i]["word_count"])[0])
    return preds


def _inner_select(rows, k=5):
    """Pick a feature set by k-fold CV *within* the given rows. Deterministic: contiguous folds."""
    best = (-2.0, None)
    for name, names in FEATURE_SETS.items():
        preds = [0] * len(rows)
        for f in range(k):
            te = [i for i in range(len(rows)) if i % k == f]
            tr = [rows[i] for i in range(len(rows)) if i % k != f]
            try:
                params = fit_aggregator(tr, names)
            except ValueError:
                preds = None
                break
            for i in te:
                preds[i] = apply_aggregator(params, rows[i]["traits"], rows[i]["word_count"])[0]
        if preds is None:
            continue
        score = _qwk([r["human_score"] for r in rows], preds)
        if score > best[0]:
            best = (score, name)
    return best[1]


def loo_nested(rows):
    """LOO where the feature set is re-selected inside each fold.

    The un-nested number uses a feature set that was chosen by looking at CV on these same 100
    essays, which is contaminated. Re-selecting on each fold's 99 makes the reported number pay for
    the choice. The gap between nested and un-nested IS the contamination, and results_v9.md reports
    it rather than only the flattering half.
    """
    preds, chosen = [], {}
    for i in range(len(rows)):
        fit_rows = rows[:i] + rows[i + 1:]
        name = _inner_select(fit_rows)
        chosen[name] = chosen.get(name, 0) + 1
        params = fit_aggregator(fit_rows, FEATURE_SETS[name])
        preds.append(apply_aggregator(params, rows[i]["traits"], rows[i]["word_count"])[0])
    return preds, chosen


def fit_v9(version="v9", check_fidelity=True):
    """Fit the v9 aggregator and write aggregator_<version>.json.

    Reports the nested-LOO estimate FIRST and stores it in the artifact as `performance_estimate`,
    deliberately instead of an in-sample score: the shipped coefficients are fitted on all 100
    because that is the best estimate of them, but they have then seen every essay they would be
    scored on, so an in-sample number in this file would flatter the model every time anyone read
    it.
    """
    cfg = VERSION_CONFIG[version]
    source_file = VERSION_CONFIG[cfg["derived_from"]]["predictions_file"]
    if check_fidelity:
        check_v4_fidelity(source_file, weights=cfg["weights"])
        print(f"Fidelity check passed: {cfg['derived_from']}'s trait scores reproduce its own "
              f"holistic scores exactly, so the trait side is carried through untouched")

    rows = read_predictions(source_file)
    human = [r["human_score"] for r in rows]

    nested, chosen = loo_nested(rows)
    q_nested = _qwk(human, nested)
    plain = loo_predict(rows, cfg["features"])
    q_plain = _qwk(human, plain)

    print(f"\nNested LOO (feature set re-selected on each fold's {len(rows) - 1}): "
          f"QWK {q_nested:.4f}")
    print("  fold selections: " + ", ".join(f"{k}={v}" for k, v in sorted(chosen.items())))
    print(f"Un-nested LOO (features fixed to {'+'.join(cfg['features'])}): QWK {q_plain:.4f}")
    print(f"  selection cost: {q_plain - q_nested:+.4f}")

    params = fit_aggregator(rows, cfg["features"])
    params["performance_estimate"] = {
        "nested_loo_qwk": round(q_nested, 6),
        "loo_qwk_fixed_features": round(q_plain, 6),
        "fold_selections": chosen,
        "note": "LOO on the 100 evaluation essays. No in-sample score is recorded here on purpose "
                "-- these coefficients are fitted on all 100 and would flatter themselves.",
    }
    params["source"] = os.path.basename(source_file)
    with open(cfg["aggregator_file"], "w", encoding="utf-8") as f:
        json.dump(params, f, indent=2)
        f.write("\n")
    print(f"\nWrote {os.path.basename(cfg['aggregator_file'])}")
    print("  s = " + " + ".join(
        [f"{params['beta'][0]:.4f}"]
        + [f"{b:.4f}*{n}" for b, n in zip(params["beta"][1:], params["features"])]))
    print("  cuts = [" + ", ".join(f"{c:.4f}" for c in params["cuts"]) + "]")
    return params


def derive_v9(version="v9", check_fidelity=True):
    """Write predictions_<version>.csv from LOO predictions.

    Every row's score comes from a model fitted on the other 99 essays -- the CSV is the honest
    artifact, not an in-sample one. The all-100 coefficients live in aggregator_v9.json for anyone
    who wants to score a NEW essay; they are not what this file reports.
    """
    cfg = VERSION_CONFIG[version]
    agg_file = cfg["aggregator_file"]
    if not os.path.exists(agg_file):
        raise FileNotFoundError(
            f"{os.path.basename(agg_file)} does not exist. Fit it first:\n"
            f"    python3 grade_essays.py --fit --version {version}"
        )
    with open(agg_file) as f:
        params = json.load(f)
    if tuple(params["features"]) != tuple(cfg["features"]):
        raise ValueError(
            f"{os.path.basename(agg_file)} was fitted on features {params['features']} but "
            f"VERSION_CONFIG[{version!r}] declares {list(cfg['features'])}. Refusing to apply a "
            f"stale aggregator -- re-run --fit."
        )

    source_file = VERSION_CONFIG[cfg["derived_from"]]["predictions_file"]
    if check_fidelity:
        check_v4_fidelity(source_file, weights=cfg["weights"])
    rows = read_predictions(source_file)
    if params["n"] != len(rows):
        raise ValueError(f"aggregator fitted on n={params['n']} but source has {len(rows)} rows")

    preds = loo_predict(rows, cfg["features"])
    sub = cfg["sub_score_fields"]
    with open(cfg["predictions_file"], "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow([
            "essay_id", "human_score", "system_holistic_score",
            *[f"system_{x}" for x in sub],
            # v9 audit columns: the continuous score each essay's band decision turned on, the
            # interval it landed in, and the two features -- the analog of v4's system_weighted_mean
            # / system_decisive_mass, so a band decision is still checkable per essay.
            "system_continuous_score", "system_band", "system_weighted_mean", "system_log10_wc",
            "word_count", "rationale",
        ])
        for row, pred in zip(rows, preds):
            _, s, band = apply_aggregator(params, row["traits"], row["word_count"])
            f1, f2 = aggregator_features(row["traits"], row["word_count"],
                                         ("weighted_trait_mean", "log10_word_count"))
            w.writerow([
                row["essay_id"], row["human_score"], pred,
                *[row["traits"][x] for x in sub],
                f"{s:.4f}", band, f"{f1:.2f}", f"{f2:.3f}",
                row["word_count"],
                f"fitted aggregator, leave-one-out: s={s:.3f} falls in {band}",
            ])

    dist = {}
    for p in preds:
        dist[p] = dist.get(p, 0) + 1
    hd = {}
    for r in rows:
        hd[r["human_score"]] = hd.get(r["human_score"], 0) + 1
    print(f"Wrote {len(rows)} leave-one-out rows to {os.path.basename(cfg['predictions_file'])}")
    print(f"  QWK {_qwk([r['human_score'] for r in rows], preds):.4f}")
    print(f"  system distribution {dict(sorted(dist.items()))}")
    print(f"  human  distribution {dict(sorted(hd.items()))}")
    return {"n": len(rows), "preds": preds}


def score_essay_batch(essay_ids, csv_path, rubric_text):
    """Stub — see module docstring. Not used by any version's assembly path so far.

    If you ever wire this up: the returned objects must NOT contain a SCORES field. That field is
    added afterwards by annotate_scores() precisely so the grader stays blind to the gold score.
    """
    raise NotImplementedError(
        "No version so far called this function programmatically. Grading was performed by "
        "Claude via the Agent tool during an interactive session, with raw outputs saved to "
        "grading/batch_results[_<version>]/*.json. Wire this up to a real API call (see "
        "docstring) for a fully headless run."
    )


def load_source_scores(source_csv_path):
    scores = {}
    lengths = {}
    with open(source_csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            scores[row["essay_id"]] = int(row["score"])
            lengths[row["essay_id"]] = len(row["full_text"].split())
    return scores, lengths


def batch_filenames(batch_results_dir):
    """Batch JSONs in a results dir, in order, excluding sidecars like the annotation manifest."""
    return sorted(
        f for f in os.listdir(batch_results_dir)
        if f.startswith("batch_") and f.endswith(".json")
    )


def dump_batch(items, path):
    """Write a batch array in the project's 2-space style, with a blank line after SCORES.

    The blank line is cosmetic -- JSON ignores whitespace between tokens -- but it makes annotated
    files scannable: the reviewer's eye lands on the score comparison, then on the graded content
    beneath it. json.load() round-trips it away, so nothing that reads these files is affected.
    """
    text = json.dumps(items, indent=2, ensure_ascii=False)
    text = re.sub(rf'^(\s*"{SCORES_FIELD}": .*,)$', r"\1\n", text, flags=re.M)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text + "\n")


def load_manifest(batch_results_dir):
    """essay_ids this script has previously annotated, per batch file. Missing manifest -> empty."""
    path = os.path.join(batch_results_dir, ANNOTATION_MANIFEST)
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f).get("annotated", {})


def save_manifest(batch_results_dir, annotated):
    path = os.path.join(batch_results_dir, ANNOTATION_MANIFEST)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "_comment": (
                    "Written by grade_essays.py --annotate-scores. Records which essay_ids this "
                    "script injected the post-hoc SCORES field into. Its purpose is leakage "
                    "detection: a SCORES field on an essay NOT listed here was not written by this "
                    "script, which means something that could see the human gold score wrote it -- "
                    "most likely a grader, which would invalidate the blind-grading premise the "
                    "QWK numbers rest on. Do not hand-edit."
                ),
                "annotated": annotated,
            },
            f,
            indent=2,
        )
        f.write("\n")


def check_no_foreign_scores(batch_results_dir, version):
    """Leakage guard: every SCORES field present must be one this script wrote (per the manifest).

    A SCORES field encodes the human gold score. The grader is supposed to be blind to it, so a
    SCORES field this script cannot account for is evidence that the gold score reached the model's
    context -- which would make the run's QWK meaningless. Fail loudly rather than assemble it.
    """
    manifest = load_manifest(batch_results_dir)
    unaccounted = []
    for fname in batch_filenames(batch_results_dir):
        known = set(manifest.get(fname, []))
        with open(os.path.join(batch_results_dir, fname), encoding="utf-8") as f:
            for item in json.load(f):
                if SCORES_FIELD in item and item.get("essay_id") not in known:
                    unaccounted.append(f"{fname}:{item.get('essay_id')}")
    if unaccounted:
        raise RuntimeError(
            f"{len(unaccounted)} essay(s) carry a '{SCORES_FIELD}' field that this script did not "
            f"write: {unaccounted[:10]}{' ...' if len(unaccounted) > 10 else ''}\n"
            f"That field encodes the human gold score, so no grader should ever be producing it. "
            f"If one is, the run is not blind and its QWK is not meaningful -- check the grading "
            f"prompt before trusting these results. To clear the field and start over:\n"
            f"    python3 grade_essays.py --strip-scores --version {version}"
        )


def cross_check_predictions(version, batch_holistics):
    """Warn if the batch JSONs disagree with the version's existing predictions CSV.

    SCORES is computed from each batch JSON's holistic_score, while every reported metric (QWK,
    confusion matrix, results_<version>.md) comes from predictions_<version>.csv. If the two drift
    apart -- a batch re-graded without rebuilding the CSV, or the reverse -- then the comparison a
    reviewer reads in the batch file is not the comparison the headline QWK describes, and nothing
    would otherwise say so. Non-fatal, because the CSV is legitimately absent before the first
    assemble; loud, because a silent drift here quietly invalidates the analysis.
    """
    predictions_file = VERSION_CONFIG[version]["predictions_file"]
    if not os.path.exists(predictions_file):
        return []

    mismatches = []
    with open(predictions_file, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            eid = row["essay_id"]
            if eid in batch_holistics and int(row["system_holistic_score"]) != batch_holistics[eid]:
                mismatches.append((eid, batch_holistics[eid], int(row["system_holistic_score"])))

    if mismatches:
        preview = ", ".join(f"{e}: batch={b} csv={c}" for e, b, c in mismatches[:8])
        print(
            f"WARNING: {len(mismatches)} of {len(batch_holistics)} essays have a holistic_score in "
            f"{os.path.basename(VERSION_CONFIG[version]['batch_results_dir'])}/ that disagrees with "
            f"{os.path.basename(predictions_file)} [{preview}"
            f"{', ...' if len(mismatches) > 8 else ''}].\n"
            f"         The SCORES fields just written reflect the BATCH files; the reported QWK "
            f"reflects the CSV. Re-run --assemble to rebuild the CSV from the batch results, then "
            f"recompute metrics, before trusting either.",
            file=sys.stderr,
        )
    return mismatches


def annotate_scores(source_csv_path, version, quiet=False):
    """Inject/refresh the leading "<human> vs. <system>" SCORES field in a version's batch JSONs.

    Runs strictly after grading -- see the module docstring. Idempotent: every value is recomputed
    on each run, so editing a holistic_score and re-annotating corrects the comparison rather than
    leaving a stale one behind.

    Raises RuntimeError if a batch file carries SCORES for an essay the manifest doesn't account
    for, since that field could only have come from something other than this script.
    """
    cfg = VERSION_CONFIG[version]
    if not cfg.get("annotate_scores"):
        raise ValueError(
            f"annotate_scores is not enabled for {version} (only v3+ carries the SCORES field; "
            f"v1/v2 batch results are frozen historical artifacts)"
        )

    batch_results_dir = cfg["batch_results_dir"]
    human_scores, _ = load_source_scores(source_csv_path)
    check_no_foreign_scores(batch_results_dir, version)

    new_manifest, changed, total = {}, 0, 0
    batch_holistics = {}
    for fname in batch_filenames(batch_results_dir):
        path = os.path.join(batch_results_dir, fname)
        with open(path, encoding="utf-8") as f:
            items = json.load(f)

        annotated_items = []
        for item in items:
            eid = item["essay_id"]
            if eid not in human_scores:
                raise ValueError(f"{fname}: essay_id {eid} has no human score in {source_csv_path}")
            # v5+: the grader never wrote a holistic_score, so compute the system half of the
            # comparison from the trait scores using the same function assemble() uses.
            if cfg.get("holistic_source") == "derived":
                system_holistic = derived_item_fields(item, cfg)[0]
            else:
                system_holistic = item["holistic_score"]
            value = f"{human_scores[eid]} vs. {system_holistic}"
            batch_holistics[eid] = system_holistic
            if item.get(SCORES_FIELD) != value:
                changed += 1
            # Rebuild so SCORES leads the object; every other key keeps its original order.
            annotated_items.append(
                {SCORES_FIELD: value, **{k: v for k, v in item.items() if k != SCORES_FIELD}}
            )
            total += 1

        dump_batch(annotated_items, path)
        new_manifest[fname] = [i["essay_id"] for i in annotated_items]

    save_manifest(batch_results_dir, new_manifest)
    if not quiet:
        print(f"Annotated {total} essays across {len(new_manifest)} batch files in "
              f"{batch_results_dir} ({changed} value(s) written or refreshed)")
    mismatches = cross_check_predictions(version, batch_holistics)
    return {"total": total, "changed": changed, "files": len(new_manifest),
            "csv_mismatches": mismatches}


def strip_scores(version, out_dir=None):
    """Inverse of annotate_scores(): produce batch results carrying no SCORES field.

    Use this before showing prior batch results to any model (e.g. a v4 run that compares itself
    against v3 output), so gold scores never enter a grader's context. With out_dir the originals
    are left alone and blind copies are written there; without it, the files are stripped in place
    and the annotation manifest is cleared.
    """
    cfg = VERSION_CONFIG[version]
    src_dir = cfg["batch_results_dir"]
    dest_dir = out_dir or src_dir
    os.makedirs(dest_dir, exist_ok=True)

    names = batch_filenames(src_dir)
    stripped = 0
    for fname in names:
        with open(os.path.join(src_dir, fname), encoding="utf-8") as f:
            items = json.load(f)
        clean = []
        for item in items:
            if SCORES_FIELD in item:
                stripped += 1
            clean.append({k: v for k, v in item.items() if k != SCORES_FIELD})
        dump_batch(clean, os.path.join(dest_dir, fname))

    if out_dir:
        print(f"Wrote blind copies of {len(names)} batch files to {dest_dir} "
              f"({stripped} SCORES field(s) removed); originals in {src_dir} untouched")
    else:
        manifest_path = os.path.join(src_dir, ANNOTATION_MANIFEST)
        if os.path.exists(manifest_path):
            os.remove(manifest_path)
        print(f"Stripped {stripped} SCORES field(s) in place from {src_dir} and cleared "
              f"{ANNOTATION_MANIFEST}")
    return stripped


def assemble(source_csv_path, version, annotate=True):
    cfg = VERSION_CONFIG[version]
    if cfg.get("derived_from"):
        raise ValueError(
            f"{version} has no batch results to assemble -- it is derived from "
            f"{cfg['derived_from']}'s trait scores rather than graded. Use:\n"
            f"    python3 grade_essays.py --derive --version {version}"
        )
    sub_score_fields = cfg["sub_score_fields"]
    extra_fields = cfg.get("extra_fields", [])
    gate_rule = cfg.get("gate_rule")
    derived_holistic = cfg.get("holistic_source") == "derived"
    if derived_holistic:
        # v5+: the grader supplies evidence notes and four trait scores, nothing else.
        required_fields = ["essay_id", "evidence_notes", *sub_score_fields]
    else:
        required_fields = ["essay_id", "evidence_notes", *sub_score_fields,
                           "holistic_score", "rationale"]
        if gate_rule == "v3_severe_weakness":
            required_fields += ["gate_applied", "gate_rationale"]

    human_scores, word_counts = load_source_scores(source_csv_path)

    with open(BATCHES_FILE) as f:
        batches = json.load(f)
    expected_ids = [eid for batch in batches for eid in batch]

    results = {}
    batch_results_dir = cfg["batch_results_dir"]
    if not os.path.isdir(batch_results_dir):
        print(f"ERROR: {batch_results_dir} does not exist yet.", file=sys.stderr)
        sys.exit(1)

    # Leakage guard runs before anything here is trusted: if a grader emitted SCORES, the run was
    # not blind and there is no point assembling predictions from it. See module docstring.
    if cfg.get("annotate_scores"):
        check_no_foreign_scores(batch_results_dir, version)

    cap_violations = []
    gate_violations = []
    soft_gate_notes = []
    unexpected_fields = []
    for fname in batch_filenames(batch_results_dir):
        with open(os.path.join(batch_results_dir, fname)) as f:
            batch_results = json.load(f)
        for item in batch_results:
            missing = [k for k in required_fields if k not in item]
            if missing:
                raise ValueError(f"{fname}: item {item.get('essay_id')} missing fields {missing}")
            if derived_holistic:
                present = [k for k in MODEL_SIDE_ONLY_FIELDS if k in item]
                if present:
                    unexpected_fields.append((fname, item["essay_id"], present))
            checked = sub_score_fields if derived_holistic else (*sub_score_fields, "holistic_score")
            for score_field in checked:
                v = item[score_field]
                if not isinstance(v, int) or not (1 <= v <= 6):
                    raise ValueError(
                        f"{fname}: essay {item['essay_id']} field {score_field}={v} out of [1,6]"
                    )
            cap = cfg["cap_rule"]
            if cap and item[cap["field"]] == cap["trigger_value"] and item["holistic_score"] > cap["cap_value"]:
                cap_violations.append((item["essay_id"], item[cap["field"]], item["holistic_score"]))
            if gate_rule == "v3_severe_weakness":
                issues = validate_v3_gate(item, sub_score_fields)
                hard = [i for i in issues if not i.startswith("SOFT:")]
                soft = [i for i in issues if i.startswith("SOFT:")]
                if hard:
                    gate_violations.append((item["essay_id"], hard))
                if soft:
                    soft_gate_notes.append((item["essay_id"], soft))
            results[item["essay_id"]] = item

    if unexpected_fields:
        preview = ", ".join(f"{f}:{e} {p}" for f, e, p in unexpected_fields[:8])
        raise ValueError(
            f"{len(unexpected_fields)} essay(s) carry fields the {version} grader was never asked "
            f"for: {preview}{', ...' if len(unexpected_fields) > 8 else ''}\n"
            f"rubric_{version}.md stops at the four trait scores -- the holistic score, gate and "
            f"gate rationale are computed here, not graded. Their presence means this batch came "
            f"from an older prompt (or a model that kept going past its instructions), so it is not "
            f"the run predictions_{version}.csv would describe. Re-grade against rubric_{version}.md, "
            f"or assemble it as the version it actually is."
        )
    if cap_violations:
        print(f"WARNING: {len(cap_violations)} cap-rule violations (grader didn't apply the rule "
              f"correctly): {cap_violations}", file=sys.stderr)
    if gate_violations:
        print(f"WARNING: {len(gate_violations)} v3 gate-rule violations (grader didn't apply the "
              f"disjunctive/compensatory logic correctly): {gate_violations}", file=sys.stderr)
    if soft_gate_notes:
        print(f"NOTE: {len(soft_gate_notes)} soft v3 gate advisories (not hard rule violations): "
              f"{soft_gate_notes}", file=sys.stderr)

    missing_ids = set(expected_ids) - set(results.keys())
    extra_ids = set(results.keys()) - set(expected_ids)
    if missing_ids:
        raise ValueError(f"Missing grades for essay_ids: {sorted(missing_ids)}")
    if extra_ids:
        print(f"WARNING: graded essay_ids not in source set (ignored): {sorted(extra_ids)}",
              file=sys.stderr)

    predictions_file = cfg["predictions_file"]
    with open(predictions_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if derived_holistic:
            # Same column set derive_v4() writes, so predictions_v4.csv and predictions_v5.csv are
            # directly diffable -- with identical trait scores they must produce identical rows,
            # which is what isolates v5's prompt change from the aggregation.
            writer.writerow([
                "essay_id", "human_score", "system_holistic_score",
                *[f"system_{field}" for field in sub_score_fields],
                "system_gate_applied", "system_weighted_mean", "system_decisive_mass",
                "word_count", "rationale",
            ])
            for eid in expected_ids:
                r = results[eid]
                holistic, gate, rationale, audit = derived_item_fields(r, cfg)
                mass = audit["decisive_mass"]
                writer.writerow([
                    eid, human_scores[eid], holistic,
                    *[r[field] for field in sub_score_fields],
                    gate, f"{audit['weighted_mean']:.2f}",
                    "" if mass is None else f"{mass:.2f}",
                    word_counts[eid], rationale,
                ])
        else:
            writer.writerow([
                "essay_id", "human_score", "system_holistic_score",
                *[f"system_{field}" for field in sub_score_fields],
                *[header for (_, header) in extra_fields],
                "word_count", "rationale",
            ])
            for eid in expected_ids:
                r = results[eid]
                writer.writerow([
                    eid, human_scores[eid], r["holistic_score"],
                    *[r[field] for field in sub_score_fields],
                    *[r[json_field] for (json_field, _) in extra_fields],
                    word_counts[eid], r["rationale"],
                ])

    print(f"Wrote {len(expected_ids)} rows to {predictions_file}")

    # Refresh the reviewer-facing SCORES field now that the holistic scores are validated. Post-hoc
    # by construction -- the grader finished long before this point in the pipeline.
    annotation = None
    if annotate and cfg.get("annotate_scores"):
        annotation = annotate_scores(source_csv_path, version)

    return {"cap_violations": cap_violations, "gate_violations": gate_violations,
            "soft_gate_notes": soft_gate_notes, "annotation": annotation}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--assemble", action="store_true",
                         help="Assemble predictions_<version>.csv from grading/batch_results*/*.json")
    parser.add_argument("--annotate-scores", action="store_true",
                         help="Inject/refresh the post-hoc '<human> vs. <system>' SCORES field at "
                              "the top of each object in the version's batch result JSONs, without "
                              "rebuilding the predictions CSV. v3+ only. Reviewer convenience "
                              "applied AFTER grading -- the grader never sees or writes it.")
    parser.add_argument("--no-annotate", action="store_true",
                         help="With --assemble, skip the SCORES refresh and leave the batch JSONs "
                              "byte-identical")
    parser.add_argument("--strip-scores", action="store_true",
                         help="Remove the SCORES field from the version's batch results. Use this "
                              "before showing prior batch output to any model, so gold scores "
                              "never reach a grader's context.")
    parser.add_argument("--derive", action="store_true",
                         help="Recompute predictions_<version>.csv from the trait scores of the "
                              "version it declares in `derived_from`, applying that version's trait "
                              "weights. For versions that are a pure aggregation change (v4) and so "
                              "need no re-grading. Trait scores are carried through unmodified.")
    parser.add_argument("--check-fidelity", action="store_true", default=None,
                         help="With --derive, verify first that the recompute reproduces the source "
                              "version's graded scores exactly under equal weights (on by default; "
                              "disable with --no-check-fidelity)")
    parser.add_argument("--no-check-fidelity", action="store_true",
                         help="Skip the fidelity check before deriving. Not recommended.")
    parser.add_argument("--fit", action="store_true",
                         help="Fit the version's aggregator and write aggregator_<version>.json. "
                              "Reports nested leave-one-out first, then the fixed-feature LOO, and "
                              "records both in the artifact. v9+.")
    parser.add_argument("--make-blind-csv", action="store_true",
                         help="Write a projection of the source CSV containing only essay_id and "
                              "full_text, for passes that must not see the gold score at all "
                              "(v7's triage pass). Goes to --out-dir, default /tmp/blind_source.")
    parser.add_argument("--out-dir", default=None,
                         help="With --strip-scores, write blind copies here instead of stripping "
                              "the originals in place. With --make-blind-csv, where to write it.")
    parser.add_argument("--version", default="v1", choices=sorted(VERSION_CONFIG.keys()),
                         help="Which rubric version's batch results to assemble")
    parser.add_argument("--source-csv", default=None,
                         help="Path to personal_training_set.csv (defaults to sibling of this "
                              "script's parent dir, i.e. ../../personal_training_set.csv, which "
                              "matches the layout once this folder lives inside the project dir)")
    args = parser.parse_args()

    source_csv = args.source_csv or os.path.join(HERE, "..", "..", "personal_training_set.csv")
    source_csv = os.environ.get("PERSONAL_TRAINING_SET_CSV", source_csv)

    if args.make_blind_csv:
        out_dir = args.out_dir or "/tmp/blind_source"
        make_blind_csv(source_csv, os.path.join(out_dir, "essays_blind.csv"))
    elif args.fit:
        if not VERSION_CONFIG[args.version].get("aggregator_file"):
            raise SystemExit(f"--fit is for versions with a fitted aggregator; {args.version} has "
                             f"none. v3-v8 use hand-written rules and need no fitting step.")
        fit_v9(args.version, check_fidelity=not args.no_check_fidelity)
    elif args.derive:
        # Three derivation shapes so far: a pure aggregation change (v4, from one source CSV), a
        # trait-carry-through plus a second independent pass (v7/v8), and a fitted aggregator (v9).
        # Dispatch on the config rather than the version string so a later version gets the right
        # one by declaring what it has.
        if VERSION_CONFIG[args.version].get("aggregator_file"):
            derive_v9(args.version, check_fidelity=not args.no_check_fidelity)
        elif VERSION_CONFIG[args.version].get("triage_results_dir"):
            derive_v7(args.version, check_fidelity=not args.no_check_fidelity)
        else:
            derive_v4(args.version, check_fidelity=not args.no_check_fidelity)
    elif args.assemble:
        assemble(source_csv, args.version, annotate=not args.no_annotate)
    elif args.annotate_scores:
        annotate_scores(source_csv, args.version)
    elif args.strip_scores:
        strip_scores(args.version, out_dir=args.out_dir)
    else:
        parser.print_help()
