from copy import deepcopy

import pytest

from src.api.app import CURRICULUM_EXAMPLE
from src.normalization.candidate.curriculum import to_candidate_profile
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
    ("section", "maximum"),
    [
        ("formacoes", 20),
        ("experiencias", 50),
        ("projetos", 50),
        ("competencias", 200),
        ("idiomas", 20),
    ],
)
def test_every_accepted_collection_boundary_adapts(section, maximum):
    payload = deepcopy(CURRICULUM_EXAMPLE)
    payload[section] *= maximum
    to_candidate_profile(CurriculumRequest.model_validate(payload))


def test_adapter_does_not_impose_historical_internal_text_bounds():
    payload = deepcopy(CURRICULUM_EXAMPLE)
    payload["competencias"][0]["descricao"] = "x" * 201
    payload["competencias"][0]["nivel"] = "x" * 201
    payload["experiencias"][0].update(empresa="x" * 201, cargo="x" * 201, descricao="x" * 6000)
    payload["projetos"][0]["descricao"] = "x" * 2000
    profile = to_candidate_profile(CurriculumRequest.model_validate(payload))
    assert len(profile.skills[0]) == 201
    assert len(profile.experience[0].description) == 6000
