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
            "start_date": "2021-03-15",
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

# Smallest valid profile: skills plus role context.
BASE = {"skills": ["Python"], "job_titles": ["Developer"]}


def error_locs(exc: pytest.ExceptionInfo[ValidationError]) -> set[tuple]:
    return {error["loc"] for error in exc.value.errors()}


def test_full_profile_is_accepted() -> None:
    profile = CandidateProfile.model_validate(FULL_PROFILE)

    assert profile.experience[0].end_date is None
    assert profile.preferences.modes == ["remote", "hybrid"]


@pytest.mark.parametrize(
    "payload",
    [
        {"skills": ["Excel"], "job_titles": ["Data Analyst"]},
        {"skills": ["Customer service"], "experience": [{"title": "Cashier"}]},
    ],
)
def test_minimal_profile_is_accepted(payload: dict) -> None:
    profile = CandidateProfile.model_validate(payload)

    assert profile.education == []
    assert profile.seniority is None
    assert profile.preferences.modes == []


def test_text_is_stripped() -> None:
    profile = CandidateProfile.model_validate({**BASE, "skills": ["  Python "]})

    assert profile.skills == ["Python"]


def test_documented_example_is_valid() -> None:
    example = CandidateProfile.model_json_schema()["examples"][0]

    CandidateProfile.model_validate(example)


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"job_titles": ["Developer"]},
        {"skills": [], "job_titles": ["Developer"]},
    ],
)
def test_profile_without_skills_is_rejected(payload: dict) -> None:
    with pytest.raises(ValidationError) as exc:
        CandidateProfile.model_validate(payload)

    assert ("skills",) in error_locs(exc)


@pytest.mark.parametrize(
    "payload",
    [
        {"skills": ["Python"]},
        {"skills": ["Python"], "job_titles": [], "experience": []},
        {"skills": ["Python"], "occupations": ["Accountant"], "education": [{"degree": "BSc"}]},
    ],
)
def test_profile_without_role_context_is_rejected(payload: dict) -> None:
    with pytest.raises(ValidationError) as exc:
        CandidateProfile.model_validate(payload)

    assert error_locs(exc) == {()}


@pytest.mark.parametrize(
    ("changes", "loc"),
    [
        ({"skills": "Python"}, ("skills",)),
        ({"skills": [""]}, ("skills", 0)),
        ({"skills": ["   "]}, ("skills", 0)),
        ({"skills": ["x" * 201]}, ("skills", 0)),
        ({"skills": ["Python"] * 201}, ("skills",)),
        ({"years_experience": -1}, ("years_experience",)),
        ({"years_experience": "many"}, ("years_experience",)),
        ({"seniority": 3}, ("seniority",)),
        ({"unknown_field": 1}, ("unknown_field",)),
        ({"experience": [{"company": "Acme"}]}, ("experience", 0, "title")),
        ({"languages": [{"proficiency": "advanced"}]}, ("languages", 0, "name")),
        ({"certifications": [{}]}, ("certifications", 0, "name")),
        ({"preferences": {"modes": "remote"}}, ("preferences", "modes")),
        ({"preferences": {"salary": 1}}, ("preferences", "salary")),
    ],
)
def test_malformed_field_is_rejected(changes: dict, loc: tuple) -> None:
    with pytest.raises(ValidationError) as exc:
        CandidateProfile.model_validate({**BASE, **changes})

    assert loc in error_locs(exc)


@pytest.mark.parametrize("value", ["2021", "2021-03", "2021-03-15", "2024-02-29"])
def test_iso_date_is_accepted(value: str) -> None:
    CandidateProfile.model_validate({**BASE, "experience": [{"title": "Dev", "start_date": value}]})


@pytest.mark.parametrize(
    "value",
    [
        "15-03-2021",
        "15/03/2021",
        "03/2021",
        "2021/03",
        "21-03",
        "2021-13",
        "2021-02-30",
        "2023-02-29",
    ],
)
def test_non_iso_or_impossible_date_is_rejected(value: str) -> None:
    with pytest.raises(ValidationError) as exc:
        CandidateProfile.model_validate(
            {**BASE, "experience": [{"title": "Dev", "start_date": value}]}
        )

    assert error_locs(exc) == {("experience", 0, "start_date")}


@pytest.mark.parametrize(
    ("field", "item"),
    [
        ("experience", {"title": "Dev", "start_date": "2021-05", "end_date": "2021-04"}),
        ("experience", {"title": "Dev", "start_date": "2021", "end_date": "2020-12"}),
        ("experience", {"title": "Dev", "start_date": "2021-03-15", "end_date": "2021-03-14"}),
        ("education", {"degree": "Bachelor", "start_date": "2020", "end_date": "2019"}),
    ],
)
def test_period_ending_before_it_starts_is_rejected(field: str, item: dict) -> None:
    with pytest.raises(ValidationError) as exc:
        CandidateProfile.model_validate({**BASE, field: [item]})

    assert error_locs(exc) == {(field, 0)}


@pytest.mark.parametrize(
    ("start", "end"),
    [("2021-03", "2021"), ("2021-03-15", "2021-03"), ("2021", "2021-01-01")],
)
def test_period_with_same_date_at_different_precision_is_accepted(start: str, end: str) -> None:
    item = {"title": "Dev", "start_date": start, "end_date": end}

    CandidateProfile.model_validate({**BASE, "experience": [item]})


def test_education_without_content_is_rejected() -> None:
    with pytest.raises(ValidationError) as exc:
        CandidateProfile.model_validate({**BASE, "education": [{"end_date": "2020"}]})

    assert error_locs(exc) == {("education", 0)}
