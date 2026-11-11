"""Deterministic active/readiness-gated PostgreSQL textual retrieval."""

from sqlalchemy import Select, false, func, select
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import ColumnElement

from src.indexing.textual import any_term_query, job_search_document
from src.normalization.candidate.curriculum import NormalizedCandidate
from src.persistence.job.job import Job, JobStatus


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


def textual_statement(
    query_text: str,
    *,
    readiness: ColumnElement[bool] | None = None,
    requirements: ColumnElement | None = None,
    limit: int = 100,
) -> Select:
    """Return ``(Job, textual_score)`` ordered by score then source identity.

    Caller must supply current successful extraction readiness. Missing readiness
    fails closed. Retrieval never uses location or work mode for eligibility.
    PostgreSQL ts_rank_cd normalization 32 maps rank to rank/(rank+1); scaling
    gives a bounded [0,100] component, not an employment probability.
    """
    if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
        raise ValueError("retrieval limit must be a positive integer")
    document = job_search_document(requirements=requirements)
    query = any_term_query(query_text)
    score = (func.ts_rank_cd(document, query, 32) * 100.0).label("textual_score")
    gate = false() if readiness is None else readiness
    return (
        select(Job, score)
        .where(Job.status == JobStatus.ACTIVE, gate, document.op("@@")(query))
        .order_by(score.desc(), Job.platform.asc(), Job.source_job_id.asc(), Job.id.asc())
        .limit(limit)
    )


def retrieve_textual(
    session: Session,
    candidate: NormalizedCandidate,
    *,
    readiness: ColumnElement[bool] | None = None,
    requirements: ColumnElement | None = None,
    limit: int = 100,
) -> list[tuple[Job, float]]:
    """Run one request-scoped query; persist/log none of its candidate evidence."""
    statement = textual_statement(
        candidate_query_text(candidate),
        readiness=readiness,
        requirements=requirements,
        limit=limit,
    )
    return [(job, float(score)) for job, score in session.execute(statement)]
