"""Rendering a response with its spans, including the overlap cases the design permits."""

import re

from render import all_spans, paragraph_ranges, primary, response_html, segment

TEXT = "Alpha beta gamma.\n\nDelta epsilon zeta.\n\nEta theta."


def span(start, end, criterion="argumentation", polarity="strength"):
    return {"start": start, "end": end, "criterion": criterion, "polarity": polarity}


def marks(html):
    return re.findall(r'<mark class="([^"]*)" data-criteria="([^"]*)"[^>]*>(.*?)</mark>', html)


# --- paragraphs ---------------------------------------------------------------------------------

def test_paragraphs_are_found_and_exclude_the_blank_lines():
    assert [TEXT[a:b] for a, b in paragraph_ranges(TEXT)] == [
        "Alpha beta gamma.", "Delta epsilon zeta.", "Eta theta."]


def test_text_without_blank_lines_is_one_paragraph():
    assert paragraph_ranges("just one line") == [(0, len("just one line"))]


def test_every_paragraph_is_rendered():
    assert response_html(TEXT, []).count("<p class=") == 3


# --- segmentation -------------------------------------------------------------------------------

def test_segments_reassemble_into_the_paragraphs():
    segments = segment(TEXT, [span(0, 5), span(19, 24)])
    rebuilt = {}
    for s in segments:
        rebuilt.setdefault(s["paragraph"], []).append(s["text"])
    joined = ["".join(v) for _, v in sorted(rebuilt.items())]
    assert joined == ["Alpha beta gamma.", "Delta epsilon zeta.", "Eta theta."]


def test_a_segment_lists_every_span_covering_it():
    """Two traits citing the same sentence is permitted, so the segment carries both."""
    overlapping = [span(0, 17, "argumentation"), span(0, 17, "organization")]
    covered = [s for s in segment(TEXT, overlapping) if s["spans"]]
    assert len(covered) == 1
    assert sorted(x["criterion"] for x in covered[0]["spans"]) == ["argumentation", "organization"]


def test_partial_overlap_splits_into_three_segments():
    partial = [span(0, 10, "argumentation"), span(6, 17, "conventions")]
    covered = [s for s in segment(TEXT, partial) if s["spans"]]
    assert [len(s["spans"]) for s in covered] == [1, 2, 1]
    assert covered[1]["text"] == TEXT[6:10]


def test_a_nested_span_does_not_hide_the_outer_one():
    nested = [span(0, 17, "argumentation"), span(6, 10, "conventions")]
    inner = [s for s in segment(TEXT, nested) if len(s["spans"]) == 2]
    assert len(inner) == 1
    assert primary(inner[0]["spans"])["criterion"] == "argumentation"


def test_a_span_crossing_a_paragraph_break_becomes_two_segments():
    crossing = [span(6, 24)]
    covered = [s for s in segment(TEXT, crossing) if s["spans"]]
    assert len(covered) == 2
    assert {s["paragraph"] for s in covered} == {0, 1}


# --- markup -------------------------------------------------------------------------------------

def test_the_primary_span_supplies_the_colour_and_polarity_classes():
    html = response_html(TEXT, [span(0, 17, "conventions", "weakness")])
    classes = marks(html)[0][0]
    assert "c-conventions" in classes and "p-weakness" in classes


def test_a_segment_cited_by_two_traits_is_marked_as_multiple():
    html = response_html(TEXT, [span(0, 17, "argumentation"), span(0, 17, "development")])
    classes, criteria, _ = marks(html)[0]
    assert "hl-multi" in classes
    assert set(criteria.split()) == {"argumentation", "development"}


def test_a_segment_cited_once_is_not_marked_as_multiple():
    html = response_html(TEXT, [span(0, 17)])
    assert "hl-multi" not in marks(html)[0][0]


def test_the_title_names_every_citing_trait_and_its_direction():
    html = response_html(TEXT, [span(0, 17, "argumentation", "strength"),
                                span(0, 17, "conventions", "weakness")])
    title = re.search(r'title="([^"]*)"', html).group(1)
    assert "argumentation" in title and "conventions" in title
    assert "strength" in title and "weakness" in title


def test_markup_in_the_response_is_escaped():
    hostile = 'She wrote <script>alert("x")</script> & meant it.'
    html = response_html(hostile, [span(0, 9)])
    assert "<script>" not in html
    assert "&lt;script&gt;" in html and "&amp;" in html


def test_a_single_newline_inside_a_paragraph_becomes_a_line_break():
    html = response_html("first line\nsecond line", [])
    assert "<br>" in html
    assert html.count("<p class=") == 1


def test_a_response_with_no_spans_renders_no_marks():
    assert "<mark" not in response_html(TEXT, [])


def test_marked_text_is_the_students_text_unchanged():
    html = response_html(TEXT, [span(0, 17)])
    assert marks(html)[0][2] == "Alpha beta gamma."


# --- flattening artifact criteria ---------------------------------------------------------------

def test_all_spans_tags_each_span_with_its_criterion_and_orders_by_position():
    criteria = {
        "conventions": {"spans": [{"start": 19, "end": 24, "polarity": "weakness"}]},
        "argumentation": {"spans": [{"start": 0, "end": 5, "polarity": "strength"}]},
    }
    flat = all_spans(criteria)
    assert [s["criterion"] for s in flat] == ["argumentation", "conventions"]


def test_all_spans_of_an_empty_criterion_contributes_nothing():
    assert all_spans({"development": {"spans": []}}) == []


# --- focusing one trait repaints its own evidence ------------------------------------------------
#
# The resting fill of a segment belongs to whichever span is outermost. That is right when reading
# the whole response, and wrong the moment a reader asks what ONE trait looked at: a conventions
# citation wrapped by an organization span would stay blue. These per-criterion classes are what
# let CSS repaint it in the focused trait's own colour and direction.

def test_a_mark_declares_every_trait_that_cited_it():
    html = response_html(TEXT, [span(0, 17, "organization", "strength"),
                                span(4, 10, "conventions", "weakness")])
    inner = [m for m in marks(html) if "conventions" in m[1]]
    assert inner, "the inner citation produced no mark"
    assert "has-conventions" in inner[0][0]
    assert "has-organization" in inner[0][0]


def test_a_mark_declares_each_traits_own_direction():
    """The wrapping span is a strength and the inner one a weakness; both must be recoverable,
    because whichever trait is focused supplies the underline."""
    html = response_html(TEXT, [span(0, 17, "organization", "strength"),
                                span(4, 10, "conventions", "weakness")])
    classes = [m[0] for m in marks(html) if "conventions" in m[1]][0]
    assert "pol-organization-strength" in classes
    assert "pol-conventions-weakness" in classes


def test_the_resting_fill_still_comes_from_the_outermost_span():
    html = response_html(TEXT, [span(0, 17, "organization", "strength"),
                                span(4, 10, "conventions", "weakness")])
    classes = [m[0] for m in marks(html) if "conventions" in m[1]][0]
    assert "c-organization" in classes and "c-conventions" not in classes.split()


def test_a_singly_cited_mark_carries_exactly_one_has_class():
    html = response_html(TEXT, [span(0, 17, "development", "weakness")])
    classes = marks(html)[0][0].split()
    assert [c for c in classes if c.startswith("has-")] == ["has-development"]
    assert [c for c in classes if c.startswith("pol-")] == ["pol-development-weakness"]
