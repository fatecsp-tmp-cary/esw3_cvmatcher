"""Regressions for adapting every valid public request without tightening it."""

from dataclasses import asdict
from datetime import date
from uuid import UUID

from src.normalization.candidate.curriculum import normalize_curriculum
from src.schemas.candidate.curriculum import CurriculumRequest


def request(**sections):
    return CurriculumRequest(
        curriculo_id=UUID(int=1),
        **dict.fromkeys(("formacoes", "experiencias", "projetos", "competencias", "idiomas"), [])
        | sections,
    )


def test_empty_sections_are_valid_and_identifier_is_not_retained():
    candidate = normalize_curriculum(request())
    assert all(value == () for value in asdict(candidate).values())
    assert "curriculo_id" not in asdict(candidate)
    assert str(UUID(int=1)) not in repr(candidate)


def test_preserves_all_sections_dates_levels_and_order():
    source = request(
        experiencias=[
            {
                "empresa": "Empresa",
                "cargo": "Dev",
                "descricao": "Python",
                "inicio": "2020-01-01",
                "fim": None,
            }
        ],
        formacoes=[
            {
                "instituicao": "Universidade",
                "curso": "Computação",
                "nivel": "graduacao",
                "status": "em_andamento",
                "inicio": "2019-03-01",
                "fim": "2027-12-01",
            }
        ],
        projetos=[{"titulo": "Projeto", "descricao": "Detalhes", "tecnologias": "Python, SQL"}],
        competencias=[
            {"descricao": "Python", "nivel": "avançado"},
            {"descricao": "SQL", "nivel": "iniciante"},
        ],
        idiomas=[{"idioma": "Português", "nivel": "nativo"}],
    )
    candidate = normalize_curriculum(source)
    assert asdict(candidate.experience[0]) == {
        "company": "Empresa",
        "title": "Dev",
        "description": "Python",
        "start_date": date(2020, 1, 1),
        "end_date": None,
    }
    assert asdict(candidate.education[0]) == {
        "institution": "Universidade",
        "course": "Computação",
        "level": "graduacao",
        "status": "em_andamento",
        "start_date": date(2019, 3, 1),
        "end_date": date(2027, 12, 1),
    }
    assert asdict(candidate.projects[0]) == {
        "title": "Projeto",
        "description": "Detalhes",
        "technologies": "Python, SQL",
    }
    assert [(x.description, x.level) for x in candidate.competencies] == [
        ("Python", "avançado"),
        ("SQL", "iniciante"),
    ]
    assert asdict(candidate.languages[0]) == {"name": "Português", "level": "nativo"}
    source.experiencias[0].descricao = "changed"
    assert candidate.experience[0].description == "Python"
    assert "Empresa" not in repr(candidate.experience[0])


def test_does_not_apply_legacy_text_or_collection_caps():
    text = "x" * 6000
    source = request(
        experiencias=[
            {"empresa": text, "cargo": text, "descricao": text, "inicio": "2020-01-01", "fim": None}
        ]
        * 51,
        competencias=[{"descricao": text, "nivel": text}] * 201,
        idiomas=[{"idioma": text, "nivel": text}] * 21,
    )
    candidate = normalize_curriculum(source)
    assert len(candidate.experience) == 51
    assert len(candidate.competencies) == 201
    assert len(candidate.languages) == 21
    assert all(x.description == text for x in candidate.experience)
    assert candidate.competencies[0].level == text
    assert candidate.languages[0].name == text
