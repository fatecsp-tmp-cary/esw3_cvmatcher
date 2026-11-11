from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from threading import Event
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from src.extraction.service import ExtractionWorker
from src.ingestion.apibr import ingest_apibr
from src.persistence.extraction import JobExtraction
from src.persistence.job.job import Job, JobStatus
from src.persistence.job.job_source import JobSource
from src.persistence.job.source_run import SourceRun
from src.worker.__main__ import main
from src.worker.runtime import BackgroundWorker
from src.worker.scheduler import SourceScheduler, source_lock

NOW = datetime(2026, 11, 11, 12, tzinfo=UTC)


@pytest.fixture
def records(db_engine):
    identifiers = []

    def source(**kwargs):
        with Session(db_engine) as session:
            row = JobSource(
                name=f"worker-{uuid4()}", type="api", polling_mode="INCREMENTAL", **kwargs
            )
            session.add(row)
            session.commit()
            identifiers.append(row.id)
            return row.id, row.name

    yield source
    with Session(db_engine) as session, session.begin():
        session.execute(delete(SourceRun).where(SourceRun.source_id.in_(identifiers)))
        session.execute(delete(Job).where(Job.source_id.in_(identifiers)))
        session.execute(delete(JobSource).where(JobSource.id.in_(identifiers)))


def scheduler(engine, pollers, **kwargs):
    return SourceScheduler(
        engine, lambda: Session(engine), pollers=pollers, clock=lambda: NOW, **kwargs
    )


def test_scheduler_only_polls_enabled_due_sources_and_updates_completion_timestamps(
    db_engine, records
):
    due, due_name = records(polling_interval=30)
    default_due, default_name = records(polling_interval=0)
    disabled, disabled_name = records(enabled=False)
    future, future_name = records(next_run_at=NOW + timedelta(hours=1))
    calls = []

    def poll(session, identifier):
        calls.append(identifier)
        session.commit()
        return SimpleNamespace(status="SUCCEEDED")

    subject = scheduler(
        db_engine, dict.fromkeys((due_name, default_name, disabled_name, future_name), poll)
    )
    outcomes = subject.run_due(now=NOW)
    assert {outcome.source_id for outcome in outcomes} == {due, default_due}
    assert set(calls) == {due, default_due}
    with Session(db_engine) as session:
        row = session.get(JobSource, due)
        assert row.last_run_at == row.last_success_at == NOW
        assert row.next_run_at == NOW + timedelta(seconds=30)
        assert row.last_error is None
        assert session.get(JobSource, default_due).next_run_at == NOW + timedelta(hours=1)
        assert session.get(JobSource, disabled).last_run_at is None
        assert session.get(JobSource, future).last_run_at is None
    assert subject.run_due(now=NOW) == ()


@pytest.mark.parametrize("outcome", ["PARTIAL", "FAILED", "INVALID", "raises"])
def test_partial_and_failed_poll_preserve_success_and_use_safe_categories(
    db_engine, records, outcome, caplog
):
    previous = NOW - timedelta(days=1)
    identifier, name = records(last_success_at=previous, polling_interval=90)

    def poll(session, source_id):
        if outcome == "raises":
            raise RuntimeError("private source text and credentials")
        return SimpleNamespace(status=outcome)

    result = scheduler(db_engine, {name: poll}).run_due(now=NOW)
    expected = "PARTIAL" if outcome == "PARTIAL" else "FAILED"
    assert result[0].status == expected
    with Session(db_engine) as session:
        source = session.get(JobSource, identifier)
        assert source.last_success_at == previous
        assert source.last_run_at == NOW
        assert source.next_run_at == NOW + timedelta(seconds=90)
        assert source.last_error == ("partial_records" if expected == "PARTIAL" else "poll_failed")
    assert "private" not in caplog.text


def test_unsupported_source_never_triggers_another_adapter(db_engine, records):
    identifier, _ = records()
    assert scheduler(db_engine, {}).run_due(now=NOW)[0].status == "UNSUPPORTED"
    with Session(db_engine) as session:
        source = session.get(JobSource, identifier)
        assert source.last_error == "unsupported_source"
        assert source.next_run_at == NOW + timedelta(hours=1)


def test_dedicated_source_lock_survives_ingestion_commits_and_prevents_concurrent_poll(
    db_engine, records
):
    identifier, name = records()
    entered = Event()
    release = Event()
    calls = []

    def poll(session, source_id):
        calls.append(source_id)
        session.commit()
        with source_lock(db_engine, source_id) as acquired:
            assert not acquired
        session.commit()
        entered.set()
        assert release.wait(5), "test did not release first poll"
        return SimpleNamespace(status="SUCCEEDED")

    subject = scheduler(db_engine, {name: poll})
    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(subject.run_due, now=NOW)
        try:
            assert entered.wait(5)
            # Force the second scheduler's due predicate beyond the reservation;
            # only the dedicated source lock can stop this concurrent attempt.
            second = pool.submit(subject.run_due, now=NOW + timedelta(days=1))
            assert second.result(timeout=5) == ()
        finally:
            release.set()
        assert first.result(timeout=5)[0].status == "SUCCEEDED"
    assert calls == [identifier]
    with source_lock(db_engine, identifier) as acquired:
        assert acquired


def test_scheduler_retains_real_apibr_source_runs_and_safe_partial_state(db_engine, records):
    identifier, name = records()

    class Pages:
        def __init__(self):
            self.pages = iter([[{"id": 1, "title": "Python", "state": "open"}, None], []])

        def fetch_page(self, page):
            return next(self.pages)

    def poll(session, source_id):
        return ingest_apibr(session, source_id, Pages())

    assert scheduler(db_engine, {name: poll}).run_due(now=NOW)[0].status == "PARTIAL"
    with Session(db_engine) as session:
        run = session.scalar(select(SourceRun).where(SourceRun.source_id == identifier))
        assert run.status == "PARTIAL"
        assert run.snapshot_complete is False
        assert run.jobs_rejected == 1
        assert session.get(JobSource, identifier).last_success_at is None


class EmptyExtractor:
    def extract(self, text):
        return []


def background(engine, **kwargs):
    extraction = ExtractionWorker(lambda: Session(engine), EmptyExtractor(), "worker-v1")
    return BackgroundWorker(
        scheduler(engine, {}), lambda: Session(engine), extraction, "worker-v1", **kwargs
    )


def test_enqueue_only_missing_or_stale_work_and_explicit_retry_preserves_lifecycle(
    db_engine, records
):
    source_id, _ = records(enabled=False)
    identifiers = {}
    with Session(db_engine) as session, session.begin():
        for name in (
            "missing",
            "failed",
            "running",
            "old-config",
            "old-hash",
            "expired",
            "no-hash",
        ):
            job = Job(
                source_id=source_id,
                platform="synthetic",
                source_job_id=name,
                title="Python job",
                status=JobStatus.EXPIRED if name == "expired" else JobStatus.ACTIVE,
                content_hash=None if name == "no-hash" else "current-hash",
            )
            session.add(job)
            session.flush()
            identifiers[name] = job.id
            if name in ("failed", "running", "old-config", "old-hash"):
                session.add(
                    JobExtraction(
                        job_id=job.id,
                        config_version="old-version" if name == "old-config" else "worker-v1",
                        content_hash="old-hash" if name == "old-hash" else "current-hash",
                        status="RUNNING" if name == "running" else "FAILED",
                        attempts=1 if name == "running" else 3,
                        claim_token="active-claim" if name == "running" else None,
                        lease_expires_at=NOW + timedelta(minutes=5) if name == "running" else None,
                        updated_at=NOW,
                        error_code=None if name == "running" else "inference_error",
                    )
                )
    subject = background(db_engine)
    assert subject.enqueue_missing() == 3
    assert subject.enqueue_missing() == 0
    with Session(db_engine) as session:
        for name in ("missing", "old-config", "old-hash"):
            state = session.get(JobExtraction, identifiers[name])
            assert state.status == "PENDING" and state.attempts == 0
            assert state.config_version == "worker-v1"
            assert state.content_hash == "current-hash"
        assert session.get(JobExtraction, identifiers["failed"]).status == "FAILED"
        assert session.get(JobExtraction, identifiers["failed"]).attempts == 3
        assert session.get(JobExtraction, identifiers["running"]).claim_token == "active-claim"
        assert session.get(JobExtraction, identifiers["expired"]) is None
        assert session.get(JobExtraction, identifiers["no-hash"]) is None
        assert session.get(Job, identifiers["expired"]).status is JobStatus.EXPIRED
    subject.retry_extraction(identifiers["failed"])
    with Session(db_engine) as session:
        state = session.get(JobExtraction, identifiers["failed"])
        assert state.status == "PENDING" and state.attempts == 0
        assert session.get(Job, identifiers["failed"]).status is JobStatus.ACTIVE


def test_once_pipeline_and_cli_explicit_retry_use_stored_job_only(db_engine, records):
    source_id, _ = records(enabled=False)
    with Session(db_engine) as session:
        job = Job(
            source_id=source_id,
            platform="synthetic",
            source_job_id="pipeline",
            title="Python developer",
            status=JobStatus.ACTIVE,
            content_hash="pipeline-hash",
        )
        session.add(job)
        session.commit()
        job_id = job.id
    calls = []
    subject = background(
        db_engine,
        expiration_hook=lambda: calls.append("expire"),
        embedding_hook=lambda: calls.append("embed"),
    )
    assert main(["--once"], worker_factory=lambda: subject) == 0
    assert calls == ["expire", "embed"]
    with Session(db_engine) as session:
        assert session.get(JobExtraction, job_id).status == "SUCCEEDED"
        assert session.get(Job, job_id).status is JobStatus.ACTIVE
    assert main(["--retry-extraction", str(job_id)], worker_factory=lambda: subject) == 0
    with Session(db_engine) as session:
        state = session.get(JobExtraction, job_id)
        assert state.status == "PENDING" and state.attempts == 0


@pytest.mark.parametrize("outcome", ["FAILED", "INVALID", "raises"])
def test_failed_poller_cannot_commit_staged_job_changes(db_engine, records, outcome):
    identifier, name = records()

    def poll(session, source_id):
        session.add(
            Job(
                source_id=source_id,
                platform="synthetic",
                source_job_id="must-rollback",
                title="Private failed work",
                status=JobStatus.ACTIVE,
            )
        )
        session.flush()
        if outcome == "raises":
            raise RuntimeError("private source text")
        return SimpleNamespace(status=outcome)

    assert scheduler(db_engine, {name: poll}).run_due(now=NOW)[0].status == "FAILED"
    with Session(db_engine) as session:
        assert session.scalar(select(Job.id).where(Job.source_id == identifier)) is None
