from datetime import date

import pytest
from sqlalchemy.dialects import postgresql

from src.matching.textual import candidate_query_text, textual_statement
from src.normalization.candidate.curriculum import (
    Competency,
    Education,
    Experience,
    Language,
    NormalizedCandidate,
    Project,
)


def test_candidate_projection_keeps_all_sections_without_identity_or_dates():
    candidate = NormalizedCandidate(
        experience=(Experience("Company", "Cargo", "Experiência", date(2020, 1, 1), None),),
        education=(Education("Institution", "Curso", "tecnico", "concluido", date.min, date.min),),
        projects=(Project("Projeto", "Descrição", "Python"),),
        competencies=(Competency("Competência", "avançado"),),
        languages=(Language("Inglês", "fluente"),),
    )
    result = candidate_query_text(candidate)
    assert result.splitlines() == [
        "Cargo",
        "Experiência",
        "Curso",
        "tecnico",
        "Projeto",
        "Descrição",
        "Python",
        "Competência",
        "Inglês",
        "fluente",
    ]
    assert "Company" not in result
    assert "2020" not in result


def test_empty_candidate_has_no_invented_query_evidence():
    assert candidate_query_text(NormalizedCandidate((), (), (), (), ())) == ""


def test_query_data_is_bound_and_readiness_defaults_closed():
    submitted = "private' | ! & database; --"
    compiled = textual_statement(submitted).compile(dialect=postgresql.dialect())
    assert submitted not in str(compiled)
    assert submitted in compiled.params.values()
    assert "WHERE false" in str(compiled)


@pytest.mark.parametrize("limit", [0, -1, True, 1.5, "10"])
def test_invalid_internal_retrieval_limit_is_rejected(limit):
    with pytest.raises(ValueError, match="positive integer"):
        textual_statement("python", limit=limit)
