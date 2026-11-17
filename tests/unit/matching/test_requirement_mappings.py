from types import SimpleNamespace

import pytest

from src.domain.job import SeniorityLevel
from src.domain.requirements import (
    bidirectional_skill_score,
    cefr,
    comparable_score,
    employment,
    language,
    mandatory_coverage_ratio,
)
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
    one_skill = bidirectional_skill_score(
        required_skills={"python"},
        preferred_skills=set(),
        nice_to_have_skills=set(),
        matched={"python"},
        candidate_core_skills={"python"},
    )
    assert one_skill == pytest.approx(100.0 * 3.25 * (2.25 / 3.5) / (2.25 * (2.25 / 3.5) + 1.0))
    assert comparable_score(
        candidate,
        job,
        skills={"python"},
        matched={"python"},
        requirements=["English B2"],
        relevant_experience=candidate.experience,
    ) == pytest.approx((one_skill + 100.0 + 0.0) / 3)
    # Unknown proficiency is omitted rather than scored as incompatible.
    candidate.languages[0].level = "fluent"
    assert comparable_score(
        candidate,
        job,
        skills={"python"},
        matched={"python"},
        requirements=["English B2"],
        relevant_experience=candidate.experience,
    ) == pytest.approx((one_skill + 100.0) / 2)
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
        ("Diferencial: Python", "PREFERRED"),
        ("Diferenciais: Python", "PREFERRED"),
        ("Python is not required", None),
        ("Required or optional: Python", "REQUIRED"),
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
    expected = bidirectional_skill_score(
        required_skills={"python"},
        preferred_skills=set(),
        nice_to_have_skills=set(),
        matched={"python"},
        candidate_core_skills={"python"},
    )
    assert comparable_score(
        candidate,
        job,
        skills={"python"},
        matched={"python"},
        requirements=[],
        relevant_experience=(),
    ) == pytest.approx(expected)
    coordinator = [SimpleNamespace(title="Project coordinator")]
    # ADR-027 places COORDINATOR (4) one step above SENIOR (3): gap=1 -> score 40.
    assert comparable_score(
        candidate,
        job,
        skills={"python"},
        matched={"python"},
        requirements=[],
        relevant_experience=coordinator,
    ) == pytest.approx((expected + 40.0) / 2)


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


@pytest.mark.parametrize(
    "n_req, n_match, expected",
    [
        (0, 0, None),
        (1, 1, 1.0),
        (2, 1, 0.5),
        (3, 3, 1.0),
        (4, 3, 1.0),
        (5, 4, 1.0),
        (10, 7, 1.0),
        (10, 5, 5 / 7),
    ],
)
def test_adr021_mandatory_coverage_thresholds_and_rounding(n_req, n_match, expected):
    required = {f"skill_{i}" for i in range(n_req)}
    matched = {f"skill_{i}" for i in range(n_match)}
    result = mandatory_coverage_ratio(required, matched)
    if expected is None:
        assert result is None
    else:
        assert result == pytest.approx(expected)


def test_sparse_job_is_damped_and_rich_meupadrinho_job_beats_one_skill_apibr_job():
    candidate_toolkit = {
        "python",
        "django",
        "postgresql",
        "docker",
        "aws",
        "redis",
        "git",
        "linux",
        "pytest",
        "rest",
    }
    apibr_sparse = bidirectional_skill_score(
        required_skills={"python"},
        preferred_skills=set(),
        nice_to_have_skills=set(),
        matched={"python"},
        candidate_core_skills=candidate_toolkit,
    )
    meupadrinho_rich = bidirectional_skill_score(
        required_skills={"python", "django", "postgresql", "docker", "aws", "pytest"},
        preferred_skills={"redis"},
        nice_to_have_skills={"graphql", "kubernetes", "terraform"},
        matched={"python", "django", "postgresql", "docker", "aws", "pytest", "redis"},
        candidate_core_skills=candidate_toolkit,
        exact_required={"python", "django", "postgresql", "docker", "aws", "pytest"},
        exact_matched={"python", "django", "postgresql", "docker", "aws", "pytest"},
    )
    assert 30.0 <= apibr_sparse <= 45.0
    assert meupadrinho_rich > 70.0
    assert meupadrinho_rich > apibr_sparse


def test_bidirectional_skill_score_invariants_and_non_core_exclusion():
    # Property checks across varied tier sizes, core toolkits and extra non-core hits.
    for n_req in (0, 1, 3, 6):
        for n_pref in (0, 2):
            for n_opt in (0, 4):
                if n_req + n_pref + n_opt == 0:
                    continue
                req = {f"r{i}" for i in range(n_req)}
                pref = {f"p{i}" for i in range(n_pref)}
                opt = {f"o{i}" for i in range(n_opt)}
                for n_core in (1, 2, 5, 10, 20):
                    core = {f"r{i}" for i in range(min(n_core, n_req))} | {
                        f"extra{i}" for i in range(max(0, n_core - n_req))
                    }
                    # Include non-core matches (e.g. old titles / education) in `matched`:
                    # precision must stay <= 1.0 and score <= 100.0, never inflating to 100.
                    non_core_hits = req | pref | opt
                    score = bidirectional_skill_score(
                        required_skills=req,
                        preferred_skills=pref,
                        nice_to_have_skills=opt,
                        matched=non_core_hits,
                        candidate_core_skills=core,
                    )
                    assert 0.0 <= score <= 100.0
                    # If only 1 of 5 required skills is in core, score cannot exceed 80 even
                    # when non-core skills cover the rest.
                    if n_req >= 5 and len(core & (req | pref | opt)) < 2:
                        assert score < 80.0

    # Broad 15-skill toolkit matching a 3-skill job stays >= 50 (not over-penalized).
    three_skill_broad = bidirectional_skill_score(
        required_skills={"python", "fastapi", "postgresql"},
        preferred_skills=set(),
        nice_to_have_skills=set(),
        matched={"python", "fastapi", "postgresql"},
        candidate_core_skills={"python", "fastapi", "postgresql"} | {f"s{i}" for i in range(12)},
    )
    assert three_skill_broad > 50.0


def test_long_optional_list_does_not_crush_qualified_candidate_and_exact_vs_approx_differs():
    candidate_skills = {"python", "sql", "fastapi"}
    required = {"python", "sql", "fastapi"}
    many_optional = {f"bonus_{i}" for i in range(12)}
    score_exact = bidirectional_skill_score(
        required_skills=required,
        preferred_skills=set(),
        nice_to_have_skills=many_optional,
        matched=required,
        candidate_core_skills=candidate_skills,
        exact_required=required,
        exact_matched=required,
    )
    # Approximate matches support score but do not satisfy ADR-021 mandatory coverage.
    score_approx = bidirectional_skill_score(
        required_skills=required,
        preferred_skills=set(),
        nice_to_have_skills=many_optional,
        matched=required,
        candidate_core_skills=candidate_skills,
        exact_required=required,
        exact_matched=set(),
    )
    assert score_exact > 70.0
    assert score_exact > score_approx


def test_precision_denominator_caps_at_15_and_exact_skill_matcher_excludes_typos():
    from src.extraction.taxonomy import compile_skill_matcher

    toolkit_15 = {f"skill_{i}" for i in range(15)}
    toolkit_30 = {f"skill_{i}" for i in range(30)}
    args: dict[str, set[str]] = {
        "required_skills": {"skill_0", "skill_1"},
        "preferred_skills": set(),
        "nice_to_have_skills": set(),
        "matched": {"skill_0", "skill_1"},
    }
    assert bidirectional_skill_score(**args, candidate_core_skills=toolkit_15) == pytest.approx(
        bidirectional_skill_score(**args, candidate_core_skills=toolkit_30)
    )

    matcher = compile_skill_matcher(["Pythom e PostgreSQL"])
    assert matcher.match({"python", "postgresql"}) == {"postgresql", "python"}
    assert matcher.match({"python", "postgresql"}, include_approximate=False) == {"postgresql"}


def test_seniority_ladder_and_symmetric_hard_filter():
    from src.domain.requirements import SENIORITY_LADDER, seniority_alignment

    assert SENIORITY_LADDER[SeniorityLevel.INTERN] < SENIORITY_LADDER[SeniorityLevel.JUNIOR]
    assert SENIORITY_LADDER[SeniorityLevel.JUNIOR] < SENIORITY_LADDER[SeniorityLevel.MID]
    assert SENIORITY_LADDER[SeniorityLevel.MID] < SENIORITY_LADDER[SeniorityLevel.SENIOR]
    assert SENIORITY_LADDER[SeniorityLevel.SENIOR] < SENIORITY_LADDER[SeniorityLevel.SPECIALIST]
    assert (
        SENIORITY_LADDER[SeniorityLevel.SPECIALIST] == SENIORITY_LADDER[SeniorityLevel.COORDINATOR]
    )

    # Gap >= 2 hard-filters in both directions.
    assert seniority_alignment(SeniorityLevel.JUNIOR, SeniorityLevel.SENIOR) == (False, 0.0, 0.0)
    assert seniority_alignment(SeniorityLevel.SENIOR, SeniorityLevel.JUNIOR) == (False, 0.0, 0.0)
    assert seniority_alignment(SeniorityLevel.INTERN, SeniorityLevel.MID) == (False, 0.0, 0.0)
    assert seniority_alignment(SeniorityLevel.COORDINATOR, SeniorityLevel.MID) == (False, 0.0, 0.0)

    # Gap == 1 stays allowed with score penalty + multiplier.
    assert seniority_alignment(SeniorityLevel.MID, SeniorityLevel.SENIOR) == (True, 40.0, 0.85)
    assert seniority_alignment(SeniorityLevel.SENIOR, SeniorityLevel.MID) == (True, 40.0, 0.85)

    # Exact or unknown never filters.
    assert seniority_alignment(SeniorityLevel.SPECIALIST, SeniorityLevel.COORDINATOR) == (
        True,
        100.0,
        1.0,
    )
    assert seniority_alignment(None, SeniorityLevel.SENIOR) == (True, None, 1.0)
    assert seniority_alignment(SeniorityLevel.SENIOR, None) == (True, None, 1.0)


def test_conservative_tenure_fallback_handles_overlap_career_change_and_dates():
    from datetime import date

    from src.domain.requirements import resolve_candidate_seniority

    as_of = date(2026, 6, 1)
    # Zero experiences -> JUNIOR.
    assert resolve_candidate_seniority(SimpleNamespace(experience=[]), ()) is SeniorityLevel.JUNIOR

    # Concurrent 6-month roles stay 6 months (< 12) -> JUNIOR.
    concurrent = [
        SimpleNamespace(
            title="Backend Developer", start_date=date(2026, 1, 1), end_date=date(2026, 6, 1)
        ),
        SimpleNamespace(title="Freelance Dev", start_date=date(2026, 1, 1), end_date=None),
    ]
    assert (
        resolve_candidate_seniority(
            SimpleNamespace(experience=concurrent), concurrent, as_of_date=as_of
        )
        is SeniorityLevel.JUNIOR
    )

    # >= 60 months across relevant experiences -> SENIOR.
    long_relevant = [
        SimpleNamespace(title="Software Engineer", start_date=date(2021, 1, 1), end_date=None)
    ]
    assert (
        resolve_candidate_seniority(
            SimpleNamespace(experience=long_relevant), long_relevant, as_of_date=as_of
        )
        is SeniorityLevel.SENIOR
    )

    # Career changer: 60+ months unrelated (relevant_experience=()) stays unknown, not SENIOR.
    assert (
        resolve_candidate_seniority(SimpleNamespace(experience=long_relevant), (), as_of_date=as_of)
        is None
    )

    # Explicit relevant title marker overrides tenure.
    marked = [
        SimpleNamespace(title="Tech Lead", start_date=date(2026, 1, 1), end_date=date(2026, 4, 1))
    ]
    assert (
        resolve_candidate_seniority(
            SimpleNamespace(experience=marked),
            [SimpleNamespace(title="Junior Developer", start_date=date(2026, 1, 1), end_date=None)],
            as_of_date=as_of,
        )
        is SeniorityLevel.JUNIOR
    )


def test_estagiario_alias_and_stale_junior_marker_overridden_by_senior_tenure():
    from datetime import date

    from src.domain.requirements import explicit_seniority, resolve_candidate_seniority

    assert explicit_seniority("Estagiário Python") is SeniorityLevel.INTERN
    assert explicit_seniority("Estagiária de Dados") is SeniorityLevel.INTERN

    as_of = date(2026, 6, 1)
    career = [
        SimpleNamespace(
            title="Desenvolvedor Júnior",
            start_date=date(2020, 1, 1),
            end_date=date(2021, 1, 1),
        ),
        SimpleNamespace(
            title="Engenheiro de Software",
            start_date=date(2021, 1, 2),
            end_date=None,
        ),
    ]
    assert (
        resolve_candidate_seniority(SimpleNamespace(experience=career), career, as_of_date=as_of)
        is SeniorityLevel.SENIOR
    )
