"""Deterministic status/readiness-gated PostgreSQL textual retrieval."""

from dataclasses import dataclass

from sqlalchemy import Select, false, func, select, union_all
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import ColumnElement

from src.indexing.textual import any_term_query, job_search_document, requirement_search_document
from src.normalization.candidate.curriculum import NormalizedCandidate
from src.persistence.job.job import ACTIVE_STATUSES, Job, JobStatus, status_predicate
from src.persistence.job.skill import JobRequirement


def candidate_query_text(candidate: NormalizedCandidate) -> str:
    """Project all available matching text transiently, without identity/dates.

    Do not log this value or persist it in search/indexing metadata. Categorical
    free text remains supporting textual evidence, never a mandatory exclusion.
    """
    sections = (
        ((x.title, x.description) for x in candidate.experience),
        ((x.course, x.level) for x in candidate.education),
        ((x.title, x.description, x.technologies) for x in candidate.projects),
        ((x.description,) for x in candidate.competencies),
        ((x.name, x.level) for x in candidate.languages),
    )
    return "\n".join(value for section in sections for entry in section for value in entry)


@dataclass(frozen=True, slots=True)
class TextualMatch:
    """Legacy retrieval result carrying raw PostgreSQL rank, not compatibility."""

    job: Job
    score: float


def _retrieval_statement(
    query_text, *, readiness, requirements, limit, bounded, statuses=ACTIVE_STATUSES
):
    if not isinstance(query_text, str):
        raise TypeError("query must be text")
    if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
        raise ValueError("retrieval limit must be a positive integer")
    document = job_search_document(requirements=requirements)
    requirement_document = requirement_search_document()
    query = any_term_query(query_text)
    gate = false() if readiness is None else readiness
    status = status_predicate(statuses)
    job_matches = select(
        Job.id.label("job_id"), func.ts_rank_cd(document, query).label("rank")
    ).where(status, gate, document.bool_op("@@")(query))
    # Maximum avoids multiplying evidence by the number of requirement rows.
    requirement_matches = (
        select(
            JobRequirement.job_id.label("job_id"),
            func.max(func.ts_rank_cd(requirement_document, query)).label("rank"),
        )
        .join(Job, Job.id == JobRequirement.job_id)
        .where(status, gate, requirement_document.bool_op("@@")(query))
        .group_by(JobRequirement.job_id)
    )
    matches = union_all(job_matches, requirement_matches).subquery()
    scores = (
        select(matches.c.job_id, func.sum(matches.c.rank).label("rank"))
        .group_by(matches.c.job_id)
        .subquery()
    )
    raw = scores.c.rank
    score = (100.0 * raw / (1.0 + raw) if bounded else raw).label("textual_score")
    return (
        select(Job, score)
        .join(scores, scores.c.job_id == Job.id)
        .order_by(
            score.desc(),
            Job.publication_date.desc().nulls_last(),
            Job.platform.asc(),
            Job.source_job_id.asc(),
            Job.id.asc(),
        )
        .limit(limit)
    )


def textual_statement(
    query_text: str,
    *,
    readiness: ColumnElement[bool] | None = None,
    requirements: ColumnElement | None = None,
    limit: int = 100,
    statuses: tuple[JobStatus, ...] = ACTIVE_STATUSES,
) -> Select:
    """Select (Job, bounded score), with explicit successful-extraction readiness.

    Omitted readiness fails closed on job and requirement paths. Raw job rank
    plus maximum requirement-row rank is normalized as 100*r/(1+r). Callers may
    append a Job.id pool predicate. Location never controls eligibility. Only
    the given status group is searched; the default is the active group.
    """
    return _retrieval_statement(
        query_text,
        readiness=readiness,
        requirements=requirements,
        limit=limit,
        bounded=True,
        statuses=statuses,
    )


def search_active_jobs(
    session: Session,
    query: str,
    *,
    limit: int = 100,
    readiness: ColumnElement[bool] | None = None,
) -> list[TextualMatch]:
    """Legacy raw-rank interface; readiness is mandatory for any returned job.

    No query-length cap is imposed on the frozen public request projection.
    Omitted readiness fails closed, including for requirement-only matches.
    """
    if not isinstance(query, str):
        raise TypeError("query must be text")
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 500:
        raise ValueError("limit must be between 1 and 500")
    if not query.strip():
        return []
    statement = _retrieval_statement(
        query, readiness=readiness, requirements=None, limit=limit, bounded=False
    )
    return [TextualMatch(job, float(score)) for job, score in session.execute(statement).all()]


def retrieve_textual(
    session: Session,
    candidate: NormalizedCandidate,
    *,
    readiness: ColumnElement[bool] | None = None,
    requirements: ColumnElement | None = None,
    limit: int = 100,
    statuses: tuple[JobStatus, ...] = ACTIVE_STATUSES,
) -> list[tuple[Job, float]]:
    """Run one request-scoped query; persist/log none of its candidate evidence."""
    statement = textual_statement(
        candidate_query_text(candidate),
        readiness=readiness,
        requirements=requirements,
        limit=limit,
        statuses=statuses,
    )
    return [(job, float(score)) for job, score in session.execute(statement)]
