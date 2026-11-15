"""Display trust is separate from score-only extraction associations."""

from copy import deepcopy

import pytest

from src.matching.pipeline import trusted_extracted_skills

EXACT = {
    "canonical_skill": "Python",
    "matched_skill": "Python",
    "requirement_class": "REQUIRED",
    "approximate_match": False,
    "negated": False,
    "conflicting": False,
    "requirement_selected": True,
}


@pytest.mark.parametrize(
    "override",
    [
        {"approximate_match": True},
        {"negated": True},
        {"conflicting": True},
        {"requirement_class": None},
        {"canonical_skill": None},
        {"canonical_skill": ""},
        {"approximate_match": None},
    ],
)
def test_uncertain_or_unclassified_evidence_cannot_be_displayed(override):
    assert trusted_extracted_skills([{**EXACT, **override}]) == set()


def test_missing_evidence_is_unknown():
    assert trusted_extracted_skills(None) == set()
    assert trusted_extracted_skills([]) == set()
    assert trusted_extracted_skills([{"canonical_skill": "Python"}]) == set()


def test_exact_affirmative_evidence_does_not_need_to_be_consolidation_winner():
    rows = [{**EXACT, "requirement_selected": False}, {**EXACT, "requirement_class": "PREFERRED"}]
    before = deepcopy(rows)
    assert trusted_extracted_skills(rows) == {"python"}
    assert rows == before


@pytest.mark.parametrize("text", ["Python required. Python optional.", "Python"])
def test_retained_conflicting_or_unknown_mentions_are_not_display_evidence(text):
    from src.extraction.classification import annotate_spans

    raw = []
    annotate_spans(text, raw)
    assert trusted_extracted_skills(raw) == set()


def test_actual_approximate_score_support_does_not_become_a_displayed_skill():
    from src.extraction.classification import annotate_spans
    from src.extraction.contracts import SpanEvidence

    text = "Pyhton required."
    raw = [SpanEvidence(0, 6, "skill", 0.9).serialize(text)]
    (selected,) = annotate_spans(text, raw)
    assert selected["matched_skill"] == "Python"
    assert selected["requirement_class"] == "REQUIRED"
    assert selected["approximate_match"] is True
    assert trusted_extracted_skills(raw) == set()
