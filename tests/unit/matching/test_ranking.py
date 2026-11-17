import pytest

from src.matching.ranking import RankingPolicy, SimilarityCalibration


def test_calibration_boundaries_and_provisional_version():
    policy = SimilarityCalibration()
    assert policy.score(-1) == 0
    assert policy.score(0.5) == 0
    assert policy.score(0.75) == 50
    assert policy.score(1) == 100
    assert "provisional" in policy.version
    with pytest.raises(ValueError):
        policy.score(float("nan"))
    with pytest.raises(ValueError):
        SimilarityCalibration(zero=1, full=0)


def test_final_blend_retains_frozen_coefficients():
    policy = RankingPolicy()
    assert policy.score(100, 0, 0) == 45
    assert policy.score(0, 100, 0) == 35
    assert policy.score(0, 0, 100) == 20
    assert policy.score(100, 100, 100) == 100
    with pytest.raises(ValueError):
        policy.score(101, 0, 0)
    with pytest.raises(ValueError):
        RankingPolicy(textual=1)


def test_accepted_floating_point_weights_cannot_exceed_public_score_bounds():
    policy = RankingPolicy(textual=0.4500000001)
    assert policy.score(100, 100, 100) == 100
    assert policy.score(0, 0, 0) == 0
    assert policy.score(20, 40, 60) == pytest.approx(35.0)


@pytest.mark.parametrize("limit", [False, True, 0, -1, 1.5, float("nan"), float("inf"), "10", None])
def test_retrieval_limit_rejects_non_integer_or_nonpositive_counts(limit):
    with pytest.raises(ValueError, match="Invalid ranking policy"):
        RankingPolicy(retrieval_limit=limit)


@pytest.mark.parametrize("limit", [1, 100, 1000])
def test_retrieval_limit_accepts_positive_integer_counts(limit):
    assert RankingPolicy(retrieval_limit=limit).retrieval_limit == limit


def test_dual_similarity_never_lets_long_descriptions_drag_the_core_below_itself():
    import numpy as np

    from src.matching.ranking import dual_similarity

    core = np.array([0.90, 0.70, 0.80])
    full = np.array([0.60, 0.90, 0.80])
    result = dual_similarity(np, core, full, RankingPolicy().core_weight)
    # Boilerplate-diluted full vector: the core similarity is kept.
    assert result[0] == pytest.approx(0.90)
    # Matching detail in the description can lift the entry.
    assert result[1] == pytest.approx(0.65 * 0.70 + 0.35 * 0.90)
    assert result[2] == pytest.approx(0.80)
    assert all(result >= core)


@pytest.mark.parametrize("weight", [-0.1, 1.1, float("nan"), float("inf")])
def test_core_weight_is_a_finite_share(weight):
    with pytest.raises(ValueError, match="Invalid ranking policy"):
        RankingPolicy(core_weight=weight)
