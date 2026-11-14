"""Job-only embedding maintenance with short PostgreSQL claim transactions."""

import json
import logging
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import and_, exists, func, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from src.embeddings.config import DIMENSIONS, EmbeddingConfig
from src.embeddings.encoder import LocalEmbeddingEncoder, normalized_vector
from src.extraction.service import ready_predicate as extraction_ready
from src.persistence.embedding import JobEmbedding
from src.persistence.job.job import Job, JobStatus
from src.persistence.job.skill import JobRequirement

logger = logging.getLogger(__name__)


def _extraction_version(value: str) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > 255:
        raise ValueError("An explicit extraction version is required")
    return value


def ready_predicate(config: EmbeddingConfig, extraction_version: str):
    """Require a current successful extraction and matching embedding provenance."""
    return and_(
        Job.embedding.is_not(None),
        func.vector_dims(Job.embedding) == DIMENSIONS,
        extraction_ready(_extraction_version(extraction_version)),
        exists().where(
            JobEmbedding.job_id == Job.id,
            JobEmbedding.status == "SUCCEEDED",
            JobEmbedding.content_hash == Job.content_hash,
            JobEmbedding.model_version == config.model_version,
            JobEmbedding.extraction_version == extraction_version,
        ),
    )


def enqueue(
    session: Session,
    job_id: int,
    config: EmbeddingConfig,
    extraction_version: str,
    *,
    retry: bool = False,
) -> None:
    """Invalidate independently on content/model/policy/extraction changes.

    A same-version failed task needs explicit retry=True. No commits are performed
    here; the caller coordinates this with its job/extraction transaction.
    """
    _extraction_version(extraction_version)
    job = session.scalar(
        select(Job)
        .where(Job.id == job_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if job is None or not job.content_hash:
        raise ValueError("A persisted job with a content hash is required")
    now = datetime.now(UTC)
    created = session.scalar(
        insert(JobEmbedding)
        .values(
            job_id=job.id,
            content_hash=job.content_hash,
            model_version=config.model_version,
            extraction_version=extraction_version,
            status="PENDING",
            attempts=0,
            updated_at=now,
        )
        .on_conflict_do_nothing(index_elements=[JobEmbedding.job_id])
        .returning(JobEmbedding.job_id)
    )
    state = session.scalar(
        select(JobEmbedding)
        .where(JobEmbedding.job_id == job_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if state is None:
        raise RuntimeError("Embedding state invariant failed")
    if (
        created is not None
        or retry
        or state.content_hash != job.content_hash
        or state.model_version != config.model_version
        or state.extraction_version != extraction_version
    ):
        job.embedding = None
        state.content_hash = job.content_hash
        state.model_version = config.model_version
        state.extraction_version = extraction_version
        state.status = "PENDING"
        state.attempts = 0
        state.claim_token = None
        state.lease_expires_at = None
        state.next_attempt_at = None
        state.updated_at = now
        state.error_code = None


def job_text(job: Job, requirements: Iterable[str] = ()) -> str:
    """Job-only semantic representation including current normalized requirements.

    The full cleaned description is retained. Explicit skills, location and mode
    are descriptive text, never a geographic eligibility decision.
    """
    fields = [job.title]
    if job.skills:
        fields.append("\n".join(job.skills))
    fields.extend(sorted(set(requirements)))
    if job.description:
        fields.append(job.description)
    if job.location:
        fields.extend(value for _, value in sorted(job.location.items()) if isinstance(value, str))
    if job.work_arrangement:
        fields.append(job.work_arrangement.value)
    return "\n".join(fields)


@dataclass(frozen=True, slots=True, repr=False)
class EmbeddingClaim:
    job_id: int
    content_hash: str
    model_version: str
    extraction_version: str
    token: str
    text: str


class EmbeddingWorker:
    def __init__(
        self,
        sessions: Callable[[], Session],
        encoder: LocalEmbeddingEncoder,
        extraction_version: str,
    ):
        self.sessions = sessions
        self.encoder = encoder
        self.config = encoder.config
        self.extraction_version = _extraction_version(extraction_version)

    def claim(self, *, now: datetime | None = None) -> EmbeddingClaim | None:
        now = now or datetime.now(UTC)
        with self.sessions() as session, session.begin():
            state = session.scalar(
                select(JobEmbedding)
                .join(Job, Job.id == JobEmbedding.job_id)
                .where(
                    or_(
                        and_(
                            JobEmbedding.status == "PENDING",
                            JobEmbedding.attempts < 3,
                            or_(
                                JobEmbedding.next_attempt_at.is_(None),
                                JobEmbedding.next_attempt_at <= now,
                            ),
                        ),
                        and_(
                            JobEmbedding.status == "RUNNING",
                            JobEmbedding.lease_expires_at <= now,
                        ),
                    ),
                    JobEmbedding.content_hash == Job.content_hash,
                    JobEmbedding.model_version == self.config.model_version,
                    JobEmbedding.extraction_version == self.extraction_version,
                    extraction_ready(self.extraction_version),
                    Job.status != JobStatus.EXPIRED,
                )
                .order_by(JobEmbedding.job_id)
                .limit(1)
                .with_for_update(skip_locked=True, of=JobEmbedding)
            )
            if state is None:
                return None
            if state.attempts == 3:
                state.status = "FAILED"
                state.claim_token = None
                state.lease_expires_at = None
                state.error_code = "claim_expired"
                state.updated_at = now
                _alert(state.job_id, "claim_expired")
                return None
            job = session.get(Job, state.job_id)
            if job is None:
                raise RuntimeError("Embedding job invariant failed")
            state.status = "RUNNING"
            state.claim_token = str(uuid4())
            state.lease_expires_at = now + timedelta(minutes=5)
            state.updated_at = now
            state.attempts += 1
            return EmbeddingClaim(
                job.id,
                state.content_hash,
                state.model_version,
                state.extraction_version,
                state.claim_token,
                job_text(
                    job,
                    session.scalars(
                        select(JobRequirement.text).where(JobRequirement.job_id == job.id)
                    ),
                ),
            )

    def finish(
        self,
        claim: EmbeddingClaim,
        vector: list[float] | None,
        *,
        error_code: str | None = None,
        now: datetime | None = None,
    ) -> bool:
        if error_code not in (None, "inference_error", "invalid_result"):
            raise ValueError("Unknown embedding error category")
        prepared = normalized_vector(vector) if error_code is None and vector is not None else None
        if error_code is None and prepared is None:
            raise ValueError("Successful embedding requires a vector")
        now = now or datetime.now(UTC)
        alert = False
        with self.sessions() as session, session.begin():
            # Consistent Job -> metadata lock order with enqueue prevents stale publication.
            job = session.scalar(select(Job).where(Job.id == claim.job_id).with_for_update())
            state = session.scalar(
                select(JobEmbedding).where(JobEmbedding.job_id == claim.job_id).with_for_update()
            )
            if (
                state is None
                or job is None
                or state.status != "RUNNING"
                or state.claim_token != claim.token
                or state.lease_expires_at is None
                or state.lease_expires_at <= now
                or state.model_version != claim.model_version
                or state.extraction_version != claim.extraction_version
                or claim.model_version != self.config.model_version
            ):
                return False
            is_extracted = (
                session.scalar(
                    select(Job.id).where(
                        Job.id == job.id, extraction_ready(self.extraction_version)
                    )
                )
                is not None
            )
            state.claim_token = None
            state.lease_expires_at = None
            state.updated_at = now
            if (
                job.content_hash != claim.content_hash
                or not is_extracted
                or job.status == JobStatus.EXPIRED
            ):
                job.embedding = None
                state.status = "PENDING"
                state.attempts = 0
                state.content_hash = job.content_hash or claim.content_hash
                state.error_code = None
                state.next_attempt_at = None
                return False
            state.error_code = error_code
            if error_code:
                job.embedding = None
                state.status = "FAILED" if state.attempts == 3 else "PENDING"
                state.next_attempt_at = (
                    None if state.attempts == 3 else now + timedelta(seconds=30 * state.attempts)
                )
                alert = state.status == "FAILED"
            else:
                job.embedding = prepared
                state.status = "SUCCEEDED"
                state.next_attempt_at = None
        if alert:
            _alert(claim.job_id, error_code)
        return True

    def process_once(self, *, now: datetime | None = None) -> bool:
        claim = self.claim(now=now)
        if claim is None:
            return False
        try:
            vectors = self.encoder.encode_jobs([claim.text])
        except Exception:
            self.finish(claim, None, error_code="inference_error", now=now)
            return True
        try:
            if len(vectors) != 1:
                raise ValueError("Invalid embedding batch")
            vector = normalized_vector(vectors[0])
        except Exception:
            self.finish(claim, None, error_code="invalid_result", now=now)
            return True
        self.finish(claim, vector, now=now)
        return True


def _alert(job_id: int, code: str | None) -> None:
    logger.error(
        json.dumps(
            {
                "event": "job_embedding_failed",
                "job_id": job_id,
                "error_code": code,
                "attempts": 3,
            },
            sort_keys=True,
        )
    )
