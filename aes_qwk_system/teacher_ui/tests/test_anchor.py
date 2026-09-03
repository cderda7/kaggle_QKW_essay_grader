"""Anchoring: does a quote the annotator wrote land on the text the student actually wrote?

Every test here asserts observable behaviour -- which characters get selected, or that a bad quote
fails with a message naming what to fix. None of them reach into how normalisation is implemented.
"""

import glob
import json
import os

import pytest

from anchor import AnchorError, anchor, resolve_spans
from conftest import ANNOTATION_DIR, SOURCE_CSV


# --- the ordinary case -------------------------------------------------------------------------

def test_exact_quote_selects_itself(essay):
    start, end = anchor(essay, "I don't like the idea of driveless cars.")
    assert essay[start:end] == "I don't like the idea of driveless cars."


def test_offsets_index_the_original_text_not_the_normalised_projection(essay):
    """The student typed three spaces in "full   speed"; a normally-spaced quote must still anchor,
    and the returned offsets must select the student's spacing, not a tidied copy of it."""
    start, end = anchor(essay, "right into a buliding at full speed")
    selected = essay[start:end]
    assert selected == "right into a buliding at full   speed"
    assert "   " in selected


def test_quote_rewrapped_with_newlines_and_doubled_spaces_anchors(essay):
    """Models re-wrap text they quote. That must not be the difference between anchoring and not."""
    messy = "Another con is that they  are\n   basically illlegal"
    start, end = anchor(essay, messy)
    assert essay[start:end] == "Another con is that they are basically illlegal"


def test_quote_spanning_a_paragraph_break_anchors(essay):
    start, end = anchor(essay, "drive by itself. Another con is that they are")
    assert essay[start:end].startswith("drive by itself.")
    assert "\n\n" in essay[start:end]


# --- occurrence selection ----------------------------------------------------------------------

def test_occurrence_defaults_to_the_first_match(essay):
    start, end = anchor(essay, "Another con is that")
    assert essay[end:end + 6] == " they "
    assert essay[start:].startswith("Another con is that they can't")


def test_occurrence_two_selects_the_second_match(essay):
    start, _ = anchor(essay, "Another con is that", 2)
    assert essay[start:].startswith("Another con is that they are basically")


def test_occurrence_beyond_the_number_of_matches_fails_and_reports_the_count(essay):
    with pytest.raises(AnchorError) as exc:
        anchor(essay, "Another con is that", 3, essay_id="E1")
    message = str(exc.value)
    assert "occurrence 3" in message
    assert "2 time(s)" in message
    assert "E1" in message


@pytest.mark.parametrize("occurrence", [0, -1])
def test_occurrence_below_one_fails(essay, occurrence):
    with pytest.raises(AnchorError):
        anchor(essay, "Another con is that", occurrence)


# --- the failures that matter ------------------------------------------------------------------

def test_a_silently_corrected_typo_does_not_anchor(essay):
    """The realistic failure mode. The student wrote "buliding"; an annotator that tidies it to
    "building" must fail, not land a highlight on text it never actually cited."""
    with pytest.raises(AnchorError) as exc:
        anchor(essay, "drive right into a building at full speed", essay_id="E1",
               criterion="development[2]")
    assert "not found" in str(exc.value)


def test_a_missing_quote_names_the_essay_the_criterion_and_the_quote(essay):
    with pytest.raises(AnchorError) as exc:
        anchor(essay, "a phrase the student never wrote", essay_id="0079938",
               criterion="argumentation[0]")
    message = str(exc.value)
    assert "0079938" in message
    assert "argumentation[0]" in message
    assert "a phrase the student never wrote" in message


def test_case_differences_are_not_folded(essay):
    """Deliberate strictness: the instrument forbids editing the student's text inside a quote, so
    silently accepting a re-cased quote would defeat the check the guard exists to make."""
    with pytest.raises(AnchorError):
        anchor(essay, "another con is that")


def test_empty_quote_fails(essay):
    with pytest.raises(AnchorError):
        anchor(essay, "   \n  ")


# --- typographic folding -----------------------------------------------------------------------

def test_curly_apostrophe_matches_the_straight_one_the_student_typed(essay):
    start, end = anchor(essay, "they can’t drive by itself")
    assert essay[start:end] == "they can't drive by itself"


def test_curly_double_quotes_and_dashes_fold():
    source = 'She wrote "no" - and meant it.'
    start, end = anchor(source, '“no” — and meant it')
    assert source[start:end] == '"no" - and meant it'


# --- resolve_spans -----------------------------------------------------------------------------

def test_resolve_spans_returns_criterion_polarity_and_the_text_it_selected(essay, spans_for):
    criteria = spans_for("conventions", "basically illlegal in most states", polarity="weakness")
    resolved = resolve_spans(essay, criteria, essay_id="E1")
    assert len(resolved) == 1
    span = resolved[0]
    assert span["criterion"] == "conventions"
    assert span["polarity"] == "weakness"
    assert span["resolved_text"] == essay[span["start"]:span["end"]]
    assert span["resolved_text"] == "basically illlegal in most states"


def test_resolve_spans_orders_by_position_in_the_response(essay, spans_for):
    criteria = spans_for(
        "organization",
        "Or they will drive right into",
        "I don't like the idea",
        "Another con is that they are",
    )
    resolved = resolve_spans(essay, criteria)
    assert [s["start"] for s in resolved] == sorted(s["start"] for s in resolved)
    assert resolved[0]["quote"] == "I don't like the idea"


def test_resolve_spans_reports_every_bad_quote_at_once(essay, spans_for):
    criteria = spans_for(
        "argumentation",
        "text that is not in the response",
        "another absent phrase entirely",
        "I don't like the idea",
    )
    with pytest.raises(AnchorError) as exc:
        resolve_spans(essay, criteria, essay_id="E1")
    message = str(exc.value)
    assert "2 span(s) could not be anchored" in message
    assert "text that is not in the response" in message
    assert "another absent phrase entirely" in message


def test_resolve_spans_accepts_a_criterion_with_no_spans(essay):
    """The no-evidence path (decision ui_8): an absence is a finding, not an anchoring failure.
    Whether the reason is *present* is a build guard, not anchoring's job."""
    criteria = {
        "argumentation": {
            "comment": "The response never states a position.",
            "spans": [],
            "no_evidence_reason": "There is no claim in the response to point at.",
        }
    }
    assert resolve_spans(essay, criteria, essay_id="E1") == []


# --- integration: the real annotated essay -----------------------------------------------------

def _real_batches():
    if not os.path.exists(SOURCE_CSV):
        return []
    return sorted(glob.glob(os.path.join(ANNOTATION_DIR, "batch_*.json")))


@pytest.mark.skipif(not _real_batches(),
                    reason="corpus CSV or annotation batches not available")
def test_every_span_in_the_real_annotation_batches_anchors_exactly():
    """The check that ticket 01 ran by hand, persisted: every quote in every annotated essay must
    anchor, and the text the offsets select must be identical to what the annotator wrote."""
    from check_anchors import load_essays

    essays = load_essays(SOURCE_CSV)
    checked = 0
    for path in _real_batches():
        with open(path) as f:
            items = json.load(f)
        for item in items:
            eid = item["essay_id"]
            assert eid in essays, "%s is annotated but not in the source corpus" % eid
            for span in resolve_spans(essays[eid], item["criteria"], essay_id=eid):
                assert span["resolved_text"] == span["quote"], (
                    "%s %s: offsets select %r but the annotator wrote %r"
                    % (eid, span["criterion"], span["resolved_text"], span["quote"])
                )
                checked += 1
    assert checked > 0, "no spans were checked -- the annotation batches look empty"
