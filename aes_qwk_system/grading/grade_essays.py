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
  Same batches.json (essay_id split) is reused across versions so runs are directly comparable.

USAGE:
    python3 grade_essays.py --assemble --version v1
    python3 grade_essays.py --assemble --version v2
"""

import argparse
import csv
import json
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
    },
    "v2": {
        "batch_results_dir": os.path.join(HERE, "batch_results_v2"),
        "predictions_file": os.path.join(HERE, "predictions_v2.csv"),
        "sub_score_fields": ["organization", "development", "conventions", "argumentation"],
        # (field, value) that caps holistic_score at cap_value
        "cap_rule": {"field": "argumentation", "trigger_value": 1, "cap_value": 3},
    },
}


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
    required_fields = ["essay_id", "evidence_notes", *sub_score_fields, "holistic_score", "rationale"]

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
            results[item["essay_id"]] = item

    if cap_violations:
        print(f"WARNING: {len(cap_violations)} cap-rule violations (grader didn't apply the rule "
              f"correctly): {cap_violations}", file=sys.stderr)

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
            "word_count", "rationale",
        ])
        for eid in expected_ids:
            r = results[eid]
            writer.writerow([
                eid, human_scores[eid], r["holistic_score"],
                *[r[field] for field in sub_score_fields],
                word_counts[eid], r["rationale"],
            ])

    print(f"Wrote {len(expected_ids)} rows to {predictions_file}")


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
