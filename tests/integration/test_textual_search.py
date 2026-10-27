import json
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select

from src.ingestion.upsert import upsert_job
from src.matching.textual import search_active_jobs
from src.normalization.jobs.apibr import normalize_apibr_job
from src.persistence.job.job import Job
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
