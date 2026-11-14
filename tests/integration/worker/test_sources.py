import json
from contextlib import nullcontext
from datetime import UTC, datetime

import pytest
from sqlalchemy import select

from src.persistence.job.job_source import JobSource
from src.worker.sources import main, register_source


def test_register_creates_an_enabled_incremental_source_by_default(db_session):
    source_id, created = register_source(db_session, "apibr")
    source = db_session.get(JobSource, source_id)

    assert created is True
    assert (source.name, source.type, source.polling_mode, source.enabled) == (
        "apibr",
        "api",
        "INCREMENTAL",
        True,
    )


def test_register_is_idempotent_and_preserves_scheduling_state(db_session):
    last_run = datetime(2026, 11, 12, 11, tzinfo=UTC)
    db_session.add(
        JobSource(name="APiBR", type="api", polling_mode="INCREMENTAL", last_run_at=last_run)
    )
    db_session.commit()

    source_id, created = register_source(
        db_session, " ApiBR ", polling_mode="SNAPSHOT", enabled=False
    )
    source = db_session.get(JobSource, source_id)

    assert created is False
    assert db_session.scalars(select(JobSource.id)).all() == [source_id]
    assert (source.name, source.polling_mode, source.enabled) == ("APiBR", "SNAPSHOT", False)
    assert source.last_run_at == last_run


@pytest.mark.parametrize("name", ["gupy", "", "   ", None])
def test_unsupported_source_names_are_rejected(db_session, name):
    with pytest.raises(ValueError):
        register_source(db_session, name)
    assert db_session.scalars(select(JobSource.id)).all() == []


def test_invalid_polling_mode_is_rejected(db_session):
    with pytest.raises(ValueError):
        register_source(db_session, "apibr", polling_mode="HOURLY")


def test_command_registers_and_reports_only_fixed_fields(db_session, capsys):
    status = main(
        ["register", "apibr", "--polling-mode", "SNAPSHOT"],
        sessions=lambda: nullcontext(db_session),
    )
    report = json.loads(capsys.readouterr().out)
    source = db_session.get(JobSource, report["source_id"])

    assert status == 0
    assert report == {
        "created": True,
        "enabled": True,
        "event": "source_registered",
        "polling_mode": "SNAPSHOT",
        "source_id": source.id,
    }
    assert source.polling_mode == "SNAPSHOT"
