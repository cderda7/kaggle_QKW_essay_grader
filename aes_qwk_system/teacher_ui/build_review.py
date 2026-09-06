"""Join graded predictions, annotation batches, essay text and override records into one artifact.

This is the single seam the teacher review UI rests on. Override records are an INPUT here rather
than a mutation applied downstream, which puts span anchoring, batch validation, the join, holistic
recomputation and override application all below one testable boundary and leaves the HTTP layer
with no logic worth testing. If that boundary erodes -- if override application drifts into a
request handler, or anchoring gets called from a template -- the test suite loses most of its value.
See teacher_ui/decisions_log.md ui_6.

Every guard below is a HARD error, and they are collected rather than raised one at a time so a bad
batch is fixed in one pass. This follows the stance the pipeline already takes in `load_triage()`
and `check_v4_fidelity()`: a partially-usable annotation run is not a thing.

The gold score is never read into the artifact. It lives in the source CSV beside the essay text and
is deliberately left there -- teacher_ui/decisions_log.md ui_4.

    python3 build_review.py [--essays a,b,c] [--out review_ui_v1.json]
"""

import argparse
import csv
import glob
import json
import math
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "grading"))

from anchor import AnchorError, resolve_spans          # noqa: E402
from grade_essays import (V4_WEIGHTS, aggregator_features,  # noqa: E402
                          apply_aggregator)

LADDER_VERSION = "ui_v1"
TRAIT_RUN = "v6_runB"

MANIFEST = os.path.join(HERE, "essays_ui_v1.json")
ANNOTATION_DIR = os.path.join(HERE, "annotation_v6_runB")
PREDICTIONS_CSV = os.path.join(HERE, "..", "grading", "predictions_v9.csv")
AGGREGATOR_FILE = os.path.join(HERE, "..", "aggregator_v9.json")
# Overridable for the same reason the corpus path and the reveal ledger are: an end-to-end pass,
# or a test, has to be able to record a correction without writing into the committed audit record.
OVERRIDES_FILE = os.environ.get("TEACHER_UI_OVERRIDES_FILE",
                                os.path.join(HERE, "overrides.json"))
SOURCE_CSV = os.environ.get("PERSONAL_TRAINING_SET_CSV",
                            os.path.join(HERE, "..", "..", "personal_training_set.csv"))
DEFAULT_OUT = os.path.join(HERE, "review_ui_v1.json")

CRITERIA = ("argumentation", "organization", "development", "conventions")
POLARITIES = ("strength", "weakness")

# A record says what kind of disagreement it is. `trait_correction` changes scores; `dissent` says
# the final score is wrong while the traits are not, and carries a rationale and no number;
# `cleared` withdraws a trait correction without erasing the fact that it was made.
OVERRIDE_KINDS = ("trait_correction", "dissent", "cleared")
DEFAULT_OVERRIDE_KIND = "trait_correction"
MIN_TRAIT, MAX_TRAIT = 1, 6

MIN_QUOTE_WORDS = 3
MAX_SPANS_PER_CRITERION = 4
MAX_SPAN_FRACTION = 0.25

ITEM_KEYS = {"essay_id", "overview", "criteria"}
CRITERION_KEYS = {"comment", "spans", "no_evidence_reason"}
SPAN_KEYS = {"quote", "occurrence", "polarity"}

# Fields whose presence means the annotator was asked for, or improvised, something it does not own.
# The scores belong to the grading pipeline; the annotator explains them.
FORBIDDEN_FIELDS = ("holistic_score", "score", "human_score", "SCORES", "gate_applied",
                    "triage_label") + CRITERIA

# Prose that states or alludes to the number already on screen. The overview exists to say something
# the number cannot; restating it turns the paragraph into a defence of a score. ui_v1 spec, and the
# instrument's "never state the numeric score in prose" rule.
GRADE_LANGUAGE = re.compile(
    r"\b[1-6]\s*/\s*6\b"
    r"|\bout of\s+(?:six|6)\b"
    r"|\b(?:score[sd]?|scoring|grade[sd]?|grading|mark(?:s|ed)?|marking|band|rubric|"
    r"criteri(?:on|a)|trait[s]?)\b",
    re.IGNORECASE,
)


class AnnotationError(ValueError):
    """One or more annotation batches are not usable. Lists every problem found."""


class OverrideError(ValueError):
    """One or more override records are not usable. Lists every problem found."""


# --------------------------------------------------------------------------------------------
# loading
# --------------------------------------------------------------------------------------------

def load_manifest(path=MANIFEST):
    with open(path) as f:
        return json.load(f)


def load_essays(source_csv=SOURCE_CSV):
    """essay_id -> full_text. The `score` column is deliberately not read (ui_4)."""
    with open(source_csv, newline="", encoding="utf-8") as f:
        return {r["essay_id"]: r["full_text"] for r in csv.DictReader(f)}


def load_predictions(path=PREDICTIONS_CSV):
    with open(path, newline="") as f:
        return {r["essay_id"]: r for r in csv.DictReader(f)}


def load_overrides(path=None):
    """Append-only record list. Missing file means nothing has been corrected yet.

    The path resolves at call time, not at import time: a default bound when this module was first
    imported cannot be redirected afterwards, which would silently point every caller at the
    committed ledger no matter what they asked for.
    """
    path = OVERRIDES_FILE if path is None else path
    if not os.path.exists(path):
        return []
    with open(path) as f:
        return json.load(f)


def _word_count(s):
    return len(s.split())


# --------------------------------------------------------------------------------------------
# guards
# --------------------------------------------------------------------------------------------

def _check_span(span, essay_text, essay_id, criterion, index, problems):
    where = "%s %s[%d]" % (essay_id, criterion, index)

    unknown = sorted(set(span) - SPAN_KEYS)
    if unknown:
        problems.append("%s: unknown span field(s) %s" % (where, unknown))
    if "quote" not in span:
        problems.append("%s: span has no quote" % where)
        return
    if span.get("polarity") not in POLARITIES:
        problems.append("%s: polarity=%r is not one of %s -- every span must say whether it is "
                        "evidence of a strength or a weakness"
                        % (where, span.get("polarity"), list(POLARITIES)))

    words = _word_count(span["quote"])
    if words < MIN_QUOTE_WORDS:
        problems.append("%s: quote is %d word(s), minimum is %d -- a shorter quote appears in too "
                        "many places to be meaningful as a highlight: %r"
                        % (where, words, MIN_QUOTE_WORDS, span["quote"]))

    limit = MAX_SPAN_FRACTION * _word_count(essay_text)
    if words > limit:
        problems.append("%s: quote is %d words, more than %.0f%% of the %d-word response (limit "
                        "%.0f) -- quote the sentence that carries the point, not the paragraph"
                        % (where, words, 100 * MAX_SPAN_FRACTION, _word_count(essay_text), limit))


def _check_item(item, essays, problems):
    eid = item.get("essay_id")
    if not eid:
        problems.append("an annotation object has no essay_id")
        return
    if eid not in essays:
        problems.append("%s: annotated but not present in the source corpus" % eid)
        return
    text = essays[eid]

    unknown = sorted(set(item) - ITEM_KEYS)
    if unknown:
        forbidden = [k for k in unknown if k in FORBIDDEN_FIELDS]
        if forbidden:
            problems.append("%s: carries field(s) the annotator was never asked for: %s -- the "
                            "scores are owned by the grading pipeline, not the annotation pass"
                            % (eid, forbidden))
        rest = [k for k in unknown if k not in FORBIDDEN_FIELDS]
        if rest:
            problems.append("%s: unknown field(s) %s" % (eid, rest))

    overview = (item.get("overview") or "").strip()
    if not overview:
        problems.append("%s: overview is missing or empty" % eid)
    else:
        hit = GRADE_LANGUAGE.search(overview)
        if hit:
            problems.append("%s: overview names the grade (%r) -- the teacher can already see "
                            "the number; the overview exists to say what it cannot"
                            % (eid, hit.group(0)))

    criteria = item.get("criteria")
    if not isinstance(criteria, dict):
        problems.append("%s: criteria is missing" % eid)
        return

    missing = [c for c in CRITERIA if c not in criteria]
    extra = sorted(set(criteria) - set(CRITERIA))
    if missing:
        problems.append("%s: no annotation for %s" % (eid, missing))
    if extra:
        problems.append("%s: annotation for unknown criteria %s" % (eid, extra))

    for name in CRITERIA:
        crit = criteria.get(name)
        if not isinstance(crit, dict):
            continue
        where = "%s %s" % (eid, name)

        unknown = sorted(set(crit) - CRITERION_KEYS)
        if unknown:
            problems.append("%s: unknown field(s) %s" % (where, unknown))
        if not (crit.get("comment") or "").strip():
            problems.append("%s: comment is missing or empty" % where)
        else:
            hit = GRADE_LANGUAGE.search(crit["comment"])
            if hit:
                problems.append("%s: comment names the grade or the grading process (%r)"
                                % (where, hit.group(0)))

        spans = crit.get("spans")
        if spans is None:
            problems.append("%s: spans is missing" % where)
            continue
        if len(spans) > MAX_SPANS_PER_CRITERION:
            problems.append("%s: %d spans, maximum is %d -- past that the highlighting stops "
                            "selecting and starts covering"
                            % (where, len(spans), MAX_SPANS_PER_CRITERION))
        if not spans:
            # ui_8: an absence is a finding, but it has to be stated as one.
            if not (crit.get("no_evidence_reason") or "").strip():
                problems.append("%s: no spans and no no_evidence_reason -- if there is genuinely "
                                "nothing in the response to cite for this trait, say so; silent "
                                "absence is not permitted" % where)
        elif (crit.get("no_evidence_reason") or "").strip():
            problems.append("%s: has both spans and a no_evidence_reason -- the reason is only for "
                            "a trait with nothing to point at" % where)

        for i, span in enumerate(spans or []):
            _check_span(span, text, eid, name, i, problems)


def load_annotation(batch_dir=ANNOTATION_DIR, essays=None, expected_ids=None):
    """Read and validate annotation batches into {essay_id: item}. Every failure is a hard error."""
    if essays is None:
        essays = load_essays()
    if not os.path.isdir(batch_dir):
        raise AnnotationError(
            "%s does not exist. Annotate the essays against annotation_instrument_ui_v1.md into "
            "that directory as batch_00.json .. batch_NN.json first." % batch_dir
        )

    problems = []
    items = {}
    for path in sorted(glob.glob(os.path.join(batch_dir, "batch_*.json"))):
        with open(path) as f:
            batch = json.load(f)
        for item in batch:
            eid = item.get("essay_id")
            if eid in items:
                problems.append("%s: annotated twice" % eid)
            _check_item(item, essays, problems)
            if eid:
                items[eid] = item

    if expected_ids is not None:
        missing = sorted(set(expected_ids) - set(items))
        extra = sorted(set(items) - set(expected_ids))
        if missing:
            problems.append("no annotation for %d essay(s): %s" % (len(missing), missing))
        if extra:
            problems.append("annotation for essay(s) not in the requested set: %s" % extra)

    # Anchor last: a quote can only be located once the item's shape is known to be sane.
    for eid, item in sorted(items.items()):
        if eid not in essays or not isinstance(item.get("criteria"), dict):
            continue
        try:
            resolve_spans(essays[eid], item["criteria"], essay_id=eid)
        except (AnchorError, KeyError) as exc:
            problems.append(str(exc))

    if problems:
        raise AnnotationError(
            "annotation in %s is not usable (%d problem(s)):\n  %s"
            % (os.path.basename(batch_dir), len(problems), "\n  ".join(problems))
        )
    return items


# --------------------------------------------------------------------------------------------
# build
# --------------------------------------------------------------------------------------------

def _continuous(aggregator, traits, word_count):
    """The continuous score `s` alone, through the pipeline's own aggregator."""
    return apply_aggregator(aggregator, traits, word_count)[1]


def _score_formation(aggregator, traits, word_count):
    """Everything the teacher needs to see how the holistic was produced, and nothing recomputed
    in the page. The holistic itself comes from the pipeline's own aggregator, not a copy of it.

    The additive terms and the two sensitivities are computed here for the same reason: a page that
    multiplies a coefficient by a feature is a second implementation of the aggregator, and two
    implementations eventually disagree. The renderer formats these numbers; it never derives one
    (ui_10). Terms are built by zipping the aggregator's own `features` list rather than by
    positional assumption, so a future feature set cannot silently mislabel a term.
    """
    holistic, s, band = apply_aggregator(aggregator, traits, word_count)
    cuts = aggregator["cuts"]
    above = [c for c in cuts if c > s]
    below = [c for c in cuts if c <= s]
    to_up = (min(above) - s) if above else None
    to_down = (s - max(below)) if below else None
    nearest = min([d for d in (to_up, to_down) if d is not None], default=None)
    if nearest is None:
        direction = None
    elif to_up is not None and nearest == to_up:
        direction = "up"
    else:
        direction = "down"

    beta = aggregator["beta"]
    features = list(aggregator["features"])
    terms = dict(zip(features,
                     (b * v for b, v in zip(beta[1:],
                                            aggregator_features(traits, word_count, features)))))

    # What actually moves the score, stated as movement rather than left to be inferred from three
    # coefficients. Both are measured against this essay's own aggregator rather than derived by
    # hand: a point on every trait, and twice the length. decisions_log.md ui_5 and D2.
    raised = {k: v + 1 for k, v in traits.items()}
    return holistic, {
        "weighted_trait_mean": sum(V4_WEIGHTS[k] * traits[k] for k in V4_WEIGHTS),
        "log10_word_count": math.log10(max(word_count, 1)),
        "word_count": word_count,
        "intercept": beta[0],
        "terms": terms,
        "trait_term": terms.get("weighted_trait_mean"),
        "length_term": terms.get("log10_word_count"),
        "continuous_score": s,
        "band": band,
        "cuts": list(cuts),
        "to_next_band_up": to_up,
        "to_next_band_down": to_down,
        "distance_to_nearest_cut": nearest,
        "nearest_cut_direction": direction,
        "s_per_trait_point": _continuous(aggregator, raised, word_count) - s,
        "s_per_length_doubling": _continuous(aggregator, traits, word_count * 2) - s,
        "beta": list(beta),
        "weights": dict(V4_WEIGHTS),
    }


def record_kind(kind):
    """The kind a record counts as, in one place. The guard, the fold and the writer have to agree:
    a record validated as a trait correction must be stored and read back as one, so none of them
    may carry its own copy of this default."""
    return kind or DEFAULT_OVERRIDE_KIND


def _whole_number(value):
    """A trait score has to be a whole number, and `int()` alone does not say so -- it truncates
    5.9 to 5 and turns True into 1, either of which would re-score an essay through the frozen
    aggregator without anything raising."""
    if isinstance(value, bool):
        return False
    if isinstance(value, int):
        return True
    if isinstance(value, float):
        return value.is_integer()
    if isinstance(value, str):
        try:
            int(value)
        except ValueError:
            return False
        return True
    return False


def _check_override(rec, index, problems):
    where = "override record %d (%s)" % (index, rec.get("essay_id") or "no essay_id")
    essay_id = rec.get("essay_id")
    if essay_id is None or (isinstance(essay_id, str) and not essay_id.strip()):
        problems.append("%s: has no essay_id" % where)
    elif not isinstance(essay_id, str):
        problems.append("%s: essay_id is %r, expected text -- an id written without its quotes "
                        "matches no essay, so the record would apply to nothing at all"
                        % (where, type(essay_id).__name__))

    kind = record_kind(rec.get("kind"))
    if kind not in OVERRIDE_KINDS:
        problems.append("%s: kind=%r is not one of %s" % (where, kind, list(OVERRIDE_KINDS)))
        return

    corrected = rec.get("corrected_traits") or {}
    if not isinstance(corrected, dict):
        problems.append("%s: corrected_traits is %r, expected an object"
                        % (where, type(corrected).__name__))
        return

    if kind == "trait_correction" and not corrected:
        problems.append("%s: a trait correction that corrects no trait -- to withdraw a "
                        "correction, record kind=cleared instead" % where)
    if kind in ("dissent", "cleared") and corrected:
        problems.append("%s: kind=%s must not carry corrected_traits (found %s) -- a dissent is "
                        "about the aggregator, not the traits, and clearing withdraws rather than "
                        "sets" % (where, kind, sorted(corrected)))

    rationale = rec.get("rationale")
    if rationale is not None and not isinstance(rationale, str):
        problems.append("%s: rationale is %r, expected text" % (where, type(rationale).__name__))
    if kind == "dissent" and not (rationale or "").strip():
        problems.append("%s: a dissent records a rationale and no number, so the rationale is the "
                        "whole record -- it cannot be empty" % where)

    for name, value in sorted(corrected.items()):
        if name not in CRITERIA:
            problems.append("%s: corrects unknown trait %r, expected one of %s"
                            % (where, name, list(CRITERIA)))
            continue
        if not _whole_number(value):
            problems.append("%s: %s=%r is not a whole number" % (where, name, value))
            continue
        score = int(value)
        if not MIN_TRAIT <= score <= MAX_TRAIT:
            problems.append("%s: %s=%d is outside the %d-%d scale the rubric defines"
                            % (where, name, score, MIN_TRAIT, MAX_TRAIT))


def check_override_records(records):
    """Every override record is usable, or none of them are. Collects all problems, like the
    annotation guards -- overrides.json is hand-editable and diffable by design, so a typo in it
    has to name itself rather than quietly re-scoring an essay."""
    problems = []
    for index, rec in enumerate(records):
        if not isinstance(rec, dict):
            problems.append("override record %d is %r, expected an object"
                            % (index, type(rec).__name__))
            continue
        _check_override(rec, index, problems)
    if problems:
        raise OverrideError("%d override record problem(s):\n  %s"
                            % (len(problems), "\n  ".join(problems)))
    return records


def _fold(records):
    """The per-section latest-wins fold itself, over any slice of one essay's records."""
    fold = {"corrected_traits": None, "dissent": None, "rationale": None}
    for rec in records:
        kind = record_kind(rec.get("kind"))
        rationale = (rec.get("rationale") or "").strip() or None
        if kind == "trait_correction":
            fold["corrected_traits"] = {k: int(v)
                                        for k, v in (rec.get("corrected_traits") or {}).items()}
            fold["rationale"] = rationale
        elif kind == "cleared":
            fold["corrected_traits"] = None
            fold["rationale"] = None
        elif kind == "dissent":
            fold["dissent"] = {"rationale": rationale, "recorded_at": rec.get("recorded_at")}
    return fold


def override_state(records, essay_id):
    """Fold one essay's records into its current state.

    Latest wins PER SECTION rather than wholesale. A dissent and a trait correction answer
    different questions -- "the aggregator is wrong" and "the traits are wrong" -- so letting one
    record's silence on the other erase it would make a teacher's second action quietly undo their
    first. The append-only trail is preserved either way; this only decides how it is read back.
    See teacher_ui/decisions_log.md ui_12.

    `rationale` belongs to the standing trait correction and to nothing else. Withdrawing a
    correction takes its reason with it rather than inheriting the withdrawal's own reason: a
    justification that survived the record it was written for would be offered back as the reason
    for whatever the teacher does next, which is how a reason arguing the AI was right ends up
    stored against a fresh correction. The withdrawal's reason stays in `trail`, where it names
    the record it was typed for. See decisions_log.md ui_14 and ui_15.

    `before_latest` is the same fold one record short: the state the most recent record was made
    against. A page that tells a teacher what their save just did needs the score that save met,
    not the AI's -- on a second correction those are different numbers. It is None when the essay
    has no records at all. See decisions_log.md ui_16.

    `latest_kind` names what that most recent record was. A dissent moves no trait and no score by
    design, so it can only be narrated as itself; asking whether the score moved without first
    asking what the teacher actually did reports a dissent as a correction that failed. See
    decisions_log.md ui_17.
    """
    mine = [r for r in records if r.get("essay_id") == essay_id]
    state = dict(_fold(mine))
    state["records"] = len(mine)
    state["trail"] = [{
        "kind": record_kind(rec.get("kind")),
        "recorded_at": rec.get("recorded_at"),
        "corrected_traits": rec.get("corrected_traits") or None,
        "recomputed_holistic": rec.get("recomputed_holistic"),
        "rationale": (rec.get("rationale") or "").strip() or None,
        "gold_revealed": bool(rec.get("gold_revealed")),
    } for rec in mine]
    state["before_latest"] = _fold(mine[:-1]) if mine else None
    state["latest_kind"] = record_kind(mine[-1].get("kind")) if mine else None
    return state


def build_review(predictions=None, annotation=None, essays=None, override_records=(),
                 expected_ids=None, aggregator=None, manifest=None):
    """Return the review artifact implied by predictions, annotation, essay text and overrides."""
    manifest = manifest if manifest is not None else load_manifest()
    essays = essays if essays is not None else load_essays()
    predictions = predictions if predictions is not None else load_predictions()
    if aggregator is None:
        with open(AGGREGATOR_FILE) as f:
            aggregator = json.load(f)
    if expected_ids is None:
        expected_ids = list(manifest["essay_ids"])
    if annotation is None:
        annotation = load_annotation(essays=essays, expected_ids=expected_ids)
    check_override_records(override_records)

    out_essays = []
    for eid in sorted(expected_ids):
        pred = predictions[eid]
        text = essays[eid]
        word_count = int(pred["word_count"])
        ai_traits = {c: int(pred["system_" + c]) for c in CRITERIA}

        state = override_state(override_records, eid)
        traits = dict(ai_traits)
        if state["corrected_traits"]:
            traits.update(state["corrected_traits"])

        ai_holistic, _ = _score_formation(aggregator, ai_traits, word_count)
        holistic, formation = _score_formation(aggregator, traits, word_count)

        before_latest = None
        if state["before_latest"] is not None:
            standing = dict(ai_traits)
            if state["before_latest"]["corrected_traits"]:
                standing.update(state["before_latest"]["corrected_traits"])
            before_latest, _ = _score_formation(aggregator, standing, word_count)

        item = annotation[eid]
        criteria = {}
        for name in CRITERIA:
            crit = item["criteria"][name]
            criteria[name] = {
                "comment": crit["comment"],
                "trait_score": traits[name],
                "ai_trait_score": ai_traits[name],
                "spans": [],
            }
            if crit.get("no_evidence_reason"):
                criteria[name]["no_evidence_reason"] = crit["no_evidence_reason"]

        for span in resolve_spans(text, item["criteria"], essay_id=eid):
            criteria[span["criterion"]]["spans"].append({
                "quote": span["quote"],
                "occurrence": span["occurrence"],
                "polarity": span["polarity"],
                "start": span["start"],
                "end": span["end"],
            })

        out_essays.append({
            "essay_id": eid,
            "text": text,
            "word_count": word_count,
            "overview": item["overview"],
            "criteria": criteria,
            "ai_traits": ai_traits,
            "traits": traits,
            "ai_holistic": ai_holistic,
            "holistic": holistic,
            # The score standing when the most recent record was written, or None if there is
            # none. Every "what did this save do" question is answered against this, not against
            # the AI -- decisions_log.md ui_16.
            "holistic_before_latest_record": before_latest,
            # `overridden` is about the scores as they now stand, `reviewed` about whether a
            # teacher has been here at all -- a cleared correction is reviewed but not overridden,
            # and a dissent is reviewed while every trait still reads as the AI left it.
            "overridden": traits != ai_traits,
            "reviewed": state["records"] > 0,
            "dissent": state["dissent"],
            "override_rationale": state["rationale"],
            "override_records": state["records"],
            # What the most recent record was, so a consumer narrating "what did that do" names
            # the right action before asking what it moved -- decisions_log.md ui_17.
            "latest_record_kind": state["latest_kind"],
            "override_trail": state["trail"],
            "score_formation": formation,
            # Two questions with two answers, named for the baseline each is measured against so
            # a consumer cannot reach for the wrong one: whether the corrections as they now stand
            # leave the AI's score untouched, and whether the last one written moved anything.
            "score_unchanged_vs_ai": traits != ai_traits and holistic == ai_holistic,
            "score_unchanged_by_latest_record": (state["records"] > 0
                                                 and holistic == before_latest),
        })

    manifest_ids = set(manifest["essay_ids"])
    return {
        "ladder_version": LADDER_VERSION,
        "trait_run": TRAIT_RUN,
        "aggregator_source": aggregator.get("source"),
        "aggregator_n": aggregator.get("n"),
        "weights": dict(V4_WEIGHTS),
        "complete": set(expected_ids) == manifest_ids,
        "essays_requested": sorted(expected_ids),
        "essays_in_manifest": sorted(manifest_ids),
        "essays": out_essays,
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--essays", default=None,
                    help="comma-separated essay_ids to build over (default: the frozen manifest). "
                         "A partial build is recorded as such in the artifact.")
    ap.add_argument("--out", default=DEFAULT_OUT)
    args = ap.parse_args(argv)

    expected = [e.strip() for e in args.essays.split(",")] if args.essays else None
    try:
        artifact = build_review(override_records=load_overrides(), expected_ids=expected)
    except (AnnotationError, AnchorError, OverrideError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    with open(args.out, "w") as f:
        json.dump(artifact, f, indent=2, ensure_ascii=False)
        f.write("\n")

    n_spans = sum(len(c["spans"]) for e in artifact["essays"] for c in e["criteria"].values())
    print("built %s: %d essay(s), %d span(s), complete=%s"
          % (os.path.basename(args.out), len(artifact["essays"]), n_spans, artifact["complete"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
