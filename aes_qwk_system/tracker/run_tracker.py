#!/usr/bin/env python3
"""
run_tracker.py — the "agent" that turns your git commits into tracker_log.json, the data source
for the Google Doc commit tracker.

WHAT THIS SCRIPT DOES:
  Reads `git log` in the repo it's run from, finds "iteration commits" (see format below), and for
  each one looks up the real QWK / agreement rates from the matching evaluation/results_vN.json
  file already in your working tree. Writes/updates tracker_log.json with one entry per iteration
  commit, in chronological order, including auto-computed notes on how the metrics moved since the
  previous iteration.

WHAT IT DELIBERATELY DOES NOT DO:
  - Does not call the GitHub API (there's no reachable GitHub connector in the Cowork cloud
    sandbox this was built in — see decisions_log.md). It reads your LOCAL git history instead,
    which is exactly what's on GitHub as long as you've pushed. Run this from a normal clone.
  - Does not touch Google Drive/Docs at all — that's a separate step (only Claude, via the Google
    Drive MCP tools, can do that upload; a stdlib script can't call MCP tools). This script's only
    job is producing tracker_log.json.
  - Does not commit tracker_log.json to git for you. Review it and commit it yourself (or ask
    Claude to), same as every other file in this repo.
  - Does not touch the `concerns` column at all — that's yours to fill in by hand in the Doc.

COMMIT MESSAGE FORMAT THIS SCRIPT UNDERSTANDS:
    <label> ; QWK: <value or "unknown"> ; Delta: <text> ; rationale: <text>
  Segments are separated by " ; ". Not all of QWK/Delta/rationale need be present — whatever's
  there gets parsed; the label is always the text before the first " ; ". Commits with NO "QWK:"
  segment at all are not iteration commits and are skipped entirely (not given a row).

VERSION-MAPPING CONVENTION (a judgment call — see decisions_log.md):
  The Nth iteration commit (1-indexed, in chronological order, counting only commits that DO have
  a "QWK:" segment) is assumed to correspond to evaluation/results_v<N>.json in the CURRENT
  working tree — not a historical git-blob lookup. This is simple and matches this project's actual
  history (commit 1 -> results_v1.json, commit 2 -> results_v2.json), but it does mean: don't skip
  a version number, and don't reorder iteration commits relative to when their results_vN.json was
  produced, or the mapping will be wrong. If that ever stops holding, this script's `--map` option
  lets you override the mapping explicitly (see --help).

USAGE:
    cd /path/to/your/repo
    python3 aes_qwk_system/tracker/run_tracker.py
    # or, to point at a different repo/log location:
    python3 run_tracker.py --repo /path/to/repo --log /path/to/tracker_log.json
"""

import argparse
import json
import os
import re
import subprocess
import sys

RECORD_SEP = "\x1e"
FIELD_SEP = "\x1f"

SEGMENT_PATTERN = re.compile(r"^\s*(QWK|Delta|rationale)\s*:\s*(.*)$", re.IGNORECASE)


def run_git(repo, *args):
    result = subprocess.run(
        ["git", "-C", repo, *args],
        capture_output=True, text=True, check=True,
    )
    return result.stdout


def get_commits_oldest_first(repo):
    """Returns list of (sha, full_message) oldest to newest."""
    log = run_git(
        repo, "log", "--reverse",
        f"--pretty=format:%H{FIELD_SEP}%B{RECORD_SEP}",
    )
    commits = []
    for record in log.split(RECORD_SEP):
        record = record.strip("\n")
        if not record.strip():
            continue
        sha, _, message = record.partition(FIELD_SEP)
        commits.append((sha.strip(), message.strip()))
    return commits


def parse_iteration_commit(message):
    """Returns dict with label/qwk_raw/delta/rationale, or None if not an iteration commit."""
    segments = [s.strip() for s in message.split(";")]
    if not segments:
        return None
    label = segments[0].strip()
    fields = {}
    for seg in segments[1:]:
        m = SEGMENT_PATTERN.match(seg)
        if m:
            key = m.group(1).lower()
            fields[key] = m.group(2).strip()
    if "qwk" not in fields:
        return None
    return {
        "label": label,
        "qwk_raw": fields.get("qwk", ""),
        "delta": fields.get("delta", ""),
        "rationale": fields.get("rationale", ""),
    }


def load_results(repo, version):
    path = os.path.join(repo, "aes_qwk_system", "evaluation", f"results_v{version}.json")
    if not os.path.isfile(path):
        return None
    with open(path) as f:
        return json.load(f)


def pct(x):
    return f"{x:.0%}"


def build_qwk_notes(prev_results, curr_results):
    if prev_results is None or curr_results is None:
        return None
    lines = []
    if "exact_agreement_rate" in prev_results and "exact_agreement_rate" in curr_results:
        lines.append(
            f"exact agreement from {pct(prev_results['exact_agreement_rate'])} → "
            f"{pct(curr_results['exact_agreement_rate'])}"
        )
    if "adjacent_agreement_rate_within_1" in prev_results and "adjacent_agreement_rate_within_1" in curr_results:
        lines.append(
            f"adjacent agreement from {pct(prev_results['adjacent_agreement_rate_within_1'])} → "
            f"{pct(curr_results['adjacent_agreement_rate_within_1'])}"
        )
    return lines or None


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repo", default=".", help="Path to the git repo (default: cwd)")
    parser.add_argument("--log", default=None,
                         help="Path to tracker_log.json (default: <repo>/aes_qwk_system/tracker_log.json)")
    args = parser.parse_args()

    repo = os.path.abspath(args.repo)
    log_path = args.log or os.path.join(repo, "aes_qwk_system", "tracker_log.json")

    existing = []
    processed_shas = set()
    if os.path.isfile(log_path):
        with open(log_path) as f:
            existing = json.load(f)
        processed_shas = {e["commit_sha"] for e in existing}

    commits = get_commits_oldest_first(repo)

    # Determine the iteration index (for version mapping) by scanning ALL iteration commits in
    # order, not just new ones, so re-runs assign the same version number to the same commit.
    iteration_index = 0
    new_entries = []
    prev_results_for_notes = None
    # seed prev_results_for_notes from the last existing entry's own results, so a fresh run
    # picks up notes correctly relative to what's already logged
    if existing:
        last_version = len(existing)
        prev_results_for_notes = load_results(repo, last_version)

    for sha, message in commits:
        parsed = parse_iteration_commit(message)
        if parsed is None:
            continue
        iteration_index += 1
        if sha in processed_shas:
            continue  # already logged in a prior run

        version = iteration_index
        results = load_results(repo, version)
        qwk_value = results["qwk"] if results else _try_parse_float(parsed["qwk_raw"])

        entry = {
            "commit_sha": sha,
            "iteration_index": iteration_index,
            "label": parsed["label"],
            "qwk": qwk_value,
            "qwk_source": f"evaluation/results_v{version}.json" if results else "commit message (no results file found)",
            "qwk_notes": build_qwk_notes(prev_results_for_notes, results),
            "delta": parsed["delta"],
            "rationale": parsed["rationale"],
            "concerns": "",
        }
        new_entries.append(entry)
        if results:
            prev_results_for_notes = results

    all_entries = existing + new_entries
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    with open(log_path, "w") as f:
        json.dump(all_entries, f, indent=2)

    if new_entries:
        print(f"Added {len(new_entries)} new iteration(s) to {log_path}:")
        for e in new_entries:
            print(f"  [{e['iteration_index']}] {e['label']!r} — QWK={e['qwk']} (from {e['qwk_source']})")
    else:
        print(f"No new iteration commits found. {log_path} unchanged ({len(existing)} entries).")


def _try_parse_float(s):
    try:
        return float(s)
    except (TypeError, ValueError):
        return None


if __name__ == "__main__":
    main()
