"""Boundary coverage for public curriculum collections and technology tags."""

from copy import deepcopy

import pytest
from fastapi.testclient import TestClient

from src.api.app import CURRICULUM_EXAMPLE
from src.api.app import create_app as create_public_app
from src.mock_api.app import create_app as create_mock_app


@pytest.fixture(params=["production", "mock"])
def client(request):
    app = (
        create_public_app(lambda curriculum, limit: {"matches": []})
        if request.param == "production"
        else create_mock_app()
    )
    with TestClient(app) as test_client:
        yield test_client


@pytest.mark.parametrize(
    ("path", "maximum"),
    [
        (("formacao_academica",), 20),
        (("competencias",), 200),
        (("idiomas",), 20),
        (("experiencias_profissionais",), 50),
        (("projetos_academicos",), 50),
        (("projetos_academicos", 0, "tecnologias"), 100),
    ],
)
def test_curriculum_collection_boundaries(client, path, maximum) -> None:
    payload = deepcopy(CURRICULUM_EXAMPLE)
    parent = payload
    for part in path[:-1]:
        parent = parent[part]
    item = parent[path[-1]][0]
    parent[path[-1]] = [item] * maximum
    assert client.post("/matches", json=payload).status_code == 200

    parent[path[-1]].append(item)
    response = client.post("/matches", json=payload)

    assert response.status_code == 422
    assert response.headers["content-type"] == "application/problem+json"
    assert response.json()["errors"][0]["loc"] == ["body", *path]
    assert response.json()["errors"][0]["type"] == "too_long"


def test_technology_tags_have_bounded_nonempty_text(client) -> None:
    payload = deepcopy(CURRICULUM_EXAMPLE)
    payload["projetos_academicos"][0]["tecnologias"] = ["x" * 200]
    assert client.post("/matches", json=payload).status_code == 200

    for invalid_tag in ("x" * 201, "   "):
        payload["projetos_academicos"][0]["tecnologias"] = [invalid_tag]
        response = client.post("/matches", json=payload)
        assert response.status_code == 422
        assert response.json()["errors"][0]["loc"] == [
            "body",
            "projetos_academicos",
            0,
            "tecnologias",
            0,
        ]
