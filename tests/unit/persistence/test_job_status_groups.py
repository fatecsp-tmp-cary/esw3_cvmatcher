import pytest
from sqlalchemy import true
from sqlalchemy.dialects import postgresql

from src.embeddings.config import EmbeddingConfig
from src.embeddings.retrieval import semantic_statement
from src.matching.textual import textual_statement
from src.persistence.job.job import (
    ACTIVE_STATUSES,
    INACTIVE_STATUSES,
    JobStatus,
    status_predicate,
)


def _sql(clause) -> str:
    return str(clause.compile(dialect=postgresql.dialect()))


def test_status_groups_partition_every_job_status():
    assert ACTIVE_STATUSES == (JobStatus.ACTIVE,)
    assert set(ACTIVE_STATUSES) | set(INACTIVE_STATUSES) == set(JobStatus)
    assert not set(ACTIVE_STATUSES) & set(INACTIVE_STATUSES)


def test_single_status_keeps_the_equality_form_used_by_the_active_indexes():
    assert "jobs.status = " in _sql(status_predicate(ACTIVE_STATUSES))
    assert " IN " not in _sql(status_predicate(ACTIVE_STATUSES))
    assert "jobs.status IN " in _sql(status_predicate(INACTIVE_STATUSES))


def test_empty_status_group_is_rejected():
    with pytest.raises(ValueError):
        status_predicate(())


def test_retrieval_statements_search_the_active_group_by_default():
    vector = [1.0] + [0.0] * 383
    semantic = _sql(semantic_statement(vector, EmbeddingConfig(), "extraction-v1"))
    # Omitted readiness fails closed to SQL false, so pass an explicit predicate.
    textual = _sql(textual_statement("python", readiness=true()))

    assert "jobs.status = " in semantic and "jobs.status IN " not in semantic
    assert "jobs.status = " in textual and "jobs.status IN " not in textual


def test_retrieval_statements_search_only_the_requested_status_group():
    vector = [1.0] + [0.0] * 383
    semantic = _sql(
        semantic_statement(vector, EmbeddingConfig(), "extraction-v1", statuses=INACTIVE_STATUSES)
    )
    textual = _sql(textual_statement("python", readiness=true(), statuses=INACTIVE_STATUSES))

    assert "jobs.status IN " in semantic and "jobs.status = " not in semantic
    # Both the job branch and the requirement branch are restricted to the group.
    assert textual.count("jobs.status IN ") == 2 and "jobs.status = " not in textual
