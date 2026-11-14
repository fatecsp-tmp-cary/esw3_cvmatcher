"""Source-specific persistence of normalized jobs."""

import hashlib
import json
from collections.abc import Iterable
from datetime import datetime
from typing import Any

from sqlalchemy import func, select
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


# Bound PostgreSQL shared lock-table use even for the largest permitted scan.
_IDENTITY_LOCK_STRIPES = 256
_IDENTITY_LOCK_NAMESPACE = 1129729365


def _identity_lock_key(platform: str, source_job_id: str) -> int:
    identity = json.dumps([platform, source_job_id], ensure_ascii=False).encode("utf-8")
    return int.from_bytes(hashlib.sha256(identity).digest()[:8]) % _IDENTITY_LOCK_STRIPES


def lock_job_identities(session: Session, identities: Iterable[tuple[str, str]]) -> None:
    """Acquire a complete batch in global key order before writing any identity.

    Fetch/normalize remote observations first. Locks last until outer commit or
    rollback, including across savepoints. Sorting actual lock keys also keeps
    stripe collisions from introducing a different acquisition order. At most
    256 two-integer advisory locks are held per transaction.
    """
    for key in sorted({_identity_lock_key(*identity) for identity in identities}):
        session.execute(select(func.pg_advisory_xact_lock(_IDENTITY_LOCK_NAMESPACE, key)))


def upsert_job(
    session: Session,
    source_id: int,
    normalized: dict[str, Any],
    observed_at: datetime,
    verified: bool,
) -> tuple[str, bool, bool]:
    """Insert or update a job by its source platform and source job ID.

    A transaction-scoped advisory lock serializes writers of the same source
    identity, including identities that do not have a row yet. Callers must
    commit or roll back to release it. Bounded stripe collisions serialize unrelated
    identities; the database unique constraint remains authoritative. Multi-record
    transactions must call lock_job_identities with their complete identity set
    before the first upsert; never fetch remote pages while holding these locks.

    The return values are the content outcome, whether this call newly expired
    the job, and whether it reactivated a stale job.
    """
    platform = normalized["platform"]
    source_job_id = normalized["source_job_id"]
    lock_job_identities(session, [(platform, source_job_id)])
    existing = session.scalar(
        select(Job)
        .where(Job.platform == platform, Job.source_job_id == source_job_id)
        .execution_options(populate_existing=True)
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
