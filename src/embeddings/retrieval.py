"""Exact pgvector retrieval with current job provenance; no candidate persistence."""

from typing import Literal

from sqlalchemy import func, literal, select
from sqlalchemy.orm import Session

from src.embeddings.config import EmbeddingConfig
from src.embeddings.encoder import normalized_vector
from src.embeddings.service import ready_predicate
from src.persistence.embedding import JobEmbedding
from src.persistence.job.job import ACTIVE_STATUSES, Job, JobStatus, status_predicate

VectorKind = Literal["full", "core", "best"]


def semantic_statement(
    query_vector: list[float],
    config: EmbeddingConfig,
    extraction_version: str,
    *,
    limit: int = 100,
    statuses: tuple[JobStatus, ...] = ACTIVE_STATUSES,
    exclude_ids: tuple[int, ...] = (),
    vector: VectorKind = "full",
):
    """Exact cosine scan over full, job-core, or best-of-both vectors (ADR-027)."""
    if type(limit) is not int or limit < 1:
        raise ValueError("Retrieval limit must be a positive integer")
    if vector not in ("full", "core", "best"):
        raise ValueError("Unknown job vector kind")
    query = normalized_vector(query_vector)
    if vector == "full":
        distance = Job.embedding.cosine_distance(query)
    elif vector == "core":
        distance = JobEmbedding.core_embedding.cosine_distance(query)
    else:
        distance = func.least(
            Job.embedding.cosine_distance(query),
            JobEmbedding.core_embedding.cosine_distance(query),
        )
    similarity = func.greatest(-1.0, func.least(1.0, literal(1.0) - distance)).label("similarity")
    statement = select(Job, similarity)
    if vector in ("core", "best"):
        statement = statement.join(JobEmbedding, JobEmbedding.job_id == Job.id)
    statement = (
        statement.where(status_predicate(statuses), ready_predicate(config, extraction_version))
        .order_by(distance.asc(), Job.platform.asc(), Job.source_job_id.asc(), Job.id.asc())
        .limit(limit)
    )
    if exclude_ids:
        statement = statement.where(Job.id.not_in(exclude_ids))
    return statement


def retrieve_semantic(
    session: Session,
    query_vector: list[float],
    config: EmbeddingConfig,
    extraction_version: str,
    *,
    limit: int = 100,
    statuses: tuple[JobStatus, ...] = ACTIVE_STATUSES,
    exclude_ids: tuple[int, ...] = (),
    vector: VectorKind = "full",
) -> list[tuple[Job, float]]:
    """Return cosine similarities [-1,1]; caller owns empirical score calibration."""
    return [
        (job, float(score))
        for job, score in session.execute(
            semantic_statement(
                query_vector,
                config,
                extraction_version,
                limit=limit,
                statuses=statuses,
                exclude_ids=exclude_ids,
                vector=vector,
            )
        )
    ]
