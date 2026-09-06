"""Writing a correction down, and what the record has to carry.

The ledger under test is always a temp file. A test run that appends to the committed audit record
would corrupt the evidence the ladder is judged on.
"""

import json
import os

import pytest

import build_review
import overrides
from conftest import SOURCE_CSV

pytestmark = pytest.mark.skipif(not os.path.exists(SOURCE_CSV),
                                reason="corpus CSV not available")

ESSAYS = ["0079938", "0105e2e", "019e8c3"]


@pytest.fixture
def ledger(tmp_path, monkeypatch):
    """Redirecting the one name that owns the ledger path moves every reader and every writer.
    Having to patch a second copy would mean the app could read one file and append to another."""
    path = str(tmp_path / "overrides.json")
    monkeypatch.setattr(build_review, "OVERRIDES_FILE", path)
    return path


def correct(essay_id=ESSAYS[0], **kwargs):
    kwargs.setdefault("expected_ids", ESSAYS)
    return overrides.record_correction(essay_id, **kwargs)


def test_a_correction_recomputes_the_holistic_through_the_frozen_aggregator(ledger):
    record, essay = correct(corrected_traits={c: 6 for c in build_review.CRITERIA})
    assert essay["traits"] == {c: 6 for c in build_review.CRITERIA}
    assert essay["holistic"] > essay["ai_holistic"]
    assert record["recomputed_holistic"] == essay["holistic"]
    assert record["original_holistic"] == essay["ai_holistic"]


def test_the_recorded_holistic_is_the_one_the_build_produces(ledger):
    """Not a number this module worked out: the record is the build's own output, so there is no
    second implementation of the aggregator to drift from the first."""
    record, essay = correct(corrected_traits={"argumentation": 6})
    rebuilt = build_review.build_review(override_records=json.load(open(ledger)),
                                        expected_ids=ESSAYS)
    holistic = next(e["holistic"] for e in rebuilt["essays"] if e["essay_id"] == ESSAYS[0])
    assert record["recomputed_holistic"] == holistic


def test_a_correction_that_does_not_move_the_band_is_recorded_as_such(ledger):
    """The measured common case (ui_9/D2): one trait, one point, no visible effect."""
    record, essay = correct(corrected_traits={"conventions": 6})
    if record["recomputed_holistic"] == record["original_holistic"]:
        assert record["score_unchanged"] is True
        assert essay["score_unchanged_by_override"] is True


def test_the_record_carries_what_it_was_made_against(ledger):
    record, _ = correct(corrected_traits={"conventions": 5}, rationale="spelling is not the issue")
    for key in ("essay_id", "kind", "recorded_at", "original_traits", "corrected_traits",
                "original_holistic", "recomputed_holistic", "rationale", "gold_revealed",
                "ladder_version", "trait_run", "aggregator"):
        assert key in record, key
    assert record["trait_run"] == "v6_runB"
    assert record["aggregator"] == "aggregator_v9.json"
    assert record["rationale"] == "spelling is not the issue"


def test_a_rationale_is_optional_on_a_correction(ledger):
    record, _ = correct(corrected_traits={"conventions": 5})
    assert record["rationale"] is None


def test_a_correction_made_after_a_reveal_carries_the_flag(ledger):
    """The leakage control ticket 04 built, now stamped where it was always meant to land."""
    plain, _ = correct(corrected_traits={"conventions": 5})
    anchored, _ = correct(corrected_traits={"conventions": 4}, gold_revealed=True)
    assert plain["gold_revealed"] is False
    assert anchored["gold_revealed"] is True


def test_records_are_appended_and_the_latest_is_current(ledger):
    correct(corrected_traits={"conventions": 5}, rationale="first")
    _, essay = correct(corrected_traits={"conventions": 2}, rationale="second")
    stored = json.load(open(ledger))
    assert len(stored) == 2
    assert [r["rationale"] for r in stored] == ["first", "second"]
    assert essay["traits"]["conventions"] == 2


def test_an_earlier_record_is_never_mutated(ledger):
    correct(corrected_traits={"conventions": 5}, rationale="first")
    before = json.load(open(ledger))[0]
    correct(corrected_traits={"conventions": 1}, rationale="second")
    assert json.load(open(ledger))[0] == before


def test_a_correction_survives_a_restart(ledger):
    """Nothing is held in memory: the next build reads the same file from disk."""
    _, essay = correct(corrected_traits={"argumentation": 6})
    fresh = build_review.build_review(override_records=build_review.load_overrides(ledger),
                                      expected_ids=ESSAYS)
    after = next(e for e in fresh["essays"] if e["essay_id"] == ESSAYS[0])
    assert after["traits"]["argumentation"] == 6
    assert after["overridden"] is True


def test_clearing_restores_the_ai_scores_and_keeps_the_history(ledger):
    correct(corrected_traits={"argumentation": 6})
    record, essay = correct(kind="cleared", rationale="on reflection the AI had it right")
    assert essay["traits"] == essay["ai_traits"]
    assert essay["overridden"] is False
    assert essay["reviewed"] is True
    assert len(json.load(open(ledger))) == 2
    assert record["recomputed_holistic"] == essay["ai_holistic"]


def test_a_dissent_records_a_reason_and_no_number(ledger):
    record, essay = correct(kind="dissent", rationale="four traits at 4 cannot be a 2")
    assert "corrected_traits" not in record
    assert record["rationale"] == "four traits at 4 cannot be a 2"
    assert essay["traits"] == essay["ai_traits"]
    assert essay["holistic"] == essay["ai_holistic"]
    assert essay["dissent"]["rationale"] == "four traits at 4 cannot be a 2"


def test_a_dissent_after_a_correction_does_not_claim_the_correction_s_movement(ledger):
    """The ledger is read by hand, so each record has to describe its own effect. A dissent moves
    no number; stamping it against the AI baseline would make it read as the cause of the earlier
    correction's move."""
    _, corrected = correct(corrected_traits={c: 6 for c in build_review.CRITERIA})
    assert corrected["holistic"] != corrected["ai_holistic"]
    record, essay = correct(kind="dissent", rationale="the number is still wrong")
    assert record["original_holistic"] == corrected["holistic"]
    assert record["recomputed_holistic"] == corrected["holistic"]
    assert record["score_unchanged"] is True
    assert record["ai_holistic"] == essay["ai_holistic"]


def test_clearing_records_the_move_back_that_it_caused(ledger):
    """Withdrawing a correction that had moved the score moves it back, and the record says so."""
    _, corrected = correct(corrected_traits={c: 6 for c in build_review.CRITERIA})
    record, essay = correct(kind="cleared", rationale="on reflection the AI had it right")
    assert record["original_holistic"] == corrected["holistic"]
    assert record["recomputed_holistic"] == essay["ai_holistic"]
    assert record["score_unchanged"] is False


def test_a_write_that_fails_partway_leaves_the_ledger_as_it_was(ledger, monkeypatch):
    """The whole list is rewritten on every append, so a half-finished write must not be able to
    take the append-only record with it."""
    correct(corrected_traits={"conventions": 5}, rationale="first")
    before = json.load(open(ledger))

    def explode(*args, **kwargs):
        raise IOError("no space left on device")

    monkeypatch.setattr(overrides.json, "dump", explode)
    with pytest.raises(IOError):
        correct(corrected_traits={"conventions": 2}, rationale="second")
    assert json.load(open(ledger)) == before
    assert not os.path.exists(ledger + ".pending")


def test_a_malformed_trait_score_names_itself_instead_of_raising(ledger):
    """The values arrive from an HTTP body, so they are checked before anything coerces them --
    otherwise int("six") raises past the guard and the caller sees an unexplained crash."""
    for traits, expected in ((({"argumentation": "six"}), "not a whole number"),
                             (([6]), "expected an object"),
                             (({"argumentation": 11}), "outside the 1-6 scale")):
        with pytest.raises(build_review.OverrideError) as exc:
            correct(corrected_traits=traits)
        assert expected in str(exc.value)
    with pytest.raises(build_review.OverrideError) as exc:
        correct(corrected_traits={"conventions": 5}, rationale=5)
    assert "expected text" in str(exc.value)
    assert not os.path.exists(ledger)


def test_a_dissent_is_distinct_from_a_trait_correction(ledger):
    correct(corrected_traits={"conventions": 5}, rationale="conventions are fine")
    _, essay = correct(kind="dissent", rationale="and the final number is still wrong")
    assert essay["traits"]["conventions"] == 5
    assert essay["dissent"]["rationale"] == "and the final number is still wrong"
    kinds = [r["kind"] for r in json.load(open(ledger))]
    assert kinds == ["trait_correction", "dissent"]


def test_a_refused_record_is_not_written(ledger):
    """A guard that rejects after writing would leave the ledger in the state it refused."""
    with pytest.raises(build_review.OverrideError):
        correct(corrected_traits={"argumentation": 11})
    assert not os.path.exists(ledger)


def test_a_refused_record_does_not_disturb_the_ones_already_there(ledger):
    correct(corrected_traits={"conventions": 5})
    before = json.load(open(ledger))
    with pytest.raises(build_review.OverrideError):
        correct(kind="dissent", rationale="")
    assert json.load(open(ledger)) == before
