"""Lazy production composition; public API factories remain independently testable."""

import os
from functools import lru_cache
from threading import Lock

from src.api.errors import DependencyUnavailableError
from src.processing import ProcessingUnavailable, checkpoint
from src.schemas.candidate.curriculum import CurriculumRequest
from src.schemas.matches import MatchesResponse

_factory_lock = Lock()


@lru_cache(maxsize=1)
def _configured_pipeline():
    from src.embeddings.config import EmbeddingConfig
    from src.embeddings.encoder import LocalEmbeddingEncoder
    from src.extraction.gliner import EXTRACTION_VERSION
    from src.matching.pipeline import MatchingPipeline
    from src.persistence.database import create_db_engine, create_session_factory

    sessions = create_session_factory(create_db_engine())
    encoder = LocalEmbeddingEncoder(
        EmbeddingConfig(cache_directory=os.environ.get("CVMATCHER_EMBEDDING_CACHE"))
    )
    return MatchingPipeline(sessions, encoder, EXTRACTION_VERSION)


def get_pipeline():
    # functools cache alone may call the factory twice on simultaneous first calls.
    with _factory_lock:
        return _configured_pipeline()


def production_matches(request: CurriculumRequest, limit: int) -> MatchesResponse:
    try:
        pipeline = get_pipeline()
        checkpoint()
        return pipeline(request, limit)
    except ProcessingUnavailable:
        # The HTTP boundary converts this fixed-category budget failure to 503.
        raise
    except Exception:
        # Never expose DB URLs, model paths, submitted text or library exceptions.
        raise DependencyUnavailableError from None


def production_ready() -> None:
    try:
        from sqlalchemy import select

        from src.persistence.extraction import JobExtraction

        pipeline = get_pipeline()
        with pipeline.sessions() as session:
            session.execute(select(JobExtraction.job_id).limit(1)).all()
        pipeline.encoder.encode_queries(["model readiness"])
    except Exception:
        raise DependencyUnavailableError from None
