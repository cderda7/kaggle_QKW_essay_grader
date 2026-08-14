#!/usr/bin/env python3
"""
grade_essays.py — orchestration script for the AES QWK grading system (v1).

WHAT THIS SCRIPT DOES ON ITS OWN:
  - Loads personal_training_set.csv
  - Splits essay_ids into batches (default 10 per batch) matching batches.json
  - Assembles predictions_v1.csv from per-batch grading results (JSON files)
  - Validates schema (all essay_ids present, scores in [1,6], etc.)

WHAT IT DELIBERATELY DOES NOT DO (documented judgment call, see decisions_log.md #1):
  This sandbox does not expose a usable ANTHROPIC_API_KEY to shell scripts, so this script does
  NOT itself call an LLM API to grade essays. Instead, `score_essay_batch()` below is a stub that
  raises NotImplementedError with instructions for both of the two real ways to fill it in:

    (a) Point it at a real Claude API call (recommended for a fully headless, repeatable v2):
        pip install anthropic --break-system-packages
        client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        # send the prompt built from grading_prompt_template.md + rubric_v1.md, parse the
        # returned JSON array, and return it.

    (b) What v1 actually did: a human operator (Claude, running interactively via the Agent tool
        in a Cowork session) read each batch's essays and rubric and produced the JSON output
        by hand-reasoning through each essay, batch by batch, in parallel subagent calls. Those
        raw JSON outputs are saved in grading/batch_results/*.json — this script's job is just to
        assemble and validate them into predictions_v1.csv, which is what actually happened for
        this run.

USAGE:
    python3 grade_essays.py --assemble   # build predictions_v1.csv from grading/batch_results/*.json
"""

import argparse
import csv
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BATCH_RESULTS_DIR = os.path.join(HERE, "batch_results")
BATCHES_FILE = os.path.join(HERE, "batches.json")
PREDICTIONS_FILE = os.path.join(HERE, "predictions_v1.csv")

REQUIRED_FIELDS = [
    "essay_id", "evidence_notes", "organization", "development",
    "conventions", "holistic_score", "rationale",
]


def score_essay_batch(essay_ids, csv_path, rubric_text):
    """Stub — see module docstring. Not used by v1's assembly path."""
    raise NotImplementedError(
        "v1 did not call this function programmatically. Grading was performed by Claude via "
        "the Agent tool during an interactive session, with raw outputs saved to "
        "grading/batch_results/*.json. Wire this up to a real API call (see docstring) for a "
        "headless v2."
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


def assemble(source_csv_path):
    human_scores, word_counts = load_source_scores(source_csv_path)

    with open(BATCHES_FILE) as f:
        batches = json.load(f)
    expected_ids = [eid for batch in batches for eid in batch]

    results = {}
    if not os.path.isdir(BATCH_RESULTS_DIR):
        print(f"ERROR: {BATCH_RESULTS_DIR} does not exist yet.", file=sys.stderr)
        sys.exit(1)

    for fname in sorted(os.listdir(BATCH_RESULTS_DIR)):
        if not fname.endswith(".json"):
            continue
        with open(os.path.join(BATCH_RESULTS_DIR, fname)) as f:
            batch_results = json.load(f)
        for item in batch_results:
            missing = [k for k in REQUIRED_FIELDS if k not in item]
            if missing:
                raise ValueError(f"{fname}: item {item.get('essay_id')} missing fields {missing}")
            for score_field in ("organization", "development", "conventions", "holistic_score"):
                v = item[score_field]
                if not isinstance(v, int) or not (1 <= v <= 6):
                    raise ValueError(
                        f"{fname}: essay {item['essay_id']} field {score_field}={v} out of [1,6]"
                    )
            results[item["essay_id"]] = item

    missing_ids = set(expected_ids) - set(results.keys())
    extra_ids = set(results.keys()) - set(expected_ids)
    if missing_ids:
        raise ValueError(f"Missing grades for essay_ids: {sorted(missing_ids)}")
    if extra_ids:
        print(f"WARNING: graded essay_ids not in source set (ignored): {sorted(extra_ids)}",
              file=sys.stderr)

    with open(PREDICTIONS_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "essay_id", "human_score", "system_holistic_score", "system_organization",
            "system_development", "system_conventions", "word_count", "rationale",
        ])
        for eid in expected_ids:
            r = results[eid]
            writer.writerow([
                eid, human_scores[eid], r["holistic_score"], r["organization"],
                r["development"], r["conventions"], word_counts[eid], r["rationale"],
            ])

    print(f"Wrote {len(expected_ids)} rows to {PREDICTIONS_FILE}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--assemble", action="store_true",
                         help="Assemble predictions_v1.csv from grading/batch_results/*.json")
    parser.add_argument("--source-csv", default=None,
                         help="Path to personal_training_set.csv (defaults to sibling of this "
                              "script's parent dir, i.e. ../../personal_training_set.csv, which "
                              "matches the layout once this folder lives inside the project dir)")
    args = parser.parse_args()

    source_csv = args.source_csv or os.path.join(HERE, "..", "..", "personal_training_set.csv")
    source_csv = os.environ.get("PERSONAL_TRAINING_SET_CSV", source_csv)

    if args.assemble:
        assemble(source_csv)
    else:
        parser.print_help()
