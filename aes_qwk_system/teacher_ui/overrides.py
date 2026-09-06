"""Writing the teacher's disagreement down.

`build_review` owns reading `overrides.json` and folding it into review state; this module owns
putting a record into it. The split matters because override records are an INPUT to the build
(teacher_ui/decisions_log.md ui_6) -- so the recomputed holistic a record carries must come from
the build itself, not from a second calculation performed here. `record_correction` therefore
builds the artifact twice, once without the prospective record and once with it, and stores what
the real seam produced. Two implementations of a fitted map eventually disagree; this one has none.

The file is append-only. Nothing here mutates or removes a record: withdrawing a correction is
itself a record (`kind="cleared"`), so a teacher who changes their mind twice leaves a trail rather
than a revision.
"""

import datetime
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import build_review  # noqa: E402


def _now():
    return datetime.datetime.now().astimezone().isoformat(timespec="seconds")


def _essay(artifact, essay_id):
    for essay in artifact["essays"]:
        if essay["essay_id"] == essay_id:
            return essay
    raise KeyError("no review for essay %s" % essay_id)


def append(record, path=None):
    """Append one validated record to the ledger.

    The path resolves at call time and through `build_review`, which is the one binding that owns
    it: a second copy here could be redirected on its own and leave this module appending to the
    committed audit record while the app read a temp one.

    The whole list is rewritten, so the swap is made atomic with a sibling temp file and
    `os.replace`. Truncating the real file first would put the entire append-only record, not just
    the record being added, inside the window between truncation and a completed write.
    """
    path = build_review.OVERRIDES_FILE if path is None else path
    records = build_review.load_overrides(path)
    build_review.check_override_records(records + [record])
    records.append(record)
    pending = path + ".pending"
    try:
        with open(pending, "w") as f:
            json.dump(records, f, indent=2, ensure_ascii=False)
            f.write("\n")
        os.replace(pending, path)
    except BaseException:
        if os.path.exists(pending):
            os.remove(pending)
        raise
    return record


def record_correction(essay_id, kind="trait_correction", corrected_traits=None, rationale=None,
                      gold_revealed=False, path=None, build=None, now=None, **build_kwargs):
    """Record one correction event and return (record, essay_after).

    The record carries what the correction was made against as well as what it changed: the AI's
    own trait scores and holistic, the recomputed holistic, the rationale, whether the answer key
    had been revealed first, and the trait run and aggregator the numbers belong to. That last
    pair is what stops a correction made against `v6_runB` traits being silently reused against
    different ones.

    Two baselines are kept apart rather than conflated, because this ledger is read by hand.
    `original_traits` and `ai_holistic` are what the AI itself produced; `original_holistic` is the
    score standing at the instant this record was made, which for a dissent or a withdrawal
    recorded after a correction is the corrected score, not the AI's. `score_unchanged` is
    measured against that same standing score, so it states what THIS record did -- a record that
    credited itself with an earlier correction's movement would be worse than one making no claim.

    The incoming values are checked before anything coerces them, so a malformed trait score names
    itself through the guard a hand-edited ledger would hit rather than raising a TypeError at the
    coercion and reaching the caller as an unexplained crash.
    """
    path = build_review.OVERRIDES_FILE if path is None else path
    build = build_review.build_review if build is None else build

    existing = build_review.load_overrides(path)
    build_review.check_override_records(existing + [{
        "essay_id": essay_id,
        "kind": kind,
        "corrected_traits": corrected_traits or None,
        "rationale": rationale,
    }])
    before = _essay(build(override_records=existing, **build_kwargs), essay_id)

    record = {
        "essay_id": essay_id,
        "kind": kind,
        "recorded_at": now if now is not None else _now(),
        "original_traits": dict(before["ai_traits"]),
        "corrected_traits": {k: int(v) for k, v in (corrected_traits or {}).items()} or None,
        "original_holistic": before["holistic"],
        "ai_holistic": before["ai_holistic"],
        "rationale": (rationale or "").strip() or None,
        "gold_revealed": bool(gold_revealed),
        "ladder_version": build_review.LADDER_VERSION,
        "trait_run": build_review.TRAIT_RUN,
        "aggregator": os.path.basename(build_review.AGGREGATOR_FILE),
    }
    if record["corrected_traits"] is None:
        del record["corrected_traits"]

    # The recomputed holistic is whatever the frozen aggregator produces for this record, obtained
    # by running the build that would result from storing it -- never by recomputing it here.
    after = _essay(build(override_records=existing + [record], **build_kwargs), essay_id)
    record["recomputed_holistic"] = after["holistic"]
    record["score_unchanged"] = after["holistic"] == before["holistic"]

    append(record, path)
    return record, after
