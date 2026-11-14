"""Bounded background cycles with injected local inference and maintenance."""

import json
import logging
import math
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from threading import Event

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from src.extraction.service import ExtractionWorker, enqueue
from src.persistence.extraction import JobExtraction
from src.persistence.job.job import Job, JobStatus
from src.worker.scheduler import PollOutcome, SourceScheduler

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class CycleResult:
    polls: tuple[PollOutcome, ...]
    enqueued: int
    extractions: int
    errors: tuple[str, ...]


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
    ) -> None:
        if not config_version or config_version != extraction_worker.config_version:
            raise ValueError("worker and extractor configuration versions must agree")
        for value in (max_extractions_per_cycle, enqueue_batch_size):
            if type(value) is not int or value <= 0:
                raise ValueError("worker batch sizes must be positive integers")
        self.scheduler = scheduler
        self.sessions = sessions
        self.extraction_worker = extraction_worker
        self.config_version = config_version
        self.embedding_hook = embedding_hook
        self.expiration_hook = expiration_hook
        self.max_extractions_per_cycle = max_extractions_per_cycle
        self.enqueue_batch_size = enqueue_batch_size
        self.poll_on_start = bool(poll_on_start)

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
        if type(job_id) is not int or job_id <= 0:
            raise ValueError("job identity must be a positive integer")
        with self.sessions() as session, session.begin():
            enqueue(session, job_id, self.config_version, retry=True)

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
                return self.scheduler.run_due(now=now, force=True)
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

    def run_forever(self, stop: Event, *, poll_seconds: float = 5.0) -> None:
        if not math.isfinite(poll_seconds) or poll_seconds <= 0:
            raise ValueError("worker polling delay must be finite and positive")
        # Only the first cycle of a long-running worker may poll before a source is due.
        force_poll = self.poll_on_start
        while not stop.is_set():
            if force_poll:
                self.run_once(force_poll=True)
                force_poll = False
            else:
                self.run_once()
            stop.wait(poll_seconds)
