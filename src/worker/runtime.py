"""Bounded background cycles with injected local inference and maintenance."""

import json
import logging
import math
import random
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from threading import Event

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from src.extraction.service import ExtractionWorker, enqueue
from src.ingestion.meupadrinho import ingest_meupadrinho_jsonl
from src.persistence.extraction import JobExtraction
from src.persistence.job.job import Job, JobStatus
from src.worker.scheduler import PollOutcome, SourceScheduler
from src.worker.sources import register_source

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class CycleResult:
    polls: tuple[PollOutcome, ...]
    enqueued: int
    extractions: int
    errors: tuple[str, ...]


def retry_extraction(sessions: Callable[[], Session], job_id: int, config_version: str) -> None:
    """Requeue stored nonterminal work without constructing inference services."""
    if type(job_id) is not int or job_id <= 0:
        raise ValueError("job identity must be a positive integer")
    with sessions() as session, session.begin():
        job = session.scalar(
            select(Job)
            .where(Job.id == job_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if job is None or job.status == JobStatus.EXPIRED:
            raise ValueError("retry requires a non-expired persisted job")
        enqueue(session, job_id, config_version, retry=True)


class BackgroundWorker:
    def __init__(
        self,
        scheduler: SourceScheduler,
        sessions: Callable[[], Session],
        extraction_worker: ExtractionWorker,
        config_version: str,
        *,
        embedding_hook: Callable[[], object] | None = None,
        expiration_hook: Callable[[], object] | None = None,
        max_extractions_per_cycle: int = 100,
        enqueue_batch_size: int = 100,
        poll_on_start: bool = False,
        poll_jitter_seconds: float = 0.0,
        rng: Callable[[], float] = random.random,
    ) -> None:
        if not config_version or config_version != extraction_worker.config_version:
            raise ValueError("worker and extractor configuration versions must agree")
        for value in (max_extractions_per_cycle, enqueue_batch_size):
            if type(value) is not int or value <= 0:
                raise ValueError("worker batch sizes must be positive integers")
        if (
            isinstance(poll_jitter_seconds, bool)
            or not isinstance(poll_jitter_seconds, (int, float))
            or not math.isfinite(poll_jitter_seconds)
            or not 0.0 <= poll_jitter_seconds <= 60.0
        ):
            raise ValueError("poll_jitter_seconds must be finite and between 0 and 60")
        self.scheduler = scheduler
        self.sessions = sessions
        self.extraction_worker = extraction_worker
        self.config_version = config_version
        self.embedding_hook = embedding_hook
        self.expiration_hook = expiration_hook
        self.max_extractions_per_cycle = max_extractions_per_cycle
        self.enqueue_batch_size = enqueue_batch_size
        self.poll_on_start = bool(poll_on_start)
        self.poll_jitter_seconds = float(poll_jitter_seconds)
        self.rng = rng

    def enqueue_missing(self) -> int:
        """Never reset FAILED/current work; new content/config must reprocess."""
        with self.sessions() as session, session.begin():
            identifiers = session.scalars(
                select(Job.id)
                .outerjoin(JobExtraction, JobExtraction.job_id == Job.id)
                .where(
                    Job.status != JobStatus.EXPIRED,
                    Job.content_hash.is_not(None),
                    Job.content_hash != "",
                    or_(
                        JobExtraction.job_id.is_(None),
                        JobExtraction.content_hash != Job.content_hash,
                        JobExtraction.config_version != self.config_version,
                    ),
                )
                .order_by(Job.id)
                .limit(self.enqueue_batch_size)
            ).all()
            for job_id in identifiers:
                enqueue(session, job_id, self.config_version)
            return len(identifiers)

    def retry_extraction(self, job_id: int) -> None:
        retry_extraction(self.sessions, job_id, self.config_version)

    def import_meupadrinho(self, path: str) -> None:
        if not isinstance(path, str) or not path.strip():
            raise ValueError("A non-empty MeuPadrinho JSONL path is required")
        with self.sessions() as session:
            source_id, _ = register_source(session, "meupadrinho")
            session.commit()
            result = ingest_meupadrinho_jsonl(session, source_id, path.strip())
            if result.status == "FAILED":
                raise RuntimeError("MeuPadrinho JSONL import failed")

    def run_once(self, *, now: datetime | None = None, force_poll: bool = False) -> CycleResult:
        errors = []

        def stage(name, operation, default):
            try:
                return operation()
            except Exception:
                # Never format exceptions: source/job/model text and secrets may
                # occur in arbitrary third-party failure messages.
                errors.append(name)
                logger.error(
                    json.dumps({"event": "worker_stage_failed", "stage": name}, sort_keys=True)
                )
                return default

        def poll():
            if force_poll:
                return self.scheduler.run_startup(now=now)
            return self.scheduler.run_due(now=now)

        polls = stage("source_poll", poll, ())
        if self.expiration_hook is not None:
            stage("expiration", self.expiration_hook, None)
        enqueued = stage("enqueue", self.enqueue_missing, 0)
        extractions = 0
        for _ in range(self.max_extractions_per_cycle):
            processed = stage(
                "extraction", lambda: self.extraction_worker.process_once(now=now), False
            )
            if not processed:
                break
            extractions += 1
        if self.embedding_hook is not None:
            stage("embedding", self.embedding_hook, None)
        return CycleResult(polls, enqueued, extractions, tuple(errors))

    def run_forever(
        self,
        stop: Event,
        *,
        poll_seconds: float = 5.0,
        max_backoff_seconds: float = 60.0,
    ) -> None:
        if not math.isfinite(poll_seconds) or poll_seconds <= 0:
            raise ValueError("worker polling delay must be finite and positive")
        if not math.isfinite(max_backoff_seconds) or max_backoff_seconds < poll_seconds:
            raise ValueError("max_backoff_seconds must be finite and >= poll_seconds")
        # Drain the finite startup snapshot across bounded cycles before ordinary polling.
        force_poll = self.poll_on_start
        consecutive_error_cycles = 0
        while not stop.is_set():
            if force_poll:
                result = self.run_once(force_poll=True)
                force_poll = self.scheduler.startup_pending
            else:
                result = self.run_once()
            if getattr(result, "errors", ()):
                consecutive_error_cycles += 1
                base_wait = min(
                    poll_seconds * (2 ** min(consecutive_error_cycles, 6)),
                    max_backoff_seconds,
                )
            else:
                consecutive_error_cycles = 0
                base_wait = poll_seconds
            jitter = (
                min(max(float(self.rng()), 0.0), 1.0) * self.poll_jitter_seconds
                if self.poll_jitter_seconds > 0.0
                else 0.0
            )
            stop.wait(base_wait + jitter)
