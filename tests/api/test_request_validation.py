"""Validates the request-validation testing approach.

The real POST /matches contract is defined in #39/#40. Until then, a test-only
route with a Pydantic body shows how valid and invalid payloads are exercised.
"""

from collections.abc import Iterator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel, Field


class _Payload(BaseModel):
    skills: list[str] = Field(min_length=1)
    years_experience: int = Field(ge=0)


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    @app.post("/_test/echo")
    def echo(payload: _Payload) -> _Payload:
        return payload

    with TestClient(app) as test_client:
        yield test_client


def test_valid_payload_is_accepted(client: TestClient) -> None:
    payload = {"skills": ["Python"], "years_experience": 3}

    response = client.post("/_test/echo", json=payload)

    assert response.status_code == 200
    assert response.json() == payload


@pytest.mark.parametrize(
    ("payload", "field"),
    [
        ({"skills": [], "years_experience": 3}, "skills"),
        ({"skills": ["Python"], "years_experience": -1}, "years_experience"),
        ({"skills": ["Python"]}, "years_experience"),
    ],
)
def test_invalid_payload_returns_422(client: TestClient, payload: dict, field: str) -> None:
    response = client.post("/_test/echo", json=payload)

    assert response.status_code == 422
    assert field in {error["loc"][-1] for error in response.json()["detail"]}


def test_malformed_json_returns_422(client: TestClient) -> None:
    response = client.post(
        "/_test/echo", content=b"{not json", headers={"Content-Type": "application/json"}
    )

    assert response.status_code == 422
