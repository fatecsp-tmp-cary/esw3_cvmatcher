from datetime import date

import pytest

from src.matching.semantic import ExperienceScore, SemanticPolicy, semantic_score


def experience(score, year=2020, ongoing=False):
    return ExperienceScore(score, date(year, 1, 1), None if ongoing else date(year, 12, 31))


def test_selects_relevance_before_recency_and_uses_best_education():
    entries = (
        experience(90, 2000),
        experience(80, 2010),
        experience(70, 2020),
        experience(1, 2025),
    )
    expected_experience = (90 + 80 * 1.25 + 70 * 1.5) / 3.75
    assert semantic_score(entries, (1, 95, 40)) == pytest.approx(
        0.8 * expected_experience + 0.2 * 95
    )


def test_more_recent_selected_experience_has_more_weight():
    assert semantic_score((experience(80, 2025), experience(20, 2000)), ()) > 50
    assert semantic_score((experience(20, 2025), experience(80, 2000)), ()) < 50


def test_equal_recency_has_equal_weight():
    assert semantic_score((experience(80), experience(20)), ()) == pytest.approx(50)


def test_similarity_ties_select_by_recency():
    entries = (
        experience(90, 2000),
        experience(70, 2010),
        experience(70, 2020),
        experience(70, 2025),
    )
    assert semantic_score(entries, ()) == pytest.approx((90 + 70 * 1.25 + 70 * 1.5) / 3.75)


def test_ongoing_precedes_completed_even_with_future_end():
    entries = (experience(100, 2000, True), experience(0, 2025))
    assert semantic_score(entries, ()) == pytest.approx(100 * 1.5 / 2.75)


@pytest.mark.parametrize(
    ("entries", "education", "expected"),
    [
        ((), (), 0),
        ((), (10, 80), 80),
        ((experience(70),), (), 70),
        ((experience(100),), (0,), 80),
        ((experience(100),) * 3, (100,), 100),
    ],
)
def test_available_sections(entries, education, expected):
    assert semantic_score(entries, education) == pytest.approx(expected)
    assert semantic_score(entries, education) == semantic_score(entries, education)


@pytest.mark.parametrize("score", [-1, 101, float("nan"), float("inf")])
def test_invalid_calibrated_scores_rejected(score):
    with pytest.raises(ValueError):
        experience(score)
    with pytest.raises(ValueError):
        semantic_score((), (score,))


@pytest.mark.parametrize(
    "kwargs",
    [
        {"experience_weight": 0},
        {"education_weight": float("nan")},
        {"recency_weights": (1, 1, 1)},
        {"version": ""},
    ],
)
def test_invalid_policy_rejected(kwargs):
    with pytest.raises(ValueError):
        SemanticPolicy(**kwargs)


def test_large_finite_relative_weights_do_not_overflow():
    policy = SemanticPolicy(
        experience_weight=1e308, education_weight=1e308, recency_weights=(1e308, 5e307, 1.0)
    )
    assert semantic_score(
        (experience(100, 2025), experience(0, 2000)), (0,), policy
    ) == pytest.approx(100 / 3)


@pytest.mark.parametrize("available", ["experience", "education"])
def test_absent_section_weight_cannot_underflow_available_evidence(available):
    experience_only = available == "experience"
    policy = SemanticPolicy(
        experience_weight=1e-308 if experience_only else 1e308,
        education_weight=1e308 if experience_only else 1e-308,
    )
    entries = (experience(100),) if experience_only else ()
    education = () if experience_only else (100,)
    assert semantic_score(entries, education, policy) == 100
    assert policy.version == "semantic-aggregation-v2-provisional"
