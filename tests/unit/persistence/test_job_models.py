from sqlalchemy import UniqueConstraint

from src.persistence.job.job import (
    Job,
    JobStatus,
    can_transition_to,
)
from src.persistence.job.job_source import JobSource
from src.persistence.job.source_run import SourceRun


def test_job_has_expected_fields():
    expected_fields = {
        "id",
        "source",
        "source_job_id",
        "company",
        "title",
        "description",
        "location",
        "mode",
        "salary",
        "currency",
        "employment_type",
        "requirements",
        "keywords",
        "published_at",
        "source_expires_at",
        "first_seen_at",
        "last_seen_at",
        "last_verified_at",
        "status",
        "canonical_url",
        "raw",
        "embedding",
        "content_hash",
    }

    actual_fields = set(Job.__table__.columns.keys())

    assert actual_fields == expected_fields


def test_job_has_unique_source_identity():
    unique_constraints = [
        constraint
        for constraint in Job.__table__.constraints
        if isinstance(constraint, UniqueConstraint)
    ]

    assert any(
        {column.name for column in constraint.columns}
        == {"source", "source_job_id"}
        for constraint in unique_constraints
    )


def test_job_status_values():
    assert {status.value for status in JobStatus} == {
        "DISCOVERED",
        "ACTIVE",
        "STALE",
        "EXPIRED",
    }


def test_job_status_transitions():
    assert can_transition_to(JobStatus.DISCOVERED, JobStatus.ACTIVE)
    assert can_transition_to(JobStatus.ACTIVE, JobStatus.STALE)
    assert can_transition_to(JobStatus.STALE, JobStatus.ACTIVE)

    assert not can_transition_to(JobStatus.EXPIRED, JobStatus.ACTIVE)
    assert not can_transition_to(JobStatus.DISCOVERED, JobStatus.STALE)


def test_job_source_has_expected_fields():
    expected_fields = {
        "id",
        "name",
        "type",
        "polling_mode",
        "enabled",
        "polling_interval",
        "last_run_at",
        "last_success_at",
        "next_run_at",
        "last_error",
    }

    assert set(JobSource.__table__.columns.keys()) == expected_fields


def test_source_run_has_expected_fields():
    expected_fields = {
        "id",
        "source_id",
        "started_at",
        "finished_at",
        "status",
        "snapshot_complete",
        "jobs_found",
        "jobs_created",
        "jobs_updated",
        "lifecycle_changes",
        "errors",
    }

    assert set(SourceRun.__table__.columns.keys()) == expected_fields


def test_source_run_references_job_source():
    foreign_keys = SourceRun.__table__.c.source_id.foreign_keys

    assert any(
        foreign_key.target_fullname == "job_sources.id"
        for foreign_key in foreign_keys
    )


def test_job_embedding_uses_vector():
    assert str(Job.__table__.c.embedding.type) == "VECTOR"
