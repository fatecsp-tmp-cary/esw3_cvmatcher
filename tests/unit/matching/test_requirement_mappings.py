from types import SimpleNamespace

import pytest

from src.domain.job import SeniorityLevel
from src.domain.requirements import cefr, comparable_score, employment, language
from src.extraction.classification import classify


@pytest.mark.parametrize(
    "value, expected", [("B2", "B2"), ("CEFR c1", "C1"), ("fluente", None), ("intermediate", None)]
)
def test_cefr_requires_an_explicit_unambiguous_level(value, expected):
    assert cefr(value) == expected


def test_language_and_employment_aliases_do_not_conflate_legal_types():
    assert language("Inglês") == language("English") == "en"
    assert employment("pessoa jurídica") == "PJ"
    assert employment("carteira assinada") == "CLT"
    assert employment("full time") is None
    assert employment("contractor") is None


def test_equal_available_dimensions_and_unknowns_are_score_only():
    candidate = SimpleNamespace(
        experience=[SimpleNamespace(title="Senior developer")],
        languages=[SimpleNamespace(name="Inglês", level="B1")],
    )
    job = SimpleNamespace(seniority_level=SeniorityLevel.SENIOR, title="Developer")
    assert comparable_score(
        candidate,
        job,
        skills={"python"},
        matched={"python"},
        requirements=["English B2"],
        relevant_experience=candidate.experience,
    ) == pytest.approx(200 / 3)
    # Unknown proficiency is omitted rather than scored as incompatible.
    candidate.languages[0].level = "fluent"
    assert (
        comparable_score(
            candidate,
            job,
            skills={"python"},
            matched={"python"},
            requirements=["English B2"],
            relevant_experience=candidate.experience,
        )
        == 100
    )
    # No public employment preference is invented from a past job/company.
    assert (
        comparable_score(
            candidate,
            job,
            skills=set(),
            matched=set(),
            requirements=["CLT"],
            relevant_experience=candidate.experience,
        )
        == 100
    )


@pytest.mark.parametrize(
    "text, expected",
    [
        ("Required: Python", "REQUIRED"),
        ("Requisitos:\nPython", "REQUIRED"),
        ("Python é desejável", "PREFERRED"),
        ("Optional: Python", "NICE_TO_HAVE"),
        ("Nice-to-have: Python", "NICE_TO_HAVE"),
        ("Diferencial: Python", "NICE_TO_HAVE"),
        ("Diferenciais: Python", "NICE_TO_HAVE"),
        ("Python is not required", None),
        ("Required or optional: Python", None),
        ("Requisitos:\nOther section\nPython", None),
        ("Python", None),
    ],
)
def test_context_classification_does_not_guess_from_presence(text, expected):
    start = text.index("Python")
    assert classify(text, start, start + 6) == expected


def test_unrelated_or_nonordinal_seniority_is_unknown_not_a_penalty():
    candidate = SimpleNamespace(experience=[SimpleNamespace(title="Senior nurse")], languages=[])
    job = SimpleNamespace(seniority_level=SeniorityLevel.SENIOR, title="Developer")
    assert (
        comparable_score(
            candidate,
            job,
            skills={"python"},
            matched={"python"},
            requirements=[],
            relevant_experience=(),
        )
        == 100.0
    )
    coordinator = [SimpleNamespace(title="Project coordinator")]
    assert (
        comparable_score(
            candidate,
            job,
            skills={"python"},
            matched={"python"},
            requirements=[],
            relevant_experience=coordinator,
        )
        == 100.0
    )


def test_missing_candidate_skills_are_omitted_but_explicit_nonmatching_skills_compare():
    candidate = SimpleNamespace(languages=[SimpleNamespace(name="English", level="B2")])
    job = SimpleNamespace(seniority_level=None, title="Developer")
    args = {"skills": {"python"}, "matched": set(), "requirements": ["English B2"]}
    # A language-only CV says nothing about technical skills: do not halve its
    # known language score merely because the job lists Python.
    assert comparable_score(candidate, job, candidate_skills=set(), **args) == 100.0
    # Explicit Java evidence establishes an available skills dimension even
    # though it does not match this job's Python evidence.
    assert comparable_score(candidate, job, candidate_skills={"java"}, **args) == 50.0
