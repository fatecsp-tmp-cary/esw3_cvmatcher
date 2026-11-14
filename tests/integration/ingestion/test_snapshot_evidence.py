import pytest
from sqlalchemy import select

from src.ingestion.adapters import SourceError
from src.ingestion.apibr import ingest_apibr
from src.persistence.job.job import Job, JobStatus
from src.persistence.job.job_source import JobSource
from src.persistence.job.source_run import SourceRun


class Client:
    request_failures = 0

    def __init__(self, expected=2):
        self.expected = expected

    def fetch_health(self):
        return {
            "status": "healthy",
            "checks": {
                "dataset_issues_body": {
                    "status": "healthy",
                    "details": {
                        "records": self.expected,
                        "last_updated": "2026-11-12T08:29:29-03:00",
                        "from_backup": False,
                    },
                }
            },
        }

    def fetch_page(self, page):
        return (
            [{"id": i, "title": "Python", "body": "Python APIs"} for i in [1, 2]]
            if page == 1
            else []
        )


def test_complete_and_incomplete_counts_do_not_invent_availability_or_absence(db_session):
    session = db_session
    source = JobSource(name="counted-snapshot", type="api", polling_mode="SNAPSHOT")
    session.add(source)
    session.flush()
    previous = Job(
        source_id=source.id,
        platform="apibr",
        source_job_id="missing",
        title="Previously observed",
        status=JobStatus.ACTIVE,
    )
    session.add(previous)
    session.commit()
    complete = ingest_apibr(session, source.id, Client())
    run = session.get(SourceRun, complete.run_id)
    assert complete.snapshot_complete is True
    assert run.polling_mode == "SNAPSHOT"
    assert run.snapshot_evidence["qualified"] is True
    assert run.snapshot_evidence["distinct_ids"] == 2
    assert run.jobs_absent == run.jobs_marked_stale == 0
    assert session.get(Job, previous.id).status == JobStatus.ACTIVE
    assert session.scalars(select(Job.status).where(Job.source_job_id != "missing")).all() == [
        JobStatus.ACTIVE,
        JobStatus.ACTIVE,
    ]
    incomplete = ingest_apibr(session, source.id, Client(expected=3))
    assert incomplete.status == "SUCCEEDED" and incomplete.snapshot_complete is False
    assert session.get(SourceRun, incomplete.run_id).snapshot_evidence["qualified"] is False
    assert session.get(Job, previous.id).status == JobStatus.ACTIVE


@pytest.mark.parametrize("fail_after_scan", [False, True])
def test_exhausted_health_transport_failure_rolls_back_all_payload_updates(
    db_session, fail_after_scan
):
    session = db_session
    source = JobSource(name="failed-health-snapshot", type="api", polling_mode="SNAPSHOT")
    session.add(source)
    session.flush()
    previous = Job(
        source_id=source.id,
        platform="apibr",
        source_job_id="1",
        title="Original",
        status=JobStatus.ACTIVE,
    )
    session.add(previous)
    session.commit()

    class FailingHealth(Client):
        calls = 0

        def fetch_health(self):
            self.calls += 1
            if fail_after_scan and self.calls == 1:
                return super().fetch_health()
            raise SourceError("private-upstream-detail")

    with pytest.raises(SourceError):
        ingest_apibr(session, source.id, FailingHealth())
    assert session.get(Job, previous.id).title == "Original"
    assert session.scalars(select(Job.source_job_id)).all() == ["1"]
    run = session.scalar(select(SourceRun))
    assert run.status == "FAILED" and run.snapshot_complete is False
    assert run.jobs_created == run.jobs_updated == 0
    assert run.errors == "SourceError"
    assert session.get(JobSource, source.id).last_success_at is None
