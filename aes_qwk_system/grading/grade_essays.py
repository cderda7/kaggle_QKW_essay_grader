#!/usr/bin/env python3
"""
grade_essays.py — orchestration script for the AES QWK grading system.

WHAT THIS SCRIPT DOES ON ITS OWN:
  - Loads personal_training_set.csv
  - Assembles predictions_<version>.csv from per-batch grading results (JSON files) matching
    grading/batches.json (the batch/essay_id split is shared across rubric versions)
  - Validates schema (all essay_ids present, scores in [1,6], version-specific rules honored)

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
               -> grading/batch_results_v3/*.json         -> predictions_v3.csv
  Same batches.json (essay_id split) is reused across versions so runs are directly comparable.

USAGE:
    python3 grade_essays.py --assemble --version v1
    python3 grade_essays.py --assemble --version v2
    python3 grade_essays.py --assemble --version v3
"""

import argparse
import csv
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BATCHES_FILE = os.path.join(HERE, "batches.json")

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
        "batch_results_dir": os.path.join(HERE, "batch_results_v3"),
        "predictions_file": os.path.join(HERE, "predictions_v3.csv"),
        "sub_score_fields": ["organization", "development", "conventions", "argumentation"],
        "cap_rule": None,  # superseded by validate_v3_gate() below
        "gate_rule": "v3_severe_weakness",
        # (json field, csv column header) pairs written straight through to the predictions CSV,
        # beyond the standard essay_id/human_score/holistic/sub-scores/word_count/rationale columns
        "extra_fields": [("gate_applied", "system_gate_applied")],
    },
}


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


def score_essay_batch(essay_ids, csv_path, rubric_text):
    """Stub — see module docstring. Not used by any version's assembly path so far."""
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


def assemble(source_csv_path, version):
    cfg = VERSION_CONFIG[version]
    sub_score_fields = cfg["sub_score_fields"]
    extra_fields = cfg.get("extra_fields", [])
    gate_rule = cfg.get("gate_rule")
    required_fields = ["essay_id", "evidence_notes", *sub_score_fields, "holistic_score", "rationale"]
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

    cap_violations = []
    gate_violations = []
    soft_gate_notes = []
    for fname in sorted(os.listdir(batch_results_dir)):
        if not fname.endswith(".json"):
            continue
        with open(os.path.join(batch_results_dir, fname)) as f:
            batch_results = json.load(f)
        for item in batch_results:
            missing = [k for k in required_fields if k not in item]
            if missing:
                raise ValueError(f"{fname}: item {item.get('essay_id')} missing fields {missing}")
            for score_field in (*sub_score_fields, "holistic_score"):
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
    return {"cap_violations": cap_violations, "gate_violations": gate_violations,
            "soft_gate_notes": soft_gate_notes}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--assemble", action="store_true",
                         help="Assemble predictions_<version>.csv from grading/batch_results*/*.json")
    parser.add_argument("--version", default="v1", choices=sorted(VERSION_CONFIG.keys()),
                         help="Which rubric version's batch results to assemble")
    parser.add_argument("--source-csv", default=None,
                         help="Path to personal_training_set.csv (defaults to sibling of this "
                              "script's parent dir, i.e. ../../personal_training_set.csv, which "
                              "matches the layout once this folder lives inside the project dir)")
    args = parser.parse_args()

    source_csv = args.source_csv or os.path.join(HERE, "..", "..", "personal_training_set.csv")
    source_csv = os.environ.get("PERSONAL_TRAINING_SET_CSV", source_csv)

    if args.assemble:
        assemble(source_csv, args.version)
    else:
        parser.print_help()
