"""Portuguese PostgreSQL full-text retrieval over active jobs."""

from dataclasses import dataclass

from sqlalchemy import Text, cast, func, literal_column, select
from sqlalchemy.orm import Session

from src.persistence.job.job import Job, JobStatus
from src.persistence.job.skill import JobRequirement

_PORTUGUESE_CONFIG = literal_column("'portuguese'::regconfig")


@dataclass(frozen=True, slots=True)
class TextualMatch:
    """A job retrieved by FTS and its unnormalized PostgreSQL rank."""

    job: Job
    score: float


def _job_vector():
    searchable_text = func.concat_ws(
        " ",
        Job.title,
        Job.company,
        Job.description,
        cast(Job.keywords, Text),
        cast(Job.skills, Text),
        cast(Job.location, Text),
    )
    return func.to_tsvector(_PORTUGUESE_CONFIG, searchable_text)


def search_active_jobs(
    session: Session,
    query: str,
    *,
    limit: int = 100,
) -> list[TextualMatch]:
    """Search active jobs and requirements using Portuguese stemming.

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

    tsquery = func.websearch_to_tsquery(_PORTUGUESE_CONFIG, query)
    job_vector = _job_vector()
    requirement_vector = func.to_tsvector(_PORTUGUESE_CONFIG, JobRequirement.text)
    requirement_rank = func.ts_rank_cd(requirement_vector, tsquery)
    requirement_matches = (
        select(
            JobRequirement.job_id.label("job_id"),
            func.max(requirement_rank).label("score"),
        )
        .where(requirement_vector.bool_op("@@")(tsquery))
        .group_by(JobRequirement.job_id)
        .subquery()
    )

    job_rank = func.ts_rank_cd(job_vector, tsquery)
    combined_rank = func.coalesce(job_rank, 0.0) + func.coalesce(
        requirement_matches.c.score, 0.0
    )
    statement = (
        select(Job, combined_rank.label("textual_score"))
        .outerjoin(requirement_matches, requirement_matches.c.job_id == Job.id)
        .where(
            Job.status == JobStatus.ACTIVE,
            job_vector.bool_op("@@")(tsquery) | requirement_matches.c.job_id.is_not(None),
        )
        .order_by(
            combined_rank.desc(),
            Job.publication_date.desc().nulls_last(),
            Job.platform.asc(),
            Job.source_job_id.asc(),
        )
        .limit(limit)
    )

    return [
        TextualMatch(job=job, score=float(score))
        for job, score in session.execute(statement).all()
    ]
