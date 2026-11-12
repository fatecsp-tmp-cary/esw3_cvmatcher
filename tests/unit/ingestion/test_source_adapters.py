import asyncio
import json
from datetime import UTC, datetime
from email.message import Message
from io import BytesIO
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlsplit

import pytest

from src.ingestion.adapters import PollingMode, RetryPolicy, SourceAdapter, SourceError
from src.ingestion.apibr import APiBRAdapter, APiBRClient


class Transport:
    def __init__(self, *responses):
        self.responses = iter(responses)
        self.calls = []

    def __call__(self, request, timeout):
        self.calls.append((request, timeout))
        response = next(self.responses)
        if isinstance(response, BaseException):
            raise response
        return json.dumps(response).encode()


def http_error(code, retry_after=None):
    headers = Message()
    if retry_after is not None:
        headers["Retry-After"] = retry_after
    return HTTPError("https://private.invalid/secret", code, "private body", headers, None)


def issue(identity=1, *, state="open"):
    return {"id": identity, "title": "Desenvolvedor Python", "body": "APIs", "state": state}


@pytest.mark.parametrize(
    "failure", [http_error(500), http_error(503), URLError("secret"), TimeoutError("secret")]
)
def test_transient_requests_are_bounded_and_retried(failure):
    transport = Transport(failure, failure, [issue()])
    waits = []
    client = APiBRClient(transport=transport, sleep=waits.append)
    assert client.fetch_page(4) == [issue()]
    assert waits == [1.0, 2.0]
    assert len(transport.calls) == 3
    for request, timeout in transport.calls:
        assert (
            request.full_url
            == "https://apibr.com/vagas/api/v2/issues?per_page=100&page=4&includeBody=true"
        )
        assert timeout == 15


@pytest.mark.parametrize("code", [400, 401, 403, 404, 408, 422])
def test_permanent_http_failure_is_safe_and_not_retried(code):
    transport = Transport(http_error(code))
    client = APiBRClient(transport=transport, sleep=lambda _: pytest.fail("unexpected sleep"))
    with pytest.raises(SourceError, match="^http_permanent_failure$") as failure:
        client.fetch_page(1)
    assert failure.value.retryable is False
    assert failure.value.__cause__ is None
    assert failure.value.__suppress_context__ is True
    assert len(transport.calls) == 1
    assert "secret" not in str(failure.value)


def test_exhaustion_does_not_start_a_fourth_attempt():
    transport = Transport(http_error(503), http_error(503), http_error(503), [issue()])
    waits = []
    with pytest.raises(SourceError, match="^http_server_failure$"):
        APiBRClient(transport=transport, sleep=waits.append).fetch_page(1)
    assert len(transport.calls) == 3
    assert waits == [1.0, 2.0]


@pytest.mark.parametrize(
    ("header", "expected"),
    [
        ("9", 9),
        ("99999999999", 60),
        ("0", 0),
        ("-1", 1),
        ("NaN", 1),
        ("1.5", 1),
        ("garbage", 1),
        ("Wed, 11 Nov 2026 12:00:10 GMT", 10),
        ("Wed, 11 Nov 2026 11:00:00 GMT", 0),
    ],
)
def test_rate_limit_retry_after_is_honored_and_bounded(header, expected):
    transport = Transport(http_error(429, header), [])
    waits = []
    client = APiBRClient(
        transport=transport, sleep=waits.append, now=lambda: datetime(2026, 11, 11, 12, tzinfo=UTC)
    )
    assert client.fetch_page(1) == []
    assert waits == [expected]


@pytest.mark.parametrize("payload", [{"private": "secret"}, None, 7, "secret"])
def test_valid_json_with_wrong_page_shape_is_not_retried(payload):
    transport = Transport(payload)
    with pytest.raises(SourceError, match="^invalid_page$"):
        APiBRClient(transport=transport).fetch_page(1)
    assert len(transport.calls) == 1


def test_malformed_json_is_not_retried_or_exposed():
    calls = []

    def transport(request, timeout):
        calls.append(request)
        return b"private-invalid-json"

    with pytest.raises(SourceError, match="^invalid_page$"):
        APiBRClient(transport=transport).fetch_page(1)
    assert len(calls) == 1


@pytest.mark.parametrize("attempts", [0, 4, -1, True, 1.5])
def test_invalid_retry_attempt_budget_is_rejected(attempts):
    with pytest.raises(ValueError):
        RetryPolicy(max_attempts=attempts)


@pytest.mark.parametrize(
    "base,maximum", [(-1, 60), (2, 1), (1, 61), (float("nan"), 60), (1, float("inf"))]
)
def test_invalid_retry_delays_are_rejected(base, maximum):
    with pytest.raises(ValueError):
        RetryPolicy(base_delay_seconds=base, max_delay_seconds=maximum)


@pytest.mark.parametrize("page", [0, -1, True, 1.5, "1"])
def test_invalid_page_does_not_make_request(page):
    transport = Transport()
    with pytest.raises(ValueError):
        APiBRClient(transport=transport).fetch_page(page)
    assert transport.calls == []


async def test_async_scan_is_sequential_and_preserves_raw_malformed_records():
    transport = Transport([issue(), None], [issue(2, state="closed")], [])
    adapter: SourceAdapter = APiBRAdapter(APiBRClient(transport=transport))
    records = [raw async for raw in adapter.fetch_jobs()]
    assert records == [issue(), None, issue(2, state="closed")]
    assert adapter.platform == "apibr"
    assert adapter.polling_mode is PollingMode.INCREMENTAL
    assert adapter.snapshot_complete is False
    assert [
        parse_qs(urlsplit(request.full_url).query)["page"] for request, _ in transport.calls
    ] == [["1"], ["2"], ["3"]]
    assert adapter.normalize(records[0])["status"] == "ACTIVE"
    assert adapter.normalize(records[2])["status"] == "EXPIRED"
    assert adapter.normalize({"id": 3, "title": "Python"})["status"] == "DISCOVERED"


async def test_async_scan_does_not_prefetch_pages():
    transport = Transport([issue(1)], [issue(2)], [])
    stream = APiBRAdapter(APiBRClient(transport=transport)).fetch_jobs()
    assert await anext(stream) == issue(1)
    assert len(transport.calls) == 1
    await stream.aclose()
    assert len(transport.calls) == 1


async def test_async_retry_waits_are_in_event_loop_and_cancellable():
    transport = Transport(http_error(429, "20"), [])
    waits = []

    async def cancel_sleep(delay):
        waits.append(delay)
        raise asyncio.CancelledError

    adapter = APiBRAdapter(APiBRClient(transport=transport), sleep=cancel_sleep)
    with pytest.raises(asyncio.CancelledError):
        await anext(adapter.fetch_jobs())
    assert waits == [20]
    assert len(transport.calls) == 1


async def test_async_retries_use_same_attempt_bound():
    transport = Transport(http_error(503), http_error(503), http_error(503))
    waits = []

    async def sleep(delay):
        waits.append(delay)

    adapter = APiBRAdapter(APiBRClient(transport=transport), sleep=sleep)
    with pytest.raises(SourceError, match="^http_server_failure$"):
        await anext(adapter.fetch_jobs())
    assert len(transport.calls) == 3
    assert waits == [1, 2]


async def test_page_safety_limit_does_not_claim_a_complete_snapshot():
    transport = Transport([issue(1)], [issue(2)])
    adapter = APiBRAdapter(APiBRClient(transport=transport), max_pages=2)
    with pytest.raises(SourceError, match="^page_safety_limit$"):
        _ = [record async for record in adapter.fetch_jobs()]
    assert len(transport.calls) == 2
    assert adapter.snapshot_complete is False


async def test_discover_returns_stable_ids_without_requesting_github():
    transport = Transport([issue(2), issue(" third ")], [])
    adapter = APiBRAdapter(APiBRClient(transport=transport))
    assert [identity async for identity in adapter.discover()] == ["2", "third"]
    assert all(urlsplit(request.full_url).hostname == "apibr.com" for request, _ in transport.calls)


@pytest.mark.parametrize("record", [None, {}, {"id": True}, {"id": []}, {"id": "  "}])
async def test_discovery_cannot_invent_missing_ids(record):
    adapter = APiBRAdapter(APiBRClient(transport=Transport([record])))
    with pytest.raises(SourceError, match="^invalid_discovery_record$"):
        await anext(adapter.discover())


async def test_fetch_job_scans_apibr_only_and_missing_is_not_availability_evidence():
    transport = Transport([None, issue(1)], [issue(" target ")])
    adapter = APiBRAdapter(APiBRClient(transport=transport))
    assert await adapter.fetch_job("target") == issue(" target ")
    assert len(transport.calls) == 2
    missing = APiBRAdapter(APiBRClient(transport=Transport([])))
    assert await missing.fetch_job("missing") is None
    assert missing.snapshot_complete is False


@pytest.mark.parametrize("identity", [None, 1, "", "   "])
async def test_invalid_fetch_job_identity_does_not_scan(identity):
    transport = Transport()
    with pytest.raises(ValueError):
        await APiBRAdapter(APiBRClient(transport=transport)).fetch_job(identity)
    assert transport.calls == []


def test_http_error_response_is_closed_before_retry():
    body = BytesIO(b"private response body")
    error = HTTPError("https://private.invalid", 503, "private", Message(), body)
    client = APiBRClient(transport=Transport(error, []), sleep=lambda _: None)
    assert client.fetch_page(1) == []
    assert body.closed


@pytest.mark.parametrize("limit", [0, -1, True, 1001, 1.5])
def test_async_adapter_rejects_unbounded_page_limit(limit):
    with pytest.raises(ValueError):
        APiBRAdapter(max_pages=limit)
