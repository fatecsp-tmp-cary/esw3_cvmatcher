"""Lazy production composition; public API factories remain independently testable."""

import os
from functools import lru_cache
from threading import Lock

from sqlalchemy.exc import (
    ArgumentError,
    DisconnectionError,
    InterfaceError,
    OperationalError,
)
from sqlalchemy.exc import (
    TimeoutError as DatabaseTimeoutError,
)

from src.api.errors import DependencyUnavailableError
from src.embeddings.encoder import EmbeddingUnavailableError
from src.processing import checkpoint
from src.schemas.candidate.curriculum import CurriculumRequest
from src.schemas.matches import MatchesResponse

_factory_lock = Lock()
_DEPENDENCY_ERRORS = (
    OperationalError,
    InterfaceError,
    DisconnectionError,
    DatabaseTimeoutError,
    EmbeddingUnavailableError,
)


@lru_cache(maxsize=1)
def _configured_pipeline():
    from src.embeddings.config import EmbeddingConfig
    from src.embeddings.encoder import LocalEmbeddingEncoder
    from src.extraction.gliner import EXTRACTION_VERSION
    from src.matching.pipeline import MatchingPipeline
    from src.persistence.database import create_db_engine, create_session_factory

    if not os.environ.get("DATABASE_URL", "").strip():
        raise DependencyUnavailableError
    try:
        engine = create_db_engine()
    except (ArgumentError, ImportError):
        # Invalid database configuration or a missing configured driver, only
        # at composition. Query/programming failures must retain the 500 path.
        raise DependencyUnavailableError from None
    sessions = create_session_factory(engine)
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
    except _DEPENDENCY_ERRORS:
        # Only recognized outages use 503. Unexpected application failures reach
        # the API's privacy-safe 500 handler, which retains type/source diagnostics.
        raise DependencyUnavailableError from None


def production_ready() -> None:
    try:
        from sqlalchemy import select

        from src.persistence.extraction import JobExtraction

        pipeline = get_pipeline()
        with pipeline.sessions() as session:
            session.execute(select(JobExtraction.job_id).limit(1)).all()
        pipeline.encoder.encode_queries(["model readiness"])
    except _DEPENDENCY_ERRORS:
        raise DependencyUnavailableError from None
