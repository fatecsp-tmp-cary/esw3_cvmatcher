"""Expire only from reliable source timestamps, never polling absence."""

from datetime import datetime

from sqlalchemy import update
from sqlalchemy.orm import Session

from src.ingestion.upsert import lock_all_job_identities
from src.persistence.job.job import Job, JobStatus


def expire_source_timestamps(session: Session, *, now: datetime) -> int:
    """Apply explicit upstream expiry evidence in the caller's transaction.

    The canonical source_expires_at must have been normalized from a reliable
    upstream expiry field. Neither last_seen_at nor failed/incomplete scans are
    expiry evidence. EXPIRED remains terminal and records are retained. Invoke
    before any identity upserts in this transaction (or with all stripes already
    held), and commit/rollback without network I/O while the locks are held.
    """
    if not isinstance(now, datetime) or now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("expiration clock must be timezone-aware")
    # Match ingestion's stripe-before-row order. Locking rows alone can deadlock
    # when a sweep and an ingestion batch encounter rows in different orders.
    lock_all_job_identities(session)
    expired = session.scalars(
        update(Job)
        .where(
            Job.status.in_((JobStatus.DISCOVERED, JobStatus.ACTIVE, JobStatus.STALE)),
            Job.source_expires_at.is_not(None),
            Job.source_expires_at <= now,
        )
        .values(status=JobStatus.EXPIRED)
        .returning(Job.id)
        .execution_options(synchronize_session="fetch")
    )
    return len(expired.all())
