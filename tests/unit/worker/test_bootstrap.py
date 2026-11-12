from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.dialects import postgresql

from src.embeddings.config import EmbeddingConfig
from src.extraction.gliner import EXTRACTION_VERSION
from src.worker import bootstrap
from src.worker.__main__ import main


def maintenance(results=(True, False), batch_size=2):
    session = MagicMock()
    session.__enter__.return_value = session
    session.scalars.return_value.all.return_value = [11, 12]
    sessions = MagicMock(return_value=session)
    worker = SimpleNamespace(
        config=EmbeddingConfig(),
        extraction_version=EXTRACTION_VERSION,
        process_once=MagicMock(side_effect=results),
    )
    return bootstrap.EmbeddingMaintenance(sessions, worker, batch_size=batch_size), session


def test_maintenance_enqueues_current_ready_jobs_and_stops_when_idle():
    subject, session = maintenance()
    with patch.object(bootstrap, "enqueue") as enqueue:
        assert subject() == 1
    assert enqueue.call_count == 2
    assert all("retry" not in call.kwargs for call in enqueue.call_args_list)
    sql = str(session.scalars.call_args.args[0].compile(dialect=postgresql.dialect()))
    assert "job_extractions" in sql
    assert "content_hash" in sql and "model_version" in sql and "extraction_version" in sql
    # Current state is not selected by status: FAILED work cannot starve later jobs.
    assert "job_embeddings.status" not in sql
    assert "LIMIT" in sql and "ORDER BY jobs.id" in sql
    assert subject.worker.process_once.call_count == 2
    session.begin.assert_called_once()


def test_maintenance_is_bounded_when_queue_never_empties():
    subject, _ = maintenance((True, True, True))
    with patch.object(bootstrap, "enqueue"):
        assert subject() == 2
    assert subject.worker.process_once.call_count == 2


@pytest.mark.parametrize("size", [0, -1, True, 1.5])
def test_invalid_batch(size):
    with pytest.raises(ValueError):
        bootstrap.EmbeddingMaintenance(None, None, batch_size=size)


def test_default_worker_composes_real_services_without_loading_models(monkeypatch):
    monkeypatch.setenv("CVMATCHER_EXTRACTION_DIRECTORY", "/prepared/extraction")
    monkeypatch.setenv("CVMATCHER_EMBEDDING_CACHE", "/prepared/cache")
    session = MagicMock()
    session.__enter__.return_value = session
    sessions = MagicMock(return_value=session)
    with (
        patch.object(bootstrap, "GlinerExtractor") as extractor,
        patch.object(bootstrap, "LocalEmbeddingEncoder") as encoder,
        patch.object(bootstrap, "create_db_engine") as engine,
        patch.object(bootstrap, "create_session_factory", return_value=sessions) as factory,
        patch.object(bootstrap, "expire_source_timestamps", return_value=3) as expire,
    ):
        worker = bootstrap.create_default_worker()
        extractor.assert_called_once_with("/prepared/extraction")
        assert encoder.call_args.args[0].cache_directory == "/prepared/cache"
        factory.assert_called_once_with(engine.return_value)
        assert worker.scheduler.engine is engine.return_value
        assert worker.scheduler.sessions is sessions
        assert worker.extraction_worker.extractor is extractor.return_value
        assert worker.extraction_worker.config_version == EXTRACTION_VERSION
        assert worker.embedding_hook.worker.extraction_version == EXTRACTION_VERSION
        assert worker.expiration_hook() == 3
        assert expire.call_args.kwargs["now"].utcoffset().total_seconds() == 0
        session.begin.assert_called_once()


def test_missing_model_configuration_fails_closed_without_exception_text(monkeypatch, caplog):
    monkeypatch.delenv("CVMATCHER_EXTRACTION_DIRECTORY", raising=False)
    assert main(["--once"]) == 1
    assert "worker_configuration_unavailable" in caplog.text
    assert "KeyError" not in caplog.text


@pytest.mark.parametrize("operation", ["backup", "restore"])
def test_backup_restore_use_explicit_project_without_destructive_options(tmp_path, operation):
    import os
    import subprocess
    from pathlib import Path

    archive = tmp_path / "synthetic.dump"
    log = tmp_path / "calls"
    docker = tmp_path / "docker"
    docker.write_text(
        '#!/bin/sh\nprintf "%s\\n" "$*" >> "$CALL_LOG"\n'
        'case "$*" in *psql*) echo 0;; *pg_dump*) echo synthetic-archive;; esac\n'
    )
    docker.chmod(0o755)
    if operation == "restore":
        archive.write_text("synthetic archive")
    command = [
        str(Path("scripts/operations", operation).resolve()),
        "synthetic-project",
        str(archive),
    ]
    if operation == "restore":
        command.append("--confirm-empty-database")
    result = subprocess.run(
        command,
        env={**os.environ, "PATH": f"{tmp_path}:/usr/bin:/bin", "CALL_LOG": str(log)},
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    calls = log.read_text()
    assert "--project-name synthetic-project" in calls
    assert "--clean" not in calls and "--volumes" not in calls
    if operation == "restore":
        assert "--single-transaction" in calls
        assert "pg_catalog" in calls
    else:
        assert archive.read_text().strip() == "synthetic-archive"
        repeated = subprocess.run(
            command,
            env={**os.environ, "PATH": f"{tmp_path}:/usr/bin:/bin", "CALL_LOG": str(log)},
            capture_output=True,
        )
        assert repeated.returncode != 0
        assert log.read_text() == calls


def test_restore_refuses_initialized_database(tmp_path):
    import os
    import subprocess
    from pathlib import Path

    archive = tmp_path / "synthetic.dump"
    archive.write_text("synthetic archive")
    docker = tmp_path / "docker"
    docker.write_text("#!/bin/sh\necho 1\n")
    docker.chmod(0o755)
    result = subprocess.run(
        [
            str(Path("scripts/operations/restore").resolve()),
            "synthetic-project",
            str(archive),
            "--confirm-empty-database",
        ],
        env={**os.environ, "PATH": f"{tmp_path}:/usr/bin:/bin"},
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    assert "empty database" in result.stderr
