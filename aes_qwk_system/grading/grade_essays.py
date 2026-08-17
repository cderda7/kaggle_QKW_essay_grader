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
    parser.add_argument("--out-dir", default=None,
                         help="With --strip-scores, write blind copies here instead of stripping "
                              "the originals in place")
    parser.add_argument("--version", default="v1", choices=sorted(VERSION_CONFIG.keys()),
                         help="Which rubric version's batch results to assemble")
    parser.add_argument("--source-csv", default=None,
                         help="Path to personal_training_set.csv (defaults to sibling of this "
                              "script's parent dir, i.e. ../../personal_training_set.csv, which "
                              "matches the layout once this folder lives inside the project dir)")
    args = parser.parse_args()

    source_csv = args.source_csv or os.path.join(HERE, "..", "..", "personal_training_set.csv")
    source_csv = os.environ.get("PERSONAL_TRAINING_SET_CSV", source_csv)

    if args.derive:
        derive_v4(args.version, check_fidelity=not args.no_check_fidelity)
    elif args.assemble:
        assemble(source_csv, args.version, annotate=not args.no_annotate)
    elif args.annotate_scores:
        annotate_scores(source_csv, args.version)
    elif args.strip_scores:
        strip_scores(args.version, out_dir=args.out_dir)
    else:
        parser.print_help()
