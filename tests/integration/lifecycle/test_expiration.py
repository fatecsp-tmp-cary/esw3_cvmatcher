from datetime import UTC, datetime, timedelta

import pytest

from src.lifecycle.expiration import expire_source_timestamps
from src.persistence.job.job import Job, JobStatus
from src.persistence.job.job_source import JobSource


def test_expiry_requires_explicit_due_evidence_and_preserves_history(db_session):
    now = datetime(2026, 11, 11, tzinfo=UTC)
    source = JobSource(name="synthetic-expiration", type="fixture", polling_mode="incremental")
    db_session.add(source)
    db_session.flush()
    cases = [
        (JobStatus.ACTIVE, now - timedelta(seconds=1), JobStatus.EXPIRED),
        (JobStatus.STALE, now, JobStatus.EXPIRED),
        (JobStatus.DISCOVERED, now, JobStatus.EXPIRED),
        (JobStatus.ACTIVE, now + timedelta(seconds=1), JobStatus.ACTIVE),
        (JobStatus.STALE, None, JobStatus.STALE),
        (JobStatus.ACTIVE, None, JobStatus.ACTIVE),
        (JobStatus.EXPIRED, now, JobStatus.EXPIRED),
    ]
    jobs = []
    for i, (before, expires, _) in enumerate(cases):
        job = Job(
            source_id=source.id,
            platform="fixture",
            source_job_id=str(i),
            title="Synthetic job",
            status=before,
            source_expires_at=expires,
            first_seen_at=now - timedelta(days=400),
            last_seen_at=now - timedelta(days=365),
            last_verified_at=now - timedelta(days=360),
        )
        jobs.append(job)
        db_session.add(job)
    db_session.flush()
    timestamps = [(job.first_seen_at, job.last_seen_at, job.last_verified_at) for job in jobs]
    assert expire_source_timestamps(db_session, now=now) == 3
    assert [job.status for job in jobs] == [after for _, _, after in cases]
    assert expire_source_timestamps(db_session, now=now) == 0
    assert all(db_session.get(Job, job.id) is not None for job in jobs)
    assert [
        (job.first_seen_at, job.last_seen_at, job.last_verified_at) for job in jobs
    ] == timestamps


@pytest.mark.parametrize("clock", [datetime(2026, 11, 11), "2026-11-11T00:00:00Z", None])
def test_expiry_rejects_ambiguous_clock(db_session, clock):
    with pytest.raises(ValueError, match="timezone-aware"):
        expire_source_timestamps(db_session, now=clock)
