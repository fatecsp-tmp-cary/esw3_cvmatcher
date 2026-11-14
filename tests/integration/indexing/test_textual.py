from datetime import UTC, datetime

import pytest
from sqlalchemy import Index, literal, select, text, true
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.schema import CreateIndex, DropIndex

from src.indexing.textual import any_term_query, job_search_document
from src.matching.textual import retrieve_textual, textual_statement
from src.normalization.candidate.curriculum import NormalizedCandidate
from src.persistence.job.job import Job, JobStatus
from src.persistence.job.job_source import JobSource
from src.persistence.job.skill import JobRequirement, RequirementClass


@pytest.fixture
def session(db_session):
    source = JobSource(name="fts-fixture", type="api", polling_mode="INCREMENTAL")
    db_session.add(source)
    db_session.flush()
    db_session.info["fts_source_id"] = source.id
    return db_session


def add_job(session, identity, **values):
    job = Job(
        source_id=session.info["fts_source_id"],
        platform="apibr",
        source_job_id=identity,
        title="Vaga",
        status=JobStatus.ACTIVE,
    )
    for key, value in values.items():
        setattr(job, key, value)
    session.add(job)
    session.flush()
    return job


def identities(rows):
    return [row[0].source_job_id for row in rows]


def test_portuguese_stemming_and_any_term_queries(session):
    add_job(session, "dev", title="Desenvolvedores Python")
    rows = session.execute(textual_statement("desenvolvedor ausente", readiness=true())).all()
    assert identities(rows) == ["dev"]
    assert 0 < rows[0][1] < 100
    for query in ("", "de e para", "' | ! & () :*"):
        assert session.execute(textual_statement(query, readiness=true())).all() == []


def test_json_text_rendering_and_unicode_follow_accepted_adr005(session):
    add_job(
        session,
        "unicode",
        title="Operação",
        skills=["Kubernetes", "Café"],
        keywords=["Quasar"],
        location={"searchablekey": "Paraná"},
    )
    for query in ("Kubernetes", "Paraná", "Café", "Quasar", "searchablekey"):
        assert identities(session.execute(textual_statement(query, readiness=true()))) == [
            "unicode"
        ]
    requirement = literal(["Rust"], type_=JSONB)
    assert identities(
        session.execute(textual_statement("Rust", readiness=true(), requirements=requirement))
    ) == ["unicode"]


def test_readiness_fail_closed_and_availability_independent(session):
    for state in JobStatus:
        add_job(session, state.value, title="Python", status=state)
    active = session.scalar(select(Job).where(Job.status == JobStatus.ACTIVE))
    assert session.execute(textual_statement("Python")).all() == []
    assert identities(
        session.execute(textual_statement("Python", readiness=Job.id == active.id))
    ) == ["ACTIVE"]
    assert session.execute(textual_statement("Python", readiness=Job.id != active.id)).all() == []


def test_weighting_stable_source_ties_and_no_geographic_exclusion(session):
    add_job(session, "z-body", description="Python")
    add_job(session, "c-company", company="Python")
    add_job(session, "b-skills", skills=["Python"])
    add_job(session, "a-title", title="Python", location={"city": "Tokyo"})
    add_job(session, "0-title", platform="other", title="Python", location={"city": "Lisboa"})
    statement = textual_statement("Python", readiness=true())
    first = session.execute(statement).all()
    second = session.execute(statement).all()
    assert identities(first) == ["a-title", "b-skills", "0-title", "c-company", "z-body"]
    assert [(job.id, score) for job, score in first] == [(job.id, score) for job, score in second]
    assert all(0 <= score <= 100 for _, score in first)
    assert identities(session.execute(textual_statement("Python", readiness=true(), limit=2))) == [
        "a-title",
        "b-skills",
    ]


def test_requirements_weight_and_empty_candidate(session):
    add_job(session, "one")
    requirements = literal(["PostgreSQL"], type_=JSONB)
    rows = session.execute(
        textual_statement("PostgreSQL", readiness=true(), requirements=requirements)
    ).all()
    assert identities(rows) == ["one"]
    assert rows[0][1] > 0
    assert (
        retrieve_textual(session, NormalizedCandidate((), (), (), (), ()), readiness=true()) == []
    )


def test_plain_input_operators_cannot_turn_into_boolean_tsquery(session):
    add_job(session, "python", title="Python")
    add_job(session, "rust", title="Rust")
    for query in (
        "Python & Rust",
        "Python | Rust",
        "Python !Rust",
        "Python '); DROP TABLE jobs; --",
    ):
        assert "python" in identities(session.execute(textual_statement(query, readiness=true())))
    assert session.scalar(select(text("count(*)")).select_from(Job)) == 2
    query = session.scalar(select(any_term_query("python rust")))
    assert " | " in query
    assert " & " not in query


def test_search_expression_supports_immutable_gin_index(session):
    index = Index(
        "ix_test_fts_document",
        job_search_document(),
        postgresql_using="gin",
        _table=Job.__table__,
    )
    try:
        session.execute(CreateIndex(index))
        definition = session.scalar(
            text("SELECT indexdef FROM pg_indexes WHERE indexname = 'ix_test_fts_document'")
        )
        assert "USING gin" in definition
        assert "portuguese" in definition
        session.execute(DropIndex(index))
    finally:
        Job.__table__.indexes.discard(index)


def test_requirement_rows_combined_once_and_normalized_after_raw_sum(session):
    from src.matching.textual import search_active_jobs

    both = add_job(session, "both", title="Python")
    only_requirement = add_job(session, "requirement")
    for job in (both, only_requirement):
        for _ in range(2):
            session.add(
                JobRequirement(
                    job_id=job.id, text="Python", requirement_class=RequirementClass.REQUIRED
                )
            )
    session.flush()
    raw = search_active_jobs(session, "Python", readiness=true())
    bounded = session.execute(textual_statement("Python", readiness=true())).all()
    assert identities(bounded) == ["both", "requirement"]
    assert len(raw) == len(bounded) == 2
    for match, (job, score) in zip(raw, bounded, strict=True):
        assert match.job.id == job.id
        assert score == pytest.approx(100 * match.score / (1 + match.score))
    # Repeated rows do not multiply rank, and missing readiness withholds both paths.
    assert raw[0].score == pytest.approx(1.4)
    assert raw[1].score == pytest.approx(0.4)
    assert session.execute(textual_statement("Python")).all() == []
    assert identities(
        session.execute(textual_statement("Python", readiness=Job.id == both.id))
    ) == ["both"]
    pool = textual_statement("Python", readiness=true(), limit=2).where(
        Job.id.in_([only_requirement.id])
    )
    assert identities(session.execute(pool)) == ["requirement"]


def test_publication_ties_descending_and_nulls_last(session):
    add_job(session, "a-null", title="Python")
    add_job(session, "b-old", title="Python", publication_date=datetime(2024, 1, 1, tzinfo=UTC))
    add_job(session, "z-new", title="Python", publication_date=datetime(2025, 1, 1, tzinfo=UTC))
    assert identities(session.execute(textual_statement("Python", readiness=true()))) == [
        "z-new",
        "b-old",
        "a-null",
    ]
