"""CandidateProfile request schema (#39)."""

import pytest
from pydantic import ValidationError

from src.schemas.candidate import CandidateProfile

FULL_PROFILE = {
    "skills": ["Python", "PostgreSQL", "Docker"],
    "job_titles": ["Backend Developer"],
    "occupations": ["Software Engineer"],
    "experience": [
        {
            "title": "Backend Developer",
            "company": "Acme",
            "description": "Built REST APIs with FastAPI.",
            "skills": ["Python", "FastAPI"],
            "start_date": "2021-03",
        },
        {"title": "Intern", "start_date": "2019", "end_date": "2020-12"},
    ],
    "education": [
        {
            "institution": "FATEC-SP",
            "degree": "Technologist",
            "field_of_study": "Systems Development",
            "start_date": "2018-02",
            "end_date": "2021",
        }
    ],
    "certifications": [{"name": "AWS Cloud Practitioner", "issuer": "AWS"}],
    "languages": [{"name": "English", "proficiency": "advanced"}, {"name": "Portuguese"}],
    "locations": ["São Paulo, SP"],
    "seniority": "mid",
    "years_experience": 4.5,
    "preferences": {"employment_types": ["full-time"], "modes": ["remote", "hybrid"]},
}


def error_locs(exc: pytest.ExceptionInfo[ValidationError]) -> set[tuple]:
    return {error["loc"] for error in exc.value.errors()}


def test_full_profile_is_accepted() -> None:
    profile = CandidateProfile.model_validate(FULL_PROFILE)

    assert profile.experience[0].end_date is None
    assert profile.preferences.modes == ["remote", "hybrid"]


@pytest.mark.parametrize(
    "payload",
    [
        {"skills": ["Python"]},
        {"job_titles": ["Data Analyst"]},
        {"occupations": ["Accountant"]},
        {"experience": [{"title": "Cashier"}]},
    ],
)
def test_minimal_profile_is_accepted(payload: dict) -> None:
    profile = CandidateProfile.model_validate(payload)

    assert profile.education == []
    assert profile.seniority is None
    assert profile.preferences.modes == []


def test_text_is_stripped() -> None:
    profile = CandidateProfile.model_validate({"skills": ["  Python "]})

    assert profile.skills == ["Python"]


def test_documented_example_is_valid() -> None:
    example = CandidateProfile.model_json_schema()["examples"][0]

    CandidateProfile.model_validate(example)


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"skills": [], "job_titles": []},
        {"education": [{"degree": "Bachelor"}], "languages": [{"name": "English"}]},
    ],
)
def test_profile_without_matchable_content_is_rejected(payload: dict) -> None:
    with pytest.raises(ValidationError) as exc:
        CandidateProfile.model_validate(payload)

    assert error_locs(exc) == {()}


@pytest.mark.parametrize(
    ("payload", "loc"),
    [
        ({"skills": "Python"}, ("skills",)),
        ({"skills": [""]}, ("skills", 0)),
        ({"skills": ["   "]}, ("skills", 0)),
        ({"skills": ["x" * 201]}, ("skills", 0)),
        ({"skills": ["Python"] * 201}, ("skills",)),
        ({"skills": ["Python"], "years_experience": -1}, ("years_experience",)),
        ({"skills": ["Python"], "years_experience": "many"}, ("years_experience",)),
        ({"skills": ["Python"], "seniority": 3}, ("seniority",)),
        ({"skills": ["Python"], "unknown_field": 1}, ("unknown_field",)),
        ({"experience": [{"company": "Acme"}]}, ("experience", 0, "title")),
        (
            {"experience": [{"title": "Dev", "start_date": "03/2021"}]},
            ("experience", 0, "start_date"),
        ),
        ({"experience": [{"title": "Dev", "end_date": "2021-13"}]}, ("experience", 0, "end_date")),
        (
            {"skills": ["Python"], "languages": [{"proficiency": "advanced"}]},
            ("languages", 0, "name"),
        ),
        ({"skills": ["Python"], "certifications": [{}]}, ("certifications", 0, "name")),
        ({"skills": ["Python"], "preferences": {"modes": "remote"}}, ("preferences", "modes")),
        ({"skills": ["Python"], "preferences": {"salary": 1}}, ("preferences", "salary")),
    ],
)
def test_malformed_field_is_rejected(payload: dict, loc: tuple) -> None:
    with pytest.raises(ValidationError) as exc:
        CandidateProfile.model_validate(payload)

    assert loc in error_locs(exc)


@pytest.mark.parametrize(
    ("field", "item"),
    [
        ("experience", {"title": "Dev", "start_date": "2021-05", "end_date": "2021-04"}),
        ("experience", {"title": "Dev", "start_date": "2021", "end_date": "2020-12"}),
        ("education", {"degree": "Bachelor", "start_date": "2020", "end_date": "2019"}),
    ],
)
def test_period_ending_before_it_starts_is_rejected(field: str, item: dict) -> None:
    with pytest.raises(ValidationError) as exc:
        CandidateProfile.model_validate({"skills": ["Python"], field: [item]})

    assert error_locs(exc) == {(field, 0)}


def test_period_with_same_year_at_different_precision_is_accepted() -> None:
    item = {"title": "Dev", "start_date": "2021-03", "end_date": "2021"}

    CandidateProfile.model_validate({"experience": [item]})


def test_education_without_content_is_rejected() -> None:
    with pytest.raises(ValidationError) as exc:
        CandidateProfile.model_validate({"skills": ["Python"], "education": [{"end_date": "2020"}]})

    assert error_locs(exc) == {("education", 0)}
