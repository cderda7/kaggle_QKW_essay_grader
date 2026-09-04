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

import glob
import html
import json
import os
import sys

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from build_review import (ANNOTATION_DIR, CRITERIA, AnnotationError, build_review,  # noqa: E402
                          load_overrides)
from render import all_spans, response_html  # noqa: E402

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
    except AnnotationError as exc:
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
    return (
        '<section class="card c-%s" data-criterion="%s" tabindex="0">'
        '<header class="card-head"><h3>%s</h3>'
        '<span class="card-score">%s<span class="of">/6</span></span></header>'
        '<p class="card-weight">weight %.2f</p>'
        '<p class="card-comment">%s</p>%s</section>'
        % (name, name, name.capitalize(), crit["trait_score"],
           TRAIT_WEIGHTS[name], html.escape(crit["comment"]), evidence)
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
    return page(
        "Review %s" % essay["essay_id"],
        '<header class="topbar"><a class="back" href="/">← all essays</a>'
        '<span class="essay-id">%s</span>'
        '<span class="wc">%d words</span></header>'
        '<main class="review">'
        '  <article class="response-pane">'
        '    <h2 class="label">Instructions</h2>'
        '    <p class="no-prompt">This corpus does not include the task prompt — the released data '
        'is essay text and score only, so there are no instructions to show here.</p>'
        '    <h2 class="label">Response</h2>'
        '    <div class="response">%s</div>'
        '  </article>'
        '  <aside class="assessment-pane">'
        '    <div class="score"><span class="score-value">%d</span><span class="of">/6</span></div>'
        '    <h3 class="overview-label">Overview</h3>'
        '    <p class="overview">%s</p>'
        '    %s'
        '    <p class="pin-hint">Hover a trait to see only its evidence · click to pin '
        '· Esc to release</p>'
        '    %s'
        '  </aside>'
        '</main>'
        % (html.escape(essay["essay_id"]), essay["word_count"],
           response_html(essay["text"], spans), essay["holistic"],
           html.escape(essay["overview"]), legend(), cards)
    )


def index_page(data):
    rows = "".join(
        '<tr><td><a href="/essay/%s">%s</a></td><td class="num">%d</td>'
        '<td class="num">%d</td><td class="num">%d</td><td>%s</td></tr>'
        % (e["essay_id"], e["essay_id"], e["holistic"], e["word_count"],
           sum(len(c["spans"]) for c in e["criteria"].values()),
           "reviewed" if e["overridden"] else "—")
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


def preflight(stream=sys.stderr):
    """Build the artifact once before serving. Returns it, or None with the reason printed.

    A broken annotation batch should fail at the command line where the message can be read and
    acted on, not as a 500 in a browser. This is the same stance the pipeline's --assemble and
    --derive take: validate up front, fail loudly, say which essay.
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
