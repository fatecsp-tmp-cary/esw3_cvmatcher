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


GROUPED = (
    ("a-active", JobStatus.ACTIVE),
    ("b-stale", JobStatus.STALE),
    ("c-expired", JobStatus.EXPIRED),
    ("d-discovered", JobStatus.DISCOVERED),
    ("e-active", JobStatus.ACTIVE),
)


@pytest.fixture
def grouped(db_engine):
    """Identical ready jobs processed while active, then moved to their final status.

    One additional inactive job is never extracted, so it must stay withheld.
    """
    identities = {}
    with Session(db_engine) as session, session.begin():
        source = JobSource(name=f"grouped-{uuid4()}", type="api", polling_mode="SNAPSHOT")
        session.add(source)
        session.flush()
        source_id = source.id
        for platform in [name for name, _ in GROUPED] + ["f-withheld"]:
            job = Job(
                source_id=source_id,
                platform=platform,
                source_job_id="same-upstream-id",
                title="Python Developer",
                description="Desenvolvimento Python e PostgreSQL",
                skills=["Python", "PostgreSQL"],
                content_hash="synthetic-content-v1",
                status=JobStatus.ACTIVE,
            )
            session.add(job)
            session.flush()
            identities[platform] = job.id
            if platform != "f-withheld":
                enqueue(session, job.id, VERSION)
    encoder = Encoder()

    def sessions():
        return Session(db_engine)

    extractor = ExtractionWorker(sessions, Extractor(), VERSION)
    for _ in GROUPED:
        assert extractor.process_once()
    with Session(db_engine) as session, session.begin():
        for platform, _ in GROUPED:
            enqueue_embedding(session, identities[platform], encoder.config, VERSION)
    embedder = EmbeddingWorker(sessions, encoder, VERSION)
    for _ in GROUPED:
        assert embedder.process_once()
    with Session(db_engine) as session, session.begin():
        for platform, status in (*GROUPED, ("f-withheld", JobStatus.STALE)):
            session.get(Job, identities[platform]).status = status
    try:
        yield sessions, encoder, identities
    finally:
        with Session(db_engine) as session, session.begin():
            session.execute(delete(Job).where(Job.source_id == source_id))
            session.execute(delete(JobSource).where(JobSource.id == source_id))


def test_inactive_jobs_complete_the_ranking_only_after_every_active_job(db_engine, grouped):
    sessions, encoder, identities = grouped
    pipeline = MatchingPipeline(sessions, encoder, VERSION)
    body = curriculum()
    with TestClient(create_app(pipeline, rate_limiter=GlobalRateLimiter(db_engine))) as client:
        first = client.post("/matches", json=body).json()["matches"]
        second = client.post("/matches", json=body).json()["matches"]
        two = client.post("/matches?limit=2", json=body).json()["matches"]
        three = client.post("/matches?limit=3", json=body).json()["matches"]

    assert first == second
    order = ["a-active", "e-active", "b-stale", "c-expired", "d-discovered"]
    assert [match["job"]["id"] for match in first] == [identities[name] for name in order]
    assert [match["eligibility"] for match in first] == [True, True, False, False, False]
    assert [match["rank"] for match in first] == [1, 2, 3, 4, 5]
    # Status decides the group only: identical jobs keep one compatibility score.
    assert len({match["score"] for match in first}) == 1
    assert all(match["matched_skills"] == ["postgresql", "python"] for match in first)
    # Extraction readiness still gates the inactive group.
    assert identities["f-withheld"] not in {match["job"]["id"] for match in first}

    # Enough active jobs fill the limit: no inactive job is returned.
    assert [match["job"]["id"] for match in two] == [identities[name] for name in order[:2]]
    assert all(match["eligibility"] for match in two)
    # The inactive group fills only the remaining positions.
    assert [match["job"]["id"] for match in three] == [identities[name] for name in order[:3]]
    assert [match["eligibility"] for match in three] == [True, True, False]


def test_only_inactive_ready_jobs_are_returned_as_ineligible(db_engine, grouped):
    sessions, encoder, identities = grouped
    with Session(db_engine) as session, session.begin():
        for name in ("a-active", "e-active"):
            session.get(Job, identities[name]).status = JobStatus.STALE
    pipeline = MatchingPipeline(sessions, encoder, VERSION)
    with TestClient(create_app(pipeline, rate_limiter=GlobalRateLimiter(db_engine))) as client:
        matches = client.post("/matches", json=curriculum()).json()["matches"]

    assert len(matches) == 5
    assert not any(match["eligibility"] for match in matches)
    assert [match["rank"] for match in matches] == [1, 2, 3, 4, 5]


@pytest.fixture
def enriched(db_engine):
    """One ready job whose stored skills lack a skill the worker associates."""
    with Session(db_engine) as session, session.begin():
        source = JobSource(name=f"enriched-{uuid4()}", type="api", polling_mode="INCREMENTAL")
        session.add(source)
        session.flush()
        source_id = source.id
        job = Job(
            source_id=source_id,
            platform="a-enriched",
            source_job_id="1",
            title="Backend Developer",
            description="Requisitos: Python",
            skills=["PostgreSQL"],
            content_hash="synthetic-content-v1",
            status=JobStatus.ACTIVE,
        )
        session.add(job)
        session.flush()
        job_id = job.id
        enqueue(session, job_id, VERSION)
    encoder = Encoder()

    def sessions():
        return Session(db_engine)

    assert ExtractionWorker(sessions, Extractor(), VERSION).process_once()
    with Session(db_engine) as session, session.begin():
        enqueue_embedding(session, job_id, encoder.config, VERSION)
    assert EmbeddingWorker(sessions, encoder, VERSION).process_once()
    try:
        yield sessions, encoder, job_id
    finally:
        with Session(db_engine) as session, session.begin():
            session.execute(delete(Job).where(Job.source_id == source_id))
            session.execute(delete(JobSource).where(JobSource.id == source_id))


def test_result_skills_combine_stored_and_extracted_skills_without_changing_the_job(
    db_engine, enriched
):
    sessions, encoder, job_id = enriched
    pipeline = MatchingPipeline(sessions, encoder, VERSION)
    with TestClient(create_app(pipeline, rate_limiter=GlobalRateLimiter(db_engine))) as client:
        matches = client.post("/matches", json=curriculum()).json()["matches"]

    assert [match["job"]["id"] for match in matches] == [job_id]
    assert matches[0]["job"]["skills"] == ["PostgreSQL", "Python"]
    with Session(db_engine) as session:
        assert session.get(Job, job_id).skills == ["PostgreSQL"]
