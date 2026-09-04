"""The served pages, exercised the way a browser hits them.

These run against the real annotation batches, so they double as a check that the whole path --
predictions, annotation, anchoring, build, render -- survives a page load.
"""

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
    body = client.get("/essay/%s" % essay_id).text
    data = client.get("/api/review/%s" % essay_id).json()
    shown = [int(x) for x in re.findall(r'card-score">(\d)<', body)]
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


# --- the gold score never reaches the page --------------------------------------------------

def test_no_gold_score_appears_in_the_served_page(client, essay_id):
    body = client.get("/essay/%s" % essay_id).text
    for leak in ("human_score", "gold", "human score"):
        assert leak not in body


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
