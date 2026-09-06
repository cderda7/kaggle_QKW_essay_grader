"""The human rater's score, and the ledger of every deliberate look at one.

The reviewable essays come from `personal_training_set.csv`, which carries the rater's score in a
`score` column beside the text. `build_review` never reads that column and this module is the only
thing that does -- so the review artifact, and therefore every page and every API response built
from it, cannot leak the answer key by accident (teacher_ui/decisions_log.md ui_4).

Revealing is recorded because overrides are meant to feed a few-shot bank later, and a correction
formed while looking at the answer key would launder gold labels into the grading prompt through a
door that neither the SCORES annotation manifest nor --strip-scores watches. Ticket 05 stamps its
records from `was_revealed()`.

This is a flag, not a lock. The CSV is on disk and reading it directly is neither prevented nor
recorded, and the reveal control says so -- a control that overstates its own reach teaches the
reviewer to trust a boundary that is not there.
"""

import csv
import datetime
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import ledger  # noqa: E402
from build_review import LADDER_VERSION, TRAIT_RUN  # noqa: E402

# Overridable for the same reason the corpus path is: an end-to-end pass has to be able to click
# the reveal without writing a row into the committed audit record.
REVEALS_FILE = os.environ.get("GOLD_REVEALS_FILE", os.path.join(HERE, "gold_reveals.json"))
SOURCE_CSV = os.environ.get("PERSONAL_TRAINING_SET_CSV",
                            os.path.join(HERE, "..", "..", "personal_training_set.csv"))


class UnknownEssay(KeyError):
    """Asked for the gold score of an essay the corpus does not contain."""


def gold_score(essay_id, source_csv=None):
    """The human rater's score for one essay. Read on demand; never cached into the artifact."""
    source_csv = SOURCE_CSV if source_csv is None else source_csv
    with open(source_csv, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["essay_id"] == essay_id:
                return int(row["score"])
    raise UnknownEssay("no essay %s in %s" % (essay_id, os.path.basename(source_csv)))


def load_reveals(path=None):
    """The reveal ledger. A missing file means no answer key has been looked at yet.

    Paths resolve at call time, not at import time, so a test can point the ledger at a temp file
    without the real one being written to -- an audit record that a test run can append to is not
    an audit record.
    """
    path = REVEALS_FILE if path is None else path
    if not os.path.exists(path):
        return []
    with open(path) as f:
        return json.load(f)


def revealed_ids(records=None, path=None):
    records = load_reveals(path) if records is None else records
    return {r["essay_id"] for r in records}


def was_revealed(essay_id, records=None, path=None):
    """Whether this essay's gold score was revealed -- the flag ticket 05 stamps records with."""
    return essay_id in revealed_ids(records, path)


def record_reveal(essay_id, path=None, ladder_version=None, trait_run=None, now=None):
    """Record that the answer key for `essay_id` was looked at. Returns (record, is_new).

    One record per essay rather than one per click: after the first reveal the score renders with
    the page, so a second look takes no action to record. What the ledger has to answer is "was
    this correction formed with the answer key in view", and that is a property of the essay from
    the first reveal onwards. Re-revealing returns the original record and its original timestamp,
    which is the one that bounds the corrections.

    "One record per essay" is a read-modify-write, so the check and the write are held under the
    ledger's lock together: two reveals of the same essay arriving at once would otherwise both
    find no record and both append one. `ledger.write_json` also makes the swap atomic, where
    truncating the real file first put every reveal already recorded inside the failure window
    rather than only the one being added. See decisions_log.md ui_19.
    """
    path = REVEALS_FILE if path is None else path
    with ledger.lock(path):
        records = load_reveals(path)
        for existing in records:
            if existing["essay_id"] == essay_id:
                return existing, False

        stamp = now if now is not None else datetime.datetime.now().astimezone()
        record = {
            "essay_id": essay_id,
            "revealed_at": stamp.isoformat(timespec="seconds"),
            "ladder_version": ladder_version if ladder_version is not None else LADDER_VERSION,
            "trait_run": trait_run if trait_run is not None else TRAIT_RUN,
        }
        records.append(record)
        ledger.write_json(path, records)
    return record, True
