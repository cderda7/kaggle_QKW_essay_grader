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


def test_the_served_stylesheet_has_no_unterminated_comment(client):
    """A stylesheet whose comment never closes swallows every rule after it, and the page renders
    unstyled rather than broken -- nothing raises, nothing 500s, and every other test still
    passes. Caught exactly that way while reflowing a section divider, so it is covered now."""
    css = client.get("/static/app.css").text
    assert css.count("/*") == css.count("*/"), "unbalanced CSS comment markers"

    position, blocks, live = 0, 0, []
    while True:
        start = css.find("/*", position)
        if start < 0:
            live.append(css[position:])
            break
        end = css.find("*/", start + 2)
        assert end > start, "unterminated CSS comment at offset %d" % start
        assert "/*" not in css[start + 2:end], "nested CSS comment at offset %d" % start
        live.append(css[position:start])
        position, blocks = end + 2, blocks + 1
    assert blocks, "no comments at all -- the file is probably not the stylesheet"

    # The rules the page depends on have to survive whatever the comments do. Each selector has to
    # still head a rule once every comment span is cut out; merely occurring in the text would
    # also be true of a selector that a runaway comment had swallowed.
    live = "\n".join(live)
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


def test_a_correction_that_changes_nothing_opens_the_panel_and_explains(client, essay_id,
                                                                       ledger_overrides):
    """ui_9/D2: the control's dominant experience is that it appears not to work. The panel
    opening itself is what turns that into an explanation instead of a bug report."""
    response = client.post("/api/override/%s" % essay_id,
                           json={"corrected_traits": {"conventions": 6}})
    essay = response.json()["essay"]
    if not essay["score_unchanged_by_override"]:
        pytest.skip("this essay's conventions correction did move the band")

    body = client.get("/essay/%s" % essay_id).text
    assert '<details class="formation" open>' in body
    assert "did not move the score" in body
    assert "nearest cut point" in body


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


# --- the essay list ------------------------------------------------------------------------------

def test_saving_an_unchanged_form_is_refused_before_it_reaches_the_ledger(client, essay_id,
                                                                          ledger_overrides):
    """A correction identical to the one already stored is not a second decision. The control is
    guarded in the page; this asserts the seam agrees that an empty correction is a mistake."""
    import build_review
    with pytest.raises(build_review.OverrideError) as exc:
        build_review.check_override_records(
            [{"essay_id": essay_id, "kind": "trait_correction", "corrected_traits": {}}])
    assert "corrects no trait" in str(exc.value)


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
