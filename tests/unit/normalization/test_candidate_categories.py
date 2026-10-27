import pytest

from src.normalization.candidate.categories import (
    normalize_candidate_categories,
    normalize_seniority,
    normalize_work_arrangement,
)
from src.persistence.job.job import SeniorityLevel, WorkArrangement
from src.schemas.candidate.profile import CandidateProfile


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
        ("coordenador(a)", SeniorityLevel.COORDINATOR),
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


def test_normalize_candidate_categories_maps_enums_and_preserves_free_text():
    candidate = CandidateProfile.model_validate(
        {
            "skills": ["Python"],
            "job_titles": ["Developer"],
            "languages": [{"name": "English", "proficiency": "advanced"}],
            "seniority": "Sênior",
            "preferences": {
                "modes": ["Remoto", "Hybrid", "unrecognized", "remoto"],
                "employment_types": ["full-time", "contract"],
            },
        }
    )

    normalized = normalize_candidate_categories(candidate)

    assert normalized.seniority == SeniorityLevel.SENIOR
    assert normalized.modes == (WorkArrangement.REMOTE, WorkArrangement.HYBRID)
    assert normalized.languages[0].proficiency == "advanced"
    assert normalized.employment_types == ("full-time", "contract")


def test_unknown_candidate_categories_do_not_create_hard_categories():
    candidate = CandidateProfile.model_validate(
        {
            "skills": ["Python"],
            "job_titles": ["Developer"],
            "seniority": "executive",
            "preferences": {"modes": ["field work"]},
        }
    )

    normalized = normalize_candidate_categories(candidate)

    assert normalized.seniority is None
    assert normalized.modes == ()
