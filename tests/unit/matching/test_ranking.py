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
