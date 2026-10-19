from sqlalchemy import JSON, DateTime, Text, UniqueConstraint
from sqlalchemy import Enum as SQLAlchemyEnum

from src.persistence.job.job import (
    Job,
    SeniorityLevel,
    WorkArrangement,
)
from src.persistence.job.job_source import JobSource
from src.persistence.job.source_run import SourceRun


def test_job_has_expected_fields():
    expected_fields = {
        "id",
        "platform",
        "source_job_id",
        "company",
        "title",
        "description",
        "location",
        "work_arrangement",
        "seniority_level",
        "skills",
        "keywords",
        "salary",
        "job_url",
        "publication_date",
        "first_seen_at",
        "last_seen_at",
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
        {column.name for column in constraint.columns} == {"platform", "source_job_id"}
        for constraint in unique_constraints
    )


def test_normalized_enum_values():
    assert {arrangement.value for arrangement in WorkArrangement} == {
        "REMOTE",
        "HYBRID",
        "ON_SITE",
    }
    assert {level.value for level in SeniorityLevel} == {
        "INTERN",
        "JUNIOR",
        "MID",
        "SENIOR",
        "SPECIALIST",
        "COORDINATOR",
    }


def test_normalized_fields_use_documented_storage_types():
    assert isinstance(Job.__table__.c.location.type, JSON)
    assert isinstance(Job.__table__.c.work_arrangement.type, SQLAlchemyEnum)
    assert isinstance(Job.__table__.c.seniority_level.type, SQLAlchemyEnum)
    assert isinstance(Job.__table__.c.skills.type, JSON)
    assert isinstance(Job.__table__.c.keywords.type, JSON)
    assert isinstance(Job.__table__.c.salary.type, JSON)
    assert isinstance(Job.__table__.c.job_url.type, Text)
    assert isinstance(Job.__table__.c.publication_date.type, DateTime)
    assert isinstance(Job.__table__.c.first_seen_at.type, DateTime)
    assert isinstance(Job.__table__.c.last_seen_at.type, DateTime)
    assert "status" not in Job.__table__.columns


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
        "errors",
    }

    assert set(SourceRun.__table__.columns.keys()) == expected_fields


def test_source_run_references_job_source():
    foreign_keys = SourceRun.__table__.c.source_id.foreign_keys

    assert any(foreign_key.target_fullname == "job_sources.id" for foreign_key in foreign_keys)
