"""Re-locate every annotator quote in its source essay and report what the offsets actually select.

This is the ticket-01 proof: it answers whether a model asked to quote student writing verbatim
reproduces it faithfully enough to anchor, before anything is built on top of the assumption. Run it
after every annotation batch.

    python3 check_anchors.py [--batch-dir DIR] [--source-csv PATH] [--verbose]

Exits non-zero if any span fails to anchor, naming the essay and the quote.
"""

import argparse
import csv
import glob
import json
import os
import sys

from anchor import AnchorError, resolve_spans

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_BATCH_DIR = os.path.join(HERE, "annotation_v6_runB")
DEFAULT_SOURCE_CSV = os.path.join(HERE, "..", "..", "personal_training_set.csv")


def load_essays(source_csv):
    with open(source_csv, newline="", encoding="utf-8") as f:
        return {r["essay_id"]: r["full_text"] for r in csv.DictReader(f)}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--batch-dir", default=DEFAULT_BATCH_DIR)
    ap.add_argument("--source-csv", default=os.environ.get("PERSONAL_TRAINING_SET_CSV",
                                                           DEFAULT_SOURCE_CSV))
    ap.add_argument("--verbose", action="store_true",
                    help="print every span, not only the ones whose resolved text differs")
    args = ap.parse_args(argv)

    essays = load_essays(args.source_csv)
    paths = sorted(glob.glob(os.path.join(args.batch_dir, "batch_*.json")))
    if not paths:
        print(f"no batch files in {args.batch_dir}", file=sys.stderr)
        return 2

    total = exact = 0
    failures = []

    for path in paths:
        with open(path) as f:
            items = json.load(f)
        for item in items:
            eid = item["essay_id"]
            if eid not in essays:
                failures.append(f"{eid}: not present in {os.path.basename(args.source_csv)}")
                continue
            text = essays[eid]
            try:
                spans = resolve_spans(text, item["criteria"], essay_id=eid)
            except AnchorError as exc:
                failures.append(str(exc))
                continue

            print(f"\n=== {eid} — {len(spans)} span(s) ===")
            for s in spans:
                total += 1
                ok = s["resolved_text"] == s["quote"]
                exact += ok
                mark = "ok  " if ok else "DIFF"
                if ok and not args.verbose:
                    print(f"  {mark} [{s['start']:>4}:{s['end']:>4}] {s['criterion']:<13} "
                          f"{s['polarity']:<8} {s['quote'][:58]!r}")
                else:
                    print(f"  {mark} [{s['start']:>4}:{s['end']:>4}] {s['criterion']:<13} "
                          f"{s['polarity']}")
                    print(f"       annotator wrote: {s['quote']!r}")
                    print(f"       offsets select : {s['resolved_text']!r}")

            for name, crit in item["criteria"].items():
                if not (crit.get("spans") or []):
                    reason = crit.get("no_evidence_reason")
                    tag = "no-evidence" if reason else "EMPTY, NO REASON"
                    print(f"  ---- {name:<13} {tag}: {reason or '(missing)'}")

    print("\n" + "-" * 60)
    print(f"{total} span(s) anchored; {exact} selected text identical to the quote as written")
    if total:
        print(f"first-pass anchor rate: {exact}/{total} = {100 * exact / total:.0f}%")
    if failures:
        print(f"\n{len(failures)} FAILURE(S):", file=sys.stderr)
        for f_ in failures:
            print(f"  {f_}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
