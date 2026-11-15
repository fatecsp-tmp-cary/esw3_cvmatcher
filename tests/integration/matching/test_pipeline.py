"""Pipeline boundary regressions with real retrieval and deterministic inference."""

import logging
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from src.embeddings.config import EmbeddingConfig
from src.matching import pipeline as module
from src.matching.pipeline import MatchingPipeline
from src.persistence.embedding import JobEmbedding
from src.persistence.extraction import JobExtraction
from src.persistence.job.job import Job, JobStatus
from src.persistence.job.job_source import JobSource
from src.schemas.candidate.curriculum import CurriculumRequest

CONFIG = EmbeddingConfig()
EXTRACTION = "pipeline-fixture-v1"
VECTOR = [1.0] + [0.0] * 383


class Encoder:
    config = CONFIG
    model_version = CONFIG.model_version

    def __init__(self, result=None):
        self.calls = []
        self.result = result

    def encode_queries(self, texts):
        self.calls.append(list(texts))
        return self.result if self.result is not None else [VECTOR for _ in texts]


def request(*, experience=False, skill=None):
    return CurriculumRequest(
        curriculo_id=uuid4(),
        formacoes=[],
        experiencias=[
            {
                "empresa": "Private company",
                "cargo": "Python",
                "descricao": "Build APIs",
                "inicio": "2024-01-01",
                "fim": None,
            }
        ]
        if experience
        else [],
        projetos=[],
        competencias=[{"descricao": skill, "nivel": "intermediario"}] if skill else [],
        idiomas=[],
    )


@pytest.fixture
def setup(db_session):
    source = JobSource(name="pipeline-fixture", type="api", polling_mode="INCREMENTAL")
    db_session.add(source)
    db_session.flush()

    def add(identity, *, vector=VECTOR, **values):
        job = Job(
            source_id=source.id,
            platform="fixture",
            source_job_id=identity,
            title="Python",
            status=JobStatus.ACTIVE,
            content_hash="hash-" + identity,
            embedding=vector,
        )
        for name, value in values.items():
            setattr(job, name, value)
        db_session.add(job)
        db_session.flush()
        now = datetime.now(UTC)
        db_session.add_all(
            [
                JobExtraction(
                    job_id=job.id,
                    content_hash=job.content_hash,
                    config_version=EXTRACTION,
                    status="SUCCEEDED",
                    attempts=1,
                    evidence=[],
                    updated_at=now,
                ),
                JobEmbedding(
                    job_id=job.id,
                    content_hash=job.content_hash,
                    model_version=CONFIG.model_version,
                    extraction_version=EXTRACTION,
                    status="SUCCEEDED",
                    attempts=1,
                    updated_at=now,
                ),
            ]
        )
        db_session.flush()
        return job

    def pipeline(encoder=None):
        return MatchingPipeline(
            lambda: Session(bind=db_session.connection(), join_transaction_mode="create_savepoint"),
            encoder or Encoder(),
            EXTRACTION,
        )

    return add, pipeline


def test_empty_candidate_does_not_encode_or_open_a_session():
    encoder = Encoder()

    def no_session():
        pytest.fail("Empty input must return before database access")

    assert MatchingPipeline(no_session, encoder, EXTRACTION)(request(), 10).matches == []
    assert encoder.calls == []


def test_competency_only_uses_textual_evidence_without_semantic_fallback(setup):
    add, pipeline = setup
    related = add("related", vector=None)
    add("unrelated", title="Gardener")
    encoder = Encoder()
    result = pipeline(encoder)(request(skill="Python"), 10)
    assert [row.job.id for row in result.matches] == [related.id]
    assert result.matches[0].score > 0
    assert encoder.calls == []


def test_union_deduplicates_and_stable_ties_preserve_privacy_and_geography(setup, caplog):
    add, pipeline = setup
    first = add("a", location={"city": "Lisboa"}, work_arrangement="REMOTE")
    second = add("b", location={"city": "Tokyo"}, work_arrangement="ON_SITE")
    encoder = Encoder()
    subject = pipeline(encoder)
    candidate = request(experience=True)
    with caplog.at_level(logging.INFO, logger="src.matching.pipeline"):
        result = subject(candidate, 10)
        repeated = subject(candidate, 10)
    assert [row.job.id for row in result.matches] == [first.id, second.id]
    assert result == repeated
    assert result.matches[0].score == result.matches[1].score
    assert all(row.eligibility for row in result.matches)
    assert [row.rank for row in result.matches] == [1, 2]
    assert encoder.calls == [["Python\nBuild APIs"], ["Python\nBuild APIs"]]
    assert str(candidate.curriculo_id) not in result.model_dump_json()
    assert "Private company" not in caplog.text and "Build APIs" not in caplog.text
    assert "matching_outcome=success" in caplog.text


@pytest.mark.parametrize("state", [JobStatus.DISCOVERED, JobStatus.STALE, JobStatus.EXPIRED])
def test_inactive_jobs_never_reach_final_response(setup, state):
    add, pipeline = setup
    add("inactive", status=state)
    assert pipeline()(request(experience=True), 10).matches == []


@pytest.mark.parametrize("invalid", ["extraction", "hash", "model", "dimension"])
def test_semantic_only_candidates_require_current_valid_provenance(setup, db_session, invalid):
    add, pipeline = setup
    job = add("semantic", title="Gardener")
    if invalid == "extraction":
        db_session.get(JobExtraction, job.id).status = "FAILED"
    elif invalid == "hash":
        db_session.get(JobEmbedding, job.id).content_hash = "obsolete"
    elif invalid == "model":
        db_session.get(JobEmbedding, job.id).model_version = "obsolete"
    else:
        job.embedding = [1.0, 0.0]
    db_session.flush()
    assert pipeline()(request(experience=True), 10).matches == []


@pytest.mark.parametrize("initial", ["textual", "semantic"])
def test_final_evidence_recheck_drops_stale_pool_hits(setup, monkeypatch, initial):
    add, pipeline = setup
    add("changed", title="Python" if initial == "textual" else "Gardener")
    retrieve = module.retrieve_semantic

    def invalidate(session, *args, **kwargs):
        rows = retrieve(session, *args, **kwargs)
        assert len(rows) == 1
        job = rows[0][0]
        # Simulate an update visible after candidate retrieval, before final checks.
        job.title = "Gardener"
        job.embedding = None
        session.flush()
        return rows

    monkeypatch.setattr(module, "retrieve_semantic", invalidate)
    assert pipeline()(request(experience=True), 10).matches == []


def test_final_textual_evidence_survives_embedding_invalidation(setup, monkeypatch):
    add, pipeline = setup
    job = add("textual")
    retrieve = module.retrieve_semantic

    def invalidate(session, *args, **kwargs):
        rows = retrieve(session, *args, **kwargs)
        rows[0][0].embedding = None
        session.flush()
        return rows

    monkeypatch.setattr(module, "retrieve_semantic", invalidate)
    result = pipeline()(request(experience=True), 10)
    assert [row.job.id for row in result.matches] == [job.id]
    assert result.matches[0].score > 0


@pytest.mark.parametrize(
    "vectors", [[], [VECTOR, VECTOR], [[0.0] * 384], [[float("nan")] * 384], [[1.0]]]
)
def test_invalid_encoder_results_fail_before_retrieval(setup, vectors):
    _, pipeline = setup
    with pytest.raises(ValueError):
        pipeline(Encoder(vectors))(request(experience=True), 10)


@pytest.mark.parametrize("revoked", ["availability", "extraction"])
def test_final_active_and_extraction_gate_reject_revoked_hits(setup, monkeypatch, revoked):
    add, pipeline = setup
    add("revoked")
    retrieve = module.retrieve_semantic

    def invalidate(session, *args, **kwargs):
        rows = retrieve(session, *args, **kwargs)
        assert len(rows) == 1
        job = rows[0][0]
        if revoked == "availability":
            job.status = JobStatus.EXPIRED
        else:
            session.get(JobExtraction, job.id).status = "FAILED"
        session.flush()
        return rows

    monkeypatch.setattr(module, "retrieve_semantic", invalidate)
    assert pipeline()(request(experience=True), 10).matches == []
