"""Locate annotator-supplied quotes in the essay they came from.

The annotation pass emits a verbatim quote plus which occurrence of it it means; this module turns
that into a `[start, end)` character range in the ORIGINAL essay text. Models cannot count
characters, so an offset a model emits directly is silently wrong -- and a silently misplaced
highlight is the worst failure available in a review UI, because it looks authoritative to the
teacher whose trust the feature exists to earn. A quote either matches or it fails loudly.

Matching runs on a whitespace-normalised projection of both strings, because real student text
contains irregular spacing and line breaks that a model will not reproduce faithfully when quoting,
and because a model's own output is routinely re-wrapped. Typographic substitutions (curly quotes,
en/em dashes, ellipses) are folded for the same reason: they are the difference between what a
student typed and what a model emits when quoting it, and they are never a meaningful difference.

Case, spelling and punctuation are NOT folded. The instrument tells the annotator never to correct
the student's text inside a quote, and silently accepting a corrected quote would defeat the check.
"""

# Typographic folds applied to both essay and quote before matching. Each maps to a single ASCII
# character so the index map stays 1:1 with the source string.
_FOLD = {
    "‘": "'", "’": "'", "‚": "'", "‛": "'",
    "“": '"', "”": '"', "„": '"', "‟": '"',
    "–": "-", "—": "-", "‒": "-", "−": "-",
    " ": " ", " ": " ", " ": " ",
}


class AnchorError(ValueError):
    """A quote could not be located. Carries enough context to fix the annotation."""


def _normalize(s):
    """Return (normalised text, index map) where map[i] is the source index of normalised char i.

    Runs of whitespace collapse to a single space; leading and trailing whitespace is dropped. The
    index map is what lets a match found in normalised space be reported against the original
    string, so highlights land on the text the student actually wrote.
    """
    out, idx = [], []
    prev_space = True  # True at the start so leading whitespace is dropped
    for i, ch in enumerate(s):
        ch = _FOLD.get(ch, ch)
        if ch.isspace():
            if prev_space:
                continue
            out.append(" ")
            idx.append(i)
            prev_space = True
        else:
            out.append(ch)
            idx.append(i)
            prev_space = False
    while out and out[-1] == " ":
        out.pop()
        idx.pop()
    return "".join(out), idx


def _find_all(haystack, needle):
    starts, i = [], haystack.find(needle)
    while i != -1:
        starts.append(i)
        i = haystack.find(needle, i + 1)
    return starts


def anchor(essay_text, quote, occurrence=1, *, essay_id=None, criterion=None):
    """Locate `quote` in `essay_text`, returning (start, end) into the ORIGINAL string.

    Raises AnchorError if the quote does not occur, or if `occurrence` exceeds the number of
    matches. Both are hard failures: there is no sensible partial answer, and guessing would put a
    highlight on text the annotator never cited.
    """
    where = " ".join(p for p in (
        f"essay {essay_id}" if essay_id else "",
        f"criterion {criterion}" if criterion else "",
    ) if p) or "quote"

    norm_essay, idx_map = _normalize(essay_text)
    norm_quote, _ = _normalize(quote)

    if not norm_quote:
        raise AnchorError(f"{where}: empty quote")

    starts = _find_all(norm_essay, norm_quote)
    if not starts:
        raise AnchorError(
            f"{where}: quote not found in the response.\n"
            f"    quote: {quote!r}\n"
            f"    The annotator must copy the student's text exactly, including its spelling and "
            f"punctuation. Check for a silently corrected typo."
        )
    if occurrence < 1:
        raise AnchorError(f"{where}: occurrence must be >= 1, got {occurrence}")
    if occurrence > len(starts):
        raise AnchorError(
            f"{where}: occurrence {occurrence} requested but the quote appears "
            f"{len(starts)} time(s).\n    quote: {quote!r}"
        )

    s = starts[occurrence - 1]
    e = s + len(norm_quote) - 1
    return idx_map[s], idx_map[e] + 1


def resolve_spans(essay_text, criteria, essay_id=None):
    """Anchor every span in an annotation object's `criteria`. Returns a flat list of spans.

    Collects every failure before raising, so one run reports all the bad quotes in an essay rather
    than making the annotator fix them one at a time.
    """
    resolved, problems = [], []
    for name, crit in criteria.items():
        for i, span in enumerate(crit.get("spans") or []):
            try:
                start, end = anchor(
                    essay_text, span["quote"], span.get("occurrence", 1),
                    essay_id=essay_id, criterion=f"{name}[{i}]",
                )
            except AnchorError as exc:
                problems.append(str(exc))
                continue
            resolved.append({
                "criterion": name,
                "polarity": span["polarity"],
                "quote": span["quote"],
                "occurrence": span.get("occurrence", 1),
                "start": start,
                "end": end,
                "resolved_text": essay_text[start:end],
            })
    if problems:
        raise AnchorError(
            f"{len(problems)} span(s) could not be anchored:\n  " + "\n  ".join(problems)
        )
    return sorted(resolved, key=lambda s: (s["start"], -s["end"]))
