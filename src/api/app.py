from fastapi import FastAPI

from src.api.errors import register_error_handlers


def create_app() -> FastAPI:
    """Build the CV-Match API application."""
    app = FastAPI(title="CV-Match", version="0.1.0")
    register_error_handlers(app)

    @app.get("/health", tags=["system"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
