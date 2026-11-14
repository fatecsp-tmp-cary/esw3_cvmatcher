import json
from threading import Event
from types import SimpleNamespace

import pytest

from src.worker.__main__ import main
from src.worker.runtime import BackgroundWorker, CycleResult
from src.worker.scheduler import interval_seconds, source_lock


class Extraction:
    config_version = "test-v1"

    def __init__(self, *results):
        self.results = iter(results)
        self.calls = 0

    def process_once(self, **kwargs):
        self.calls += 1
        return next(self.results)


def worker(extraction=None, scheduler=None, **kwargs):
    return BackgroundWorker(
        scheduler or SimpleNamespace(run_due=lambda **_: ()),
        lambda: pytest.fail("unit tests must not open a database"),
        extraction or Extraction(False),
        "test-v1",
        **kwargs,
    )


@pytest.mark.parametrize(
    "value,expected", [(None, 3600), (0, 3600), (-5, 3600), (True, 3600), (15, 15)]
)
def test_polling_interval_uses_only_positive_integers(value, expected):
    assert interval_seconds(value) == expected


@pytest.mark.parametrize("default", [0, -1, True, 1.5])
def test_invalid_default_interval_is_rejected(default):
    with pytest.raises(ValueError):
        interval_seconds(None, default)


def test_worker_cycle_order_and_extraction_batch_ceiling(monkeypatch):
    order = []
    scheduler = SimpleNamespace(run_due=lambda **_: order.append("poll") or ())
    extraction = Extraction(True, True, True)
    subject = worker(
        extraction,
        scheduler,
        expiration_hook=lambda: order.append("expire"),
        embedding_hook=lambda: order.append("embed"),
        max_extractions_per_cycle=2,
    )
    monkeypatch.setattr(subject, "enqueue_missing", lambda: order.append("enqueue") or 4)
    result = subject.run_once()
    assert order == ["poll", "expire", "enqueue", "embed"]
    assert result == CycleResult((), 4, 2, ())
    assert extraction.calls == 2


def test_stage_failures_do_not_leak_exception_text_or_skip_independent_stages(monkeypatch, caplog):
    calls = []

    def broken():
        raise RuntimeError("private job, candidate text and database credentials")

    subject = worker(expiration_hook=broken, embedding_hook=lambda: calls.append("embed"))
    monkeypatch.setattr(subject, "enqueue_missing", broken)
    result = subject.run_once()
    assert result.errors == ("expiration", "enqueue")
    assert result.extractions == 0
    assert calls == ["embed"]
    assert "private" not in caplog.text
    assert [json.loads(record.message)["stage"] for record in caplog.records] == [
        "expiration",
        "enqueue",
    ]


def test_extraction_storage_failure_stops_batch_but_keeps_embedding(monkeypatch):
    class BrokenExtraction:
        config_version = "test-v1"

        def process_once(self, **kwargs):
            raise RuntimeError("private")

    calls = []
    subject = worker(BrokenExtraction(), embedding_hook=lambda: calls.append("embed"))
    monkeypatch.setattr(subject, "enqueue_missing", lambda: 0)
    assert subject.run_once().errors == ("extraction",)
    assert calls == ["embed"]


@pytest.mark.parametrize("batch", [0, -1, True, 1.5])
def test_invalid_batch_limits_rejected(batch):
    with pytest.raises(ValueError):
        worker(max_extractions_per_cycle=batch)
    with pytest.raises(ValueError):
        worker(enqueue_batch_size=batch)


def test_worker_config_must_match_extractor():
    with pytest.raises(ValueError):
        BackgroundWorker(None, None, Extraction(), "different")


@pytest.mark.parametrize("identity", [0, -1, True, "1"])
def test_explicit_retry_rejects_invalid_id_before_database(identity):
    with pytest.raises(ValueError):
        worker().retry_extraction(identity)


def test_stopped_worker_does_not_run_another_cycle(monkeypatch):
    subject = worker()
    stop = Event()
    calls = []

    def cycle():
        calls.append(True)
        stop.set()

    monkeypatch.setattr(subject, "run_once", cycle)
    subject.run_forever(stop, poll_seconds=0.01)
    assert calls == [True]


@pytest.mark.parametrize("delay", [0, -1, float("nan"), float("inf")])
def test_loop_rejects_invalid_poll_delay(delay):
    with pytest.raises(ValueError):
        worker().run_forever(Event(), poll_seconds=delay)


@pytest.mark.parametrize("errors,expected", [((), 0), (("embedding",), 1)])
def test_cli_once_returns_failed_stage_status(errors, expected):
    subject = SimpleNamespace(run_once=lambda: CycleResult((), 0, 0, errors))
    assert main(["--once"], worker_factory=lambda: subject) == expected


def test_cli_retry_is_explicit_and_does_not_run_cycles():
    identifiers = []
    subject = SimpleNamespace(retry_extraction=identifiers.append)
    assert main(["--retry-extraction", "42"], worker_factory=lambda: subject) == 0
    assert identifiers == [42]


def test_cli_configuration_failure_is_safe(caplog):
    def broken():
        raise RuntimeError("private credentials")

    assert main(["--once"], worker_factory=broken) == 1
    assert "private" not in caplog.text
    assert json.loads(caplog.records[0].message) == {"event": "worker_configuration_unavailable"}


def test_cli_operation_failure_is_safe(caplog):
    def broken():
        raise RuntimeError("private job data")

    subject = SimpleNamespace(run_once=broken)
    assert main(["--once"], worker_factory=lambda: subject) == 1
    assert "private" not in caplog.text
    assert json.loads(caplog.records[0].message) == {"event": "worker_operation_failed"}


class Connection:
    def __init__(self, *results):
        self.results = iter(results)
        self.invalidated = False
        self.calls = []

    def __enter__(self):
        return self

    def __exit__(self, *_):
        pass

    def execution_options(self, **kwargs):
        assert kwargs == {"isolation_level": "AUTOCOMMIT"}
        return self

    def scalar(self, statement):
        self.calls.append(str(statement))
        result = next(self.results)
        if isinstance(result, Exception):
            raise result
        return result

    def invalidate(self):
        self.invalidated = True


@pytest.mark.parametrize("response", [False, RuntimeError("uncertain unlock")])
def test_uncertain_advisory_unlock_discards_physical_connection(response):
    connection = Connection(True, response)
    engine = SimpleNamespace(connect=lambda: connection)
    if isinstance(response, Exception):
        with pytest.raises(RuntimeError), source_lock(engine, 1) as acquired:
            assert acquired
    else:
        with source_lock(engine, 1) as acquired:
            assert acquired
    assert connection.invalidated
    assert len(connection.calls) == 2


def test_uncertain_lock_acquisition_discards_connection():
    connection = Connection(RuntimeError("unknown native outcome"))
    with pytest.raises(RuntimeError), source_lock(SimpleNamespace(connect=lambda: connection), 1):
        pytest.fail("uncertain acquisition must not enter polling")
    assert connection.invalidated


def test_busy_advisory_lock_is_neither_polled_nor_unlocked():
    connection = Connection(False)
    with source_lock(SimpleNamespace(connect=lambda: connection), 1) as acquired:
        assert not acquired
    assert not connection.invalidated
    assert len(connection.calls) == 1
