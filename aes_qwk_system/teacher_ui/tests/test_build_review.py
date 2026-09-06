"""The build seam: its guards, and the artifact it produces.

Every guard test asserts two things -- that the guard fires at all, and that its message names the
essay. A guard that rejects a batch without saying which essay is wrong makes a ten-essay run
unfixable, so the naming is part of the behaviour, not a nicety.

The artifact tests assert what a reader of the artifact would observe: that the holistic matches
what the pipeline itself computed, that the gold score is absent, and that two builds of the same
inputs are identical.
"""

import json

import pytest

from build_review import (AGGREGATOR_FILE, CRITERIA, AnnotationError, OverrideError,
                          build_review, check_override_records, load_annotation,
                          override_state)

# A short response with predictable wording, so quote-length limits are easy to reason about.
ESSAY = (
    "The city should build more bicycle lanes. Cars make the air dirty and they are "
    "dangerous for children walking to school. A bicycle costs less than a car and it "
    "does not need petrol. Some people say the winter is too cold for cycling but a coat "
    "solves that problem. I think the council should act now."
)
ESSAYS = {"E1": ESSAY}

QUOTES = [
    "The city should build more bicycle lanes.",
    "Cars make the air dirty",
    "A bicycle costs less than a car",
    "I think the council should act now.",
]


def make_item(essay_id="E1", **kwargs):
    item = {
        "essay_id": essay_id,
        "overview": "You state a clear opinion and support it with everyday reasons a reader "
                    "can follow. Push each reason one step further before moving on.",
        "criteria": {
            name: {
                "comment": "You argue this clearly and could develop it further.",
                "spans": [{"quote": QUOTES[i], "occurrence": 1, "polarity": "strength"}],
            }
            for i, name in enumerate(CRITERIA)
        },
    }
    item.update(kwargs)
    return item


@pytest.fixture
def write_batch(tmp_path):
    """Write annotation objects to a batch directory and return its path."""
    def _write(*items):
        d = tmp_path / "annotation"
        d.mkdir(exist_ok=True)
        (d / "batch_00.json").write_text(json.dumps(list(items)))
        return str(d)
    return _write


def load(batch_dir, expected_ids=("E1",)):
    return load_annotation(batch_dir=batch_dir, essays=ESSAYS, expected_ids=list(expected_ids))


def fails(batch_dir, expected_ids=("E1",)):
    with pytest.raises(AnnotationError) as exc:
        load(batch_dir, expected_ids)
    return str(exc.value)


# --- the valid case ----------------------------------------------------------------------------

def test_a_well_formed_batch_loads(write_batch):
    items = load(write_batch(make_item()))
    assert set(items) == {"E1"}


# --- guard 1: coverage -------------------------------------------------------------------------

def test_missing_essay_fails_and_names_it(write_batch):
    message = fails(write_batch(make_item("E1")), expected_ids=("E1", "E2"))
    assert "no annotation for 1 essay(s)" in message
    assert "E2" in message


def test_essay_outside_the_requested_set_fails_and_names_it(write_batch):
    item = make_item("E1")
    stray = make_item("E1")
    stray["essay_id"] = "E9"
    message = fails(write_batch(item, stray))
    assert "not in the requested set" in message
    assert "E9" in message


def test_the_same_essay_annotated_twice_fails(write_batch):
    message = fails(write_batch(make_item("E1"), make_item("E1")))
    assert "E1: annotated twice" in message


def test_essay_not_in_the_corpus_fails(write_batch):
    item = make_item("E1")
    item["essay_id"] = "NOPE"
    message = fails(write_batch(item), expected_ids=("NOPE",))
    assert "NOPE" in message
    assert "not present in the source corpus" in message


# --- guard 2: closed schema --------------------------------------------------------------------

@pytest.mark.parametrize("field", ["holistic_score", "human_score", "SCORES", "argumentation"])
def test_a_score_field_on_the_item_fails_and_names_it(write_batch, field):
    message = fails(write_batch(make_item(**{field: 3})))
    assert "E1" in message
    assert field in message
    assert "never asked for" in message


def test_unknown_item_field_fails(write_batch):
    message = fails(write_batch(make_item(confidence=0.9)))
    assert "E1" in message and "confidence" in message


def test_unknown_criterion_field_fails(write_batch):
    item = make_item()
    item["criteria"]["argumentation"]["severity"] = "high"
    message = fails(write_batch(item))
    assert "E1 argumentation" in message and "severity" in message


def test_unknown_span_field_fails(write_batch):
    item = make_item()
    item["criteria"]["argumentation"]["spans"][0]["confidence"] = 0.5
    message = fails(write_batch(item))
    assert "E1 argumentation[0]" in message and "confidence" in message


# --- guard 3: anchoring ------------------------------------------------------------------------

def test_a_quote_that_is_not_in_the_response_fails_at_build(write_batch):
    item = make_item()
    item["criteria"]["development"]["spans"][0]["quote"] = "a sentence the student never wrote"
    message = fails(write_batch(item))
    assert "E1" in message and "not found" in message


# --- guard 4: minimum quote length --------------------------------------------------------------

def test_a_quote_shorter_than_three_words_fails(write_batch):
    item = make_item()
    item["criteria"]["argumentation"]["spans"][0]["quote"] = "The city"
    message = fails(write_batch(item))
    assert "E1 argumentation[0]" in message
    assert "2 word(s)" in message


# --- guard 5: maximum span length ---------------------------------------------------------------

def test_a_quote_longer_than_a_quarter_of_the_response_fails(write_batch):
    item = make_item()
    item["criteria"]["organization"]["spans"][0]["quote"] = (
        "Cars make the air dirty and they are dangerous for children walking to school. "
        "A bicycle costs less"
    )
    message = fails(write_batch(item))
    assert "E1 organization[0]" in message
    assert "25%" in message


# --- guard 6: span counts and the no-evidence path ----------------------------------------------

def test_more_than_four_spans_on_one_criterion_fails(write_batch):
    item = make_item()
    item["criteria"]["conventions"]["spans"] = [
        {"quote": q, "occurrence": 1, "polarity": "weakness"} for q in QUOTES
    ] + [{"quote": "Some people say the winter", "occurrence": 1, "polarity": "weakness"}]
    message = fails(write_batch(item))
    assert "E1 conventions" in message
    assert "5 spans, maximum is 4" in message


def test_no_spans_and_no_reason_fails(write_batch):
    item = make_item()
    item["criteria"]["development"]["spans"] = []
    message = fails(write_batch(item))
    assert "E1 development" in message
    assert "no_evidence_reason" in message


def test_no_spans_with_a_stated_reason_is_accepted(write_batch):
    """ui_8: on a response with nothing to cite for a trait, the absence is the finding."""
    item = make_item()
    item["criteria"]["development"]["spans"] = []
    item["criteria"]["development"]["no_evidence_reason"] = (
        "The response never supports its claims, so there is no evidence to point at."
    )
    items = load(write_batch(item))
    assert items["E1"]["criteria"]["development"]["spans"] == []


def test_spans_together_with_a_no_evidence_reason_fails(write_batch):
    item = make_item()
    item["criteria"]["development"]["no_evidence_reason"] = "there is nothing here"
    message = fails(write_batch(item))
    assert "E1 development" in message
    assert "both spans and a no_evidence_reason" in message


# --- guard 7: criteria and polarity in range ----------------------------------------------------

def test_a_missing_criterion_fails_and_names_it(write_batch):
    item = make_item()
    del item["criteria"]["conventions"]
    message = fails(write_batch(item))
    assert "E1" in message and "conventions" in message


def test_an_unknown_criterion_fails(write_batch):
    item = make_item()
    item["criteria"]["creativity"] = {"comment": "x", "spans": []}
    message = fails(write_batch(item))
    assert "E1" in message and "creativity" in message


@pytest.mark.parametrize("polarity", [None, "neutral", "positive", ""])
def test_a_span_without_a_valid_polarity_fails(write_batch, polarity):
    item = make_item()
    item["criteria"]["argumentation"]["spans"][0]["polarity"] = polarity
    message = fails(write_batch(item))
    assert "E1 argumentation[0]" in message
    assert "polarity" in message


# --- guard 8: prose is present and does not name the grade --------------------------------------

def test_an_empty_overview_fails(write_batch):
    message = fails(write_batch(make_item(overview="   ")))
    assert "E1" in message and "overview" in message


def test_an_empty_comment_fails(write_batch):
    item = make_item()
    item["criteria"]["conventions"]["comment"] = ""
    message = fails(write_batch(item))
    assert "E1 conventions" in message and "comment" in message


@pytest.mark.parametrize("overview", [
    "Overall this response earns a 3/6 for its clarity and its handling of the question.",
    "A solid piece of work that is worth three out of six on the whole.",
    "Your score here reflects a clear opinion supported by everyday reasons.",
    "Against the rubric this sits comfortably in the middle of the range.",
])
def test_an_overview_that_names_the_grade_fails(write_batch, overview):
    message = fails(write_batch(make_item(overview=overview)))
    assert "E1" in message
    assert "overview names the grade" in message


def test_a_comment_that_names_the_grading_process_fails(write_batch):
    item = make_item()
    item["criteria"]["organization"]["comment"] = "This trait was graded on structure alone."
    message = fails(write_batch(item))
    assert "E1 organization" in message
    assert "names the grade" in message


# --- problems are collected, not reported one at a time -----------------------------------------

def test_every_problem_in_a_batch_is_reported_at_once(write_batch):
    item = make_item(overview="")
    item["criteria"]["argumentation"]["spans"][0]["polarity"] = "neutral"
    item["criteria"]["development"]["spans"][0]["quote"] = "The city"
    item["criteria"]["conventions"]["comment"] = ""
    message = fails(write_batch(item))
    assert "4 problem(s)" in message


# --- the artifact ------------------------------------------------------------------------------

PRED_TRAITS = {"argumentation": 4, "organization": 3, "development": 3, "conventions": 2}
PREDICTIONS = {
    "E1": dict({"system_" + c: str(v) for c, v in PRED_TRAITS.items()},
               essay_id="E1", word_count="60"),
}
MANIFEST = {"essay_ids": ["E1"]}


def _artifact(overrides=()):
    annotation = {"E1": make_item()}
    return build_review(predictions=PREDICTIONS, annotation=annotation, essays=ESSAYS,
                        override_records=list(overrides), expected_ids=["E1"],
                        manifest=MANIFEST)


def test_the_artifact_carries_the_response_prose_and_resolved_spans():
    essay = _artifact()["essays"][0]
    assert essay["text"] == ESSAY
    assert essay["overview"]
    for name in CRITERIA:
        crit = essay["criteria"][name]
        assert crit["comment"]
        assert crit["spans"]
        for span in crit["spans"]:
            assert ESSAY[span["start"]:span["end"]] == span["quote"]
            assert span["polarity"] in ("strength", "weakness")


def test_each_criterion_card_carries_its_own_trait_score():
    essay = _artifact()["essays"][0]
    assert essay["criteria"]["argumentation"]["trait_score"] == 4
    assert essay["criteria"]["conventions"]["trait_score"] == 2


def test_the_artifact_holds_the_values_the_score_formation_panel_needs():
    formation = _artifact()["essays"][0]["score_formation"]
    for key in ("weighted_trait_mean", "log10_word_count", "word_count", "continuous_score",
                "band", "cuts", "distance_to_nearest_cut", "beta", "weights"):
        assert key in formation, key


def test_the_formation_terms_add_up_to_the_continuous_score():
    """The panel shows a sum, so the stored terms have to be that sum -- a page that displays
    addends which do not reach the total is worse than showing no derivation at all."""
    formation = _artifact()["essays"][0]["score_formation"]
    total = formation["intercept"] + sum(formation["terms"].values())
    assert total == pytest.approx(formation["continuous_score"])
    assert (formation["trait_term"] + formation["length_term"] + formation["intercept"]
            == pytest.approx(formation["continuous_score"]))


def test_each_term_is_labelled_with_the_feature_it_came_from():
    """Terms are zipped from the aggregator's own feature list, so a future feature set cannot
    silently relabel a coefficient."""
    with open(AGGREGATOR_FILE) as f:
        aggregator = json.load(f)
    formation = _artifact()["essays"][0]["score_formation"]
    assert list(formation["terms"]) == list(aggregator["features"])


def test_the_length_contribution_is_stored_rather_than_left_to_be_inferred():
    formation = _artifact()["essays"][0]["score_formation"]
    assert formation["length_term"] is not None
    assert formation["length_term"] == pytest.approx(
        formation["beta"][2] * formation["log10_word_count"])


def test_a_point_on_every_trait_moves_the_score_by_the_stated_amount():
    """The sensitivity the panel prints is measured against the aggregator, not asserted."""
    formation = _artifact()["essays"][0]["score_formation"]
    raised = {"essay_id": "E1", "corrected_traits": {c: PRED_TRAITS[c] + 1 for c in CRITERIA}}
    after = _artifact([raised])["essays"][0]["score_formation"]
    assert (after["continuous_score"] - formation["continuous_score"]
            == pytest.approx(formation["s_per_trait_point"]))


def test_doubling_the_length_moves_the_score_by_the_stated_amount():
    formation = _artifact()["essays"][0]["score_formation"]
    doubled = dict(PREDICTIONS["E1"], word_count=str(2 * int(PREDICTIONS["E1"]["word_count"])))
    after = build_review(predictions={"E1": doubled}, annotation={"E1": make_item()},
                         essays=ESSAYS, expected_ids=["E1"],
                         manifest=MANIFEST)["essays"][0]["score_formation"]
    assert (after["continuous_score"] - formation["continuous_score"]
            == pytest.approx(formation["s_per_length_doubling"]))


def test_length_moves_this_system_further_than_the_traits_do():
    """The uncomfortable fact the panel exists to state (ui_5). If this ever stops being true the
    panel's lead sentence must stop being printed, so it is asserted rather than assumed."""
    formation = _artifact()["essays"][0]["score_formation"]
    assert formation["s_per_length_doubling"] > formation["s_per_trait_point"]


def test_the_nearest_cut_point_is_named_with_its_direction():
    formation = _artifact()["essays"][0]["score_formation"]
    s, nearest = formation["continuous_score"], formation["distance_to_nearest_cut"]
    assert formation["nearest_cut_direction"] in ("up", "down")
    if formation["nearest_cut_direction"] == "up":
        assert min(c for c in formation["cuts"] if c > s) - s == pytest.approx(nearest)
    else:
        assert s - max(c for c in formation["cuts"] if c <= s) == pytest.approx(nearest)


def test_the_gold_score_is_absent_from_the_artifact():
    blob = json.dumps(_artifact())
    for leak in ("human_score", '"gold"', '"human"', '"score"'):
        assert leak not in blob, leak


def test_two_builds_of_the_same_inputs_are_identical():
    assert json.dumps(_artifact(), sort_keys=True) == json.dumps(_artifact(), sort_keys=True)


def test_a_partial_build_is_recorded_as_incomplete():
    annotation = {"E1": make_item()}
    artifact = build_review(predictions=PREDICTIONS, annotation=annotation, essays=ESSAYS,
                            expected_ids=["E1"], manifest={"essay_ids": ["E1", "E2"]})
    assert artifact["complete"] is False
    assert artifact["essays_in_manifest"] == ["E1", "E2"]


def test_a_build_over_the_whole_manifest_is_recorded_as_complete():
    assert _artifact()["complete"] is True


# --- overrides are an input to the build --------------------------------------------------------

def test_an_override_changes_the_traits_and_recomputes_the_holistic():
    record = {"essay_id": "E1", "corrected_traits": {"conventions": 6, "development": 6,
                                                     "organization": 6, "argumentation": 6}}
    before = _artifact()["essays"][0]
    after = _artifact([record])["essays"][0]
    assert after["ai_traits"] == before["ai_traits"]
    assert after["traits"]["conventions"] == 6
    assert after["ai_holistic"] == before["holistic"]
    assert after["holistic"] > before["holistic"]
    assert after["overridden"] is True


def test_an_override_that_does_not_move_the_band_is_flagged_as_such():
    """The measured common case (ui_9/D2): a single-trait correction usually changes nothing.

    The inputs are synthetic precisely so this is a fact rather than a coin toss -- the corpus
    decides whether a given essay's correction crosses a cut, and a test that depended on that
    could pass while asserting nothing about the case the ticket is built around."""
    record = {"essay_id": "E1", "corrected_traits": {"conventions": 3}}
    essay = _artifact([record])["essays"][0]
    assert essay["traits"]["conventions"] == 3
    assert essay["overridden"] is True
    assert essay["holistic"] == essay["ai_holistic"]
    assert essay["score_unchanged_vs_ai"] is True
    assert essay["score_unchanged_by_latest_record"] is True
    assert essay["score_formation"]["distance_to_nearest_cut"] is not None


def test_an_override_that_does_move_the_band_is_not_flagged_as_unchanged():
    """The other half, so the flag above is not simply always true on these inputs."""
    record = {"essay_id": "E1", "corrected_traits": {c: 6 for c in CRITERIA}}
    essay = _artifact([record])["essays"][0]
    assert essay["holistic"] != essay["ai_holistic"]
    assert essay["score_unchanged_vs_ai"] is False
    assert essay["score_unchanged_by_latest_record"] is False


def test_the_latest_override_record_wins():
    records = [
        {"essay_id": "E1", "corrected_traits": {"conventions": 5}},
        {"essay_id": "E1", "corrected_traits": {"conventions": 1}},
    ]
    assert _artifact(records)["essays"][0]["traits"]["conventions"] == 1


def test_an_override_for_another_essay_is_ignored():
    record = {"essay_id": "SOMEONE_ELSE", "corrected_traits": {"conventions": 6}}
    essay = _artifact([record])["essays"][0]
    assert essay["overridden"] is False
    assert essay["traits"] == essay["ai_traits"]


# --- override guards ------------------------------------------------------------------------------
#
# overrides.json is diffable and hand-editable by design, so a typo in it must name itself rather
# than quietly re-score an essay. Same stance as the annotation guards: hard error, all at once.

def _refuses(records):
    with pytest.raises(OverrideError) as exc:
        check_override_records(records)
    return str(exc.value)


def test_a_trait_outside_the_scale_is_refused_and_named():
    message = _refuses([{"essay_id": "E1", "corrected_traits": {"argumentation": 7}}])
    assert "E1" in message and "argumentation=7" in message and "1-6" in message


def test_a_correction_of_an_unknown_trait_is_refused_and_named():
    message = _refuses([{"essay_id": "E1", "corrected_traits": {"handwriting": 4}}])
    assert "E1" in message and "handwriting" in message


def test_a_trait_score_that_is_not_a_number_is_refused():
    message = _refuses([{"essay_id": "E1", "corrected_traits": {"conventions": "good"}}])
    assert "conventions='good'" in message or "conventions=\'good\'" in message


def test_a_fractional_trait_score_is_refused_rather_than_truncated():
    """int(5.9) is 5, so a guard that only catches what int() rejects would re-score the essay
    at a value nobody wrote."""
    message = _refuses([{"essay_id": "E1", "corrected_traits": {"argumentation": 5.9}}])
    assert "E1" in message and "argumentation=5.9" in message and "whole number" in message


def test_a_boolean_trait_score_is_refused_rather_than_counted_as_one():
    """int(True) is 1, a legal score, so this would otherwise pass every guard silently."""
    message = _refuses([{"essay_id": "E1", "corrected_traits": {"conventions": True}}])
    assert "E1" in message and "conventions=True" in message and "whole number" in message


def test_a_whole_number_written_as_a_float_is_accepted():
    """5.0 is how JSON may spell 5; rejecting wholeness must not mean rejecting the type."""
    essay = _artifact([{"essay_id": "E1", "corrected_traits": {"conventions": 5.0}}])["essays"][0]
    assert essay["traits"]["conventions"] == 5


def test_a_record_without_an_essay_is_refused():
    assert "no essay_id" in _refuses([{"corrected_traits": {"conventions": 3}}])


def test_an_unknown_kind_is_refused_and_named():
    message = _refuses([{"essay_id": "E1", "kind": "vibes",
                         "corrected_traits": {"conventions": 3}}])
    assert "vibes" in message


def test_a_trait_correction_that_corrects_nothing_is_refused():
    """Withdrawing is its own kind, so an empty correction is a mistake rather than a shorthand."""
    message = _refuses([{"essay_id": "E1", "kind": "trait_correction", "corrected_traits": {}}])
    assert "corrects no trait" in message and "cleared" in message


def test_a_dissent_carrying_a_trait_score_is_refused():
    """A dissent is about the aggregator. A number on it would disguise it as a trait correction."""
    message = _refuses([{"essay_id": "E1", "kind": "dissent", "rationale": "too low",
                         "corrected_traits": {"conventions": 5}}])
    assert "must not carry corrected_traits" in message


def test_a_dissent_without_a_rationale_is_refused():
    message = _refuses([{"essay_id": "E1", "kind": "dissent", "rationale": "  "}])
    assert "rationale is the whole record" in message


def test_every_bad_record_is_reported_at_once():
    message = _refuses([
        {"essay_id": "E1", "corrected_traits": {"argumentation": 9}},
        {"essay_id": "E2", "corrected_traits": {"spelling": 3}},
    ])
    assert "2 override record problem(s)" in message
    assert "E1" in message and "E2" in message


def test_a_bad_record_fails_the_build_rather_than_re_scoring_an_essay():
    with pytest.raises(OverrideError):
        _artifact([{"essay_id": "E1", "corrected_traits": {"argumentation": 0}}])


# --- current state is a fold over the trail -------------------------------------------------------

def test_state_is_empty_for_an_essay_nobody_has_touched():
    state = override_state([], "E1")
    assert state["corrected_traits"] is None and state["dissent"] is None
    assert state["records"] == 0


def test_a_dissent_does_not_erase_a_trait_correction():
    """Latest wins per section, not wholesale (ui_12). The two answer different questions, so a
    later dissent must not silently undo an earlier correction."""
    records = [
        {"essay_id": "E1", "kind": "trait_correction", "corrected_traits": {"conventions": 5}},
        {"essay_id": "E1", "kind": "dissent", "rationale": "the map is wrong here"},
    ]
    essay = _artifact(records)["essays"][0]
    assert essay["traits"]["conventions"] == 5
    assert essay["dissent"]["rationale"] == "the map is wrong here"
    assert essay["overridden"] is True


def test_a_trait_correction_does_not_erase_a_dissent():
    records = [
        {"essay_id": "E1", "kind": "dissent", "rationale": "the map is wrong here"},
        {"essay_id": "E1", "kind": "trait_correction", "corrected_traits": {"conventions": 5}},
    ]
    essay = _artifact(records)["essays"][0]
    assert essay["dissent"]["rationale"] == "the map is wrong here"
    assert essay["traits"]["conventions"] == 5


def test_a_dissent_alone_changes_no_trait_and_no_score():
    record = {"essay_id": "E1", "kind": "dissent", "rationale": "too generous"}
    essay = _artifact([record])["essays"][0]
    assert essay["traits"] == essay["ai_traits"]
    assert essay["holistic"] == essay["ai_holistic"]
    assert essay["overridden"] is False
    assert essay["reviewed"] is True


# --- clearing -------------------------------------------------------------------------------------

def test_clearing_returns_the_essay_to_the_ai_scores():
    records = [
        {"essay_id": "E1", "kind": "trait_correction", "corrected_traits": {"conventions": 6}},
        {"essay_id": "E1", "kind": "cleared"},
    ]
    essay = _artifact(records)["essays"][0]
    assert essay["traits"] == essay["ai_traits"]
    assert essay["holistic"] == essay["ai_holistic"]
    assert essay["overridden"] is False


def test_clearing_does_not_erase_the_record_that_it_happened():
    records = [
        {"essay_id": "E1", "kind": "trait_correction", "corrected_traits": {"conventions": 6}},
        {"essay_id": "E1", "kind": "cleared"},
    ]
    essay = _artifact(records)["essays"][0]
    assert essay["reviewed"] is True
    assert essay["override_records"] == 2
    assert [t["kind"] for t in essay["override_trail"]] == ["trait_correction", "cleared"]


def test_a_withdrawal_reason_does_not_become_the_correction_textarea_s_content():
    """A reason travels with the record kind it was typed for (ui_15). The reason for withdrawing
    a correction is not a reason for making one, and `override_rationale` is what the page renders
    back into the correction textarea and what the next save would carry."""
    records = [
        {"essay_id": "E1", "kind": "trait_correction", "corrected_traits": {"conventions": 6},
         "rationale": "the spelling is minor"},
        {"essay_id": "E1", "kind": "cleared", "rationale": "on reflection the AI had it right"},
    ]
    essay = _artifact(records)["essays"][0]
    assert essay["override_rationale"] is None
    reasons = [t["rationale"] for t in essay["override_trail"]]
    assert reasons == ["the spelling is minor", "on reflection the AI had it right"]


def test_a_correction_after_a_clear_applies_again():
    records = [
        {"essay_id": "E1", "kind": "trait_correction", "corrected_traits": {"conventions": 6}},
        {"essay_id": "E1", "kind": "cleared"},
        {"essay_id": "E1", "kind": "trait_correction", "corrected_traits": {"conventions": 4}},
    ]
    assert _artifact(records)["essays"][0]["traits"]["conventions"] == 4


def test_a_correction_matching_the_ai_scores_is_reviewed_but_not_overridden():
    """`overridden` is about the scores as they stand, not about whether a record exists."""
    record = {"essay_id": "E1", "corrected_traits": {"conventions": 2}}   # what the AI said
    essay = _artifact([record])["essays"][0]
    assert essay["overridden"] is False
    assert essay["reviewed"] is True


# --- what the record has to carry -----------------------------------------------------------------

def test_the_trail_preserves_every_record_in_order():
    records = [
        {"essay_id": "E1", "kind": "trait_correction", "corrected_traits": {"conventions": 5},
         "recorded_at": "2026-09-05T10:00:00", "rationale": "first thought"},
        {"essay_id": "E1", "kind": "trait_correction", "corrected_traits": {"conventions": 1},
         "recorded_at": "2026-09-05T11:00:00", "rationale": "second thought"},
    ]
    essay = _artifact(records)["essays"][0]
    assert essay["traits"]["conventions"] == 1
    assert [t["rationale"] for t in essay["override_trail"]] == ["first thought", "second thought"]
    assert essay["override_rationale"] == "second thought"
