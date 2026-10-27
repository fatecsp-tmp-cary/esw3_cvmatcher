from collections.abc import Callable

from fastapi import FastAPI, Query
from fastapi.openapi.utils import get_openapi

from src.api.errors import DependencyUnavailableError, ProblemDetail, register_error_handlers
from src.schemas.candidate import CurriculumRequest
from src.schemas.matches import MatchesResponse

MatchExecutor = Callable[[CurriculumRequest, int], MatchesResponse]


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
        curriculum: CurriculumRequest,
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
