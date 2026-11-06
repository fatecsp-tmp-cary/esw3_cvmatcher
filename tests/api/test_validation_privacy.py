"""Arbitrary JSON keys must not escape through validation locations or logs."""

import logging
from copy import deepcopy

import pytest
from fastapi.testclient import TestClient

from src.api.app import CURRICULUM_EXAMPLE
from src.api.app import create_app as create_public_app
from src.mock_api.app import create_app as create_mock_app


@pytest.mark.parametrize("app_factory", [create_public_app, create_mock_app])
@pytest.mark.parametrize(
    "path",
    [(), ("dados_pessoais",), ("formacao_academica", 0), ("projetos_academicos", 0)],
)
def test_extra_field_names_and_values_stay_private(app_factory, path, caplog) -> None:
    payload = deepcopy(CURRICULUM_EXAMPLE)
    containing_object = payload
    for part in path:
        containing_object = containing_object[part]
    private_key = "private-candidate-key-7f3a9c"
    private_value = "private-candidate-value-91bcef"
    containing_object[private_key] = private_value

    with caplog.at_level(logging.DEBUG), TestClient(app_factory()) as client:
        response = client.post("/matches", json=payload)

    assert response.status_code == 422
    assert response.headers["content-type"] == "application/problem+json"
    assert response.json()["errors"] == [
        {
            "loc": ["body", *path],
            "msg": "Extra inputs are not permitted",
            "type": "extra_forbidden",
        }
    ]
    for private_data in (private_key, private_value, payload["curriculo_id"]):
        assert private_data not in response.text
        assert private_data not in caplog.text
