from collections.abc import Callable
from typing import Annotated

from fastapi import Body, FastAPI, Query, Request
from fastapi.openapi.utils import get_openapi
from starlette.concurrency import run_in_threadpool

from src.api.errors import (
    DependencyUnavailableError,
    ProblemDetail,
    problem_response,
    register_error_handlers,
)
from src.api.rate_limit import GlobalRateLimiter
from src.api.runtime import production_matches, production_ready
from src.schemas.candidate import CurriculumRequest
from src.schemas.matches import MatchesResponse

MatchExecutor = Callable[[CurriculumRequest, int], MatchesResponse]
CURRICULUM_EXAMPLE = {
    "curriculo_id": "550e8400-e29b-41d4-a716-446655440000",
    "formacoes": [
        {
            "instituicao": "FATEC-SP",
            "curso": "Análise e Desenvolvimento de Sistemas",
            "nivel": "tecnologo",
            "status": "em_andamento",
            "inicio": "2024-02-01",
            "fim": "2026-12-01",
        }
    ],
    "experiencias": [
        {
            "empresa": "Empresa de exemplo",
            "cargo": "Estagiário de Desenvolvimento",
            "descricao": "Desenvolvimento de APIs REST e manutenção de banco de dados relacional.",
            "inicio": "2025-01-01",
            "fim": None,
        }
    ],
    "projetos": [
        {
            "titulo": "Sistema de Apoio Profissional",
            "descricao": "Plataforma de currículos e busca de vagas.",
            "tecnologias": "Java, Clean Architecture, Docker",
        }
    ],
    "competencias": [
        {
            "descricao": "Python",
            "nivel": "intermediario",
        }
    ],
    "idiomas": [{"idioma": "Inglês", "nivel": "B2"}],
}


def create_app(
    match_executor: MatchExecutor | None = None,
    *,
    rate_limiter: GlobalRateLimiter | None = None,
    readiness: Callable[[], None] | None = None,
) -> FastAPI:
    """Build the CV-Match API application."""
    app = FastAPI(title="CV-Match", version="0.1.0")
    register_error_handlers(app)

    if rate_limiter is not None:

        @app.middleware("http")
        async def admission_limit(request: Request, call_next):
            try:
                allowed = await run_in_threadpool(rate_limiter.allow)
            except Exception:
                # Do not expose database URLs, exception messages or request data.
                return problem_response(
                    503, "Service Unavailable", "Request admission is unavailable."
                )
            if not allowed:
                return problem_response(429, "Too Many Requests", headers={"Retry-After": "60"})
            return await call_next(request)

    @app.get("/health", tags=["system"])
    def health() -> dict[str, str]:
        if readiness is not None:
            readiness()
        return {"status": "ok"}

    @app.post(
        "/matches",
        response_model=MatchesResponse,
        tags=["matches"],
        responses={
            422: {"model": ProblemDetail, "description": "Invalid request"},
            429: {"model": ProblemDetail, "description": "Global request limit exceeded"},
            503: {"model": ProblemDetail, "description": "Matching service unavailable"},
        },
    )
    def matches(
        curriculum: Annotated[
            CurriculumRequest,
            Body(
                openapi_examples={
                    "sistema_curriculo": {
                        "summary": "Implemented Sistema Currículo preview: matching sections",
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
        for status in ("422", "429", "503"):
            content = schema["paths"]["/matches"]["post"]["responses"][status]["content"]
            content["application/problem+json"] = content.pop("application/json")
        app.openapi_schema = schema
        return schema

    app.openapi = custom_openapi  # type: ignore[method-assign]

    return app


app = create_app(
    match_executor=production_matches, rate_limiter=GlobalRateLimiter(), readiness=production_ready
)
