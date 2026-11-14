"""Portuguese PostgreSQL full-text retrieval over active jobs."""

from dataclasses import dataclass

from sqlalchemy import func, select, union_all
from sqlalchemy.orm import Session

from src.indexing.textual import any_term_query, job_search_document, requirement_search_document
from src.persistence.job.job import Job, JobStatus
from src.persistence.job.skill import JobRequirement


@dataclass(frozen=True, slots=True)
class TextualMatch:
    """A job retrieved by FTS and its unnormalized PostgreSQL rank."""

    job: Job
    score: float


def search_active_jobs(
    session: Session,
    query: str,
    *,
    limit: int = 100,
) -> list[TextualMatch]:
    """Retrieve active jobs matching any plain-text query lexeme.

    Location text participates only in retrieval. This function never applies
    geographic eligibility filters. Its raw rank is intended for an internal
    matching stage, not as the public `[0, 100]` compatibility score.
    """
    if not isinstance(query, str):
        raise TypeError("query must be text")
    if len(query) > 5000:
        raise ValueError("query must be at most 5000 characters")
    if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 500:
        raise ValueError("limit must be between 1 and 500")
    if not query.strip():
        return []

    tsquery = any_term_query(query)
    job_vector = job_search_document()
    requirement_vector = requirement_search_document()
    requirement_rank = func.ts_rank_cd(requirement_vector, tsquery)
    requirement_matches = (
        select(
            JobRequirement.job_id.label("job_id"),
            func.max(requirement_rank).label("score"),
        )
        .join(Job, Job.id == JobRequirement.job_id)
        .where(Job.status == JobStatus.ACTIVE, requirement_vector.bool_op("@@")(tsquery))
        .group_by(JobRequirement.job_id)
    )
    job_matches = select(
        Job.id.label("job_id"), func.ts_rank_cd(job_vector, tsquery).label("score")
    ).where(Job.status == JobStatus.ACTIVE, job_vector.bool_op("@@")(tsquery))
    candidates = union_all(job_matches, requirement_matches).subquery()
    scores = (
        select(candidates.c.job_id, func.sum(candidates.c.score).label("score"))
        .group_by(candidates.c.job_id)
        .subquery()
    )
    statement = (
        select(Job, scores.c.score)
        .join(scores, scores.c.job_id == Job.id)
        .order_by(
            scores.c.score.desc(),
            Job.publication_date.desc().nulls_last(),
            Job.platform.asc(),
            Job.source_job_id.asc(),
        )
        .limit(limit)
    )

    return [
        TextualMatch(job=job, score=float(score)) for job, score in session.execute(statement).all()
    ]
