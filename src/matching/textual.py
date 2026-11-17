"""Deterministic status/readiness-gated PostgreSQL textual retrieval."""

from dataclasses import dataclass
from datetime import date

from sqlalchemy import Select, Text, false, func, literal, select, union_all
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import ColumnElement

from src.indexing.textual import (
    _CONFIG,
    any_term_query,
    job_search_document,
    requirement_search_document,
)
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


def focused_candidate_query_text(candidate: NormalizedCandidate) -> str:
    """Focused, deduplicated candidate projection for FTS retrieval (ADR-027).

    Keeps competencies, all experience titles, the three most recent experience
    descriptions, project titles/technologies, education courses, and language
    names so sprawling profiles do not flood any-term FTS queries. Falls back to
    ``candidate_query_text`` when all focused fields are blank.
    """
    recent_experiences = sorted(
        candidate.experience,
        key=lambda x: (x.end_date is None, x.end_date or date.min, x.start_date),
        reverse=True,
    )[:3]
    raw_items = [
        *(x.description for x in candidate.competencies),
        *(x.title for x in candidate.experience),
        *(x.description for x in recent_experiences),
        *(value for x in candidate.projects for value in (x.title, x.technologies)),
        *(x.course for x in candidate.education),
        *(x.name for x in candidate.languages),
    ]
    seen: set[str] = set()
    unique: list[str] = []
    for item in raw_items:
        cleaned = " ".join(item.split())
        if not cleaned:
            continue
        folded = cleaned.casefold()
        if folded not in seen:
            seen.add(folded)
            unique.append(cleaned)
    return "\n".join(unique) if unique else candidate_query_text(candidate)


@dataclass(frozen=True, slots=True)
class TextualMatch:
    """Legacy retrieval result carrying raw PostgreSQL rank, not compatibility."""

    job: Job
    score: float


def _retrieval_statement(
    query_text,
    *,
    readiness,
    requirements,
    limit,
    bounded,
    statuses=ACTIVE_STATUSES,
    exclude_ids: tuple[int, ...] = (),
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
    job_filters = [status, gate, document.bool_op("@@")(query)]
    req_filters = [status, gate, requirement_document.bool_op("@@")(query)]
    if exclude_ids:
        job_filters.append(Job.id.not_in(exclude_ids))
        req_filters.append(Job.id.not_in(exclude_ids))
    # When bounded, PostgreSQL flag 32 saturates cover density without
    # penalizing long descriptions or varying city-name token counts (ADR-005/027).
    rank_expr = (
        func.ts_rank_cd(document, query, 32) if bounded else func.ts_rank_cd(document, query)
    )
    req_rank_expr = (
        func.ts_rank_cd(requirement_document, query, 32)
        if bounded
        else func.ts_rank_cd(requirement_document, query)
    )
    job_matches = select(Job.id.label("job_id"), rank_expr.label("rank")).where(*job_filters)
    # Maximum avoids multiplying evidence by the number of requirement rows.
    requirement_matches = (
        select(
            JobRequirement.job_id.label("job_id"),
            func.max(req_rank_expr).label("rank"),
        )
        .join(Job, Job.id == JobRequirement.job_id)
        .where(*req_filters)
        .group_by(JobRequirement.job_id)
    )
    matches = union_all(job_matches, requirement_matches).subquery()
    scores = (
        select(matches.c.job_id, func.sum(matches.c.rank).label("rank"))
        .group_by(matches.c.job_id)
        .subquery()
    )
    raw = scores.c.rank
    if bounded:
        distinct_terms = func.length(func.to_tsvector(_CONFIG, literal(query_text, type_=Text)))
        query_norm = literal(1.0) + literal(0.15) * func.ln(literal(1.0) + distinct_terms)
        normalized_rank = raw / query_norm
        score = (100.0 * normalized_rank / (1.0 + normalized_rank)).label("textual_score")
    else:
        score = raw.label("textual_score")
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
    exclude_ids: tuple[int, ...] = (),
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
        exclude_ids=exclude_ids,
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
    exclude_ids: tuple[int, ...] = (),
) -> list[tuple[Job, float]]:
    """Run one request-scoped query; persist/log none of its candidate evidence."""
    statement = textual_statement(
        focused_candidate_query_text(candidate),
        readiness=readiness,
        requirements=requirements,
        limit=limit,
        statuses=statuses,
        exclude_ids=exclude_ids,
    )
    return [(job, float(score)) for job, score in session.execute(statement)]
