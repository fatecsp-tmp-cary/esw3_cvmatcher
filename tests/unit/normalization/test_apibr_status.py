import json
from urllib.error import HTTPError, URLError

import pytest

from src.normalization.jobs import apibr_status
from src.persistence.job.job import JobStatus


class _Response:
    status = 200

    def __init__(self, payload: dict[str, str]) -> None:
        self._payload = json.dumps(payload).encode()

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def read(self) -> bytes:
        return self._payload


@pytest.mark.parametrize(
    ("state", "expected"),
    [("open", JobStatus.ACTIVE), ("closed", JobStatus.EXPIRED), ("unknown", None)],
)
def test_check_apibr_job_status_maps_github_issue_state(monkeypatch, state, expected):
    monkeypatch.setattr(
        apibr_status, "urlopen", lambda *_args, **_kwargs: _Response({"state": state})
    )

    result = apibr_status.check_apibr_job_status("https://github.com/acme/jobs/issues/42")

    assert result == expected


@pytest.mark.parametrize("status_code", [404, 410])
def test_check_apibr_job_status_expires_on_missing_issue(monkeypatch, status_code):
    def raise_http_error(*_args, **_kwargs):
        raise HTTPError(
            "https://api.github.com/repos/acme/jobs/issues/42",
            status_code,
            "",
            {},
            None,
        )

    monkeypatch.setattr(apibr_status, "urlopen", raise_http_error)

    result = apibr_status.check_apibr_job_status("https://github.com/acme/jobs/issues/42")

    assert result == JobStatus.EXPIRED


@pytest.mark.parametrize("failure", [TimeoutError(), URLError("rate limited"), OSError()])
def test_check_apibr_job_status_ignores_transient_failures(monkeypatch, failure):
    def raise_failure(*_args, **_kwargs):
        raise failure

    monkeypatch.setattr(apibr_status, "urlopen", raise_failure)

    result = apibr_status.check_apibr_job_status("https://github.com/acme/jobs/issues/42")

    assert result is None


@pytest.mark.parametrize("status_code", [429, 500, 503])
def test_check_apibr_job_status_ignores_transient_http_statuses(monkeypatch, status_code):
    def raise_http_error(*_args, **_kwargs):
        raise HTTPError(
            "https://api.github.com/repos/acme/jobs/issues/42",
            status_code,
            "",
            {},
            None,
        )

    monkeypatch.setattr(apibr_status, "urlopen", raise_http_error)

    result = apibr_status.check_apibr_job_status("https://github.com/acme/jobs/issues/42")

    assert result is None


@pytest.mark.parametrize(
    "url",
    [
        "https://example.com/acme/jobs/issues/42",
        "http://github.com/acme/jobs/issues/42",
        "https://github.com/acme/jobs/pull/42",
        None,
    ],
)
def test_check_apibr_job_status_rejects_non_issue_urls(monkeypatch, url):
    def unexpected_request(*_args, **_kwargs):
        pytest.fail("invalid URL must not be requested")

    monkeypatch.setattr(apibr_status, "urlopen", unexpected_request)

    assert apibr_status.check_apibr_job_status(url) is None
