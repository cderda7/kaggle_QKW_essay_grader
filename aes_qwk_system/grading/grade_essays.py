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
  Each object in batch_results_v3/*.json leads with a human-readable comparison field:

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
               -> grading/batch_results_v3/*.json         -> predictions_v3.csv
  Same batches.json (essay_id split) is reused across versions so runs are directly comparable.

USAGE:
    python3 grade_essays.py --assemble --version v1
    python3 grade_essays.py --assemble --version v2
    python3 grade_essays.py --assemble --version v3   # also refreshes SCORES in batch_results_v3/
    python3 grade_essays.py --annotate-scores --version v3   # annotate only, no CSV rebuild
    python3 grade_essays.py --assemble --version v3 --no-annotate
    python3 grade_essays.py --strip-scores --version v3 --out-dir /tmp/blind_v3
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
        # v3+ only: inject the post-hoc "<human> vs. <system>" SCORES field into the batch JSONs.
        # Deliberately NOT enabled for v1/v2 -- those runs are frozen historical artifacts whose
        # results are already reported, and rewriting them would dirty the diff for no analytical
        # gain (decisions_log.md #41). Future versions opt in by setting this flag.
        "annotate_scores": True,
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
            value = f"{human_scores[eid]} vs. {item['holistic_score']}"
            batch_holistics[eid] = item["holistic_score"]
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

    # Leakage guard runs before anything here is trusted: if a grader emitted SCORES, the run was
    # not blind and there is no point assembling predictions from it. See module docstring.
    if cfg.get("annotate_scores"):
        check_no_foreign_scores(batch_results_dir, version)

    cap_violations = []
    gate_violations = []
    soft_gate_notes = []
    for fname in batch_filenames(batch_results_dir):
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

    if args.assemble:
        assemble(source_csv, args.version, annotate=not args.no_annotate)
    elif args.annotate_scores:
        annotate_scores(source_csv, args.version)
    elif args.strip_scores:
        strip_scores(args.version, out_dir=args.out_dir)
    else:
        parser.print_help()
