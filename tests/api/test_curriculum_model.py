"""Contract cases from Sistema Currículo's implemented preview and domain.

Source: sistema-curriculo commit 66af300, api/previa_versao_curriculo.py,
domain/itens_perfil.py and domain/value_objects.py. No source app is executed.
"""

import json
from copy import deepcopy
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.api.app import create_app as create_public_app
from src.mock_api.app import create_app as create_mock_app

SOURCE_PREVIEW = json.loads(
    (Path(__file__).parents[2] / "examples/mock_api/curriculum.json").read_text(encoding="utf-8")
)


@pytest.fixture(params=["production", "mock"])
def client(request):
    app = (
        create_public_app(lambda curriculum, limit: {"matches": []})
        if request.param == "production"
        else create_mock_app()
    )
    with TestClient(app) as test_client:
        yield test_client


def test_implemented_preview_matching_sections_are_accepted(client) -> None:
    payload = deepcopy(SOURCE_PREVIEW)
    # These are valid source values rejected by the outdated integration document.
    payload["formacoes"][0].update(status="interrompido", fim=None)
    payload["competencias"][0].update(descricao="C", nivel="Experiente")
    payload["idiomas"][0]["nivel"] = "Nativo"
    response = client.post("/matches", json=payload)
    assert response.status_code == 200


def test_empty_preview_sections_are_valid(client) -> None:
    payload = {
        key: [] for key in ("formacoes", "experiencias", "projetos", "competencias", "idiomas")
    }
    payload["curriculo_id"] = SOURCE_PREVIEW["curriculo_id"]
    assert client.post("/matches", json=payload).status_code == 200


@pytest.mark.parametrize("section", ["formacoes", "experiencias"])
def test_period_accepts_null_end_and_rejects_reversed_dates(client, section) -> None:
    payload = deepcopy(SOURCE_PREVIEW)
    payload[section][0]["fim"] = None
    assert client.post("/matches", json=payload).status_code == 200
    payload[section][0]["fim"] = "2000-01-01"
    response = client.post("/matches", json=payload)
    assert response.status_code == 422
    assert response.json()["errors"][0]["loc"] == ["body", section, 0]


def test_completed_education_requires_end_date(client) -> None:
    payload = deepcopy(SOURCE_PREVIEW)
    payload["formacoes"][0].update(status="concluido", fim=None)
    assert client.post("/matches", json=payload).status_code == 422
    payload["formacoes"][0]["fim"] = "2026-12-01"
    assert client.post("/matches", json=payload).status_code == 200


@pytest.mark.parametrize(
    ("section", "field", "invalid"),
    [
        ("experiencias", "inicio", "2025-02-30"),
        ("formacoes", "nivel", "inventado"),
        ("formacoes", "status", "trancado"),
        ("projetos", "tecnologias", ["Python", "FastAPI"]),
        ("competencias", "descricao", "   "),
        ("idiomas", "nivel", "   "),
    ],
)
def test_values_outside_implemented_model_are_rejected(client, section, field, invalid) -> None:
    payload = deepcopy(SOURCE_PREVIEW)
    payload[section][0][field] = invalid
    response = client.post("/matches", json=payload)
    assert response.status_code == 422
    assert response.headers["content-type"] == "application/problem+json"
    assert response.json()["errors"][0]["loc"] == ["body", section, 0, field]


@pytest.mark.parametrize(
    ("section", "field", "maximum"),
    [
        ("formacoes", "instituicao", 200),
        ("formacoes", "curso", 200),
        ("projetos", "titulo", 200),
        ("projetos", "descricao", 2000),
        ("projetos", "tecnologias", 300),
    ],
)
def test_source_text_boundaries_and_controls(client, section, field, maximum) -> None:
    payload = deepcopy(SOURCE_PREVIEW)
    payload[section][0][field] = "x" * maximum
    assert client.post("/matches", json=payload).status_code == 200
    for invalid in ("x" * (maximum + 1), "\nvalid text", "valid\ttext", "   "):
        payload[section][0][field] = invalid
        assert client.post("/matches", json=payload).status_code == 422


@pytest.mark.parametrize("field", ["inicio", "fim", "descricao"])
def test_experience_fields_are_required_like_the_preview(client, field) -> None:
    payload = deepcopy(SOURCE_PREVIEW)
    del payload["experiencias"][0][field]
    response = client.post("/matches", json=payload)
    assert response.status_code == 422
    assert response.json()["errors"][0]["loc"] == ["body", "experiencias", 0, field]


@pytest.mark.parametrize(
    "field", ["dados_pessoais", "formacao_academica", "experiencias_profissionais"]
)
def test_outdated_integration_fields_are_rejected(client, field) -> None:
    payload = deepcopy(SOURCE_PREVIEW)
    payload[field] = []
    assert client.post("/matches", json=payload).status_code == 422


def test_source_uuid_identifiers_are_not_limited_to_version_four(client) -> None:
    payload = deepcopy(SOURCE_PREVIEW)
    payload["curriculo_id"] = "6ba7b810-9dad-11d1-80b4-00c04fd430c8"
    assert client.post("/matches", json=payload).status_code == 200


def test_invalid_curriculum_uuid_does_not_echo_parser_details(client) -> None:
    payload = deepcopy(SOURCE_PREVIEW)
    payload["curriculo_id"] = "private-candidate-item"
    response = client.post("/matches", json=payload)
    assert response.status_code == 422
    assert response.json()["errors"][0]["msg"] == ("Value error, identifier must be a valid UUID")
    assert "private-candidate-item" not in response.text


@pytest.mark.parametrize(
    "section", ["formacoes", "experiencias", "projetos", "competencias", "idiomas"]
)
def test_section_item_ids_are_not_part_of_the_cv_contract(client, section) -> None:
    payload = deepcopy(SOURCE_PREVIEW)
    assert all("id" not in item for item in payload[section])
    assert client.post("/matches", json=payload).status_code == 200
    payload[section][0]["id"] = "unnecessary-item-id"
    response = client.post("/matches", json=payload)
    assert response.status_code == 422
    assert response.json()["errors"][0]["type"] == "extra_forbidden"
