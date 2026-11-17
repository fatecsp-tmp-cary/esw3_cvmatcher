import json
from email.message import Message
from urllib.error import HTTPError, URLError

import pytest

from src.ingestion.adapters import PollingMode, RateLimiter, RetryPolicy, SourceError
from src.ingestion.meupadrinho import (
    MEUPADRINHO_MAX_REQUESTS_PER_SECOND,
    MeuPadrinhoAdapter,
    MeuPadrinhoClient,
)


class Transport:
    def __init__(self, *responses):
        self.responses = iter(responses)
        self.calls = []

    def __call__(self, request, timeout):
        self.calls.append((request, timeout))
        response = next(self.responses)
        if isinstance(response, BaseException):
            raise response
        if isinstance(response, bytes):
            return response
        return json.dumps(response).encode()


def http_error(code, retry_after=None):
    headers = Message()
    if retry_after is not None:
        headers["Retry-After"] = retry_after
    return HTTPError("https://meupadrinho.com.br/api/vagas", code, "err", headers, None)


def detail_payload(title="Python Developer", closed=False):
    return {
        "titulo_vaga": title,
        "local": "Brasil",
        "horario_registro": "2026-11-10T10:00:00",
        "link_vaga": "https://example.com/job",
        "forma_trabalho": "remoto",
        "nivel_vaga": "Sênior",
        "requisitos_tecnicos": "Python; Docker",
        "nome_empresa": "Acme",
        "vaga_encerrada": closed,
    }


def test_fetch_job_returns_wrapped_record_and_handles_404():
    transport = Transport(detail_payload(), http_error(404))
    client = MeuPadrinhoClient(transport=transport)

    job = client.fetch_job("0faqqUu3")
    assert job == {"nano_id": "0faqqUu3", "contents": detail_payload()}
    assert transport.calls[0][0].full_url == "https://meupadrinho.com.br/api/vagas/0faqqUu3"

    missing = client.fetch_job("missing1")
    assert missing is None


def test_fetch_listing_retries_transient_failure_and_handles_empty_204():
    transport = Transport(
        URLError("transient"),
        {"vagas": [{"nano_id": "id1"}, {"nano_id": "id2"}]},
        b"",
    )
    waits = []
    client = MeuPadrinhoClient(
        transport=transport,
        retry_policy=RetryPolicy(jitter_ratio=0.0),
        rate_limiter=RateLimiter(60.0, clock=lambda: 0.0),
        sleep=waits.append,
    )

    listing = client.fetch_listing({"cargos": "backend", "niveis": "senior"})
    assert listing == [{"nano_id": "id1"}, {"nano_id": "id2"}]
    assert waits[0] == 1.0
    assert client.fetch_listing() == []


def test_meupadrinho_rate_limiter_enforces_60_requests_per_second_and_retry_jitter():
    now_clock = [10.0]
    waits = []

    def fake_sleep(delay):
        waits.append(delay)
        now_clock[0] += delay

    limiter = RateLimiter(
        MEUPADRINHO_MAX_REQUESTS_PER_SECOND,
        jitter_seconds=0.0,
        clock=lambda: now_clock[0],
    )
    retry = RetryPolicy(jitter_ratio=0.2, rng=lambda: 0.75)
    transport = Transport(
        detail_payload("Job 1"),
        URLError("transient"),
        detail_payload("Job 2"),
    )
    client = MeuPadrinhoClient(
        transport=transport,
        retry_policy=retry,
        rate_limiter=limiter,
        sleep=fake_sleep,
    )
    assert client.rate_limiter.max_requests_per_second == 60.0
    assert client.fetch_job("id1")["contents"]["titulo_vaga"] == "Job 1"
    # Second request happens immediately at t=10.0, so rate limiter waits 1/60s,
    # then transient failure triggers jittered backoff (1.0 * (0.8 + 0.4 * 0.75) = 1.1s).
    assert client.fetch_job("id2")["contents"]["titulo_vaga"] == "Job 2"
    assert len(waits) == 2
    assert abs(waits[0] - (1.0 / 60.0)) < 1e-6
    assert abs(waits[1] - 1.1) < 1e-6


@pytest.mark.parametrize("bad_id", ["", "   ", None, 123])
def test_fetch_job_rejects_invalid_nano_id(bad_id):
    client = MeuPadrinhoClient(transport=Transport())
    with pytest.raises(ValueError):
        client.fetch_job(bad_id)


async def test_async_adapter_discover_and_fetch_jobs():
    transport = Transport(
        {"vagas": [{"nano_id": "id1"}, {"nano_id": "id1"}, {"nano_id": "id2"}]},
        detail_payload("Job 1"),
        http_error(404),
    )
    adapter = MeuPadrinhoAdapter(MeuPadrinhoClient(transport=transport))
    assert adapter.platform == "meupadrinho"
    assert adapter.polling_mode is PollingMode.INCREMENTAL
    assert adapter.snapshot_complete is False

    jobs = [raw async for raw in adapter.fetch_jobs()]
    assert len(jobs) == 1
    assert jobs[0]["nano_id"] == "id1"
    normalized = adapter.normalize(jobs[0])
    assert normalized["platform"] == "meupadrinho"
    assert normalized["source_job_id"] == "id1"
    assert normalized["title"] == "Job 1"


async def test_async_adapter_rejects_invalid_discovery_records():
    adapter = MeuPadrinhoAdapter(MeuPadrinhoClient(transport=Transport({"vagas": [{}]})))
    with pytest.raises(SourceError, match="^invalid_discovery_record$"):
        await anext(adapter.discover())
