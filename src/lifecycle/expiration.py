"""Expire only from reliable source timestamps, never polling absence."""

from datetime import datetime

from sqlalchemy import update
from sqlalchemy.orm import Session

from src.persistence.job.job import Job, JobStatus


def expire_source_timestamps(session: Session, *, now: datetime) -> int:
    """Apply explicit upstream expiry evidence in the caller's transaction.

    The canonical source_expires_at must have been normalized from a reliable
    upstream expiry field. Neither last_seen_at nor failed/incomplete scans are
    expiry evidence. EXPIRED remains terminal and records are retained.
    """
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("expiration clock must be timezone-aware")
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
