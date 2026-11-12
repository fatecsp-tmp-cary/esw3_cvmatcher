"""Immutable PostgreSQL Portuguese search expressions.

Explicit configurations and JSON string-only filters keep expression indexes
independent of session defaults and prevent JSON keys becoming job evidence.
"""

from sqlalchemy import Text, cast, func, literal, literal_column
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlalchemy.sql.elements import ColumnElement, SQLColumnExpression

# SQL constants are fixed by the algorithm, never constructed from request data.
_CONFIG: ColumnElement = literal_column("'pg_catalog.portuguese'::regconfig")
_STRING_VALUES: ColumnElement = literal_column("'[\"string\"]'::jsonb")
_EMPTY_JSON: ColumnElement = literal_column("'[]'::jsonb")
TEXTUAL_VERSION = "portuguese-weighted-any-term-v1"


def _text_vector(value: SQLColumnExpression, weight: str) -> ColumnElement:
    return func.setweight(
        func.to_tsvector(_CONFIG, func.coalesce(value, literal_column("''::text"))),
        literal_column(f"'{weight}'"),
        type_=TSVECTOR,
    )


def _json_vector(value: SQLColumnExpression, weight: str) -> ColumnElement:
    return func.setweight(
        func.jsonb_to_tsvector(
            _CONFIG, func.coalesce(cast(value, JSONB), _EMPTY_JSON), _STRING_VALUES
        ),
        literal_column(f"'{weight}'"),
        type_=TSVECTOR,
    )


def job_search_document(*, requirements: ColumnElement | None = None) -> ColumnElement:
    """Build a weighted job vector without adding fields to canonical Job.

    ``requirements`` is a job-only JSON SQL expression supplied by the caller
    from validated supporting extraction metadata. It must use the same
    expression for an index and retrieval. No requirements source is invented.
    """
    # Lazy import lets the persistence metadata register this same expression
    # after Job is defined, without a module import cycle.
    from src.persistence.job.job import Job

    requirements = _EMPTY_JSON if requirements is None else requirements
    sections = (
        _text_vector(Job.title, "A"),
        _json_vector(Job.skills, "B"),
        _json_vector(requirements, "B"),
        _text_vector(Job.company, "C"),
        _text_vector(Job.description, "D"),
        _json_vector(Job.location, "D"),
    )
    result = sections[0]
    for section in sections[1:]:
        result = result.op("||", return_type=TSVECTOR)(section)
    return result


def any_term_query(query_text: str) -> ColumnElement:
    """Tokenize bound plain text, then OR its safely quoted PostgreSQL lexemes.

    PostgreSQL owns tokenization and quoting. Public text never becomes raw
    tsquery syntax: operators in submitted text are ordinary punctuation/words.
    Replacing the generated conjunction joins every surviving lexeme with OR;
    empty/stopword-only inputs remain an empty query and match no documents.
    """
    plain = func.plainto_tsquery(_CONFIG, literal(query_text, type_=Text))
    return func.to_tsquery(_CONFIG, func.replace(cast(plain, Text), " & ", " | "))
