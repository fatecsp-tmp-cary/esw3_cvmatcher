from fastapi.testclient import TestClient


def valid_curriculum() -> dict:
    return {
        "curriculo_id": "cur_Abcd1234",
        "dados_pessoais": {"modalidade_preferencial": "remoto"},
        "formacao_academica": [{"curso": "Sistemas", "status": "em_andamento"}],
        "competencias": [{"nome": "Python", "nivel": "intermediario"}],
    }


def test_matches_contract_uses_flat_body_and_default_limit() -> None:
    received: list[tuple[dict, int]] = []

    def execute(curriculum, limit):
        received.append((curriculum.model_dump(), limit))
        return {"matches": []}

    from src.api.app import create_app

    with TestClient(create_app(execute)) as injected_client:
        response = injected_client.post("/matches", json=valid_curriculum())

    assert response.status_code == 200
    assert response.json() == {"matches": []}
    assert received[0][1] == 10
    assert received[0][0]["formacao_academica"][0]["instituicao"] == "FATEC-SP"


def test_matches_limit_bounds_and_no_offset(client: TestClient) -> None:
    for limit in (0, 101):
        response = client.post(f"/matches?limit={limit}", json=valid_curriculum())
        assert response.status_code == 422
    schema = client.get("/openapi.json").json()
    parameter_names = [
        parameter["name"] for parameter in schema["paths"]["/matches"]["post"]["parameters"]
    ]
    assert parameter_names == ["limit"]


def test_matches_validation_error_does_not_echo_candidate_id(client: TestClient) -> None:
    body = valid_curriculum()
    body["curriculo_id"] = "private_candidate_value"

    response = client.post("/matches", json=body)

    assert response.status_code == 422
    assert response.headers["content-type"].startswith("application/problem+json")
    assert "private_candidate_value" not in response.text


def test_matches_unavailable_returns_problem_details(client: TestClient) -> None:
    response = client.post("/matches", json=valid_curriculum())

    assert response.status_code == 503
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["status"] == 503


def test_openapi_documents_matches_contract_and_problem_responses(client: TestClient) -> None:
    schema = client.get("/openapi.json").json()
    operation = schema["paths"]["/matches"]["post"]

    assert operation["parameters"] == [
        {
            "name": "limit",
            "in": "query",
            "required": False,
            "schema": {
                "type": "integer",
                "maximum": 100,
                "minimum": 1,
                "default": 10,
                "title": "Limit",
            },
        }
    ]
    assert "CurriculumRequest" in str(operation["requestBody"])
    assert "MatchesResponse" in str(operation["responses"]["200"])
    assert "application/problem+json" in operation["responses"]["422"]["content"]
    assert "application/problem+json" in operation["responses"]["503"]["content"]
    assert "curriculo_id" not in schema["components"]["schemas"]["MatchesResponse"]


def test_swagger_page_is_available(client: TestClient) -> None:
    response = client.get("/swagger")

    assert response.status_code == 200
    assert "swagger-ui" in response.text
    assert "/openapi.json" in response.text
