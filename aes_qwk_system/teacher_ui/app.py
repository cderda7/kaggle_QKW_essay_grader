"""Teacher review UI — a local, single-user app for reviewing AI-graded essays.

    python3 app.py            # then open http://127.0.0.1:8000

Reads local files only: no model API call, no database, no auth. The artifact is rebuilt from
predictions, annotation batches, essay text and override records on every request, because override
records are an INPUT to the build rather than a mutation applied to its output (decisions_log.md
ui_6). At ten essays the rebuild is free and it keeps every guard on the path a page load takes.

HTML is rendered in Python rather than through Jinja2Templates: the installed jinja2 (2.11) predates
what Starlette's template integration needs, and upgrading a shared dependency to serve one page is
a worse trade than a few format strings.
"""

import datetime
import glob
import html
import json
import os
import sys

from fastapi import Body, FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from build_review import (ANNOTATION_DIR, OVERRIDES_FILE, AnnotationError,  # noqa: E402
                          OverrideError, build_review, load_overrides)
from render import all_spans, response_html  # noqa: E402
import gold  # noqa: E402
import overrides  # noqa: E402

# Cards are ordered by the weight each trait carries in the score, not alphabetically, so the trait
# with the largest influence is read first. Organization and development tie at 0.25 and keep the
# rubric's own order.
CARD_ORDER = ("argumentation", "organization", "development", "conventions")
TRAIT_WEIGHTS = {"argumentation": 0.35, "organization": 0.25,
                 "development": 0.25, "conventions": 0.15}

class NoCacheStatic(StaticFiles):
    """Serve assets with revalidation forced.

    The HTML here is generated per request, so a stale stylesheet or script pairs new markup with
    old behaviour -- which looks exactly like a broken feature rather than a cached one, and cost a
    real debugging cycle. This is a local single-user tool; correctness beats caching.
    """

    def file_response(self, *args, **kwargs):
        response = super().file_response(*args, **kwargs)
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        return response


app = FastAPI(title="Teacher review UI")
app.mount("/static", NoCacheStatic(directory=os.path.join(HERE, "static")), name="static")


def asset(name):
    """A static URL stamped with the file's mtime, so an edit always changes the URL."""
    path = os.path.join(HERE, "static", name)
    stamp = int(os.path.getmtime(path)) if os.path.exists(path) else 0
    return "/static/%s?v=%d" % (name, stamp)


def annotated_ids(batch_dir=ANNOTATION_DIR):
    """Essays that actually have annotation, so a partial corpus still serves."""
    ids = []
    for path in sorted(glob.glob(os.path.join(batch_dir, "batch_*.json"))):
        with open(path) as f:
            ids.extend(item["essay_id"] for item in json.load(f))
    return sorted(set(ids))


def artifact():
    try:
        return build_review(override_records=load_overrides(), expected_ids=annotated_ids())
    except (AnnotationError, OverrideError) as exc:
        raise HTTPException(status_code=500, detail=str(exc))


def find(essay_id):
    for essay in artifact()["essays"]:
        if essay["essay_id"] == essay_id:
            return essay
    raise HTTPException(status_code=404, detail="no review for essay %s" % essay_id)


# --------------------------------------------------------------------------------------------
# markup
# --------------------------------------------------------------------------------------------

def page(title, body):
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        '<title>%s</title><link rel="stylesheet" href="%s"></head>'
        '<body>%s<script src="%s"></script></body></html>'
        % (html.escape(title), asset("app.css"), body, asset("app.js"))
    )


def criterion_card(name, crit):
    spans = crit["spans"]
    counts = {p: sum(1 for s in spans if s["polarity"] == p) for p in ("strength", "weakness")}
    if spans:
        evidence = (
            '<p class="card-evidence">%d cited %s — %d strength, %d weakness</p>'
            % (len(spans), "passage" if len(spans) == 1 else "passages",
               counts["strength"], counts["weakness"])
        )
    else:
        evidence = (
            '<p class="card-evidence card-noevidence">Nothing in the response to cite: %s</p>'
            % html.escape(crit.get("no_evidence_reason", "no reason given"))
        )
    options = "".join(
        '<option value="%d"%s>%d</option>'
        % (v, " selected" if v == crit["trait_score"] else "", v)
        for v in range(1, 7)
    )
    # The AI's own score stays visible next to a corrected one: a review surface that forgets what
    # it originally said cannot be audited, and the record stores both for the same reason.
    was = ("" if crit["trait_score"] == crit["ai_trait_score"] else
           '<span class="card-was">AI said %d</span>' % crit["ai_trait_score"])
    return (
        '<section class="card c-%s" data-criterion="%s" tabindex="0">'
        '<header class="card-head"><h3>%s</h3>'
        '<span class="card-score">'
        '<select class="card-score-select" name="%s" data-ai="%d" data-score="%d" '
        'aria-label="%s score out of 6">%s</select><span class="of">/6</span></span></header>'
        '<p class="card-weight">weight %.2f%s</p>'
        '<p class="card-comment">%s</p>%s</section>'
        % (name, name, name.capitalize(), name, crit["ai_trait_score"], crit["trait_score"],
           name.capitalize(), options,
           TRAIT_WEIGHTS[name], was, html.escape(crit["comment"]), evidence)
    )


def _num(value, places=2):
    """A number as the page shows it: fixed places, real minus sign."""
    return ("%.*f" % (places, value)).replace("-", "−")


def _signed(value, places=2):
    return ("+" if value >= 0 else "−") + ("%.*f" % (places, abs(value)))


def _reveal_display(stamp):
    """An ISO timestamp as a person reads it. The ledger keeps the ISO string; this is the eye's."""
    try:
        when = datetime.datetime.fromisoformat(stamp)
    except ValueError:
        return stamp
    return when.strftime("%-d %b %Y at %H:%M")


def formation_panel(essay):
    """How the holistic was actually formed — collapsed, and reading straight off the artifact.

    Every number here is a stored value (build_review._score_formation); nothing on this page
    multiplies a coefficient by a feature. The panel exists because four trait cards beside a bare
    N/6 assert that the traits produced it, and a substantial part of every score is length
    (decisions_log.md ui_5).
    """
    f = essay["score_formation"]
    band = (
        '<p class="formation-band">s = <b>%s</b> falls in %s, the band for <b>%d/6</b>.'
        % (_num(f["continuous_score"], 3), html.escape(f["band"]), essay["holistic"])
    )
    if f["distance_to_nearest_cut"] is not None:
        up = f["nearest_cut_direction"] == "up"
        band += (
            ' The nearest cut point is <b>%s</b> %s — past it the score would be %d.'
            % (_num(f["distance_to_nearest_cut"], 3), "above" if up else "below",
               essay["holistic"] + (1 if up else -1))
        )
    band += "</p>"

    leads = ("<b>Length moves this score further than a full point on all four traits.</b> "
             if f["s_per_length_doubling"] > f["s_per_trait_point"] else "")
    return (
        '<details class="formation"%s>'
        '<summary>How this score was formed</summary>'
        '<div class="formation-body">'
        '<table class="formation-sum"><tbody>'
        '<tr><th>Weighted trait mean</th><td class="num">%s</td>'
        '<td class="num coef">× %s</td><td class="num term">%s</td></tr>'
        '<tr><th>Length <span class="sub">%d words</span></th>'
        '<td class="num">log₁₀ %s</td><td class="num coef">× %s</td>'
        '<td class="num term">%s</td></tr>'
        '<tr><th>Baseline</th><td class="num"></td><td class="num coef"></td>'
        '<td class="num term">%s</td></tr>'
        '</tbody><tfoot><tr><th>Continuous score s</th><td class="num"></td>'
        '<td class="num coef"></td><td class="num term">%s</td></tr></tfoot></table>'
        '%s'
        '<dl class="formation-moves">'
        '<div><dt>A point on every trait</dt><dd>%s</dd></div>'
        '<div><dt>Twice as many words</dt><dd>%s</dd></div>'
        '</dl>'
        '<p class="formation-caveat">%sAcross the corpus, the correlation between word count and '
        'the score this system gives is 0.820, against 0.688 for the human raters. Four trait '
        'cards beside a single number imply the traits produced it; on their own, they did not.</p>'
        '</div></details>'
        # Three places on every term so the column adds up on screen: a sum whose addends are
        # rounded harder than its total reads as an arithmetic error.
        # ui_9/D2: the dominant experience of this control is that it appears not to work. When a
        # correction lands in the same band, the panel opens itself and shows the distance to the
        # cut -- the dead control becomes the explanation rather than a bug report.
        % (" open" if score_narration(essay)["opens_panel"] else "",
           _num(f["weighted_trait_mean"]), _num(f["beta"][1], 3), _signed(f["trait_term"], 3),
           f["word_count"], _num(f["log10_word_count"], 3), _num(f["beta"][2], 3),
           _signed(f["length_term"], 3), _signed(f["intercept"], 3),
           _num(f["continuous_score"], 3), band,
           _signed(f["s_per_trait_point"]), _signed(f["s_per_length_doubling"]), leads)
    )


# Every state the score narration can be in, and the three things each one decides: which
# holistic the head contrasts the current one against (None draws a single number), whether the
# score-formation panel opens itself, and what the sentence beneath says.
#
# One row per state, because deriving the three separately is what went wrong. Four rounds of
# review each found the head, the sentence and the panel disagreeing in a corner the previous
# round's conditional had not covered -- a struck-through number beside an identical one, a
# dissent reported as a correction that failed, "every trait still reads as it was scored"
# printed above four corrected traits. Those were one defect, not four (decisions_log.md ui_18).
#
# The rules the table has to keep, checked by test_the_score_narration_states_are_coherent:
#   * a contrast is only ever drawn between two DIFFERENT holistics -- a strikethrough asserts
#     the value was superseded, so beside an identical number it asserts a falsehood;
#   * "every trait still reads as it was scored" appears only where no trait differs from the
#     AI's;
#   * only a trait correction that edited traits and did not move the band opens the panel,
#     because "how far is this essay from the nearest cut" is the question a trait edit raises
#     and neither a dissent nor a withdrawal asks it;
#   * wherever a correction has moved the score off the AI's, the AI's own holistic is on the
#     page EXACTLY ONCE -- in the head where the head already contrasts against it, and in a
#     labelled line beneath where it does not. That is a property of every state rather than a
#     column, so a row added later can neither drop the number the whole surface exists to let a
#     teacher audit, nor print it twice over in a header three lines tall.
SCORE_NARRATION = {
    "untouched": (None, False, None),
    "corrected_moved": (
        "holistic_before_latest_record", False,
        "Your latest correction moved this from %(was)d to %(now)d, recomputed through the "
        "same frozen aggregator that produced the original."),
    "corrected_inert": (
        None, True,
        "Your latest correction did not move the score \u2014 it is still %(now)d/6, exactly "
        "where it stood before you saved it. That is the instrument, not a failed save: the "
        "panel below is open, showing how far this essay sits from the nearest cut point."),
    "corrected_inert_off_ai": (
        "ai_holistic", True,
        "Your corrections have moved this from %(ai)d to %(now)d. The latest one did not move "
        "it any further \u2014 it is still %(now)d/6, exactly where it stood before you saved "
        "it. That is the instrument, not a failed save: the panel below is open, showing how "
        "far this essay sits from the nearest cut point."),
    "reason_revised": (
        None, False,
        "You revised the reason for your correction \u2014 no trait score changed, so the "
        "score is still %(now)d/6."),
    "reason_revised_off_ai": (
        "ai_holistic", False,
        "You revised the reason for your correction \u2014 no trait score changed, so the "
        "score is still %(now)d/6, where your correction had already moved it from %(ai)d."),
    "cleared": (
        None, False,
        "You withdrew your trait correction \u2014 every trait reads as the AI scored it "
        "again, and the score is %(now)d/6. Both the correction and the withdrawal stay in the "
        "record below."),
    "dissent": (
        None, False,
        "Your dissent was recorded against the aggregator \u2014 it carries no number, so the "
        "score is unchanged at %(now)d/6 and every trait still reads as it was scored."),
    "dissent_over_correction": (
        None, False,
        "Your dissent was recorded against the aggregator \u2014 it carries no number, so the "
        "score is unchanged at %(now)d/6. Your trait correction still stands; it did not move "
        "the score off the one the AI gave."),
    "dissent_over_moving_correction": (
        "ai_holistic", False,
        "Your dissent was recorded against the aggregator \u2014 it carries no number, so the "
        "score above is unchanged at %(now)d/6. Your trait correction, which moved it from "
        "%(ai)d, still stands."),
}


def narration_state(essay):
    """Which row of SCORE_NARRATION this essay is in.

    The dimensions are independent and the table keeps them so: what the latest record WAS,
    whether it changed any trait, whether it moved the holistic, and whether the correction now
    standing has moved the holistic off the AI's. The last two are not the same question -- a
    second correction can add nothing while the first has already moved the score.
    """
    kind = essay["latest_record_kind"]
    if kind is None:
        return "untouched"
    if kind == "cleared":
        return "cleared"
    off_ai = essay["holistic"] != essay["ai_holistic"]
    if kind == "dissent":
        if not essay["overridden"]:
            return "dissent"
        return "dissent_over_moving_correction" if off_ai else "dissent_over_correction"
    if not essay["latest_record_changed_traits"]:
        return "reason_revised_off_ai" if off_ai else "reason_revised"
    if not essay["score_unchanged_by_latest_record"]:
        return "corrected_moved"
    return "corrected_inert_off_ai" if off_ai else "corrected_inert"


def score_narration(essay):
    """The head, the sentence and the panel's open state, decided together in one lookup."""
    state = narration_state(essay)
    contrast, panel, sentence = SCORE_NARRATION[state]
    was = essay[contrast] if contrast else None
    numbers = {"now": essay["holistic"], "ai": essay["ai_holistic"], "was": was}
    return {
        "state": state,
        "was": was,
        "opens_panel": panel,
        "sentence": sentence % numbers if sentence else None,
    }


def _plain_score(holistic, state):
    return ('<div class="score score-%s"><span class="score-value">%d</span>'
            '<span class="of">/6</span></div>' % (state.replace("_", "-"), holistic))


def _moved_score(was, holistic, state):
    return ('<div class="score corrected score-%s">'
            '<span class="score-was">%d</span><span class="score-arrow">\u2192</span>'
            '<span class="score-value">%d</span><span class="of">/6</span></div>'
            % (state.replace("_", "-"), was, holistic))


def score_line(essay):
    """The holistic, and what the teacher's last action did to it.

    Before and after are shown together rather than the after alone: a number that silently
    changed cannot be checked, and a number that silently did not change reads as a broken
    control. Which "before" that is depends on the state, so SCORE_NARRATION names it per row
    rather than any branch here choosing -- see the table for why that matters.

    The AI's own holistic stays on the page wherever a correction has moved the score off it,
    because that is the number the teacher is auditing against and it must not fall away because
    a later save had a nearer baseline to talk about. Where the head already contrasts against
    it, the head is where it appears; only where the head contrasts something else -- a second
    correction moving 2 to 3 -- does it need the labelled line, and the label is what stops the
    two numbers reading as one three-way contrast. Naming it in both places would state the same
    number twice inside a header a few lines tall.
    """
    told = score_narration(essay)
    holistic = essay["holistic"]
    head = (_moved_score(told["was"], holistic, told["state"]) if told["was"] is not None
            else _plain_score(holistic, told["state"]))
    ai = essay["ai_holistic"]
    if holistic != ai and told["was"] != ai:
        head += '<p class="score-origin">The AI scored this <b>%d</b>/6.</p>' % ai
    if told["sentence"] is None:
        return head
    quiet = "" if told["state"] == "corrected_moved" else " unchanged"
    return head + '<p class="score-change%s">%s</p>' % (quiet, told["sentence"])


def override_form(essay):
    """The teacher disagreeing, and the two shapes that disagreement can take.

    Trait scores are corrected on the cards above; this saves them together with a reason. A direct
    holistic override is deliberately not offered -- it cannot steer anything, and it would
    decouple the displayed score from the evidence displayed beside it (decisions_log.md ui_2).
    What stands in its place is a dissent: a rationale and no number.
    """
    clear = ('<button type="button" class="override-clear">Clear the trait correction</button>'
             if essay["overridden"] else "")
    rationale = html.escape(essay["override_rationale"] or "")

    if essay["dissent"]:
        said = html.escape(essay["dissent"]["rationale"] or "")
        dissent = (
            '<div class="dissent recorded">'
            '<h4 class="dissent-head">Score dissent recorded</h4>'
            '<p class="dissent-said">%s</p>'
            '<p class="dissent-note">Stored against the aggregator, with no number attached '
            '\u2014 %s Rewriting it below records a new dissent that supersedes this one; the '
            'record above is kept either way.</p>'
            '<textarea class="dissent-rationale" rows="2" '
            'placeholder="Why is the final score wrong?">%s</textarea>'
            '<button type="button" class="dissent-save">Replace dissent</button></div>'
            % (said, ("your trait corrections above still stand." if essay["overridden"]
                      else "the traits above still read as they were scored."), said)
        )
    else:
        dissent = (
            '<div class="dissent">'
            '<h4 class="dissent-head">Disagree with the final score itself?</h4>'
            '<p class="dissent-note">If the traits are right and the number they produce is not, '
            'that is a fact about the aggregator rather than about this essay. Record it as a '
            'reason with no number \u2014 typing a holistic directly would look responsive while '
            'quietly detaching the score from the evidence beside it.</p>'
            '<textarea class="dissent-rationale" rows="2" '
            'placeholder="Why is the final score wrong?"></textarea>'
            '<button type="button" class="dissent-save">Record dissent</button></div>'
        )

    trail = ""
    if essay["override_records"]:
        trail = ('<p class="override-trail">%d record%s for this essay. Nothing is '
                 'overwritten \u2014 each correction is appended, and what you see is the '
                 'latest trait correction together with the latest dissent.</p>'
                 % (essay["override_records"], "" if essay["override_records"] == 1 else "s"))

    return (
        '<section class="override" data-essay="%s">'
        '<h3 class="override-head">Your correction</h3>'
        '<p class="override-hint">Change any trait score above, then save. The holistic recomputes '
        'through the frozen aggregator \u2014 no coefficient moves and nothing is re-fitted.</p>'
        '<textarea class="override-rationale" rows="2" '
        'placeholder="Why? (optional)">%s</textarea>'
        '<div class="override-actions">'
        '<button type="button" class="override-save">Save correction</button>%s</div>'
        '<p class="override-status" role="status"></p>'
        '%s%s</section>'
        % (html.escape(essay["essay_id"]), rationale, clear, trail, dissent)
    )


def gold_block(essay, record=None, score=None):
    """The human rater's score: absent until asked for, and the asking goes on the record.

    Nothing about it reaches the browser until a reveal has been recorded — this is a leakage
    control, not a disclosure toggle, because a correction formed against the answer key would
    launder gold labels into a later steering bank (decisions_log.md ui_4). It says what it is: the
    CSV is on disk, and reading it there is neither prevented nor recorded.
    """
    if record is None:
        return (
            '<section class="gold" data-essay="%s">'
            '<h3 class="gold-head">Human rater’s score</h3>'
            '<p class="gold-note">Hidden so your own judgment forms first. Revealing it is '
            'recorded, and every correction you make to this essay afterwards is flagged '
            '<code>gold_revealed</code> — so corrections made with the answer key in view stay '
            'identifiable, and can be kept out of anything that later steers the model.</p>'
            '<button class="gold-reveal" type="button">Reveal the rater’s score</button>'
            '<p class="gold-caveat">A record, not a restriction: the score sits in '
            'personal_training_set.csv, and reading it there is neither prevented nor logged.</p>'
            '</section>' % html.escape(essay["essay_id"])
        )

    gap = score - essay["holistic"]
    comparison = ("same as this system’s" if gap == 0 else
                  "%d %s this system’s %d"
                  % (abs(gap), "above" if gap > 0 else "below", essay["holistic"]))
    return (
        '<section class="gold revealed" data-essay="%s" data-revealed="true">'
        '<h3 class="gold-head">Human rater’s score</h3>'
        '<p class="gold-value"><span class="gold-number">%d</span><span class="of">/6</span>'
        '<span class="gold-gap">%s</span></p>'
        '<p class="gold-note">Revealed %s. Corrections to this essay from here on carry '
        '<code>gold_revealed: true</code> in their record.</p></section>'
        % (html.escape(essay["essay_id"]), score, comparison,
           html.escape(_reveal_display(record["revealed_at"])))
    )


def legend():
    swatches = "".join(
        '<span class="key"><span class="swatch c-%s"></span>%s</span>' % (c, c.capitalize())
        for c in CARD_ORDER
    )
    return (
        '<div class="legend">%s'
        '<span class="key key-sep"><span class="swatch p-strength demo"></span>strength</span>'
        '<span class="key"><span class="swatch p-weakness demo"></span>weakness</span>'
        '</div>' % swatches
    )


def review_page(essay):
    spans = all_spans(essay["criteria"])
    cards = "".join(criterion_card(n, essay["criteria"][n]) for n in CARD_ORDER)

    # Read at render time rather than joined into the artifact: the artifact is what /api/review
    # serves, and the rater's score must not be in it.
    record = next((r for r in gold.load_reveals() if r["essay_id"] == essay["essay_id"]), None)
    revealed = gold_block(essay, record,
                          gold.gold_score(essay["essay_id"]) if record else None)
    return page(
        "Review %s" % essay["essay_id"],
        '<header class="topbar"><a class="back" href="/">← all essays</a>'
        '<span class="essay-id">%s</span>'
        '<span class="wc">%d words</span></header>'
        '<main class="review">'
        '  <article class="response-pane">'
        '    <h2 class="label">Instructions</h2>'
        '    <p class="no-prompt">This corpus does not include the task prompt — the released '
        'data is essay text and score only, so there are no instructions to show here.</p>'
        '    <h2 class="label">Response</h2>'
        '    <div class="response">%s</div>'
        '  </article>'
        '  <aside class="assessment-pane">'
        '    %s'
        '    %s'
        '    <h3 class="overview-label">Overview</h3>'
        '    <p class="overview">%s</p>'
        '    %s'
        '    <p class="pin-hint">Hover a trait to see only its evidence · click to pin '
        '· Esc to release</p>'
        '    %s'
        '    %s'
        '    %s'
        '  </aside>'
        '</main>'
        % (html.escape(essay["essay_id"]), essay["word_count"],
           response_html(essay["text"], spans), score_line(essay),
           formation_panel(essay), html.escape(essay["overview"]), legend(), cards,
           override_form(essay), revealed)
    )


def _index_status(essay):
    """What a teacher has done to this essay, in the words that distinguish the cases.

    `reviewed` and `overridden` are different questions: a cleared correction and a dissent are
    both visits that left the trait scores exactly as the AI wrote them.
    """
    marks = []
    if essay["overridden"]:
        moved = essay["holistic"] != essay["ai_holistic"]
        marks.append("corrected %d\u2009\u2192\u2009%d" % (essay["ai_holistic"], essay["holistic"])
                     if moved else "corrected, same score")
    if essay["dissent"]:
        marks.append("dissent")
    if not marks:
        marks.append("reviewed" if essay["reviewed"] else "\u2014")
    return " \u00b7 ".join(marks)


def index_page(data):
    rows = "".join(
        '<tr><td><a href="/essay/%s">%s</a></td><td class="num">%d</td>'
        '<td class="num">%d</td><td class="num">%d</td><td class="status%s">%s</td></tr>'
        % (e["essay_id"], e["essay_id"], e["holistic"], e["word_count"],
           sum(len(c["spans"]) for c in e["criteria"].values()),
           "" if not e["reviewed"] else " status-touched", _index_status(e))
        for e in data["essays"]
    )
    note = "" if data["complete"] else (
        '<p class="partial">Showing %d of %d essays in the frozen sample — the rest are not '
        'annotated yet.</p>' % (len(data["essays"]), len(data["essays_in_manifest"])))
    return page(
        "Teacher review",
        '<header class="topbar"><span class="essay-id">Teacher review</span>'
        '<span class="wc">%s · %s</span></header>'
        '<main class="index"><h1>Essays</h1>%s'
        '<table class="essay-table"><thead><tr><th>Essay</th><th class="num">Score</th>'
        '<th class="num">Words</th><th class="num">Spans</th><th>Status</th></tr></thead>'
        '<tbody>%s</tbody></table></main>'
        % (data["ladder_version"], data["trait_run"], note, rows)
    )


# --------------------------------------------------------------------------------------------
# routes
# --------------------------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
def index():
    return index_page(artifact())


@app.get("/essay/{essay_id}", response_class=HTMLResponse)
def essay_page(essay_id: str):
    return review_page(find(essay_id))


@app.get("/api/review/{essay_id}")
def review_json(essay_id: str):
    return find(essay_id)


@app.get("/api/review")
def review_all():
    return artifact()


@app.post("/api/override/{essay_id}")
def record_override(essay_id: str, body: dict = Body(default_factory=dict)):
    """Record one correction and return the essay as it now stands.

    The record is written through `overrides.record_correction`, which obtains the recomputed
    holistic by running the build that would result from storing it -- so what is recorded is what
    the frozen aggregator actually produces, not a number this handler worked out. The teacher
    corrects traits; a dissent carries a rationale and no number; clearing withdraws a correction
    without erasing the record that it was made.

    The review set is checked against `annotated_ids()` rather than by building the artifact and
    looking for the essay in it: `find()` searches an artifact built over exactly those ids, so
    the answer is the same, and ui_13 defends the two builds that produce the recomputed holistic
    rather than a third that only answers a membership question.
    """
    ids = annotated_ids()
    if essay_id not in ids:
        raise HTTPException(status_code=404, detail="no review for essay %s" % essay_id)
    kind = body.get("kind", "trait_correction")
    try:
        record, essay = overrides.record_correction(
            essay_id,
            kind=kind,
            corrected_traits=body.get("corrected_traits"),
            rationale=body.get("rationale"),
            gold_revealed=gold.was_revealed(essay_id),
            expected_ids=ids,
        )
    except OverrideError as exc:
        # The guards name the essay and the offending value; handing that text back is more use
        # than a bare 400, and it is the same message the command line would print.
        raise HTTPException(status_code=400, detail=str(exc))
    return {"record": record, "essay": essay}


@app.post("/api/gold/{essay_id}")
def reveal_gold(essay_id: str):
    """Disclose the human rater's score for one essay, and put the disclosure on the record.

    POST rather than GET because it changes state: it writes the ledger entry ticket 05 reads to
    stamp `gold_revealed` on later corrections. `find()` runs first, so this cannot be used to read
    the answer key of an essay outside the review set.
    """
    essay = find(essay_id)
    record, is_new = gold.record_reveal(essay_id)
    return {
        "essay_id": essay_id,
        "gold_score": gold.gold_score(essay_id),
        "holistic": essay["holistic"],
        "revealed_at": record["revealed_at"],
        "revealed_display": _reveal_display(record["revealed_at"]),
        "already_revealed": not is_new,
    }


def preflight(stream=sys.stderr):
    """Build the artifact once before serving. Returns it, or None with the reason printed.

    A broken annotation batch, or a hand-edited override record, should fail at the command line
    where the message can be read and acted on, not as a 500 in a browser. This is the same stance
    the pipeline's --assemble and --derive take: validate up front, fail loudly, say which essay.
    The ledger is diffable and hand-editable on purpose, so the guard that names the offending
    value has to reach the person who edited it.
    """
    ids = annotated_ids()
    if not ids:
        print("No annotation found in %s\n" % ANNOTATION_DIR, file=stream)
        print("Annotate essays against annotation_instrument_ui_v1.md into that directory first, "
              "then run this again.", file=stream)
        return None
    try:
        return build_review(override_records=load_overrides(), expected_ids=ids)
    except AnnotationError as exc:
        print("Annotation is not usable — fix these, then run this again:\n", file=stream)
        print(str(exc), file=stream)
        return None
    except OverrideError as exc:
        print("%s is not usable — fix these, then run this again:\n" % OVERRIDES_FILE,
              file=stream)
        print(str(exc), file=stream)
        return None


def _banner(data, host, port):
    spans = sum(len(c["spans"]) for e in data["essays"] for c in e["criteria"].values())
    n = len(data["essays"])
    lines = [
        "",
        "  Teacher review UI · %s · trait run %s" % (data["ladder_version"], data["trait_run"]),
        "  %d essay%s, %d cited passage%s%s"
        % (n, "" if n == 1 else "s", spans, "" if spans == 1 else "s",
           "" if data["complete"]
           else "  (%d of %d in the frozen sample annotated so far)"
                % (n, len(data["essays_in_manifest"]))),
        "",
        "      http://%s:%d" % (host, port),
        "",
        "  Essays: " + ", ".join(e["essay_id"] for e in data["essays"]),
        "  Ctrl-C to stop.",
        "",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    import argparse
    import socket

    import uvicorn

    parser = argparse.ArgumentParser(description="Serve the teacher review UI locally.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", "8000")))
    options = parser.parse_args()

    ready = preflight()
    if ready is None:
        sys.exit(1)

    probe = socket.socket()
    probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        probe.bind((options.host, options.port))
    except OSError:
        print("\n  Port %d is already in use — something else is listening there." % options.port,
              file=sys.stderr)
        print("  Try:  python3 app.py --port %d\n" % (options.port + 1), file=sys.stderr)
        sys.exit(1)
    finally:
        probe.close()

    print(_banner(ready, options.host, options.port), flush=True)
    uvicorn.run(app, host=options.host, port=options.port, log_level="info")
