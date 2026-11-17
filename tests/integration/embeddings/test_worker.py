"""Real PostgreSQL provenance, claims, retries and pgvector tests with synthetic jobs."""

import json
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import delete, inspect, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.embeddings.config import EmbeddingConfig
from src.embeddings.retrieval import retrieve_semantic
from src.embeddings.service import EmbeddingWorker, enqueue, ready_predicate
from src.persistence.embedding import JobEmbedding
from src.persistence.extraction import JobExtraction
from src.persistence.job.job import Job, JobStatus
from src.persistence.job.job_source import JobSource

CONFIG = EmbeddingConfig()
EXTRACTION = "extraction-test-v1"
VECTOR = [1.0] + [0.0] * 383


class Encoder:
    config = CONFIG

    def encode_jobs(self, texts):
        return [VECTOR for _ in texts]


@pytest.fixture
def job_id(db_engine):
    with Session(db_engine) as session:
        source = JobSource(name=f"embedding-{uuid4()}", type="api", polling_mode="INCREMENTAL")
        session.add(source)
        session.flush()
        job = Job(
            source_id=source.id,
            platform="synthetic",
            source_job_id=str(uuid4()),
            title="Python developer",
            description="Requisito Python",
            content_hash="hash-v1",
            status=JobStatus.ACTIVE,
        )
        session.add(job)
        session.flush()
        session.add(
            JobExtraction(
                job_id=job.id,
                content_hash=job.content_hash,
                config_version=EXTRACTION,
                status="SUCCEEDED",
                attempts=1,
                evidence=[],
                updated_at=datetime.now(UTC),
            )
        )
        enqueue(session, job.id, CONFIG, EXTRACTION)
        session.commit()
        identifier, source_id = job.id, source.id
    try:
        yield identifier
    finally:
        with Session(db_engine) as session, session.begin():
            session.execute(delete(Job).where(Job.id == identifier))
            session.execute(delete(JobSource).where(JobSource.id == source_id))


def worker(engine, encoder=None, extraction_version=EXTRACTION):
    return EmbeddingWorker(lambda: Session(engine), encoder or Encoder(), extraction_version)


def ready(engine, identifier, config=CONFIG, extraction_version=EXTRACTION):
    with Session(engine) as session:
        return (
            session.scalar(
                select(Job.id).where(
                    Job.id == identifier, ready_predicate(config, extraction_version)
                )
            )
            is not None
        )


def test_success_requires_current_embedding_and_extraction_metadata(db_engine, job_id):
    assert not ready(db_engine, job_id)
    assert worker(db_engine).process_once()
    assert ready(db_engine, job_id)
    assert not ready(db_engine, job_id, EmbeddingConfig(overlap_tokens=32))
    assert not ready(db_engine, job_id, extraction_version="different")
    with Session(db_engine) as session, session.begin():
        job = session.get(Job, job_id)
        assert list(job.embedding) == VECTOR
        session.get(JobExtraction, job_id).status = "FAILED"
    assert not ready(db_engine, job_id)


def test_hash_and_model_policy_invalidate_independently(db_engine, job_id):
    assert worker(db_engine).process_once()
    changed = EmbeddingConfig(overlap_tokens=32)
    with Session(db_engine) as session, session.begin():
        enqueue(session, job_id, changed, EXTRACTION)
        assert session.get(Job, job_id).embedding is None
        state = session.get(JobEmbedding, job_id)
        assert state.status == "PENDING" and state.attempts == 0
        assert state.content_hash == "hash-v1"

    class Changed(Encoder):
        config = changed

    assert worker(db_engine, Changed()).process_once()
    assert ready(db_engine, job_id, changed)
    with Session(db_engine) as session, session.begin():
        session.get(Job, job_id).content_hash = "hash-v2"
        enqueue(session, job_id, changed, EXTRACTION)
    assert not ready(db_engine, job_id, changed)
    assert not worker(db_engine, Changed()).process_once()
    with Session(db_engine) as session, session.begin():
        session.get(JobExtraction, job_id).content_hash = "hash-v2"
    assert worker(db_engine, Changed()).process_once()
    assert ready(db_engine, job_id, changed)


def test_concurrent_claim_is_unique_and_revocation_rejects_stale_completion(db_engine, job_id):
    with ThreadPoolExecutor(max_workers=4) as pool:
        claims = list(pool.map(lambda _: worker(db_engine).claim(), range(8)))
    claimed = [claim for claim in claims if claim is not None]
    assert len(claimed) == 1
    with Session(db_engine) as session, session.begin():
        enqueue(session, job_id, CONFIG, EXTRACTION, retry=True)
    assert not worker(db_engine).finish(claimed[0], VECTOR, core_vector=VECTOR)
    assert worker(db_engine).process_once()
    assert ready(db_engine, job_id)


def test_content_or_extraction_changes_during_inference_cannot_publish(db_engine, job_id):
    claim = worker(db_engine).claim()
    with Session(db_engine) as session, session.begin():
        session.get(Job, job_id).content_hash = "changed"
    assert not worker(db_engine).finish(claim, VECTOR, core_vector=VECTOR)
    assert not ready(db_engine, job_id)
    with Session(db_engine) as session, session.begin():
        session.get(JobExtraction, job_id).content_hash = "changed"
    next_claim = worker(db_engine).claim()
    with Session(db_engine) as session, session.begin():
        session.get(JobExtraction, job_id).status = "FAILED"
    assert not worker(db_engine).finish(next_claim, VECTOR, core_vector=VECTOR)
    assert not ready(db_engine, job_id)


def test_three_failures_manual_retry_and_safe_local_alert(db_engine, job_id, caplog):
    class Broken(Encoder):
        def encode_jobs(self, texts):
            raise RuntimeError("secret source text must not be retained")

    now = datetime.now(UTC)
    subject = worker(db_engine, Broken())
    assert subject.process_once(now=now)
    assert not subject.process_once(now=now)
    assert subject.process_once(now=now + timedelta(seconds=31))
    assert subject.process_once(now=now + timedelta(seconds=92))
    assert not subject.process_once(now=now + timedelta(days=1))
    with Session(db_engine) as session, session.begin():
        enqueue(session, job_id, CONFIG, EXTRACTION)
        assert session.get(JobEmbedding, job_id).status == "FAILED"
        enqueue(session, job_id, CONFIG, EXTRACTION, retry=True)
    assert worker(db_engine).process_once(now=now + timedelta(days=1))
    assert ready(db_engine, job_id)
    assert "secret" not in caplog.text
    alerts = [json.loads(record.message) for record in caplog.records]
    assert alerts == [
        {
            "event": "job_embedding_failed",
            "job_id": job_id,
            "error_code": "inference_error",
            "attempts": 3,
        }
    ]


def test_invalid_output_and_expired_claims_are_bounded(db_engine, job_id):
    class Invalid(Encoder):
        def encode_jobs(self, texts):
            return [[float("nan")] * 384]

    now = datetime.now(UTC)
    assert worker(db_engine, Invalid()).process_once(now=now)
    with Session(db_engine) as session:
        assert session.get(JobEmbedding, job_id).error_code == "invalid_result"
        assert session.get(Job, job_id).embedding is None
    subject = worker(db_engine)
    second = subject.claim(now=now + timedelta(seconds=31))
    third = subject.claim(now=now + timedelta(seconds=332))
    assert second is not None and third is not None and third.token != second.token
    assert not subject.finish(second, VECTOR, core_vector=VECTOR, now=now + timedelta(seconds=333))
    assert subject.claim(now=now + timedelta(seconds=633)) is None
    with Session(db_engine) as session:
        state = session.get(JobEmbedding, job_id)
        assert state.status == "FAILED" and state.attempts == 3
    assert subject.claim(now=now + timedelta(days=1)) is None


def test_pgvector_retrieval_excludes_obsolete_failed_and_inactive_jobs(db_engine, job_id):
    assert worker(db_engine).process_once()
    with Session(db_engine) as session, session.begin():
        rows = retrieve_semantic(session, VECTOR, CONFIG, EXTRACTION)
        assert [(job.id, similarity) for job, similarity in rows] == [(job_id, 1.0)]
        assert (
            retrieve_semantic(session, VECTOR, EmbeddingConfig(overlap_tokens=32), EXTRACTION) == []
        )
        for status in (JobStatus.DISCOVERED, JobStatus.STALE, JobStatus.EXPIRED):
            session.get(Job, job_id).status = status
            session.flush()
            assert retrieve_semantic(session, VECTOR, CONFIG, EXTRACTION) == []
        session.get(Job, job_id).status = JobStatus.ACTIVE
        session.get(JobEmbedding, job_id).status = "FAILED"
        session.flush()
        assert retrieve_semantic(session, VECTOR, CONFIG, EXTRACTION) == []


def test_embedding_schema_constraints_and_migration_round_trip(db_engine, job_id):
    from alembic import command
    from alembic.config import Config

    assert "job_embeddings" in inspect(db_engine).get_table_names()
    assert "model_version" not in {
        column["name"] for column in inspect(db_engine).get_columns("jobs")
    }
    for query in (
        "UPDATE job_embeddings SET status='OTHER' WHERE job_id=:id",
        "UPDATE job_embeddings SET status='RUNNING' WHERE job_id=:id",
        "UPDATE job_embeddings SET attempts=4 WHERE job_id=:id",
    ):
        with pytest.raises(IntegrityError), db_engine.begin() as connection:
            connection.execute(text(query), {"id": job_id})
    config = Config()
    config.set_main_option("script_location", "migrations")
    command.downgrade(config, "b1e001")
    try:
        assert "job_embeddings" not in inspect(db_engine).get_table_names()
        with Session(db_engine) as session:
            assert session.get(Job, job_id).title == "Python developer"
    finally:
        command.upgrade(config, "head")
    with Session(db_engine) as session, session.begin():
        enqueue(session, job_id, CONFIG, EXTRACTION)
    assert worker(db_engine).process_once()
    assert ready(db_engine, job_id)


def test_claim_includes_requirements_and_new_extraction_generation_requeues(db_engine, job_id):
    from src.persistence.job.skill import JobRequirement, RequirementClass

    with Session(db_engine) as session, session.begin():
        session.add(
            JobRequirement(
                job_id=job_id, text="SQL expertise", requirement_class=RequirementClass.REQUIRED
            )
        )
    claim = worker(db_engine).claim()
    assert claim is not None and "SQL expertise" in claim.text
    assert worker(db_engine).finish(claim, VECTOR, core_vector=VECTOR)
    updated = "extraction-test-v2"
    with Session(db_engine) as session, session.begin():
        session.get(JobExtraction, job_id).config_version = updated
        session.execute(delete(JobRequirement).where(JobRequirement.job_id == job_id))
        session.add(
            JobRequirement(
                job_id=job_id, text="Java expertise", requirement_class=RequirementClass.PREFERRED
            )
        )
        enqueue(session, job_id, CONFIG, updated)
        assert session.get(Job, job_id).embedding is None
    assert not ready(db_engine, job_id)
    assert worker(db_engine).claim() is None
    current_worker = worker(db_engine, extraction_version=updated)
    current = current_worker.claim()
    assert current is not None and "Java expertise" in current.text
    assert "SQL expertise" not in current.text
    assert current_worker.finish(current, VECTOR, core_vector=VECTOR)
    assert ready(db_engine, job_id, extraction_version=updated)


def test_claim_reads_locked_job_without_waiting_and_skips_locked_embedding(db_engine, job_id):
    # Claim locks only JobEmbedding. Its Job read uses MVCC, so it cannot form
    # the JobEmbedding -> Job lock-order cycle alleged by the GitHub review.
    with ThreadPoolExecutor(max_workers=1) as pool, Session(db_engine) as holding:
        holding.scalar(select(Job).where(Job.id == job_id).with_for_update())
        future = pool.submit(worker(db_engine).claim)
        try:
            claim = future.result(timeout=3)
            assert claim is not None
        finally:
            holding.rollback()
    with Session(db_engine) as session, session.begin():
        enqueue(session, job_id, CONFIG, EXTRACTION, retry=True)
    with ThreadPoolExecutor(max_workers=1) as pool, Session(db_engine) as holding:
        enqueue(holding, job_id, CONFIG, EXTRACTION, retry=True)
        future = pool.submit(worker(db_engine).claim)
        try:
            assert future.result(timeout=3) is None
        finally:
            holding.rollback()


CORE = [0.0, 1.0] + [0.0] * 382


class DualEncoder(Encoder):
    """Distinct full/core outputs so tests can tell the two vectors apart."""

    def __init__(self):
        self.batches = []

    def encode_jobs(self, texts):
        self.batches.append(list(texts))
        return [VECTOR, CORE][: len(texts)]


def test_core_vector_is_published_atomically_and_required_for_readiness(db_engine, job_id):
    from src.persistence.job.skill import JobRequirement, RequirementClass

    with Session(db_engine) as session, session.begin():
        job = session.get(Job, job_id)
        job.skills = ["Python"]
        job.description = "Long company description with benefits and culture text"
        session.add_all(
            [
                JobRequirement(
                    job_id=job_id, text="Django", requirement_class=RequirementClass.REQUIRED
                ),
                JobRequirement(
                    job_id=job_id, text="Kafka", requirement_class=RequirementClass.PREFERRED
                ),
            ]
        )
    encoder = DualEncoder()
    assert worker(db_engine, encoder).process_once()
    (batch,) = encoder.batches
    full_text, core_text = batch
    # The full passage keeps the description; the core keeps only REQUIRED items.
    assert "benefits" in full_text and "Kafka" in full_text
    assert core_text == "Python developer\nPython\nDjango"
    assert ready(db_engine, job_id)
    with Session(db_engine) as session, session.begin():
        assert list(session.get(Job, job_id).embedding) == VECTOR
        assert list(session.get(JobEmbedding, job_id).core_embedding) == CORE
        rows = retrieve_semantic(session, CORE, CONFIG, EXTRACTION, vector="core")
        assert [(job.id, similarity) for job, similarity in rows] == [(job_id, 1.0)]
        best_rows = retrieve_semantic(session, CORE, CONFIG, EXTRACTION, vector="best")
        assert [(job.id, similarity) for job, similarity in best_rows] == [(job_id, 1.0)]
        # The full vector is orthogonal to the core query.
        (full_row,) = retrieve_semantic(session, CORE, CONFIG, EXTRACTION)
        assert full_row[1] == pytest.approx(0.0)
        # A job with only one of the two vectors is withheld everywhere.
        session.get(JobEmbedding, job_id).core_embedding = None
        session.flush()
        assert retrieve_semantic(session, VECTOR, CONFIG, EXTRACTION) == []
        assert retrieve_semantic(session, CORE, CONFIG, EXTRACTION, vector="core") == []


def test_invalidation_failure_and_missing_core_never_publish_a_partial_pair(db_engine, job_id):
    assert worker(db_engine).process_once()
    with Session(db_engine) as session, session.begin():
        enqueue(session, job_id, CONFIG, EXTRACTION, retry=True)
        assert session.get(JobEmbedding, job_id).core_embedding is None
        assert session.get(Job, job_id).embedding is None

    class OneVector(Encoder):
        def encode_jobs(self, texts):
            return [VECTOR]

    assert worker(db_engine, OneVector()).process_once()
    with Session(db_engine) as session:
        state = session.get(JobEmbedding, job_id)
        assert state.error_code == "invalid_result" and state.core_embedding is None
        assert session.get(Job, job_id).embedding is None
    claim = worker(db_engine).claim(now=datetime.now(UTC) + timedelta(seconds=31))
    assert claim is not None
    with pytest.raises(ValueError, match="full and core"):
        worker(db_engine).finish(claim, VECTOR)
    from src.embeddings.retrieval import semantic_statement

    with pytest.raises(ValueError, match="Unknown job vector"):
        semantic_statement(VECTOR, CONFIG, EXTRACTION, vector="other")


def test_core_embedding_migration_round_trip_keeps_canonical_jobs_unchanged(db_engine, job_id):
    from alembic import command
    from alembic.config import Config

    assert worker(db_engine).process_once()
    # The canonical jobs table gains no field; the vector lives in job_embeddings.
    assert "core_embedding" not in {c["name"] for c in inspect(db_engine).get_columns("jobs")}
    config = Config()
    config.set_main_option("script_location", "migrations")
    command.downgrade(config, "b1e007")
    try:
        columns = {c["name"] for c in inspect(db_engine).get_columns("job_embeddings")}
        assert "core_embedding" not in columns
        with Session(db_engine) as session:
            assert session.get(Job, job_id).title == "Python developer"
    finally:
        command.upgrade(config, "head")
    # Upgraded rows have no core vector yet: readiness fails until re-embedding.
    assert not ready(db_engine, job_id)
    with Session(db_engine) as session, session.begin():
        enqueue(session, job_id, CONFIG, EXTRACTION, retry=True)
    assert worker(db_engine).process_once()
    assert ready(db_engine, job_id)
