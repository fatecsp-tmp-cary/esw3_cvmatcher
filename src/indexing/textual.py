"""Shared immutable Portuguese expressions for retrieval and GIN indexes."""

from sqlalchemy import Text, cast, func, literal, literal_column
from sqlalchemy.dialects.postgresql import TSQUERY, TSVECTOR
from sqlalchemy.sql.elements import ColumnElement, SQLColumnExpression

_CONFIG: ColumnElement = literal_column("'pg_catalog.portuguese'::regconfig")
_EMPTY_TEXT: ColumnElement = literal_column("''::text")
TEXTUAL_VERSION = "portuguese-weighted-any-term-v2"


def _text_vector(value: SQLColumnExpression, weight: str) -> ColumnElement:
    return func.setweight(
        func.to_tsvector(_CONFIG, func.coalesce(value, _EMPTY_TEXT)),
        literal_column(f"'{weight}'"),
        type_=TSVECTOR,
    )


def _paired_vector(first: SQLColumnExpression, second: SQLColumnExpression, weight: str):
    # Immutable text concatenation; JSON uses PostgreSQL's text rendering, including keys.
    text = (
        func.coalesce(first, _EMPTY_TEXT)
        + literal_column("' '::text")
        + func.coalesce(second, _EMPTY_TEXT)
    )
    return _text_vector(text, weight)


def job_search_document(*, requirements: ColumnElement | None = None) -> ColumnElement:
    """Build the accepted ADR004/005 job expression, also used by indexes.

    Optional requirements must be a normalized job-only SQL expression. Separate
    requirement rows use requirement_search_document instead; do not supply the
    same evidence through both sources. JSON is rendered as PostgreSQL text.
    """
    from src.persistence.job.job import Job

    sections = [
        _paired_vector(Job.title, cast(Job.skills, Text), "A"),
        _paired_vector(Job.company, cast(Job.keywords, Text), "B"),
        _paired_vector(Job.description, cast(Job.location, Text), "D"),
    ]
    if requirements is not None:
        sections.append(_text_vector(cast(requirements, Text), "B"))
    result = sections[0]
    for section in sections[1:]:
        result = result.op("||", return_type=TSVECTOR)(section)
    return result


def requirement_search_document(value: SQLColumnExpression | None = None) -> ColumnElement:
    """Build a B-weight normalized requirement-row vector for indexes/retrieval.

    An explicit column/expression supports migration tables and aliases; omitted
    value lazily selects JobRequirement.text without a metadata import cycle.
    """
    if value is None:
        from src.persistence.job.skill import JobRequirement

        value = JobRequirement.text
    return _text_vector(value, "B")


def any_term_query(query_text: str) -> ColumnElement:
    """OR safely quoted plain-text lexemes without stemming them a second time."""
    plain = func.plainto_tsquery(_CONFIG, literal(query_text, type_=Text))
    return cast(func.replace(cast(plain, Text), " & ", " | "), TSQUERY)
