"""The served pages, exercised the way a browser hits them.

These run against the real annotation batches, so they double as a check that the whole path --
predictions, annotation, anchoring, build, render -- survives a page load.
"""

import json
import os
import re
from html.parser import HTMLParser

import pytest

from conftest import SOURCE_CSV

pytestmark = pytest.mark.skipif(not os.path.exists(SOURCE_CSV),
                                reason="corpus CSV not available")


@pytest.fixture(scope="module")
def client():
    from fastapi.testclient import TestClient
    import app as application
    return TestClient(application.app)


@pytest.fixture(scope="module")
def essay_id(client):
    return client.get("/api/review").json()["essays"][0]["essay_id"]


class _Nesting(HTMLParser):
    VOID = {"meta", "link", "br", "input", "img", "hr"}

    def __init__(self):
        HTMLParser.__init__(self)
        self.stack, self.bad = [], []

    def handle_starttag(self, tag, attrs):
        if tag not in self.VOID:
            self.stack.append(tag)

    def handle_endtag(self, tag):
        if not self.stack or self.stack[-1] != tag:
            self.bad.append(tag)
        else:
            self.stack.pop()


def assert_well_formed(html):
    parser = _Nesting()
    parser.feed(html)
    assert not parser.bad, "mismatched closing tags: %s" % parser.bad[:5]
    assert not parser.stack, "unclosed tags: %s" % parser.stack[:5]


# --- the essay list -------------------------------------------------------------------------

def test_the_index_lists_every_reviewable_essay(client):
    body = client.get("/").text
    ids = [e["essay_id"] for e in client.get("/api/review").json()["essays"]]
    assert client.get("/").status_code == 200
    for eid in ids:
        assert 'href="/essay/%s"' % eid in body


def test_the_index_shows_a_score_and_a_review_status(client):
    body = client.get("/").text
    assert "<th>Status</th>" in body
    assert "Score" in body


def test_a_partial_corpus_says_so(client):
    data = client.get("/api/review").json()
    if not data["complete"]:
        assert "not annotated yet" in client.get("/").text


# --- the review page ------------------------------------------------------------------------

def test_the_review_page_renders(client, essay_id):
    response = client.get("/essay/%s" % essay_id)
    assert response.status_code == 200
    assert_well_formed(response.text)


def test_an_unknown_essay_is_a_404(client):
    assert client.get("/essay/does-not-exist").status_code == 404


def test_the_four_trait_cards_appear_in_weight_order(client, essay_id):
    body = client.get("/essay/%s" % essay_id).text
    assert re.findall(r'data-criterion="(\w+)"', body) == [
        "argumentation", "organization", "development", "conventions"]


def test_each_card_shows_its_own_trait_score(client, essay_id):
    """The score is a control now (ticket 05), so it is read off the selected option."""
    body = client.get("/essay/%s" % essay_id).text
    data = client.get("/api/review/%s" % essay_id).json()
    shown = [int(x) for x in re.findall(r'<option value="(\d)" selected>', body)]
    expected = [data["criteria"][c]["trait_score"]
                for c in ("argumentation", "organization", "development", "conventions")]
    assert shown == expected


def test_the_headline_score_is_the_holistic_out_of_six(client, essay_id):
    body = client.get("/essay/%s" % essay_id).text
    data = client.get("/api/review/%s" % essay_id).json()
    assert int(re.search(r'score-value">(\d)<', body).group(1)) == data["holistic"]
    assert "/6" in body


def test_the_overview_is_shown(client, essay_id):
    body = client.get("/essay/%s" % essay_id).text
    data = client.get("/api/review/%s" % essay_id).json()
    assert data["overview"][:40] in body


def test_the_response_text_is_marked_up(client, essay_id):
    body = client.get("/essay/%s" % essay_id).text
    data = client.get("/api/review/%s" % essay_id).json()
    n_spans = sum(len(c["spans"]) for c in data["criteria"].values())
    assert body.count("<mark class=") >= n_spans


def test_every_mark_declares_which_traits_cited_it(client, essay_id):
    body = client.get("/essay/%s" % essay_id).text
    for classes, criteria in re.findall(r'<mark class="([^"]*)" data-criteria="([^"]*)"', body):
        assert criteria.strip(), "a mark carries no criterion"
        assert "p-strength" in classes or "p-weakness" in classes


def test_the_missing_prompt_is_stated_rather_than_invented(client, essay_id):
    """This corpus ships essay text and score only. An invented prompt would be a fabrication
    presented as source material, which is exactly what the span guards exist to prevent."""
    body = client.get("/essay/%s" % essay_id).text
    assert "does not include the task prompt" in body


def test_the_legend_explains_both_channels(client, essay_id):
    body = client.get("/essay/%s" % essay_id).text
    assert "strength" in body and "weakness" in body
    for criterion in ("Argumentation", "Organization", "Development", "Conventions"):
        assert criterion in body


# --- the score-formation panel ----------------------------------------------------------------

def test_the_formation_panel_is_collapsed_by_default(client, essay_id):
    """Collapsed keeps the ordinary read intact: score, overview, cards. `<details>` without
    `open` is closed in every browser and still readable with JS off or by a screen reader."""
    body = client.get("/essay/%s" % essay_id).text
    assert '<details class="formation">' in body
    assert '<details class="formation" open' not in body


def test_the_panel_shows_every_step_between_the_traits_and_the_number(client, essay_id):
    body = client.get("/essay/%s" % essay_id).text
    panel = body[body.index('<details class="formation">'):body.index("</details>")]
    for step in ("Weighted trait mean", "Length", "words", "log", "Baseline",
                 "Continuous score s", "band", "cut point"):
        assert step in panel, step


def test_the_panel_prints_the_values_the_build_produced(client, essay_id):
    """Read from the artifact, not recomputed in the page: every number on the panel has to be a
    formatted stored value, or the page is a second implementation of the aggregator."""
    body = client.get("/essay/%s" % essay_id).text
    panel = body[body.index('<details class="formation">'):body.index("</details>")]
    f = client.get("/api/review/%s" % essay_id).json()["score_formation"]

    assert "%.3f" % f["continuous_score"] in panel
    assert "%.2f" % f["weighted_trait_mean"] in panel
    assert "%d words" % f["word_count"] in panel
    assert "%.3f" % f["log10_word_count"] in panel
    assert "%.3f" % abs(f["length_term"]) in panel
    assert "%.3f" % abs(f["trait_term"]) in panel
    assert "%.3f" % abs(f["intercept"]) in panel
    assert "%.3f" % f["distance_to_nearest_cut"] in panel


def test_the_panel_states_the_length_contribution_rather_than_implying_it(client, essay_id):
    """The panel's whole reason for existing (ui_5): four trait cards next to one number assert
    that the traits produced it, and a substantial part of every score is length."""
    body = client.get("/essay/%s" % essay_id).text
    panel = body[body.index('<details class="formation">'):body.index("</details>")]
    f = client.get("/api/review/%s" % essay_id).json()["score_formation"]

    assert "A point on every trait" in panel and "Twice as many words" in panel
    assert "+%.2f" % f["s_per_trait_point"] in panel
    assert "+%.2f" % f["s_per_length_doubling"] in panel
    assert "0.820" in panel and "0.688" in panel


def test_the_panel_column_adds_up_on_screen(client, essay_id):
    """A sum whose printed addends do not reach its printed total reads as an arithmetic error and
    would discredit the one panel built to be checked."""
    body = client.get("/essay/%s" % essay_id).text
    panel = body[body.index('<details class="formation">'):body.index("</details>")]
    terms = [float(t.replace("\u2212", "-").replace("+", ""))
             for t in re.findall(r'class="num term">([^<]+)</td>', panel)]
    assert len(terms) == 4, terms
    assert round(sum(terms[:3]), 3) == terms[3]


# --- the rater's score is not in the page until it is deliberately revealed --------------------

@pytest.fixture
def ledger(tmp_path, monkeypatch):
    """Point the reveal ledger at a temp file: a test run must not append to the audit record."""
    import gold
    monkeypatch.setattr(gold, "REVEALS_FILE", str(tmp_path / "gold_reveals.json"))
    return str(tmp_path / "gold_reveals.json")


def test_the_raters_score_is_not_in_the_served_page_before_a_reveal(client, essay_id, ledger,
                                                                    monkeypatch):
    """Asserting the real score is absent proves nothing -- it is a digit from 1 to 6 and the page
    is full of those. A sentinel the corpus could never produce does prove it: if it is anywhere in
    the markup, the page asked for the answer key before anyone deliberately revealed it."""
    import gold
    monkeypatch.setattr(gold, "gold_score", lambda *a, **k: 987654)

    body = client.get("/essay/%s" % essay_id).text
    assert "987654" not in body
    assert 'class="gold-value"' not in body
    assert "data-revealed" not in body


def test_the_review_artifact_never_carries_the_raters_score(client):
    """The artifact is what /api/review serves, so the withholding has to hold there too."""
    def keys(node):
        if isinstance(node, dict):
            for k, v in node.items():
                yield k
                for sub in keys(v):
                    yield sub
        elif isinstance(node, list):
            for item in node:
                for sub in keys(item):
                    yield sub

    found = set(keys(client.get("/api/review").json()))
    assert not found & {"gold", "gold_score", "human_score", "score", "rater_score"}


def test_the_reveal_control_says_it_is_recorded_and_why(client, essay_id, ledger):
    body = client.get("/essay/%s" % essay_id).text
    block = body[body.index('<section class="gold"'):]
    block = block[:block.index("</section>")]
    assert "recorded" in block
    assert "gold_revealed" in block
    assert "steers the model" in block
    # A flag, not a ban -- overstating its reach teaches trust in a boundary that is not there.
    assert "personal_training_set.csv" in block
    assert "neither prevented nor logged" in block


def test_revealing_returns_the_score_and_records_it(client, essay_id, ledger):
    import gold
    response = client.post("/api/gold/%s" % essay_id)
    assert response.status_code == 200
    payload = response.json()
    assert payload["gold_score"] == gold.gold_score(essay_id)
    assert payload["already_revealed"] is False
    assert json.load(open(ledger))[0]["essay_id"] == essay_id


def test_after_a_reveal_the_page_shows_the_score_and_says_it_was_recorded(client, essay_id, ledger):
    import gold
    client.post("/api/gold/%s" % essay_id)
    body = client.get("/essay/%s" % essay_id).text
    assert 'data-revealed="true"' in body
    assert '<span class="gold-number">%d</span>' % gold.gold_score(essay_id) in body
    assert "gold_revealed: true" in body
    assert "gold-reveal" not in body, "the reveal control should be gone once it has fired"


def test_a_second_reveal_does_not_add_a_second_record(client, essay_id, ledger):
    client.post("/api/gold/%s" % essay_id)
    assert client.post("/api/gold/%s" % essay_id).json()["already_revealed"] is True
    assert len(json.load(open(ledger))) == 1


def test_the_reveal_flag_is_readable_for_the_records_that_follow(client, essay_id, ledger):
    """What ticket 05 stamps `gold_revealed` from."""
    import gold
    assert gold.was_revealed(essay_id) is False
    client.post("/api/gold/%s" % essay_id)
    assert gold.was_revealed(essay_id) is True


def test_an_essay_outside_the_review_set_cannot_be_revealed(client, ledger):
    """The endpoint must not become a way to read the answer key of an arbitrary corpus essay."""
    assert client.post("/api/gold/does-not-exist").status_code == 404
    assert not os.path.exists(ledger)


def test_the_reveal_is_a_post_because_it_writes_the_record(client, essay_id, ledger):
    assert client.get("/api/gold/%s" % essay_id).status_code == 405
    assert not os.path.exists(ledger)


# --- api and static -------------------------------------------------------------------------

def test_the_review_json_is_available_for_one_essay(client, essay_id):
    data = client.get("/api/review/%s" % essay_id).json()
    assert data["essay_id"] == essay_id
    assert set(data["criteria"]) == {"argumentation", "organization",
                                     "development", "conventions"}


def test_the_stylesheet_and_script_are_served(client):
    css = client.get("/static/app.css")
    js = client.get("/static/app.js")
    assert css.status_code == 200 and "text/css" in css.headers["content-type"]
    assert js.status_code == 200
    assert "--argumentation" in css.text


# --- startup ---------------------------------------------------------------------------------
#
# The first version of this printed nothing at all on start (uvicorn's log level was set to
# "warning", which suppresses its own startup banner), so a working server was indistinguishable
# from a hung one. These cover the feedback, not just the serving.

def test_preflight_returns_the_artifact_when_annotation_is_usable():
    import app as application
    data = application.preflight()
    assert data is not None
    assert data["essays"]


def test_preflight_explains_itself_when_there_is_no_annotation(tmp_path, monkeypatch):
    import io
    import app as application
    monkeypatch.setattr(application, "annotated_ids", lambda *a, **k: [])
    stream = io.StringIO()
    assert application.preflight(stream=stream) is None
    assert "No annotation found" in stream.getvalue()


def test_preflight_reports_guard_failures_rather_than_serving_them(monkeypatch):
    import io
    import app as application
    from build_review import AnnotationError

    def explode(**kwargs):
        raise AnnotationError("annotation in annotation_v6_runB is not usable (1 problem(s)):\n"
                              "  E1 argumentation[0]: quote not found in the response.")

    monkeypatch.setattr(application, "build_review", explode)
    stream = io.StringIO()
    assert application.preflight(stream=stream) is None
    text = stream.getvalue()
    assert "not usable" in text and "E1 argumentation[0]" in text


def test_the_banner_names_the_url_and_the_essays():
    import app as application
    data = application.preflight()
    banner = application._banner(data, "127.0.0.1", 8000)
    assert "http://127.0.0.1:8000" in banner
    for essay in data["essays"]:
        assert essay["essay_id"] in banner


def test_the_banner_says_when_the_sample_is_only_partly_annotated():
    import app as application
    data = application.preflight()
    banner = application._banner(data, "127.0.0.1", 8000)
    if not data["complete"]:
        assert "of %d in the frozen sample" % len(data["essays_in_manifest"]) in banner


def test_every_served_mark_can_be_repainted_by_any_trait_that_cited_it(client, essay_id):
    """Each mark must carry has-<criterion> and pol-<criterion>-<polarity> for every trait in its
    data-criteria, or focusing that trait would leave its own evidence in another trait's colour."""
    body = client.get("/essay/%s" % essay_id).text
    for classes, criteria in re.findall(r'<mark class="([^"]*)" data-criteria="([^"]*)"', body):
        for name in criteria.split():
            assert "has-%s" % name in classes, "%s missing has-%s" % (classes, name)
            assert any(c == "pol-%s-strength" % name or c == "pol-%s-weakness" % name
                       for c in classes.split()), "%s missing a polarity for %s" % (classes, name)


def test_the_page_explains_how_to_pin_a_trait(client, essay_id):
    assert "click to pin" in client.get("/essay/%s" % essay_id).text


# --- stale assets ------------------------------------------------------------------------------
#
# A cached app.css/app.js paired with freshly generated HTML produced new markup driven by old
# behaviour, which is indistinguishable from a broken feature. These make that impossible.

def test_asset_urls_are_stamped_with_the_files_modification_time(client, essay_id):
    body = client.get("/essay/%s" % essay_id).text
    assert re.search(r'href="/static/app\.css\?v=\d+"', body)
    assert re.search(r'src="/static/app\.js\?v=\d+"', body)


def test_editing_an_asset_changes_its_url(tmp_path, monkeypatch):
    import app as application
    before = application.asset("app.css")
    monkeypatch.setattr(application.os.path, "getmtime", lambda p: 999999999)
    assert application.asset("app.css") != before


def test_static_assets_are_served_with_revalidation_forced(client):
    for path in ("/static/app.css", "/static/app.js"):
        headers = client.get(path).headers
        assert "no-cache" in headers.get("cache-control", "")


def _live_css(css):
    """The stylesheet as a browser is left with it: every comment span removed.

    CSS comments do not nest, so a span runs to the first `*/`; an unterminated one runs to the
    end of the file and takes every rule after it. Modelling that is the point -- the regression
    this guards is a broken terminator, which raises nothing and 500s nothing and leaves the page
    rendering unstyled while every other test still passes.
    """
    live, position = [], 0
    while True:
        start = css.find("/*", position)
        if start < 0:
            live.append(css[position:])
            return "".join(live)
        live.append(css[position:start])
        end = css.find("*/", start + 2)
        if end < 0:
            return "".join(live)
        position = end + 2


def test_the_served_stylesheet_still_carries_the_rules_the_page_depends_on(client):
    """Caught exactly this way while reflowing a section divider: one broken terminator commented
    out the rest of the file. Each selector has to still head a live rule once the comment spans
    are cut away -- merely occurring in the text is also true of a swallowed rule."""
    live = _live_css(client.get("/static/app.css").text)
    for selector in (".formation", ".gold", ".override", ".card-score-select"):
        assert re.search(re.escape(selector) + r"(?![\w-])[^{};]*\{", live), selector


def test_a_stamped_asset_url_still_serves_the_file(client):
    response = client.get("/static/app.css?v=123")
    assert response.status_code == 200
    assert "--argumentation" in response.text


# --- correcting a trait ---------------------------------------------------------------------------

@pytest.fixture
def ledger_overrides(tmp_path, monkeypatch):
    """A temp overrides ledger. The committed one is evidence and tests must not append to it.

    One name owns the path, so one patch redirects the whole app: reader, writer and guard."""
    import build_review
    path = str(tmp_path / "overrides.json")
    monkeypatch.setattr(build_review, "OVERRIDES_FILE", path)
    return path


def test_every_trait_score_is_editable_on_its_card(client, essay_id):
    body = client.get("/essay/%s" % essay_id).text
    for criterion in ("argumentation", "organization", "development", "conventions"):
        assert 'class="card-score-select" name="%s"' % criterion in body
    assert body.count('<option value="6">') + body.count('<option value="6" selected>') == 4


def test_the_card_control_remembers_what_the_ai_said(client, essay_id):
    """Needed to tell a real correction from a re-selection of the same number."""
    body = client.get("/essay/%s" % essay_id).text
    data = client.get("/api/review/%s" % essay_id).json()
    for criterion, score in data["ai_traits"].items():
        assert 'name="%s" data-ai="%d"' % (criterion, score) in body


def test_a_correction_recomputes_the_holistic_and_shows_both(client, essay_id, ledger_overrides):
    response = client.post("/api/override/%s" % essay_id,
                           json={"corrected_traits": {"argumentation": 6, "organization": 6,
                                                      "development": 6, "conventions": 6},
                                 "rationale": "this is a strong response"})
    assert response.status_code == 200
    after = response.json()["essay"]

    body = client.get("/essay/%s" % essay_id).text
    assert '<span class="score-was">%d</span>' % after["ai_holistic"] in body
    assert '<span class="score-value">%d</span>' % after["holistic"] in body
    assert "moved this from %d to %d" % (after["ai_holistic"], after["holistic"]) in body


def test_a_correction_that_changes_nothing_opens_the_panel_and_explains(client, monkeypatch):
    """ui_9/D2: the control's dominant experience is that it appears not to work. The panel
    opening itself is what turns that into an explanation instead of a bug report."""
    essay = _synthetic(
        monkeypatch,
        {"essay_id": "E1", "kind": "trait_correction", "corrected_traits": {"conventions": 3}},
    )
    assert essay["overridden"] is True
    assert essay["holistic"] == essay["ai_holistic"]
    assert essay["score_unchanged_by_latest_record"] is True
    assert essay["score_unchanged_vs_ai"] is True

    body = client.get("/essay/E1").text
    assert '<details class="formation" open>' in body
    distance = ("%.3f" % essay["score_formation"]["distance_to_nearest_cut"]).replace("-", "\u2212")
    assert "The nearest cut point is <b>%s</b>" % distance in body
    assert "did not move the score" in body


def _synthetic(monkeypatch, *records, **kwargs):
    """Serve a page built from the synthetic fixture, so which corpus essay the client yields
    cannot decide whether a correction crosses a cut.

    `word_count` shifts which band the same traits land in, which is how a sequence reaching
    three distinct holistics is constructed."""
    import app as application
    from test_build_review import ESSAYS, MANIFEST, PREDICTIONS, PRED_TRAITS, make_item

    word_count = kwargs.pop("word_count", None)
    assert not kwargs, kwargs
    predictions = PREDICTIONS
    if word_count is not None:
        predictions = {"E1": dict({"system_" + c: str(v) for c, v in PRED_TRAITS.items()},
                                  essay_id="E1", word_count=str(word_count))}
    built = application.build_review(predictions=predictions, annotation={"E1": make_item()},
                                     essays=ESSAYS, override_records=list(records),
                                     expected_ids=["E1"], manifest=MANIFEST)
    monkeypatch.setattr(application, "artifact", lambda: built)
    return built["essays"][0]


ALL_SIX = {"argumentation": 6, "organization": 6, "development": 6, "conventions": 6}


def test_a_second_correction_that_moves_nothing_still_opens_the_panel(client, monkeypatch):
    """ui_9/D2 has to hold for every save, not only the first. From all traits at 6 the score is
    2; dropping conventions to 5 leaves it at 2, so that save did nothing and has to say so --
    measured against the score it was made against, not against the AI's."""
    essay = _synthetic(
        monkeypatch,
        {"essay_id": "E1", "kind": "trait_correction", "corrected_traits": dict(ALL_SIX)},
        {"essay_id": "E1", "kind": "trait_correction",
         "corrected_traits": dict(ALL_SIX, conventions=5)},
    )
    assert essay["holistic"] != essay["ai_holistic"]
    assert essay["holistic_before_latest_record"] == essay["holistic"]
    assert essay["score_unchanged_by_latest_record"] is True
    assert essay["score_unchanged_vs_ai"] is False

    body = client.get("/essay/E1").text
    assert '<details class="formation" open>' in body
    assert "did not move it any further" in body

    # Both facts have to be on the page at once: this save added nothing, AND the corrections
    # standing have moved the score off the AI's. Printing only the second number would hide the
    # AI's holistic entirely -- it appears nowhere else on the page.
    assert '<span class="score-was">%d</span>' % essay["ai_holistic"] in body
    assert "Your corrections have moved this from %d to %d" % (essay["ai_holistic"],
                                                               essay["holistic"]) in body
    assert "Your latest correction moved this from" not in body


def test_a_second_correction_that_moves_the_score_says_what_it_moved_from(client, monkeypatch):
    """The mirror: from all 6 (score 2) back to near the AI's traits gives 1, so the save moved
    2 to 1. Narrating it from the AI's 1 would credit this save with going nowhere."""
    essay = _synthetic(
        monkeypatch,
        {"essay_id": "E1", "kind": "trait_correction", "corrected_traits": dict(ALL_SIX)},
        {"essay_id": "E1", "kind": "trait_correction",
         "corrected_traits": {"argumentation": 4, "organization": 3, "development": 3,
                              "conventions": 3}},
    )
    assert essay["holistic"] == essay["ai_holistic"]
    assert essay["holistic_before_latest_record"] != essay["holistic"]
    assert essay["score_unchanged_by_latest_record"] is False
    assert essay["score_unchanged_vs_ai"] is True

    body = client.get("/essay/E1").text
    assert '<details class="formation" open>' not in body
    assert "moved this from %d to %d" % (essay["holistic_before_latest_record"],
                                         essay["holistic"]) in body
    assert "did not move the score" not in body


def test_the_page_and_the_ledger_agree_on_what_the_last_save_did(client, essay_id,
                                                                ledger_overrides):
    """The disagreement this pins down: the record says whether it moved the score, and the page
    tells the teacher the same thing about the same save."""
    client.post("/api/override/%s" % essay_id, json={"corrected_traits": ALL_SIX})
    second = client.post("/api/override/%s" % essay_id,
                         json={"corrected_traits": {"conventions": 1}}).json()

    essay = second["essay"]
    assert second["record"]["original_holistic"] == essay["holistic_before_latest_record"]
    assert second["record"]["score_unchanged"] == essay["score_unchanged_by_latest_record"]

    # Which of the two states this lands in depends on the corpus essay, so assert against the
    # sentence the row it DID land in defines rather than a phrase guessed for one of them. A
    # branch asserting a string its own state never renders reads as coverage and is not.
    import app as application

    body = client.get("/essay/%s" % essay_id).text
    state = application.narration_state(essay)
    assert state in ("corrected_moved", "corrected_inert_off_ai")
    assert application.score_narration(essay)["sentence"] in body
    assert ('<details class="formation" open>' in body) is (state == "corrected_inert_off_ai")


ONE_UP = {"conventions": 3}
SIX_BUT_ONE = dict(ALL_SIX, conventions=5)


def _correction(traits, rationale=None):
    rec = {"essay_id": "E1", "kind": "trait_correction", "corrected_traits": dict(traits)}
    if rationale is not None:
        rec["rationale"] = rationale
    return rec


def _dissent(why="length is carrying this score"):
    return {"essay_id": "E1", "kind": "dissent", "rationale": why}


# One row per state of app.SCORE_NARRATION. Each names the records that reach it and the three
# things the page must then say together: whether the head contrasts two holistics, a phrase the
# sentence must contain, and whether the score-formation panel opens itself. Asserting them one
# at a time is what let four rounds of contradictions through (decisions_log.md ui_18).
NARRATION_CASES = [
    ("untouched", [], False, None, False),
    ("corrected_moved", [_correction(ALL_SIX)], True,
     "moved this from", False),
    ("corrected_inert", [_correction(ONE_UP)], False,
     "did not move the score", True),
    ("corrected_inert_off_ai", [_correction(ALL_SIX), _correction(SIX_BUT_ONE)], True,
     "did not move it any further", True),
    ("reason_revised", [_correction(ONE_UP, "first"), _correction(ONE_UP, "second")], False,
     "revised the reason", False),
    ("reason_revised_off_ai", [_correction(ALL_SIX, "first"), _correction(ALL_SIX, "second")],
     True, "revised the reason", False),
    ("cleared", [_correction(ALL_SIX), {"essay_id": "E1", "kind": "cleared"}], False,
     "withdrew your trait correction", False),
    ("dissent", [_dissent()], False,
     "every trait still reads as it was scored", False),
    ("dissent_over_correction", [_correction(ONE_UP), _dissent()], False,
     "trait correction still stands", False),
    ("dissent_over_moving_correction", [_correction(ALL_SIX), _dissent()], True,
     "trait correction, which moved it from", False),
]


@pytest.mark.parametrize("state,records,contrasts,phrase,opens",
                         NARRATION_CASES, ids=[c[0] for c in NARRATION_CASES])
def test_each_score_narration_state_agrees_with_itself(client, monkeypatch, state, records,
                                                       contrasts, phrase, opens):
    """The head, the sentence and the panel are asserted together for every state, so a change to
    any one of them cannot silently contradict the other two."""
    import app as application

    essay = _synthetic(monkeypatch, *records)
    assert application.narration_state(essay) == state

    body = client.get("/essay/E1").text
    assert ('<span class="score-arrow">' in body) is contrasts
    if contrasts:
        was = application.score_narration(essay)["was"]
        assert was != essay["holistic"]
        assert '<span class="score-was">%d</span>' % was in body
    if phrase is None:
        assert '<p class="score-change' not in body
    else:
        assert phrase in body
    assert ('<details class="formation" open>' in body) is opens

    # A property of every row, not a column: wherever a correction has moved the score off the
    # AI's, the AI's own holistic is surfaced EXACTLY ONCE -- by the head where the head already
    # contrasts against it, by the labelled line where it does not. Asserting "exactly one"
    # rather than "at least one" is what stops a row either dropping the number the whole
    # surface exists to audit against, or stating it twice in a header a few lines tall.
    ai = essay["ai_holistic"]
    in_head = '<span class="score-was">%d</span>' % ai in body
    in_line = "The AI scored this <b>%d</b>/6." % ai in body
    off_ai = essay["holistic"] != ai
    assert [in_head, in_line].count(True) == (1 if off_ai else 0)
    if not off_ai:
        assert '<span class="score-value">%d</span>' % ai in body


def test_a_rationale_only_save_is_narrated_as_a_reason_revision(client, essay_id,
                                                                ledger_overrides):
    """The page's save handler sends every trait that differs from the AI's, so rewriting only
    the reason posts the standing traits again. That is a real record -- the reason did change --
    but it edited no trait, and telling the teacher their correction failed to move a score they
    never tried to move is the ui_17 misfire one step along."""
    import app as application

    first = {"corrected_traits": {"conventions": 5}, "rationale": "spelling is minor"}
    client.post("/api/override/%s" % essay_id, json=first)
    revised = dict(first, rationale="conventions are not the issue here")
    essay = client.post("/api/override/%s" % essay_id, json=revised).json()["essay"]

    assert essay["latest_record_changed_traits"] is False
    assert application.narration_state(essay).startswith("reason_revised")
    assert essay["override_rationale"] == "conventions are not the issue here"
    assert len(json.load(open(ledger_overrides))) == 2

    body = client.get("/essay/%s" % essay_id).text
    assert "revised the reason" in body
    assert "did not move the score" not in body
    assert '<details class="formation" open>' not in body


def test_a_correction_that_does_edit_a_trait_is_not_a_reason_revision(client, essay_id,
                                                                      ledger_overrides):
    """The other side, so the new distinction cannot collapse into always-a-revision."""
    import app as application

    client.post("/api/override/%s" % essay_id, json={"corrected_traits": {"conventions": 5}})
    essay = client.post("/api/override/%s" % essay_id,
                        json={"corrected_traits": {"conventions": 4}}).json()["essay"]
    assert essay["latest_record_changed_traits"] is True
    assert not application.narration_state(essay).startswith("reason_revised")


def test_a_second_correction_that_moves_the_score_still_shows_the_ai_holistic(client,
                                                                              monkeypatch):
    """Three distinct holistics: the AI's 1, what the first correction made it, and what the
    second did. The head contrasts what the LATEST save did -- that is the fact ui_16 exists to
    state -- so the AI's original has to be named separately or it leaves the page entirely.
    It appears nowhere else: the formation panel scores the current traits, and the trait cards
    carry per-trait AI scores only."""
    essay = _synthetic(
        monkeypatch,
        _correction({"argumentation": 5, "organization": 4}),
        _correction(ALL_SIX),
        word_count=150,
    )
    ai, was, now = essay["ai_holistic"], essay["holistic_before_latest_record"], essay["holistic"]
    assert len({ai, was, now}) == 3

    body = client.get("/essay/E1").text
    assert '<span class="score-was">%d</span>' % was in body
    assert '<span class="score-value">%d</span>' % now in body
    assert "Your latest correction moved this from %d to %d" % (was, now) in body
    assert "The AI scored this <b>%d</b>/6." % ai in body


def test_the_score_narration_states_are_coherent():
    """The rules the table exists to keep, checked over every row rather than per branch."""
    import app as application

    for state, (contrast, panel, sentence) in application.SCORE_NARRATION.items():
        if sentence is None:
            assert contrast is None and not panel, state
            continue
        if "every trait still reads as it was scored" in sentence:
            assert state == "dissent", state
        if state.startswith("dissent") or state == "cleared":
            assert not panel, state
        if panel:
            assert state.startswith("corrected_inert"), state
    assert {s for s, row in application.SCORE_NARRATION.items() if row[1]} == {
        "corrected_inert", "corrected_inert_off_ai"}
    assert set(application.SCORE_NARRATION) == {c[0] for c in NARRATION_CASES}


def test_a_dissent_after_a_correction_is_narrated_as_a_dissent(client, monkeypatch):
    """ui_17: a dissent moves no trait and no score by design, so it is never "a correction that
    did nothing". The correction standing under it keeps its own before/after head, and the panel
    stays shut -- the distance to the nearest cut answers a question a dissent never asked."""
    essay = _synthetic(
        monkeypatch,
        {"essay_id": "E1", "kind": "trait_correction", "corrected_traits": dict(ALL_SIX)},
        {"essay_id": "E1", "kind": "dissent", "rationale": "length is carrying this score"},
    )
    assert essay["latest_record_kind"] == "dissent"
    assert essay["score_unchanged_by_latest_record"] is True

    body = client.get("/essay/E1").text
    assert "Your dissent was recorded" in body
    assert "did not move the score" not in body
    assert '<details class="formation" open>' not in body
    assert ('<span class="score-was">%d</span>' % essay["ai_holistic"]) in body
    assert ('<span class="score-value">%d</span>' % essay["holistic"]) in body


def test_a_withdrawal_is_narrated_as_a_withdrawal(client, monkeypatch):
    """ui_17: clearing restores the AI's scores on purpose, so it is not a correction that
    failed either, and it does not open the panel."""
    essay = _synthetic(
        monkeypatch,
        {"essay_id": "E1", "kind": "trait_correction", "corrected_traits": dict(ALL_SIX)},
        {"essay_id": "E1", "kind": "cleared"},
    )
    assert essay["latest_record_kind"] == "cleared"
    assert essay["overridden"] is False

    body = client.get("/essay/E1").text
    assert "You withdrew your trait correction" in body
    assert "did not move the score" not in body
    assert "Your dissent was recorded" not in body
    assert '<details class="formation" open>' not in body


def test_an_untouched_essay_is_narrated_as_nothing_at_all(client, monkeypatch):
    """The fourth branch, so no narration leaks onto an essay nobody has opened."""
    essay = _synthetic(monkeypatch)
    assert essay["latest_record_kind"] is None

    body = client.get("/essay/E1").text
    for claim in ("did not move the score", "moved this from", "Your dissent was recorded",
                  "You withdrew your trait correction"):
        assert claim not in body
    assert '<details class="formation" open>' not in body


def test_the_post_response_and_a_later_get_agree_on_the_trail(client, essay_id,
                                                              ledger_overrides):
    """The build that produces a record's recomputed holistic has to read the record before it
    carries one, so the trail it returns quotes this record a field short unless it is re-folded.
    The same essay asked for twice must not answer differently."""
    posted = client.post("/api/override/%s" % essay_id,
                         json={"corrected_traits": {"conventions": 5}}).json()
    fetched = client.get("/api/review/%s" % essay_id).json()

    entry = posted["essay"]["override_trail"][-1]
    assert entry["recomputed_holistic"] == posted["record"]["recomputed_holistic"]
    assert entry == fetched["override_trail"][-1]
    assert posted["essay"]["override_trail"] == fetched["override_trail"]


def test_an_unchanged_save_does_not_render_a_struck_through_duplicate(client, monkeypatch):
    """`.score.corrected .score-was` is struck through, and a strikethrough asserts the value was
    superseded. Beside an identical number, above a sentence saying nothing moved, it contradicts
    both -- and this is the dominant render."""
    essay = _synthetic(
        monkeypatch,
        {"essay_id": "E1", "kind": "trait_correction", "corrected_traits": {"conventions": 3}},
    )
    assert essay["score_unchanged_by_latest_record"] is True

    body = client.get("/essay/E1").text
    assert "score-was" not in body
    assert "score-arrow" not in body
    assert body.count('<span class="score-value">%d</span>' % essay["holistic"]) == 1
    assert "did not move the score" in body


def test_a_correction_that_moves_the_score_leaves_the_panel_collapsed(client, monkeypatch):
    """The panel opens itself only when the correction appeared to do nothing, so the same
    synthetic inputs are used for the other half rather than a corpus essay that may do either."""
    essay = _synthetic(
        monkeypatch,
        {"essay_id": "E1", "kind": "trait_correction", "corrected_traits": dict(ALL_SIX)},
    )
    assert essay["holistic"] != essay["ai_holistic"]

    body = client.get("/essay/E1").text
    assert '<details class="formation">' in body
    assert "did not move the score" not in body
    assert "moved this from %d to %d" % (essay["ai_holistic"], essay["holistic"]) in body


def test_the_page_shows_the_ai_score_beside_a_corrected_trait(client, essay_id, ledger_overrides):
    data = client.get("/api/review/%s" % essay_id).json()
    was = data["ai_traits"]["conventions"]
    client.post("/api/override/%s" % essay_id,
                json={"corrected_traits": {"conventions": 1 if was != 1 else 6}})
    assert "AI said %d" % was in client.get("/essay/%s" % essay_id).text


def test_a_correction_survives_a_restart(client, essay_id, ledger_overrides):
    """The app holds nothing in memory -- every page load rebuilds from the file on disk."""
    client.post("/api/override/%s" % essay_id, json={"corrected_traits": {"argumentation": 6}})
    from fastapi.testclient import TestClient
    import app as application
    fresh = TestClient(application.app)
    assert fresh.get("/api/review/%s" % essay_id).json()["traits"]["argumentation"] == 6


def test_a_correction_can_be_cleared_without_erasing_it_happened(client, essay_id,
                                                                ledger_overrides):
    import json as json_module
    client.post("/api/override/%s" % essay_id, json={"corrected_traits": {"argumentation": 6}})
    cleared = client.post("/api/override/%s" % essay_id, json={"kind": "cleared"}).json()["essay"]

    assert cleared["traits"] == cleared["ai_traits"]
    assert cleared["overridden"] is False
    assert cleared["reviewed"] is True
    assert len(json_module.load(open(ledger_overrides))) == 2


def test_the_clear_control_appears_only_when_there_is_something_to_clear(client, essay_id,
                                                                        ledger_overrides):
    assert "override-clear" not in client.get("/essay/%s" % essay_id).text
    client.post("/api/override/%s" % essay_id, json={"corrected_traits": {"argumentation": 6}})
    assert "override-clear" in client.get("/essay/%s" % essay_id).text


def test_a_rationale_is_kept_and_shown_back(client, essay_id, ledger_overrides):
    client.post("/api/override/%s" % essay_id,
                json={"corrected_traits": {"conventions": 5}, "rationale": "the spelling is minor"})
    assert "the spelling is minor" in client.get("/essay/%s" % essay_id).text


# --- dissent --------------------------------------------------------------------------------------

def test_no_direct_holistic_override_is_offered(client, essay_id):
    """ui_2: a typed holistic cannot steer anything and would decouple the score from its
    evidence. What stands in its place is a dissent."""
    body = client.get("/essay/%s" % essay_id).text
    assert 'name="holistic"' not in body
    assert "dissent-save" in body


def test_a_dissent_records_a_reason_and_no_number(client, essay_id, ledger_overrides):
    response = client.post("/api/override/%s" % essay_id,
                           json={"kind": "dissent", "rationale": "the length term is doing this"})
    essay = response.json()["essay"]
    assert "corrected_traits" not in response.json()["record"]
    assert essay["traits"] == essay["ai_traits"]
    assert essay["holistic"] == essay["ai_holistic"]

    body = client.get("/essay/%s" % essay_id).text
    assert "Score dissent recorded" in body
    assert "the length term is doing this" in body


def test_a_dissent_without_a_reason_is_refused_and_says_why(client, essay_id, ledger_overrides):
    response = client.post("/api/override/%s" % essay_id, json={"kind": "dissent"})
    assert response.status_code == 400
    assert "rationale is the whole record" in response.json()["detail"]


def test_a_dissent_and_a_correction_coexist(client, essay_id, ledger_overrides):
    client.post("/api/override/%s" % essay_id, json={"corrected_traits": {"conventions": 5}})
    client.post("/api/override/%s" % essay_id, json={"kind": "dissent", "rationale": "still wrong"})
    essay = client.get("/api/review/%s" % essay_id).json()
    assert essay["traits"]["conventions"] == 5
    assert essay["dissent"]["rationale"] == "still wrong"


# --- refusals -----------------------------------------------------------------------------------

def test_an_impossible_trait_score_is_refused_with_a_message_that_names_it(client, essay_id,
                                                                          ledger_overrides):
    response = client.post("/api/override/%s" % essay_id,
                           json={"corrected_traits": {"argumentation": 9}})
    assert response.status_code == 400
    assert "argumentation=9" in response.json()["detail"]
    assert not os.path.exists(ledger_overrides)


def test_a_correction_for_an_essay_outside_the_review_set_is_a_404(client, ledger_overrides):
    assert client.post("/api/override/does-not-exist",
                       json={"corrected_traits": {"conventions": 3}}).status_code == 404
    assert not os.path.exists(ledger_overrides)


def test_a_correction_made_after_a_reveal_carries_the_flag(client, essay_id, ledger,
                                                          ledger_overrides):
    """Ticket 04 built the ledger; this is the stamp it exists for."""
    plain = client.post("/api/override/%s" % essay_id,
                        json={"corrected_traits": {"conventions": 5}}).json()["record"]
    client.post("/api/gold/%s" % essay_id)
    anchored = client.post("/api/override/%s" % essay_id,
                           json={"corrected_traits": {"conventions": 4}}).json()["record"]
    assert plain["gold_revealed"] is False
    assert anchored["gold_revealed"] is True


@pytest.mark.parametrize("body,names", [
    ({"corrected_traits": {"argumentation": "six"}}, "not a whole number"),
    ({"corrected_traits": [6]}, "expected an object"),
    ({"corrected_traits": {"conventions": 5}, "rationale": 5}, "expected text"),
])
def test_a_malformed_correction_is_a_naming_400_not_a_crash(client, essay_id, ledger_overrides,
                                                            body, names):
    """The stance is that a bad value names itself. A body that crashed on coercion before the
    guard ran would answer a 500 with no message, and the hand-edited file path would be the only
    one the guard covered."""
    response = client.post("/api/override/%s" % essay_id, json=body)
    assert response.status_code == 400
    assert names in response.json()["detail"]
    assert essay_id in response.json()["detail"]
    assert not os.path.exists(ledger_overrides)


def test_an_absent_kind_is_stored_as_the_kind_the_guard_validated(client, essay_id,
                                                                 ledger_overrides):
    """An explicit JSON null validates as a trait correction, so it has to be written down as
    one. The ledger is read by hand; a record whose kind is null does not say what it is."""
    record = client.post("/api/override/%s" % essay_id,
                         json={"kind": None,
                               "corrected_traits": {"conventions": 5}}).json()["record"]
    assert record["kind"] == "trait_correction"
    assert json.load(open(ledger_overrides))[0]["kind"] == "trait_correction"


def test_a_recorded_dissent_can_be_replaced_by_writing_a_newer_one(client, essay_id,
                                                                   ledger_overrides):
    """ui_15: a dissent is not withdrawn, it is superseded. The page has to keep offering the
    control, or a dissent recorded with a typo is permanent."""
    client.post("/api/override/%s" % essay_id,
                json={"kind": "dissent", "rationale": "the map is wrong here"})
    body = client.get("/essay/%s" % essay_id).text
    assert "the map is wrong here" in body
    assert 'class="dissent-rationale"' in body
    assert 'class="dissent-save"' in body

    client.post("/api/override/%s" % essay_id,
                json={"kind": "dissent", "rationale": "length is carrying this score"})
    essay = client.get("/api/review/%s" % essay_id).json()
    assert essay["dissent"]["rationale"] == "length is carrying this score"
    assert [r["kind"] for r in json.load(open(ledger_overrides))] == ["dissent", "dissent"]
    assert [t["rationale"] for t in essay["override_trail"]] == ["the map is wrong here",
                                                                 "length is carrying this score"]


def test_a_withdrawal_reason_is_not_offered_back_as_the_next_correction_s(client, essay_id,
                                                                          ledger_overrides):
    """The full sequence from the finding: correct with reason A, clear with reason B, correct
    again typing nothing. Record three must carry no reason rather than B."""
    client.post("/api/override/%s" % essay_id,
                json={"corrected_traits": {"conventions": 5}, "rationale": "spelling is minor"})
    client.post("/api/override/%s" % essay_id,
                json={"kind": "cleared", "rationale": "on reflection the AI had it right"})

    essay = client.get("/api/review/%s" % essay_id).json()
    assert essay["override_rationale"] is None
    assert "on reflection the AI had it right" not in client.get("/essay/%s" % essay_id).text

    client.post("/api/override/%s" % essay_id,
                json={"corrected_traits": {"argumentation": 4}, "rationale": ""})
    stored = json.load(open(ledger_overrides))
    assert [r["rationale"] for r in stored] == ["spelling is minor",
                                                "on reflection the AI had it right", None]


# --- the essay list ------------------------------------------------------------------------------

def test_a_trait_correction_that_corrects_nothing_never_reaches_the_ledger(client, essay_id,
                                                                          ledger_overrides):
    """A correction with an empty `corrected_traits` is refused by the seam, so no client can
    write one.

    This is NOT the duplicate-save guard. Re-POSTing traits identical to the standing correction
    is accepted by the server on purpose and appends a second record: the seam has no opinion
    about whether a teacher meant to decide the same thing twice, and the append-only ledger is
    the wrong place to start dropping records. What stops the accidental duplicate is a page
    affordance -- `scoresMoved()`/`rewritten()` in static/app.js, which refuses to POST an
    untouched form at all.
    """
    response = client.post("/api/override/%s" % essay_id,
                           json={"kind": "trait_correction", "corrected_traits": {}})
    assert response.status_code == 400
    assert "corrects no trait" in response.json()["detail"]
    assert not os.path.exists(ledger_overrides)


def test_an_identical_correction_posted_twice_is_recorded_twice(client, essay_id,
                                                                ledger_overrides):
    """The other half of the sentence above, stated as behaviour so it cannot drift silently:
    the server does not deduplicate, and the duplicate guard is a client affordance."""
    body = {"corrected_traits": {"conventions": 5}}
    assert client.post("/api/override/%s" % essay_id, json=body).status_code == 200
    assert client.post("/api/override/%s" % essay_id, json=body).status_code == 200
    assert len(json.load(open(ledger_overrides))) == 2


def test_the_index_distinguishes_reviewed_essays_from_untouched_ones(client, essay_id,
                                                                     ledger_overrides):
    assert "status-touched" not in client.get("/").text
    client.post("/api/override/%s" % essay_id,
                json={"corrected_traits": {"argumentation": 6, "organization": 6,
                                           "development": 6, "conventions": 6}})
    body = client.get("/").text
    assert "status-touched" in body
    assert "corrected" in body


def test_the_index_marks_a_dissent_as_a_visit_even_with_no_score_change(client, essay_id,
                                                                       ledger_overrides):
    client.post("/api/override/%s" % essay_id,
                json={"kind": "dissent", "rationale": "the map is wrong"})
    body = client.get("/").text
    assert "dissent" in body
    assert "status-touched" in body
