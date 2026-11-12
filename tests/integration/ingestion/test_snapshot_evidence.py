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


def test_only_a_qualifying_snapshot_marks_absent_active_jobs_stale(db_session):
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
    assert run.jobs_absent == run.jobs_marked_stale == 1
    assert complete.jobs_absent == complete.jobs_marked_stale == 1
    assert session.get(Job, previous.id).status == JobStatus.STALE
    assert session.scalars(select(Job.status).where(Job.source_job_id != "missing")).all() == [
        JobStatus.ACTIVE,
        JobStatus.ACTIVE,
    ]
    later = Job(
        source_id=source.id,
        platform="apibr",
        source_job_id="later-missing",
        title="Observed before a non-qualifying scan",
        status=JobStatus.ACTIVE,
    )
    session.add(later)
    session.commit()
    incomplete = ingest_apibr(session, source.id, Client(expected=3))
    incomplete_run = session.get(SourceRun, incomplete.run_id)
    assert incomplete.status == "SUCCEEDED" and incomplete.snapshot_complete is False
    assert incomplete_run.snapshot_evidence["qualified"] is False
    assert incomplete_run.jobs_absent == incomplete_run.jobs_marked_stale == 0
    assert session.get(Job, later.id).status == JobStatus.ACTIVE
    assert session.get(Job, previous.id).status == JobStatus.STALE


def _absent_job(session, source, identity, status=JobStatus.ACTIVE):
    job = Job(
        source_id=source.id,
        platform="apibr",
        source_job_id=identity,
        title="Previously observed",
        status=status,
    )
    session.add(job)
    session.commit()
    return job.id


def test_qualifying_snapshot_leaves_other_sources_and_other_states_untouched(db_session):
    session = db_session
    source = JobSource(name="scoped-snapshot", type="api", polling_mode="SNAPSHOT")
    other = JobSource(name="other-source", type="api", polling_mode="SNAPSHOT")
    session.add_all([source, other])
    session.flush()
    foreign = _absent_job(session, other, "foreign")
    discovered = _absent_job(session, source, "discovered", JobStatus.DISCOVERED)
    expired = _absent_job(session, source, "expired", JobStatus.EXPIRED)
    already_stale = _absent_job(session, source, "stale", JobStatus.STALE)

    result = ingest_apibr(session, source.id, Client())

    assert result.snapshot_complete is True
    # DISCOVERED and STALE are absent but not newly marked; EXPIRED is not counted.
    assert (result.jobs_absent, result.jobs_marked_stale) == (2, 0)
    assert session.get(Job, foreign).status == JobStatus.ACTIVE
    assert session.get(Job, discovered).status == JobStatus.DISCOVERED
    assert session.get(Job, expired).status == JobStatus.EXPIRED
    assert session.get(Job, already_stale).status == JobStatus.STALE


def test_incremental_scan_never_marks_absence(db_session):
    session = db_session
    source = JobSource(name="incremental-source", type="api", polling_mode="INCREMENTAL")
    session.add(source)
    session.flush()
    missing = _absent_job(session, source, "missing")

    result = ingest_apibr(session, source.id, Client())

    assert result.status == "SUCCEEDED" and result.snapshot_complete is False
    assert (result.jobs_absent, result.jobs_marked_stale) == (0, 0)
    assert session.get(Job, missing).status == JobStatus.ACTIVE


def test_partial_snapshot_never_marks_absence(db_session):
    session = db_session
    source = JobSource(name="partial-snapshot", type="api", polling_mode="SNAPSHOT")
    session.add(source)
    session.flush()
    missing = _absent_job(session, source, "missing")

    class Rejecting(Client):
        def fetch_page(self, page):
            return [{"id": 1, "title": "Python"}, {"id": 2, "title": ""}] if page == 1 else []

    result = ingest_apibr(session, source.id, Rejecting())

    assert result.status == "PARTIAL" and result.snapshot_complete is False
    assert (result.jobs_absent, result.jobs_marked_stale) == (0, 0)
    assert session.get(Job, missing).status == JobStatus.ACTIVE


def test_rediscovery_in_a_later_snapshot_reactivates_a_stale_job(db_session):
    session = db_session
    source = JobSource(name="rediscovery-snapshot", type="api", polling_mode="SNAPSHOT")
    session.add(source)
    session.flush()
    returning = _absent_job(session, source, "3")
    assert ingest_apibr(session, source.id, Client()).jobs_marked_stale == 1
    assert session.get(Job, returning).status == JobStatus.STALE

    class Relisted(Client):
        def fetch_page(self, page):
            return [{"id": i, "title": "Python", "body": "Python APIs"} for i in [1, 2, 3]] * (
                page == 1
            )

    result = ingest_apibr(session, source.id, Relisted(expected=3))

    assert result.snapshot_complete is True
    assert (result.jobs_reactivated, result.jobs_marked_stale) == (1, 0)
    assert session.get(Job, returning).status == JobStatus.ACTIVE


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
