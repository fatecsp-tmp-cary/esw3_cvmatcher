"""Exact pgvector retrieval with current job provenance; no candidate persistence."""

from sqlalchemy import func, literal, select
from sqlalchemy.orm import Session

from src.embeddings.config import EmbeddingConfig
from src.embeddings.encoder import normalized_vector
from src.embeddings.service import ready_predicate
from src.persistence.job.job import Job, JobStatus


def semantic_statement(
    query_vector: list[float],
    config: EmbeddingConfig,
    extraction_version: str,
    *,
    limit: int = 100,
):
    if type(limit) is not int or limit < 1:
        raise ValueError("Retrieval limit must be a positive integer")
    vector = normalized_vector(query_vector)
    distance = Job.embedding.cosine_distance(vector)
    similarity = func.greatest(-1.0, func.least(1.0, literal(1.0) - distance)).label("similarity")
    return (
        select(Job, similarity)
        .where(Job.status == JobStatus.ACTIVE, ready_predicate(config, extraction_version))
        .order_by(distance.asc(), Job.platform.asc(), Job.source_job_id.asc(), Job.id.asc())
        .limit(limit)
    )


def retrieve_semantic(
    session: Session,
    query_vector: list[float],
    config: EmbeddingConfig,
    extraction_version: str,
    *,
    limit: int = 100,
) -> list[tuple[Job, float]]:
    """Return cosine similarities [-1,1]; caller owns empirical score calibration."""
    return [
        (job, float(score))
        for job, score in session.execute(
            semantic_statement(query_vector, config, extraction_version, limit=limit)
        )
    ]
