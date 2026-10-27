import pytest

from src.normalization.candidate.categories import (
    normalize_seniority,
    normalize_work_arrangement,
)
from src.persistence.job.job import SeniorityLevel, WorkArrangement


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("estágio", SeniorityLevel.INTERN),
        ("Jr.", SeniorityLevel.JUNIOR),
        ("júnior", SeniorityLevel.JUNIOR),
        ("Pleno", SeniorityLevel.MID),
        ("mid-level", SeniorityLevel.MID),
        ("SÊNIOR", SeniorityLevel.SENIOR),
        ("especialista", SeniorityLevel.SPECIALIST),
        ("coordenadora", SeniorityLevel.COORDINATOR),
        ("executive", None),
        (None, None),
    ],
)
def test_normalize_seniority(value, expected):
    assert normalize_seniority(value) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("home office", WorkArrangement.REMOTE),
        ("REMOTO", WorkArrangement.REMOTE),
        ("híbrido", WorkArrangement.HYBRID),
        ("on-site", WorkArrangement.ON_SITE),
        ("presencial", WorkArrangement.ON_SITE),
        ("field work", None),
        (None, None),
    ],
)
def test_normalize_work_arrangement(value, expected):
    assert normalize_work_arrangement(value) == expected
