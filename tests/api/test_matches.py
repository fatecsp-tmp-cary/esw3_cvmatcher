from fastapi.testclient import TestClient

from src.api.app import create_app
from src.schemas.candidate import CandidateProfile
from src.schemas.matches import MatchesResponse

_CURRICULUM = {
    "curriculo_id": "cur_12345678",
    "dados_pessoais": {
        "cidade": "São Paulo",
        "estado": "SP",
        "modalidade_preferencial": "remoto",
    },
    "formacao_academica": [
        {
            "curso": "Análise e Desenvolvimento de Sistemas",
            "status": "em_andamento",
        }
    ],
    "competencias": [{"nome": "Python", "nivel": "intermediario"}],
    "idiomas": [{"idioma": "Inglês", "nivel": "avancado"}],
    "experiencias_profissionais": [
        {"cargo": "Developer", "empresa": "Acme", "descricao": "APIs"}
    ],
    "projetos_academicos": [
        {"titulo": "Portfolio", "tecnologias": ["FastAPI"], "descricao": "Demo"}
    ],
}
_RESULT = {
    "matches": [
        {
            "rank": 1,
            "job": {
                "company": None,
                "title": "Backend Developer",
                "description": None,
                "keywords": None,
                "location": None,
                "work_arrangement": None,
                "seniority_level": None,
                "skills": ["Python"],
                "salary": None,
                "currency": None,
                "job_url": None,
                "publication_date": None,
            },
            "score": 87.5,
            "embedding_model": "pending-model-selection",
            "algorithm_version": "v1",
        }
    ]
}


class _Executor:
    def __init__(self) -> None:
        self.received: CandidateProfile | None = None
        self.limit: int | None = None
        self.offset: int | None = None

    async def execute(
        self, candidate: CandidateProfile, *, limit: int, offset: int
    ) -> MatchesResponse:
        self.received = candidate
        self.limit = limit
        self.offset = offset
        return MatchesResponse.model_validate(_RESULT)


def test_matches_accepts_complete_curriculum_and_adapts_transient_profile() -> None:
    executor = _Executor()
    with TestClient(create_app(executor)) as client:
        response = client.post("/matches?limit=5&offset=10", json=_CURRICULUM)

    assert response.status_code == 200
    assert response.json() == _RESULT
    assert executor.received is not None
    assert executor.received.job_titles == ["Developer"]
    assert executor.received.skills == ["Python"]
    assert executor.received.education[0].institution == "FATEC-SP"
    assert executor.received.academic_projects[0].technologies == ["FastAPI"]
    assert executor.limit == 5
    assert executor.offset == 10


def test_matches_rejects_invalid_candidate_without_echoing_values() -> None:
    with TestClient(create_app(_Executor())) as client:
        response = client.post("/matches", json={"curriculo_id": "private-cv-value"})

    assert response.status_code == 422
    assert response.headers["content-type"] == "application/problem+json"
    assert "private-cv-value" not in response.text


def test_matches_reports_unavailable_when_executor_is_not_configured() -> None:
    with TestClient(create_app()) as client:
        response = client.post("/matches", json=_CURRICULUM)

    assert response.status_code == 503
    assert response.json()["status"] == 503


def test_matches_openapi_uses_curriculum_and_ranked_response_schemas() -> None:
    schema = create_app().openapi()
    operation = schema["paths"]["/matches"]["post"]

    assert operation["requestBody"]["content"]["application/json"]["schema"]["$ref"].endswith(
        "/CurriculumRequest"
    )
    assert operation["responses"]["200"]["content"]["application/json"]["schema"][
        "$ref"
    ].endswith("/MatchesResponse")
    assert {parameter["name"] for parameter in operation["parameters"]} == {
        "limit",
        "offset",
    }
