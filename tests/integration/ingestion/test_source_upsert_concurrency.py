"""Independent committed transactions exercise source-identity serialization."""

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from threading import Barrier, Event
from uuid import uuid4

import pytest
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from src.ingestion.upsert import upsert_job
from src.persistence.job.job import Job, JobStatus
from src.persistence.job.job_source import JobSource


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
