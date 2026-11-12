from datetime import date

import pytest
from sqlalchemy import column, true
from sqlalchemy.dialects import postgresql

from src.indexing.textual import any_term_query, job_search_document, requirement_search_document
from src.matching.textual import candidate_query_text, textual_statement
from src.normalization.candidate.curriculum import (
    Competency,
    Education,
    Experience,
    Language,
    NormalizedCandidate,
    Project,
)
from src.persistence.job.job import Job


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


def _sql(expression):
    return str(
        expression.compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True})
    )


def test_document_preserves_accepted_fields_weights_and_json_text():
    sql = _sql(job_search_document())
    assert "CAST(jobs.skills AS TEXT)" in sql
    assert "CAST(jobs.keywords AS TEXT)" in sql
    assert "CAST(jobs.location AS TEXT)" in sql
    assert sql.count("'A'") == sql.count("'B'") == sql.count("'D'") == 1
    assert "'C'" not in sql
    assert "jobs.title" in sql and "jobs.company" in sql and "jobs.description" in sql
    assert "jsonb_to_tsvector" not in sql
    assert "concat_ws" not in sql


def test_requirement_helper_supports_default_and_explicit_columns():
    assert "job_requirements.text" in _sql(requirement_search_document())
    sql = _sql(requirement_search_document(column("normalized_text")))
    assert "normalized_text" in sql and "'B'" in sql
    assert "coalesce" in sql and "pg_catalog.portuguese" in sql
    assert "job_requirements" not in sql


def test_query_casts_parsed_lexemes_without_restemming():
    sql = _sql(any_term_query("desenvolvedores | Python"))
    assert "plainto_tsquery" in sql and "AS TSQUERY" in sql
    assert "to_tsquery(" not in sql.replace("plainto_tsquery(", "")
    assert "' & ', ' | '" in sql


def test_union_gates_both_paths_and_combines_before_bounding():
    sql = _sql(textual_statement("Python", readiness=Job.id == 7).where(Job.id.in_([7, 9])))
    assert sql.count("jobs.id = 7") == 2
    assert sql.count("jobs.status = 'ACTIVE'") == 2
    assert "UNION ALL" in sql and "max(ts_rank_cd" in sql and "sum(" in sql
    assert "100.0 *" in sql and "1.0 +" in sql
    assert "jobs.id IN (7, 9)" in sql
    assert (
        "publication_date DESC NULLS LAST, jobs.platform ASC, jobs.source_job_id ASC, jobs.id ASC"
        in sql
    )
    assert "WHERE false" not in _sql(textual_statement("Python", readiness=true()))


def test_retrieve_textual_passes_default_readiness_and_preserves_tuple_shape():
    from src.matching.textual import retrieve_textual

    job = object()

    class Session:
        def execute(self, statement):
            self.statement = statement
            return [(job, 12)]

    session = Session()
    rows = retrieve_textual(session, NormalizedCandidate((), (), (), (), ()))
    assert rows == [(job, 12.0)]
    assert _sql(session.statement).count("WHERE false") == 2
