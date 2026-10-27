from typing import Protocol

from fastapi import FastAPI

from src.api.errors import DependencyUnavailableError, register_error_handlers
from src.schemas.candidate import CandidateProfile
from src.schemas.matches import MatchesResponse


class MatchExecutor(Protocol):
    """Request-scoped matching operation injected by the application layer."""

    async def execute(self, candidate: CandidateProfile) -> MatchesResponse:
        """Return ranked results without persisting or logging candidate data."""


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
        tags=["matching"],
        responses={503: {"description": "Matching service unavailable."}},
    )
    async def get_matches(candidate: CandidateProfile) -> MatchesResponse:
        if match_executor is None:
            raise DependencyUnavailableError
        return await match_executor.execute(candidate)

    return app


app = create_app()
