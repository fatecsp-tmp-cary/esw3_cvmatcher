"""Synthetic PostgreSQL-to-production-API regressions with deterministic inference."""

from copy import deepcopy
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, inspect, select
from sqlalchemy.orm import Session

from src.api.app import CURRICULUM_EXAMPLE, create_app
from src.api.rate_limit import GlobalRateLimiter
from src.embeddings.config import EmbeddingConfig
from src.embeddings.service import EmbeddingWorker
from src.embeddings.service import enqueue as enqueue_embedding
from src.extraction.contracts import SpanEvidence
from src.extraction.service import ExtractionWorker, enqueue
from src.matching.pipeline import MatchingPipeline
from src.persistence.job.job import Job, JobStatus
from src.persistence.job.job_source import JobSource

VERSION = "pipeline-test-extraction-v1"
VECTOR = [1.0] + [0.0] * 383


class Encoder:
    config = EmbeddingConfig()
    model_version = config.model_version

    def __init__(self):
        self.calls = []

    def encode_jobs(self, texts):
        return [VECTOR for _ in texts]

    def encode_queries(self, texts):
        self.calls.append(list(texts))
        return [VECTOR for _ in texts]


class Extractor:
    def extract(self, text):
        start = text.index("Python")
        return [SpanEvidence(start, start + 6, "skill", 0.9)]


@pytest.fixture
def populated(db_engine):
    identities = []
    with Session(db_engine) as session, session.begin():
        source = JobSource(name=f"pipeline-{uuid4()}", type="api", polling_mode="INCREMENTAL")
        session.add(source)
        session.flush()
        source_id = source.id
        for platform, status in (
            ("a-independent", JobStatus.ACTIVE),
            ("b-independent", JobStatus.ACTIVE),
            ("c-withheld", JobStatus.ACTIVE),
            ("d-expired", JobStatus.EXPIRED),
        ):
            job = Job(
                source_id=source_id,
                platform=platform,
                source_job_id="same-upstream-id",
                title="Python Developer",
                description="Desenvolvimento Python e PostgreSQL",
                skills=["Python", "PostgreSQL"],
                location={"city": "Lisboa", "country": "PT"},
                content_hash="synthetic-content-v1",
                status=status,
            )
            session.add(job)
            session.flush()
            identities.append(job.id)
            if platform in ("a-independent", "b-independent"):
                enqueue(session, job.id, VERSION)
    encoder = Encoder()

    def sessions():
        return Session(db_engine)

    extractor = ExtractionWorker(sessions, Extractor(), VERSION)
    assert extractor.process_once()
    assert extractor.process_once()
    with Session(db_engine) as session, session.begin():
        for identifier in identities[:2]:
            enqueue_embedding(session, identifier, encoder.config, VERSION)
    embedder = EmbeddingWorker(sessions, encoder, VERSION)
    assert embedder.process_once()
    assert embedder.process_once()
    try:
        yield sessions, encoder, identities
    finally:
        with Session(db_engine) as session, session.begin():
            session.execute(delete(Job).where(Job.source_id == source_id))
            session.execute(delete(JobSource).where(JobSource.id == source_id))


def curriculum():
    body = deepcopy(CURRICULUM_EXAMPLE)
    body["experiencias"][0]["cargo"] = "Python Developer"
    body["experiencias"][0]["descricao"] = "Python PostgreSQL"
    body["competencias"] = [{"descricao": "Python", "nivel": "avançado"}]
    return body


def test_background_to_api_ranking_is_repeatable_private_and_source_independent(
    db_engine, populated, caplog
):
    sessions, encoder, identities = populated
    pipeline = MatchingPipeline(sessions, encoder, VERSION)
    body = curriculum()
    with TestClient(create_app(pipeline, rate_limiter=GlobalRateLimiter(db_engine))) as client:
        first = client.post("/matches", json=body)
        second = client.post("/matches", json=body)
        limited = client.post("/matches?limit=1", json=body)
    assert first.status_code == 200
    assert first.json() == second.json()
    matches = first.json()["matches"]
    assert [match["job"]["id"] for match in matches] == identities[:2]
    assert len(limited.json()["matches"]) == 1
    assert all(match["eligibility"] for match in matches)
    assert all(0 <= match["score"] <= 100 for match in matches)
    assert all(match["matched_skills"] == ["postgresql", "python"] for match in matches)
    assert all(match["missing_requirements"] == [] for match in matches)
    assert all(match["embedding_model"] == encoder.model_version for match in matches)
    # Identical jobs from two platforms stay separate, including foreign location.
    assert matches[0]["job"]["location"]["country"] == "PT"
    assert body["curriculo_id"] not in first.text + caplog.text
    assert body["experiencias"][0]["descricao"] not in caplog.text
    assert all("candidate" not in name for name in inspect(db_engine).get_table_names())
    assert len(encoder.calls[0]) == len(body["experiencias"]) + len(body["formacoes"])


def test_empty_sections_do_not_invent_evidence_or_run_inference(populated):
    from src.schemas.candidate.curriculum import CurriculumRequest

    sessions, encoder, _ = populated
    body = {key: [] for key in ("experiencias", "formacoes", "competencias", "projetos", "idiomas")}
    body["curriculo_id"] = str(uuid4())
    assert (
        MatchingPipeline(sessions, encoder, VERSION)(
            CurriculumRequest.model_validate(body), 10
        ).matches
        == []
    )
    assert encoder.calls == []


def test_content_or_extraction_version_change_withholds_every_path(populated):
    from src.schemas.candidate.curriculum import CurriculumRequest

    sessions, encoder, identities = populated
    with sessions() as session, session.begin():
        for identifier in identities[:2]:
            session.get(Job, identifier).content_hash = "changed-content"
    request = CurriculumRequest.model_validate(curriculum())
    assert MatchingPipeline(sessions, encoder, VERSION)(request, 10).matches == []
    assert MatchingPipeline(sessions, encoder, "new-version")(request, 10).matches == []


def test_inference_failure_is_privacy_safe_and_does_not_mutate_job_data(populated, monkeypatch):
    from src.api import runtime

    sessions, encoder, identities = populated

    def broken(_texts):
        raise RuntimeError("private candidate text and secret dependency detail")

    encoder.encode_queries = broken
    monkeypatch.setattr(
        runtime, "get_pipeline", lambda: MatchingPipeline(sessions, encoder, VERSION)
    )
    with TestClient(create_app(runtime.production_matches)) as client:
        response = client.post("/matches", json=curriculum())
    assert response.status_code == 503
    assert "private candidate" not in response.text
    assert "secret" not in response.text
    with sessions() as session:
        assert (
            session.scalars(select(Job.id).where(Job.id.in_(identities)).order_by(Job.id)).all()
            == identities
        )
