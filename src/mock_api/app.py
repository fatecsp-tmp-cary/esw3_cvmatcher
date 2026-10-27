"""FastAPI app that returns deterministic sample match results."""

import argparse

import uvicorn
from fastapi import FastAPI, Query

from src.api.errors import register_error_handlers
from src.mock_api.contracts import CurriculumRequest, MatchesResponse

_SAMPLE_RESPONSE = MatchesResponse.model_validate(
    {
        "matches": [
            {
                "rank": 1,
                "job": {
                    "company": "Example Company",
                    "title": "Backend Developer",
                    "description": "Synthetic example role for API integration testing.",
                    "keywords": ["Python", "APIs", "PostgreSQL"],
                    "location": {"city": "São Paulo", "state": "SP"},
                    "work_arrangement": "REMOTE",
                    "seniority_level": "JUNIOR",
                    "skills": ["Python", "FastAPI"],
                    "salary": None,
                    "currency": None,
                    "job_url": "https://example.invalid/jobs/backend-developer",
                    "publication_date": None,
                },
                "score": 87.5,
                "embedding_model": "mock-model",
                "algorithm_version": "mock-v1",
            }
        ]
    }
)


def create_app() -> FastAPI:
    """Build the mock service without database, model, or source dependencies."""
    app = FastAPI(title="CV-Match API Mock", version="0.1.0")
    register_error_handlers(app)

    @app.get("/health", tags=["system"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/matches", response_model=MatchesResponse, tags=["matching"])
    def matches(
        _request: CurriculumRequest,
        limit: int = Query(default=10, ge=1, le=100),
    ) -> MatchesResponse:
        # The request, including curriculo_id, is deliberately not retained or echoed.
        return MatchesResponse(matches=_SAMPLE_RESPONSE.matches[:limit])

    return app


app = create_app()


def main() -> None:
    """Run locally with configurable bind host and port."""
    parser = argparse.ArgumentParser(description="Run the CV-Match API mock server.")
    parser.add_argument(
        "--host", default="127.0.0.1", help="Interface to bind (default: localhost)."
    )
    parser.add_argument("--port", type=int, default=8001, help="Port to bind (default: 8001).")
    args = parser.parse_args()
    uvicorn.run(app, host=args.host, port=args.port, access_log=False)
