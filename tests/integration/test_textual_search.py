import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import select

from src.ingestion.upsert import upsert_job
from src.matching.textual import search_active_jobs
from src.normalization.jobs.apibr import normalize_apibr_job
from src.persistence.job.job import Job, JobStatus
from src.persistence.job.job_source import JobSource
from src.persistence.job.skill import JobRequirement, RequirementClass


def test_postgresql_searches_the_captured_job_and_requirement_fixture(db_session):
    fixture_path = Path("tests/resources/jobs_fixture.json")
    issues = json.loads(fixture_path.read_text(encoding="utf-8"))
    issue = issues[0]
    source = JobSource(name="APiBR FTS fixture", type="api", polling_mode="sequential")
    db_session.add(source)
    db_session.flush()

    normalized = normalize_apibr_job(issue)
    upsert_job(db_session, source.id, normalized, datetime.now(UTC), verified=True)
    job = db_session.scalar(select(Job).where(Job.source_job_id == str(issue["id"])))
    assert job is not None
    db_session.add(
        JobRequirement(
            job_id=job.id,
            text="VectorDatabaseQuasar experience",
            requirement_class=RequirementClass.REQUIRED,
        )
    )
    db_session.flush()

    fixture_matches = search_active_jobs(db_session, "Python")
    requirement_matches = search_active_jobs(db_session, "VectorDatabaseQuasar")

    assert any(match.job.id == job.id for match in fixture_matches)
    assert any(match.job.id == job.id for match in requirement_matches)


@pytest.fixture
def source(db_session):
    source = JobSource(name="FTS regressions", type="api", polling_mode="INCREMENTAL")
    db_session.add(source)
    db_session.flush()
    return source


def _insert(db_session, source, identity, **fields):
    job = Job(source_id=source.id, platform="fixture", source_job_id=identity, **fields)
    db_session.add(job)
    db_session.flush()
    return job


def test_any_term_retrieval_and_field_weights(db_session, source):
    title = _insert(db_session, source, "title", title="Python", status=JobStatus.ACTIVE)
    description = _insert(
        db_session, source, "body", title="Developer", description="Python", status=JobStatus.ACTIVE
    )
    django = _insert(db_session, source, "django", title="Django", status=JobStatus.ACTIVE)
    _insert(db_session, source, "unrelated", title="Kotlin", status=JobStatus.ACTIVE)

    matches = search_active_jobs(db_session, "Python Django Kubernetes")
    scores = {m.job.id: m.score for m in matches}
    assert set(scores) == {title.id, description.id, django.id}
    assert scores[title.id] > scores[description.id]


@pytest.mark.parametrize("status", [JobStatus.DISCOVERED, JobStatus.STALE, JobStatus.EXPIRED])
def test_inactive_jobs_are_excluded_from_both_search_paths(db_session, source, status):
    job = _insert(db_session, source, "inactive", title="Python", status=status)
    db_session.add(
        JobRequirement(
            job_id=job.id, text="Kubernetes", requirement_class=RequirementClass.REQUIRED
        )
    )
    db_session.flush()
    assert search_active_jobs(db_session, "Python Kubernetes") == []


def test_query_operators_are_plain_text_and_order_is_stable(db_session, source):
    first = _insert(db_session, source, "a", title="Python", status=JobStatus.ACTIVE)
    second = _insert(db_session, source, "b", title="Python", status=JobStatus.ACTIVE)
    for _ in range(2):
        assert [m.job.id for m in search_active_jobs(db_session, "Python' | Django:*")] == [
            first.id,
            second.id,
        ]
    assert search_active_jobs(db_session, "de a e") == []
