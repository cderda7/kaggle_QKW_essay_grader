"""Turn a response plus its resolved spans into HTML the browser can highlight.

The hard part is overlap. Two traits can legitimately cite the same sentence, and forbidding that
would force the annotator into an arbitrary choice the teacher cannot see (decisions_log.md ui_v1
spec). So this renders by SEGMENT rather than by span: the text is cut at every span boundary and
every paragraph boundary, and each resulting segment knows the full set of spans covering it. A
segment covered by two criteria is one element carrying both, which keeps the HTML well-formed no
matter how spans nest, and lets hover light up every criterion that cited a given phrase.

Paragraph boundaries are cut points too, so a span crossing a blank line becomes two marks in two
paragraphs rather than a <mark> containing a </p>.
"""

import html
import re

PARAGRAPH_SPLIT = re.compile(r"\n[ \t]*\n+")


def paragraph_ranges(text):
    """[(start, end)] of each paragraph, excluding the blank lines between them."""
    ranges, pos = [], 0
    for m in PARAGRAPH_SPLIT.finditer(text):
        if m.start() > pos:
            ranges.append((pos, m.start()))
        pos = m.end()
    if pos < len(text):
        ranges.append((pos, len(text)))
    return ranges or [(0, len(text))]


def primary(spans):
    """The span whose fill wins on a segment: the outermost one, earliest start then longest."""
    return min(spans, key=lambda s: (s["start"], -s["end"]))


def segment(text, spans):
    """Cut `text` at every span and paragraph boundary; each segment lists the spans covering it."""
    paragraphs = paragraph_ranges(text)
    cuts = set()
    for a, b in paragraphs:
        cuts.add(a)
        cuts.add(b)
    for s in spans:
        cuts.add(s["start"])
        cuts.add(s["end"])

    out = []
    for index, (pa, pb) in enumerate(paragraphs):
        points = sorted(c for c in cuts if pa <= c <= pb)
        for a, b in zip(points, points[1:]):
            if a >= b:
                continue
            active = [s for s in spans if s["start"] <= a and s["end"] >= b]
            out.append({
                "paragraph": index,
                "start": a,
                "end": b,
                "text": text[a:b],
                "spans": active,
            })
    return out


def response_html(text, spans):
    """The student's response as paragraphs, with every cited stretch marked up."""
    by_paragraph = {}
    for seg in segment(text, spans):
        by_paragraph.setdefault(seg["paragraph"], []).append(seg)

    parts = []
    for index in sorted(by_paragraph):
        parts.append('<p class="response-para">')
        for seg in by_paragraph[index]:
            body = html.escape(seg["text"]).replace("\n", "<br>")
            if not seg["spans"]:
                parts.append(body)
                continue
            lead = primary(seg["spans"])
            criteria = sorted({s["criterion"] for s in seg["spans"]})
            classes = ["hl", "c-" + lead["criterion"], "p-" + lead["polarity"]]
            if len(criteria) > 1:
                classes.append("hl-multi")
            label = "; ".join(
                "%s — %s" % (s["criterion"], s["polarity"])
                for s in sorted(seg["spans"], key=lambda s: s["criterion"])
            )
            parts.append(
                '<mark class="%s" data-criteria="%s" title="%s">%s</mark>'
                % (" ".join(classes), " ".join(criteria), html.escape(label), body)
            )
        parts.append("</p>")
    return "".join(parts)


def all_spans(criteria):
    """Flatten an artifact essay's criteria into one span list, tagged with its criterion."""
    spans = []
    for name, crit in criteria.items():
        for s in crit["spans"]:
            span = dict(s)
            span["criterion"] = name
            spans.append(span)
    return sorted(spans, key=lambda s: (s["start"], -s["end"]))
