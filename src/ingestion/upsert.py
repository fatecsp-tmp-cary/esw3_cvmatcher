"""Source-specific persistence of normalized jobs."""

from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.ingestion.hashing import HASH_FIELDS, content_hash
from src.persistence.job.job import Job, JobStatus


def _status_transition(current: JobStatus, proposed: JobStatus) -> JobStatus:
    allowed = {
        JobStatus.DISCOVERED: {JobStatus.ACTIVE, JobStatus.EXPIRED},
        JobStatus.ACTIVE: {JobStatus.STALE, JobStatus.EXPIRED},
        JobStatus.STALE: {JobStatus.ACTIVE, JobStatus.EXPIRED},
        JobStatus.EXPIRED: set(),
    }
    return proposed if proposed == current or proposed in allowed[current] else current


def upsert_job(
    session: Session,
    source_id: int,
    normalized: dict[str, Any],
    observed_at: datetime,
    verified: bool,
) -> tuple[str, bool, bool]:
    """Insert or update a job by its source platform and source job ID.

    The return values are the content outcome, whether this call newly expired
    the job, and whether it reactivated a stale job.
    """
    platform = normalized["platform"]
    source_job_id = normalized["source_job_id"]
    existing = session.scalar(
        select(Job).where(Job.platform == platform, Job.source_job_id == source_job_id)
    )
    proposed_status = JobStatus(normalized["status"])
    digest = content_hash(normalized)

    if existing is None:
        values = {
            field: normalized.get(field)
            for field in (
                "platform",
                "source_job_id",
                *HASH_FIELDS,
                "status",
                "last_verified_at",
                "raw",
                "embedding",
            )
        }
        values["source_id"] = source_id
        values["status"] = proposed_status
        values["content_hash"] = digest
        values["first_seen_at"] = observed_at
        values["last_seen_at"] = observed_at
        values["last_verified_at"] = observed_at if verified else None
        session.add(Job(**values))
        return "created", proposed_status == JobStatus.EXPIRED, False

    changed = existing.content_hash != digest
    if changed:
        for field in HASH_FIELDS:
            setattr(existing, field, normalized.get(field))
        existing.content_hash = digest
        existing.embedding = None

    previous_status = existing.status
    existing.status = _status_transition(previous_status, proposed_status)
    existing.last_seen_at = observed_at
    if verified:
        existing.last_verified_at = observed_at

    return (
        "updated" if changed else "unchanged",
        existing.status == JobStatus.EXPIRED and previous_status != JobStatus.EXPIRED,
        existing.status == JobStatus.ACTIVE and previous_status == JobStatus.STALE,
    )
