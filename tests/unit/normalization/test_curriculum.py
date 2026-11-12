from copy import deepcopy

import pytest

from src.api.app import CURRICULUM_EXAMPLE
from src.normalization.candidate import normalize_curriculum, to_candidate_profile
from src.schemas.candidate.curriculum import CurriculumRequest


def test_adapter_preserves_every_section_and_omits_the_curriculum_id():
    request = CurriculumRequest.model_validate(CURRICULUM_EXAMPLE)
    profile = to_candidate_profile(request)
    assert profile.skills == ["Python"]
    assert profile.competencies[0].level == "intermediario"
    assert profile.education[0].level == "tecnologo"
    assert profile.education[0].status == "em_andamento"
    assert profile.education[0].start_date == "2024-02-01"
    assert profile.education[0].end_date == "2026-12-01"
    assert profile.experience[0].start_date == "2025-01-01"
    assert profile.experience[0].end_date is None
    assert profile.academic_projects[0].technologies == "Java, Clean Architecture, Docker"
    assert profile.languages[0].proficiency == "B2"
    assert str(request.curriculo_id) not in profile.model_dump_json()
    assert profile.locations == []
    assert profile.preferences.modes == []
    assert profile.seniority is None
    assert profile.years_experience is None


def test_all_empty_sections_adapt_without_inventing_candidate_data():
    request = CurriculumRequest.model_validate(
        {key: value if key == "curriculo_id" else [] for key, value in CURRICULUM_EXAMPLE.items()}
    )
    profile = to_candidate_profile(request)
    assert (
        profile.skills == profile.experience == profile.education == profile.academic_projects == []
    )


@pytest.mark.parametrize(
    ("section", "field", "maximum"),
    [
        ("formacoes", "education", 20),
        ("experiencias", "experience", 50),
        ("projetos", "academic_projects", 50),
        ("competencias", "competencies", 200),
        ("idiomas", "languages", 20),
    ],
)
@pytest.mark.parametrize("extra", [0, 1, 3])
def test_historical_collection_limits_do_not_reject_public_inputs(section, field, maximum, extra):
    payload = deepcopy(CURRICULUM_EXAMPLE)
    payload[section] *= maximum + extra
    request = CurriculumRequest.model_validate(payload)
    profile = to_candidate_profile(request)
    candidate = normalize_curriculum(request)
    assert len(getattr(profile, field)) == maximum + extra
    normalized_field = "projects" if field == "academic_projects" else field
    assert len(getattr(candidate, normalized_field)) == maximum + extra
    assert str(request.curriculo_id) not in profile.model_dump_json()
    assert not hasattr(candidate, "curriculo_id")


def test_adapter_does_not_impose_historical_internal_text_bounds():
    payload = deepcopy(CURRICULUM_EXAMPLE)
    payload["competencias"][0]["descricao"] = "x" * 201
    payload["competencias"][0]["nivel"] = "x" * 201
    payload["experiencias"][0].update(empresa="x" * 201, cargo="x" * 201, descricao="x" * 6000)
    payload["projetos"][0]["descricao"] = "x" * 2000
    profile = to_candidate_profile(CurriculumRequest.model_validate(payload))
    assert len(profile.skills[0]) == 201
    assert len(profile.experience[0].description) == 6000


def test_both_adapters_preserve_source_valid_long_text_and_date_types():
    payload = deepcopy(CURRICULUM_EXAMPLE)
    text = "x" * 6000
    payload["competencias"][0].update(descricao=text, nivel=text)
    payload["idiomas"][0].update(idioma=text, nivel=text)
    payload["experiencias"][0].update(empresa=text, cargo=text, descricao=text)
    payload["formacoes"][0].update(instituicao="i" * 200, curso="c" * 200)
    payload["projetos"][0].update(titulo="t" * 200, descricao="d" * 2000, tecnologias="s" * 300)
    request = CurriculumRequest.model_validate(payload)
    profile = to_candidate_profile(request)
    candidate = normalize_curriculum(request)
    assert profile.skills == [text]
    assert profile.competencies[0].level == candidate.competencies[0].level == text
    assert profile.languages[0].name == candidate.languages[0].name == text
    assert profile.languages[0].proficiency == candidate.languages[0].level == text
    assert profile.experience[0].company == candidate.experience[0].company == text
    assert profile.experience[0].title == candidate.experience[0].title == text
    assert profile.experience[0].description == candidate.experience[0].description == text
    assert profile.education[0].institution == candidate.education[0].institution == "i" * 200
    assert profile.education[0].degree == candidate.education[0].course == "c" * 200
    assert profile.academic_projects[0].title == candidate.projects[0].title == "t" * 200
    assert (
        profile.academic_projects[0].description == candidate.projects[0].description == "d" * 2000
    )
    assert (
        profile.academic_projects[0].technologies == candidate.projects[0].technologies == "s" * 300
    )
    assert profile.experience[0].start_date == candidate.experience[0].start_date.isoformat()
    assert profile.education[0].end_date == candidate.education[0].end_date.isoformat()
    assert profile.experience[0].end_date is candidate.experience[0].end_date is None
