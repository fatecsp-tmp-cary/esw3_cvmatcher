from collections.abc import Callable
from typing import Annotated

from fastapi import Body, FastAPI, Query
from fastapi.openapi.utils import get_openapi

from src.api.errors import DependencyUnavailableError, ProblemDetail, register_error_handlers
from src.schemas.candidate import CurriculumRequest
from src.schemas.matches import MatchesResponse

MatchExecutor = Callable[[CurriculumRequest, int], MatchesResponse]
CURRICULUM_EXAMPLE = {
    "curriculo_id": "cur_987654321",
    "dados_pessoais": {
        "cidade": "São Paulo",
        "estado": "SP",
        "modalidade_preferencial": "hibrido",
    },
    "formacao_academica": [
        {
            "curso": "Análise e Desenvolvimento de Sistemas",
            "instituicao": "FATEC-SP",
            "status": "em_andamento",
            "previsao_conclusao": "2026-12",
        }
    ],
    "competencias": [
        {"nome": "Java", "nivel": "intermediario"},
        {"nome": "Spring Boot", "nivel": "intermediario"},
        {"nome": "PostgreSQL", "nivel": "basico"},
        {"nome": "Git", "nivel": "intermediario"},
    ],
    "idiomas": [{"idioma": "Inglês", "nivel": "intermediario"}],
    "experiencias_profissionais": [
        {
            "cargo": "Estagiário de Desenvolvimento",
            "empresa": "Tech Solutions",
            "descricao": (
                "Desenvolvimento de APIs REST e manutenção de banco de dados relacional."
            ),
        }
    ],
    "projetos_academicos": [
        {
            "titulo": "Sistema de Apoio Profissional",
            "tecnologias": ["Java", "Clean Architecture", "Docker"],
            "descricao": (
                "Plataforma para auxílio na elaboração de currículos e busca de vagas integradas."
            ),
        }
    ],
}


def create_app(match_executor: MatchExecutor | None = None) -> FastAPI:
    """Build the CV-Match API application."""
    app = FastAPI(title="CV-Match", version="0.1.0")
    register_error_handlers(app)

    @app.get("/health", tags=["system"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post(
        "/matches",
        response_model=MatchesResponse,
        tags=["matches"],
        responses={
            422: {"model": ProblemDetail, "description": "Invalid request"},
            503: {"model": ProblemDetail, "description": "Matching service unavailable"},
        },
    )
    def matches(
        curriculum: Annotated[
            CurriculumRequest,
            Body(
                openapi_examples={
                    "sistema_curriculo": {
                        "summary": "Sample payload from Sistema Currículo",
                        "value": CURRICULUM_EXAMPLE,
                    }
                }
            ),
        ],
        limit: int = Query(default=10, ge=1, le=100),
    ) -> MatchesResponse:
        if match_executor is None:
            raise DependencyUnavailableError
        return match_executor(curriculum, limit)

    def custom_openapi() -> dict:
        if app.openapi_schema:
            return app.openapi_schema
        schema = get_openapi(title=app.title, version=app.version, routes=app.routes)
        for status in ("422", "503"):
            content = schema["paths"]["/matches"]["post"]["responses"][status]["content"]
            content["application/problem+json"] = content.pop("application/json")
        app.openapi_schema = schema
        return schema

    app.openapi = custom_openapi

    return app


app = create_app()
