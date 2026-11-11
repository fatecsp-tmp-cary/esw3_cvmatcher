"""Short PostgreSQL claim transactions around injected local background inference.

A crashed worker claim expires after five minutes. Recovery consumes the same
three-claim budget; stale workers cannot publish. Stop workers before config changes.
"""

import json
import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import and_, exists, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from src.extraction.contracts import LocalExtractor, SpanEvidence
from src.persistence.extraction import JobExtraction
from src.persistence.job.job import Job, JobStatus

logger = logging.getLogger(__name__)


def _version(value: str) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > 255:
        raise ValueError("An explicit extraction configuration version is required")
    return value


def ready_predicate(config_version: str):
    """SQL predicate for every retrieval path; missing/stale evidence fails closed."""
    return exists().where(
        JobExtraction.job_id == Job.id,
        JobExtraction.status == "SUCCEEDED",
        JobExtraction.content_hash == Job.content_hash,
        JobExtraction.config_version == _version(config_version),
    )


def enqueue(session: Session, job_id: int, config_version: str, *, retry: bool = False) -> None:
    """Queue current job content in the caller's transaction.

    Same-version failed/running work is unchanged unless explicit retry=True.
    Ingestion must enqueue changed content; readiness independently checks hashes.
    """
    _version(config_version)
    job = session.scalar(
        select(Job)
        .where(Job.id == job_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if job is None or not job.content_hash:
        raise ValueError("A persisted job with a content hash is required")
    now = datetime.now(UTC)
    session.execute(
        insert(JobExtraction)
        .values(
            job_id=job.id,
            content_hash=job.content_hash,
            config_version=config_version,
            status="PENDING",
            attempts=0,
            updated_at=now,
        )
        .on_conflict_do_nothing(index_elements=[JobExtraction.job_id])
    )
    state = session.scalar(
        select(JobExtraction)
        .where(JobExtraction.job_id == job_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if retry or state.content_hash != job.content_hash or state.config_version != config_version:
        state.content_hash = job.content_hash
        state.config_version = config_version
        state.status = "PENDING"
        state.attempts = 0
        state.claim_token = None
        state.lease_expires_at = None
        state.next_attempt_at = None
        state.error_code = None
        state.evidence = None
        state.updated_at = now


@dataclass(frozen=True, slots=True)
class Claim:
    job_id: int
    content_hash: str
    config_version: str
    token: str
    text: str


class ExtractionWorker:
    """Each factory call must return an independent, dedicated Session."""

    def __init__(
        self, sessions: Callable[[], Session], extractor: LocalExtractor, config_version: str
    ):
        self.sessions = sessions
        self.extractor = extractor
        self.config_version = _version(config_version)

    def claim(self, *, now: datetime | None = None) -> Claim | None:
        now = now or datetime.now(UTC)
        with self.sessions() as session, session.begin():
            state = session.scalar(
                select(JobExtraction)
                .join(Job, Job.id == JobExtraction.job_id)
                .where(
                    or_(
                        and_(
                            JobExtraction.status == "PENDING",
                            JobExtraction.attempts < 3,
                            or_(
                                JobExtraction.next_attempt_at.is_(None),
                                JobExtraction.next_attempt_at <= now,
                            ),
                        ),
                        and_(
                            JobExtraction.status == "RUNNING", JobExtraction.lease_expires_at <= now
                        ),
                    ),
                    JobExtraction.config_version == self.config_version,
                    JobExtraction.content_hash == Job.content_hash,
                    Job.status != JobStatus.EXPIRED,
                )
                .order_by(JobExtraction.job_id)
                .limit(1)
                .with_for_update(skip_locked=True, of=JobExtraction)
            )
            if state is None:
                return None
            if state.attempts == 3:
                state.status = "FAILED"
                state.claim_token = None
                state.lease_expires_at = None
                state.error_code = "claim_expired"
                state.updated_at = now
                state.evidence = None
                # Emit only fixed category and internal numeric identity.
                logger.error(
                    json.dumps(
                        {
                            "event": "job_extraction_failed",
                            "job_id": state.job_id,
                            "error_code": "claim_expired",
                            "attempts": 3,
                        },
                        sort_keys=True,
                    )
                )
                return None
            job = session.get(Job, state.job_id)
            state.lease_expires_at = now + timedelta(minutes=5)
            state.status = "RUNNING"
            state.claim_token = str(uuid4())
            state.attempts += 1
            state.updated_at = now
            return Claim(
                job.id,
                state.content_hash,
                state.config_version,
                state.claim_token,
                job.title + "\n" + (job.description or ""),
            )

    def finish(
        self,
        claim: Claim,
        evidence: list[dict[str, object]] | None,
        *,
        error_code: str | None = None,
        now: datetime | None = None,
    ) -> bool:
        """CAS completion ignores revoked claims; only fixed safe error categories persist."""
        if error_code not in (None, "inference_error", "invalid_result"):
            raise ValueError("Unknown extraction error category")
        now = now or datetime.now(UTC)
        alert = False
        with self.sessions() as session, session.begin():
            state = session.scalar(
                select(JobExtraction).where(JobExtraction.job_id == claim.job_id).with_for_update()
            )
            if (
                state is None
                or state.status != "RUNNING"
                or state.claim_token != claim.token
                or state.lease_expires_at <= now
            ):
                return False
            job = session.get(Job, claim.job_id, populate_existing=True)
            state.claim_token = None
            state.lease_expires_at = None
            state.updated_at = now
            if job.content_hash != claim.content_hash:
                state.status = "PENDING"
                state.content_hash = job.content_hash or claim.content_hash
                state.attempts = 0
                state.evidence = None
                state.error_code = None
                state.next_attempt_at = None
                return False
            state.error_code = error_code
            if error_code:
                state.evidence = None
                state.status = "FAILED" if state.attempts == 3 else "PENDING"
                state.next_attempt_at = (
                    None if state.attempts == 3 else now + timedelta(seconds=30 * state.attempts)
                )
                alert = state.status == "FAILED"
            else:
                if evidence is None:
                    raise ValueError("Successful extraction requires evidence (possibly empty)")
                state.status = "SUCCEEDED"
                state.evidence = evidence
                state.next_attempt_at = None
        if alert:
            logger.error(
                json.dumps(
                    {
                        "event": "job_extraction_failed",
                        "job_id": claim.job_id,
                        "error_code": error_code,
                        "attempts": 3,
                    },
                    sort_keys=True,
                )
            )
        return True

    def process_once(self, *, now: datetime | None = None) -> bool:
        claim = self.claim(now=now)
        if claim is None:
            return False
        try:
            spans = self.extractor.extract(claim.text)
        except Exception:
            self.finish(claim, None, error_code="inference_error", now=now)
            return True
        try:
            if not isinstance(spans, list) or any(not isinstance(s, SpanEvidence) for s in spans):
                raise ValueError("Invalid extraction result")
            serialized = [s.serialize(claim.text) for s in spans]
            # Deterministic overlap duplicates are supporting evidence only.
            unique = {}
            for span in serialized:
                key = (span["start"], span["end"], span["label"])
                if key not in unique or span["confidence"] > unique[key]["confidence"]:
                    unique[key] = span
            evidence = [unique[key] for key in sorted(unique)]
        except Exception:
            self.finish(claim, None, error_code="invalid_result", now=now)
            return True
        self.finish(claim, evidence, now=now)
        return True
