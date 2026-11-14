"""Production worker composition using pinned offline models and PostgreSQL."""

import os
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import or_, select

from src.embeddings.config import EmbeddingConfig
from src.embeddings.encoder import LocalEmbeddingEncoder
from src.embeddings.service import EmbeddingWorker, enqueue
from src.extraction.gliner import EXTRACTION_VERSION, GlinerExtractor
from src.extraction.service import ExtractionWorker, ready_predicate
from src.lifecycle.expiration import expire_source_timestamps
from src.persistence.database import create_db_engine, create_session_factory
from src.persistence.embedding import JobEmbedding
from src.persistence.job.job import Job, JobStatus
from src.worker.runtime import BackgroundWorker
from src.worker.scheduler import SourceScheduler, parse_daily_time


class EmbeddingMaintenance:
    """Enqueue only missing/outdated ready jobs; never reset current FAILED work."""

    def __init__(self, sessions, worker, *, batch_size=100):
        if type(batch_size) is not int or batch_size <= 0:
            raise ValueError("Embedding maintenance batch size must be positive")
        self.sessions = sessions
        self.worker = worker
        self.batch_size = batch_size

    def __call__(self):
        config = self.worker.config
        version = self.worker.extraction_version
        with self.sessions() as session, session.begin():
            identifiers = session.scalars(
                select(Job.id)
                .outerjoin(JobEmbedding, JobEmbedding.job_id == Job.id)
                .where(
                    Job.status != JobStatus.EXPIRED,
                    ready_predicate(version),
                    or_(
                        JobEmbedding.job_id.is_(None),
                        JobEmbedding.content_hash != Job.content_hash,
                        JobEmbedding.model_version != config.model_version,
                        JobEmbedding.extraction_version != version,
                    ),
                )
                .order_by(Job.id)
                .limit(self.batch_size)
            ).all()
            for job_id in identifiers:
                enqueue(session, job_id, config, version)
        processed = 0
        for _ in range(self.batch_size):
            if not self.worker.process_once():
                break
            processed += 1
        return processed


def source_schedule(environ: Mapping[str, str]) -> dict[str, Any]:
    """Read the optional daily polling time, time zone and poll-on-start flag.

    Invalid values raise, so the worker fails closed instead of guessing a schedule.
    """
    daily = environ.get("CVMATCHER_SOURCE_DAILY_AT", "").strip()
    zone = environ.get("CVMATCHER_SOURCE_TIMEZONE", "").strip() or "UTC"
    flag = environ.get("CVMATCHER_SOURCE_POLL_ON_START", "").strip() or "0"
    if flag not in ("0", "1"):
        raise ValueError("CVMATCHER_SOURCE_POLL_ON_START must be 0 or 1")
    try:
        timezone = ZoneInfo(zone)
    except Exception:
        raise ValueError("CVMATCHER_SOURCE_TIMEZONE must be an IANA time zone") from None
    return {
        "daily_at": parse_daily_time(daily) if daily else None,
        "timezone": timezone,
        "poll_on_start": flag == "1",
    }


def create_default_worker() -> BackgroundWorker:
    schedule = source_schedule(os.environ)
    directory = os.environ["CVMATCHER_EXTRACTION_DIRECTORY"]
    if not directory.strip():
        raise ValueError("Prepared extraction directory is required")
    extractor = GlinerExtractor(directory)
    encoder = LocalEmbeddingEncoder(
        EmbeddingConfig(cache_directory=os.environ.get("CVMATCHER_EMBEDDING_CACHE"))
    )
    engine = create_db_engine()
    sessions = create_session_factory(engine)

    def expire():
        with sessions() as session, session.begin():
            return expire_source_timestamps(session, now=datetime.now(UTC))

    return BackgroundWorker(
        SourceScheduler(
            engine,
            sessions,
            daily_at=schedule["daily_at"],
            timezone=schedule["timezone"],
        ),
        sessions,
        ExtractionWorker(sessions, extractor, EXTRACTION_VERSION),
        EXTRACTION_VERSION,
        embedding_hook=EmbeddingMaintenance(
            sessions, EmbeddingWorker(sessions, encoder, EXTRACTION_VERSION)
        ),
        expiration_hook=expire,
        poll_on_start=schedule["poll_on_start"],
    )
