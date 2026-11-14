"""Independent committed transactions exercise source-identity serialization."""

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from threading import Barrier, Event
from uuid import uuid4

import pytest
from sqlalchemy import delete, select, text
from sqlalchemy.orm import Session

from src.ingestion.apibr import ingest_apibr
from src.ingestion.upsert import upsert_job
from src.persistence.job.job import Job, JobStatus
from src.persistence.job.job_source import JobSource
from src.persistence.job.source_run import SourceRun


@pytest.fixture
def committed_source(db_engine):
    # Transaction/savepoint fixtures cannot expose rows to independent sessions.
    with Session(db_engine) as session:
        source = JobSource(name=f"concurrency-{uuid4()}", type="api", polling_mode="INCREMENTAL")
        session.add(source)
        session.commit()
        source_id = source.id
    try:
        yield source_id
    finally:
        with Session(db_engine) as session:
            session.execute(delete(Job).where(Job.source_id == source_id))
            session.execute(delete(SourceRun).where(SourceRun.source_id == source_id))
            session.execute(delete(JobSource).where(JobSource.id == source_id))
            session.commit()


def _job(source_id, *, status="ACTIVE", title="Developer"):
    return {
        "platform": "concurrency-test",
        "source_job_id": str(source_id),
        "title": title,
        "description": "Build APIs",
        "status": status,
    }


def test_competing_first_inserts_reuse_the_committed_identity(db_engine, committed_source):
    started = Event()
    now = datetime.now(UTC)

    def competing_insert():
        with Session(db_engine) as second:
            second.execute(select(1))  # Establish an independent connection.
            started.set()
            result = upsert_job(second, committed_source, _job(committed_source), now, True)
            second.commit()
            return result

    with ThreadPoolExecutor(max_workers=1) as executor, Session(db_engine) as first:
        created = upsert_job(first, committed_source, _job(committed_source), now, True)
        first.flush()  # Row exists but is not visible to the competing connection.
        future = executor.submit(competing_insert)
        try:
            assert started.wait(timeout=5)
        finally:
            first.commit()  # Release the identity lock even if the assertion fails.
        assert created == ("created", False, False)
        assert future.result(timeout=10) == ("unchanged", False, False)

    with Session(db_engine) as session:
        jobs = session.scalars(select(Job).where(Job.source_id == committed_source)).all()
        assert len(jobs) == 1


def test_competing_updates_preserve_terminal_expiration(db_engine, committed_source):
    now = datetime.now(UTC)
    with Session(db_engine) as session:
        upsert_job(session, committed_source, _job(committed_source), now, True)
        session.commit()
    ready = Barrier(2)

    def update(status):
        with Session(db_engine) as session:
            session.execute(select(1))
            ready.wait(timeout=5)
            result = upsert_job(
                session, committed_source, _job(committed_source, status=status), now, True
            )
            session.commit()
            return result

    with ThreadPoolExecutor(max_workers=2) as executor:
        expired = executor.submit(update, "EXPIRED")
        active = executor.submit(update, "ACTIVE")
        assert expired.result(timeout=10)[1] is True
        assert active.result(timeout=10)[1] is False

    with Session(db_engine) as session:
        job = session.scalar(select(Job).where(Job.source_id == committed_source))
        assert job.status == JobStatus.EXPIRED


def test_waiting_writer_refreshes_previously_loaded_lifecycle(db_engine, committed_source):
    now = datetime.now(UTC)
    with Session(db_engine) as session:
        upsert_job(session, committed_source, _job(committed_source), now, True)
        session.commit()

    with Session(db_engine) as stale, Session(db_engine) as writer:
        old_job = stale.scalar(select(Job).where(Job.source_id == committed_source))
        assert old_job.status == JobStatus.ACTIVE
        upsert_job(writer, committed_source, _job(committed_source, status="EXPIRED"), now, True)
        writer.commit()
        result = upsert_job(stale, committed_source, _job(committed_source), now, True)
        stale.commit()
        assert result == ("unchanged", False, False)
        assert old_job.status == JobStatus.EXPIRED


def _issue(issue_id):
    return {
        "id": issue_id,
        "title": f"Developer {issue_id}",
        "state": "open",
        "body": "Build APIs",
        "html_url": f"https://github.com/acme/jobs/issues/{issue_id}",
    }


def test_reversed_overlapping_scans_fetch_without_locks_and_commit_atomically(
    db_engine, committed_source
):
    # In the former streaming implementation, both scans held their first
    # identity while waiting at page two, then deadlocked on opposite identities.
    second_page = Barrier(2)
    identities = (committed_source * 10, committed_source * 10 + 1)

    def scan(order):
        with Session(db_engine) as session:

            class Pages:
                def fetch_page(self, page):
                    held = session.scalar(
                        text(
                            "SELECT count(*) FROM pg_locks "
                            "WHERE locktype = 'advisory' AND pid = pg_backend_pid()"
                        )
                    )
                    assert held == 0, "Remote fetch must precede identity locking"
                    if page == 2:
                        second_page.wait(timeout=5)
                    return [_issue(order[page - 1])] if page <= 2 else []

            return ingest_apibr(session, committed_source, Pages())

    with ThreadPoolExecutor(max_workers=2) as executor:
        first = executor.submit(scan, identities)
        second = executor.submit(scan, identities[::-1])
        results = [first.result(timeout=15), second.result(timeout=15)]
    assert all(result.status == "SUCCEEDED" for result in results)
    assert sum(result.jobs_created for result in results) == 2
    assert sum(result.jobs_unchanged for result in results) == 2
    with Session(db_engine) as session:
        jobs = session.scalars(select(Job).where(Job.source_id == committed_source)).all()
        assert len(jobs) == 2


def test_batch_write_failure_rolls_back_prior_records(db_engine, committed_source, monkeypatch):
    from src.ingestion import apibr

    calls = 0
    original = apibr.upsert_job

    def fail_second(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError("synthetic write failure")
        return original(*args, **kwargs)

    monkeypatch.setattr(apibr, "upsert_job", fail_second)

    class Pages:
        def fetch_page(self, page):
            return (
                [_issue(committed_source * 10), _issue(committed_source * 10 + 1)]
                if page == 1
                else []
            )

    with (
        Session(db_engine) as session,
        pytest.raises(RuntimeError, match="synthetic write failure"),
    ):
        ingest_apibr(session, committed_source, Pages())
    with Session(db_engine) as session:
        assert session.scalar(select(Job.id).where(Job.source_id == committed_source)) is None
        run = session.scalar(select(SourceRun).where(SourceRun.source_id == committed_source))
        assert run.status == "FAILED"
        assert run.jobs_created == 0
