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

- [ ] One command starts the app against local files, with no additional infrastructure and no model API call
- [ ] An essay list shows every essay in the artifact with its score and whether it has been reviewed
- [ ] The review page shows the response on the left and, on the right, the holistic as `N/6`, the overview paragraph, and four trait cards ordered by weight with argumentation first, each showing its own 1–6 score
- [ ] The essay's prompt or instructions appear above the response, collapsed when long
- [ ] Spans render inline within the response, coloured by criterion to match the card headers
- [ ] Polarity is distinguishable without relying on colour
- [ ] Hovering a trait card emphasises that trait's spans and mutes the rest; hovering a span identifies which card cited it
- [ ] Overlapping spans render legibly rather than as unreadable striping
- [ ] A trait with no citable evidence renders its stated reason, so the absence reads as a finding rather than an empty card
- [ ] The page is readable at a normal laptop width and the body never scrolls horizontally
