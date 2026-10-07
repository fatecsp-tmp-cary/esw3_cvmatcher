"""Standardized error responses (RFC 9457).

Test-only routes trigger each kind of error. CANARY stands in for candidate data: it
must never come back in an error body nor reach the logs.
"""

import logging
from collections.abc import Iterator

import httpx2
import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from pydantic import BaseModel, Field

from src.api.errors import DependencyUnavailableError

CANARY = "canary-7f3a9c"


class _Payload(BaseModel):
    name: str = Field(max_length=5)
    years_experience: int = Field(ge=0)


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    @app.post("/_test/payload")
    def accept_payload(payload: _Payload) -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/_test/missing-job")
    def missing_job() -> None:
        raise HTTPException(status_code=404, detail="Job not found")

    @app.get("/_test/dependency-down")
    def dependency_down() -> None:
        cause = ConnectionError(f"connection lost while matching {CANARY}")
        raise DependencyUnavailableError(f"database unreachable for {CANARY}") from cause

    @app.get("/_test/crash")
    def crash() -> None:
        raise RuntimeError(f"processing failed for {CANARY}")

    # raise_server_exceptions stays True: an exception escaping the app fails the test.
    with TestClient(app) as test_client:
        yield test_client


def assert_problem(response: httpx2.Response, status: int, title: str) -> dict:
    assert response.status_code == status
    assert response.headers["content-type"] == "application/problem+json"
    body = response.json()
    assert body["type"] == "about:blank"
    assert body["title"] == title
    assert body["status"] == status
    return body


def test_invalid_payload_returns_problem_without_submitted_values(client: TestClient) -> None:
    response = client.post("/_test/payload", json={"name": CANARY, "years_experience": -1})

    body = assert_problem(response, 422, "Unprocessable Content")
    assert {error["loc"][-1] for error in body["errors"]} == {"name", "years_experience"}
    assert all(set(error) == {"loc", "msg", "type"} for error in body["errors"])
    assert CANARY not in response.text


def test_malformed_json_returns_problem(client: TestClient) -> None:
    response = client.post(
        "/_test/payload",
        content=f'{{"name": "{CANARY}",'.encode(),
        headers={"Content-Type": "application/json"},
    )

    body = assert_problem(response, 422, "Unprocessable Content")
    assert body["errors"][0]["type"] == "json_invalid"
    assert CANARY not in response.text


def test_unknown_route_returns_problem(client: TestClient) -> None:
    response = client.get("/_test/does-not-exist")

    body = assert_problem(response, 404, "Not Found")
    assert "detail" not in body


def test_http_exception_keeps_its_detail(client: TestClient) -> None:
    response = client.get("/_test/missing-job")

    body = assert_problem(response, 404, "Not Found")
    assert body["detail"] == "Job not found"


def test_wrong_method_returns_problem_with_allow_header(client: TestClient) -> None:
    response = client.get("/_test/payload")

    assert_problem(response, 405, "Method Not Allowed")
    assert response.headers["allow"] == "POST"


def test_unavailable_dependency_returns_503(
    client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.DEBUG):
        response = client.get("/_test/dependency-down")

    body = assert_problem(response, 503, "Service Unavailable")
    assert body["detail"] == "A required dependency is unavailable. Try again later."
    assert CANARY not in response.text
    assert CANARY not in caplog.text
    assert "Dependency unavailable at test_errors.py:" in caplog.text
    assert "in dependency_down" in caplog.text


def test_unhandled_error_returns_generic_500(
    client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.DEBUG):
        response = client.get("/_test/crash")

    body = assert_problem(response, 500, "Internal Server Error")
    assert body["detail"] == "The request could not be processed."
    assert CANARY not in response.text
    assert CANARY not in caplog.text
    assert "Unhandled RuntimeError at test_errors.py:" in caplog.text
    assert "in crash" in caplog.text
