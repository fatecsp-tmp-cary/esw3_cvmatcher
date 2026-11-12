"""Production worker composition using pinned offline models and PostgreSQL."""

import os
from datetime import UTC, datetime

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
from src.worker.scheduler import SourceScheduler


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


def create_default_worker() -> BackgroundWorker:
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
        SourceScheduler(engine, sessions),
        sessions,
        ExtractionWorker(sessions, extractor, EXTRACTION_VERSION),
        EXTRACTION_VERSION,
        embedding_hook=EmbeddingMaintenance(
            sessions, EmbeddingWorker(sessions, encoder, EXTRACTION_VERSION)
        ),
        expiration_hook=expire,
    )
