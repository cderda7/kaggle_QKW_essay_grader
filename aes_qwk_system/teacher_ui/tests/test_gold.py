"""The answer key, and the ledger of every deliberate look at one.

These are the leakage control itself, so they are written against the property rather than the
implementation: the artifact must not carry the rater's score, and a reveal must be recorded before
the value can be obtained through the app at all.
"""

import datetime
import json
import os
import threading

import pytest

import gold
from conftest import SOURCE_CSV

pytestmark = pytest.mark.skipif(not os.path.exists(SOURCE_CSV),
                               reason="corpus CSV not available")


@pytest.fixture
def ledger(tmp_path, monkeypatch):
    """A ledger in a temp file. A test run must never append to the real audit record."""
    path = str(tmp_path / "gold_reveals.json")
    monkeypatch.setattr(gold, "REVEALS_FILE", path)
    return path


def test_an_untouched_ledger_is_empty_rather_than_missing(ledger):
    assert gold.load_reveals() == []
    assert gold.revealed_ids() == set()
    assert not os.path.exists(ledger), "reading the ledger must not create it"


def test_nothing_is_revealed_until_it_is_revealed(ledger):
    assert gold.was_revealed("0079938") is False


def test_a_reveal_is_written_to_disk_and_survives_a_restart(ledger):
    record, is_new = gold.record_reveal("0079938")
    assert is_new
    assert record["essay_id"] == "0079938"
    assert gold.was_revealed("0079938") is True

    reloaded = json.load(open(ledger))
    assert [r["essay_id"] for r in reloaded] == ["0079938"]


def test_a_reveal_records_which_run_it_was_made_against(ledger):
    """A correction made against v6_runB traits must not be silently reused against different
    ones -- the same reason the override record carries the pair."""
    record, _ = gold.record_reveal("0079938")
    assert record["ladder_version"] == "ui_v1"
    assert record["trait_run"] == "v6_runB"
    datetime.datetime.fromisoformat(record["revealed_at"])


def test_revealing_twice_keeps_the_first_timestamp(ledger):
    """The timestamp that matters is the one that bounds the corrections: from the first look
    onwards, every correction on this essay was formed with the answer key available."""
    first, is_new = gold.record_reveal("0079938")
    again, is_new_again = gold.record_reveal("0079938")
    assert is_new and not is_new_again
    assert again["revealed_at"] == first["revealed_at"]
    assert len(json.load(open(ledger))) == 1


def test_reveals_accumulate_per_essay(ledger):
    gold.record_reveal("0079938")
    gold.record_reveal("0105e2e")
    assert gold.revealed_ids() == {"0079938", "0105e2e"}
    assert gold.was_revealed("019e8c3") is False


def test_the_rater_score_is_read_from_the_corpus(ledger):
    score = gold.gold_score("0079938")
    assert isinstance(score, int) and 1 <= score <= 6


def test_an_essay_outside_the_corpus_says_so_rather_than_returning_nothing(ledger):
    with pytest.raises(gold.UnknownEssay) as exc:
        gold.gold_score("not-an-essay")
    assert "not-an-essay" in str(exc.value)


def test_the_build_never_reads_the_score_column():
    """The one guarantee everything else rests on: `load_essays` returns text, never scores."""
    from build_review import load_essays
    essays = load_essays()
    assert all(isinstance(v, str) for v in essays.values())


def test_concurrent_reveals_of_one_essay_record_it_once(ledger):
    """"One record per essay" is a read-modify-write, so it needs the same protection the
    override ledger needs (ui_19). Two reveals arriving together would otherwise both find no
    record and both append one, and the flag that says whether a correction was formed with the
    answer key in view would be answered from a ledger that disagrees with itself."""
    watchers = 6
    ready = threading.Barrier(watchers)
    results = []

    def reveal():
        ready.wait(timeout=10)
        results.append(gold.record_reveal("0079938")[1])

    threads = [threading.Thread(target=reveal) for _ in range(watchers)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)

    stored = json.load(open(ledger))
    assert [r["essay_id"] for r in stored] == ["0079938"]
    assert results.count(True) == 1
    assert results.count(False) == watchers - 1
