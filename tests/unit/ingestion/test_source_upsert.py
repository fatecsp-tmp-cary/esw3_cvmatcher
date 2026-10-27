from datetime import UTC, datetime

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from src.ingestion.upsert import upsert_job
from src.persistence.base import Base
from src.persistence.job.job import Job
from src.persistence.job.job_source import JobSource


@pytest.fixture
def session():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add_all(
            [
                JobSource(name="APiBR", type="api", polling_mode="sequential"),
                JobSource(name="Other", type="api", polling_mode="sequential"),
            ]
        )
        db.commit()
        yield db
    engine.dispose()


def _job(platform: str = "apibr", *, title: str = "Data engineer") -> dict:
    return {
        "platform": platform,
        "source_job_id": "same-id",
        "title": title,
        "description": "Build data systems",
        "status": "ACTIVE",
    }


def test_upsert_inserts_and_uses_source_identity(session: Session):
    now = datetime(2026, 10, 27, tzinfo=UTC)

    result = upsert_job(session, 1, _job(), now, True)
    session.flush()
    apibr_job = session.scalar(
        select(Job).where(Job.platform == "apibr", Job.source_job_id == "same-id")
    )
    other_job_result = upsert_job(session, 2, _job("other"), now, True)
    session.flush()

    assert result == ("created", False, False)
    assert other_job_result == ("created", False, False)
    assert apibr_job is not None
    assert apibr_job.source_id == 1
    assert session.scalar(select(Job.id).where(Job.platform == "other")) is not None


def test_upsert_leaves_unchanged_content_and_updates_changed_content(session: Session):
    now = datetime(2026, 10, 27, tzinfo=UTC)
    upsert_job(session, 1, _job(), now, True)
    session.flush()
    job = session.scalar(select(Job).where(Job.platform == "apibr"))
    original_hash = job.content_hash

    unchanged = upsert_job(session, 1, _job(), now, True)
    changed = upsert_job(session, 1, _job(title="Senior data engineer"), now, True)

    assert unchanged == ("unchanged", False, False)
    assert changed == ("updated", False, False)
    assert job.content_hash != original_hash
    assert job.title == "Senior data engineer"
