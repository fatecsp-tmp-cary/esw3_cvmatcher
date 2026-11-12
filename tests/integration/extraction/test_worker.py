"""Committed isolated jobs exercise real independent worker connections."""

import json
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import delete, inspect, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.extraction.contracts import SpanEvidence
from src.extraction.service import ExtractionWorker, enqueue, ready_predicate
from src.persistence.extraction import JobExtraction
from src.persistence.job.job import Job, JobStatus
from src.persistence.job.job_source import JobSource


class Extractor:
    def extract(self, value):
        return [SpanEvidence(0, 6, "skill", 0.99), SpanEvidence(0, 6, "skill", 0.99)]


@pytest.fixture
def job_id(db_engine):
    with Session(db_engine) as session:
        source = JobSource(name=f"extraction-{uuid4()}", type="api", polling_mode="INCREMENTAL")
        session.add(source)
        session.flush()
        job = Job(
            source_id=source.id,
            platform="synthetic",
            source_job_id=str(uuid4()),
            title="Python developer",
            description="Requisito: Python",
            status=JobStatus.ACTIVE,
            content_hash="hash-v1",
        )
        session.add(job)
        session.flush()
        enqueue(session, job.id, "config-v1")
        session.commit()
        identifier, source_id = job.id, source.id
    try:
        yield identifier
    finally:
        with Session(db_engine) as session, session.begin():
            session.execute(delete(Job).where(Job.id == identifier))
            session.execute(delete(JobSource).where(JobSource.id == source_id))


def worker(engine, extractor=None, config="config-v1"):
    return ExtractionWorker(lambda: Session(engine), extractor or Extractor(), config)


def ready(engine, identifier, config="config-v1"):
    with Session(engine) as session:
        return (
            session.scalar(select(Job.id).where(Job.id == identifier, ready_predicate(config)))
            is not None
        )


def test_only_successful_current_content_and_config_are_ready(db_engine, job_id):
    assert not ready(db_engine, job_id)
    assert not worker(db_engine, config="other").process_once()
    assert worker(db_engine).process_once()
    assert ready(db_engine, job_id)
    assert not ready(db_engine, job_id, "config-v2")
    with Session(db_engine) as session, session.begin():
        state = session.get(JobExtraction, job_id)
        assert len(state.evidence) == 1
        assert state.evidence[0]["requirement_class"] is None
        assert session.get(Job, job_id).status == JobStatus.ACTIVE
        session.get(Job, job_id).content_hash = "hash-v2"
    assert not ready(db_engine, job_id)
    with Session(db_engine) as session, session.begin():
        enqueue(session, job_id, "config-v1")
    assert worker(db_engine).process_once()
    assert ready(db_engine, job_id)
    with Session(db_engine) as session, session.begin():
        enqueue(session, job_id, "config-v2")
    assert not ready(db_engine, job_id)
    assert worker(db_engine, config="config-v2").process_once()
    assert ready(db_engine, job_id, "config-v2")


def test_concurrent_claim_is_at_most_once(db_engine, job_id):
    with ThreadPoolExecutor(max_workers=8) as pool:
        claims = list(pool.map(lambda _: worker(db_engine).claim(), range(16)))
    assert sum(claim is not None for claim in claims) == 1
    assert not ready(db_engine, job_id)
    with Session(db_engine) as session:
        assert session.get(JobExtraction, job_id).attempts == 1


def test_three_failures_require_explicit_retry_and_only_safe_local_alert(db_engine, job_id, caplog):
    class Broken:
        def extract(self, value):
            raise RuntimeError("secret job text and credentials must never appear")

    subject = worker(db_engine, Broken())
    now = datetime.now(UTC)
    assert subject.process_once(now=now)
    assert not subject.process_once(now=now)
    assert subject.process_once(now=now + timedelta(seconds=31))
    assert subject.process_once(now=now + timedelta(seconds=92))
    assert not subject.process_once(now=now + timedelta(days=2))
    assert not ready(db_engine, job_id)
    with Session(db_engine) as session, session.begin():
        state = session.get(JobExtraction, job_id)
        assert state.status == "FAILED" and state.attempts == 3
        assert state.error_code == "inference_error"
        enqueue(session, job_id, "config-v1")
        assert state.status == "FAILED"
        enqueue(session, job_id, "config-v1", retry=True)
    assert worker(db_engine).process_once(now=now + timedelta(days=2))
    assert ready(db_engine, job_id)
    assert "secret" not in caplog.text
    alerts = [json.loads(record.message) for record in caplog.records]
    assert alerts == [
        {
            "event": "job_extraction_failed",
            "job_id": job_id,
            "error_code": "inference_error",
            "attempts": 3,
        }
    ]


def test_revoked_claim_cannot_publish_old_output(db_engine, job_id):
    subject = worker(db_engine)
    old = subject.claim()
    with Session(db_engine) as session, session.begin():
        enqueue(session, job_id, "config-v1", retry=True)
    assert not subject.finish(old, [])
    assert not ready(db_engine, job_id)
    assert subject.process_once()
    assert ready(db_engine, job_id)


def test_content_change_during_inference_cannot_publish_success(db_engine, job_id):
    subject = worker(db_engine)
    claim = subject.claim()
    with Session(db_engine) as session, session.begin():
        session.get(Job, job_id).content_hash = "changed"
    assert not subject.finish(claim, [])
    assert not ready(db_engine, job_id)
    assert subject.process_once()
    assert ready(db_engine, job_id)


def test_invalid_output_retried_without_persisting_raw_result(db_engine, job_id):
    class Invalid:
        def extract(self, value):
            return [SpanEvidence(0, 999999, "skill", 0.8)]

    assert worker(db_engine, Invalid()).process_once()
    with Session(db_engine) as session:
        state = session.get(JobExtraction, job_id)
        assert state.error_code == "invalid_result" and state.evidence is None
        assert state.status == "PENDING"


def test_expired_job_is_not_claimed(db_engine, job_id):
    with Session(db_engine) as session, session.begin():
        session.get(Job, job_id).status = JobStatus.EXPIRED
    assert not worker(db_engine).process_once()


def test_state_database_constraints_and_schema(db_engine, job_id):
    inspector = inspect(db_engine)
    assert "job_extractions" in inspector.get_table_names()
    assert "evidence" not in {column["name"] for column in inspector.get_columns("jobs")}
    for statement in [
        "UPDATE job_extractions SET attempts=4 WHERE job_id=:id",
        "UPDATE job_extractions SET status='UNKNOWN' WHERE job_id=:id",
        "UPDATE job_extractions SET status='RUNNING' WHERE job_id=:id",
    ]:
        with pytest.raises(IntegrityError), db_engine.begin() as connection:
            connection.execute(text(statement), {"id": job_id})


def test_expired_crash_claims_recover_with_same_three_attempt_budget(db_engine, job_id, caplog):
    subject = worker(db_engine)
    now = datetime.now(UTC)
    first = subject.claim(now=now)
    assert subject.claim(now=now + timedelta(seconds=299)) is None
    second = subject.claim(now=now + timedelta(seconds=301))
    assert second is not None and second.token != first.token
    assert not subject.finish(first, [], now=now + timedelta(seconds=302))
    third = subject.claim(now=now + timedelta(seconds=602))
    assert third is not None
    assert not subject.finish(third, [], now=now + timedelta(seconds=903))
    assert subject.claim(now=now + timedelta(seconds=903)) is None
    with Session(db_engine) as session:
        state = session.get(JobExtraction, job_id)
        assert state.status == "FAILED" and state.attempts == 3
        assert state.error_code == "claim_expired"
    assert not subject.claim(now=now + timedelta(days=2))
    assert not ready(db_engine, job_id)
    assert len(caplog.records) == 1


def test_migration_upgrade_and_downgrade_preserve_canonical_jobs(db_engine, job_id):
    from alembic import command
    from alembic.config import Config

    config = Config()
    config.set_main_option("script_location", "migrations")
    command.downgrade(config, "91d0a7f3bc22")
    try:
        assert "job_extractions" not in inspect(db_engine).get_table_names()
        with Session(db_engine) as session:
            assert session.get(Job, job_id).title == "Python developer"
    finally:
        command.upgrade(config, "head")
    assert "job_extractions" in inspect(db_engine).get_table_names()
    assert not ready(db_engine, job_id)
    with Session(db_engine) as session, session.begin():
        enqueue(session, job_id, "config-v1")
    assert worker(db_engine).process_once()
    assert ready(db_engine, job_id)
