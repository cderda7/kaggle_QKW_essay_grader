"""Shared fixtures for the teacher review UI tests.

This package is the first automated test suite in this repository. The prior art for its stance is
the pipeline's own validators -- `load_triage()`, `check_v4_fidelity()`, the SCORES annotation
manifest -- which fail hard and name the cause rather than degrading quietly. These tests assert
that behaviour rather than any particular implementation of it.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

TEACHER_UI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCE_CSV = os.environ.get(
    "PERSONAL_TRAINING_SET_CSV",
    os.path.join(TEACHER_UI, "..", "..", "personal_training_set.csv"),
)
ANNOTATION_DIR = os.path.join(TEACHER_UI, "annotation_v6_runB")

# A synthetic response carrying every property the anchoring tests need, so the unit tests do not
# depend on the corpus being present: a phrase that appears twice, student misspellings that must
# not be silently corrected, a paragraph break, and a run of repeated spaces.
ESSAY = (
    "I don't like the idea of driveless cars.\n"
    "Another con is that they can't drive by itself.\n"
    "\n"
    "Another con is that they are basically illlegal in most states.\n"
    "Or they will drive right into a buliding at full   speed."
)


@pytest.fixture
def essay():
    return ESSAY


@pytest.fixture
def spans_for():
    """Build a `criteria` mapping of the shape resolve_spans() consumes."""
    def _build(criterion, *quotes, **kwargs):
        polarity = kwargs.pop("polarity", "strength")
        return {
            criterion: {
                "comment": "irrelevant to anchoring",
                "spans": [
                    {"quote": q, "occurrence": 1, "polarity": polarity} for q in quotes
                ],
            }
        }
    return _build
