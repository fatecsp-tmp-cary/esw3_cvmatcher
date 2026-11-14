import pytest
from sqlalchemy import select, text

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
        JobStatus.DISCOVERED,
        JobStatus.DISCOVERED,
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


def test_snapshot_network_finishes_before_locks_and_db_rejection_invalidates_evidence(
    db_session, monkeypatch
):
    from src.ingestion import apibr

    source = JobSource(name="snapshot-write-rejection", type="api", polling_mode="SNAPSHOT")
    db_session.add(source)
    db_session.commit()
    remote_calls = []

    class UnlockedClient(Client):
        def assert_unlocked(self):
            assert (
                db_session.scalar(
                    text(
                        "SELECT count(*) FROM pg_locks "
                        "WHERE locktype = 'advisory' AND pid = pg_backend_pid()"
                    )
                )
                == 0
            )

        def fetch_health(self):
            self.assert_unlocked()
            remote_calls.append("health")
            return super().fetch_health()

        def fetch_page(self, page):
            self.assert_unlocked()
            remote_calls.append(f"page-{page}")
            return super().fetch_page(page)

    original = apibr.upsert_job

    def reject_second(session, source_id, normalized, observed_at, verified):
        assert remote_calls == ["health", "page-1", "page-2", "health"]
        if normalized["source_job_id"] == "2":
            raise ValueError("synthetic persistence rejection")
        return original(session, source_id, normalized, observed_at, verified)

    monkeypatch.setattr(apibr, "upsert_job", reject_second)
    result = ingest_apibr(db_session, source.id, UnlockedClient())
    run = db_session.get(SourceRun, result.run_id)
    assert result.status == "PARTIAL"
    assert result.snapshot_complete is False
    assert run.snapshot_evidence["qualified"] is False
    assert run.snapshot_evidence["rejections"] == run.jobs_rejected == 1
    assert db_session.scalars(select(Job.source_job_id)).all() == ["1"]
