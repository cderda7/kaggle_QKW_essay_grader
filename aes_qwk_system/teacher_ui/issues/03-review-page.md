# 03: The review page

**What to build:** The thing a teacher actually looks at. One command starts a local app; an essay
list leads to a review page showing the student's full response on the left with the AI's evidence
highlighted in place, and on the right the score, an overview paragraph, and one card per trait
containing student-facing feedback. Highlights are coloured to match the card they belong to, so
every claim in the feedback is one glance from the text that produced it.

**This is the milestone where the layout gets seen and reacted to.** The reference mock sets the
structure and information hierarchy — response left, score and overview and cards right, highlights
colour-matched — and that structure is the requirement. Exact spacing, hues and typography are not:
the mock comes from a different marking scheme, so matching it precisely is not coherent for a 1–6
four-trait rubric. Build the structure, fix what looks genuinely broken, and let it be reacted to
rather than pre-emptively polished.

Colour carries criterion; polarity is a separate channel so it survives whatever hue it lands on and
so meaning never rests on colour alone.

**Blocked by:** 02.

**Status:** ready-for-agent

- [x] One command starts the app against local files, with no additional infrastructure and no model API call
- [x] An essay list shows every essay in the artifact with its score and whether it has been reviewed
- [x] The review page shows the response on the left and, on the right, the holistic as `N/6`, the overview paragraph, and four trait cards ordered by weight with argumentation first, each showing its own 1–6 score
- [x] ~~The essay's prompt or instructions appear above the response, collapsed when long~~ **Amended: this corpus has no prompt.** `personal_training_set.csv` and the upstream `train.csv` both carry only `essay_id, full_text, score` — the task prompt is not distributed with this data. The layout slot is kept and states plainly that the prompt is unavailable. Neither an invented prompt nor the trait grader's *hypothesised* prompt (recorded in `evidence_notes`) is shown: presenting a model's guess under an "Instructions" heading would be a fabrication displayed as source material, which is the failure the span guards exist to prevent. Restore the real behaviour when a rubric that ships prompts is used.
- [x] Spans render inline within the response, coloured by criterion to match the card headers
- [x] Polarity is distinguishable without relying on colour
- [x] Hovering a trait card emphasises that trait's spans and mutes the rest; hovering a span identifies which card cited it
- [x] Overlapping spans render legibly rather than as unreadable striping
- [x] A trait with no citable evidence renders its stated reason, so the absence reads as a finding rather than an empty card
- [x] The page is readable at a normal laptop width and the body never scrolls horizontally

## Closing note

`python3 app.py` serves the review UI at `http://127.0.0.1:8000` — local files only, no model call,
no database. **98 tests** passing across the suite (34 new: rendering, overlap, and the served pages).

### Decisions taken while building

**No Jinja2.** The installed jinja2 is 2.11, which predates what Starlette 0.49's `Jinja2Templates`
requires. HTML is rendered in Python instead of upgrading a shared dependency to serve one page.
Zero new dependencies were added.

**Rendering is by segment, not by span.** The response is cut at every span boundary *and* every
paragraph boundary, and each segment carries the full set of spans covering it. This is what makes
overlap work: a phrase cited by two traits is one element carrying both, so it responds to either
card on hover, and a span crossing a blank line becomes two marks in two paragraphs rather than a
`<mark>` containing a `</p>`. Mutation-tested — removing paragraph cuts, keeping only the first
covering span, picking the innermost span as primary, dropping escaping, or never applying the
multi-cited class each makes the suite fail.

**The artifact is rebuilt on every request** rather than read from `review_ui_v1.json`, because
override records are an input to the build (ui_6). At three essays this is free, and it means every
guard runs on the path a page load takes. Ticket 05 needs no rewiring.

### What it looks like

Colour carries criterion and matches the card headers; polarity is a separate channel (solid fill for
a strength, dotted underline for a weakness) so meaning never rests on hue alone. A passage cited by
two traits gets bracket marks rather than a second fill. Hovering a card emphasises its passages and
mutes the rest; hovering a passage lights up the card(s) that cited it and names the direction in a
tooltip. Cards are keyboard-focusable and the same linking fires on focus.

`0105e2e` renders exactly the problem ticket 04 exists to solve: four trait cards reading 4, 4, 4 and
3 — the strongest traits of the three essays — above a headline **2/6**, with nothing on the page
explaining that the response is 159 words. Right now that page looks like a bug. It is not; it is the
aggregator, and until the score-formation panel lands the UI is actively misleading on this essay.
