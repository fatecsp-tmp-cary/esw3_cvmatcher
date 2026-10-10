"""Standardized API errors, following RFC 9457 (Problem Details for HTTP APIs).

Every error leaves the API as ``application/problem+json``. Error bodies and logs never
carry submitted values or exception messages: they may contain candidate data.
"""

import logging
import traceback
from collections.abc import Awaitable, Callable
from http import HTTPStatus
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)

PROBLEM_JSON = "application/problem+json"


class ValidationIssue(BaseModel):
    """One invalid request field. Carries no submitted value.

    ``loc`` holds field names and list indexes. A free-form ``dict`` field would put the
    keys the client sent in it, so request schemas use fixed fields instead.
    """

    loc: list[str | int]
    msg: str
    type: str


class ProblemDetail(BaseModel):
    """Error body defined by RFC 9457, plus the ``errors`` extension for validation."""

    type: str = "about:blank"
    title: str
    status: int
    detail: str | None = None
    errors: list[ValidationIssue] | None = None


class DependencyUnavailableError(Exception):
    """A required dependency (database, embedding model) is unavailable."""


def _origin(exc: BaseException) -> str:
    """Where the exception was raised: file, line and function. No message, no values."""
    frames = traceback.extract_tb(exc.__traceback__)
    if not frames:
        return "unknown location"
    frame = frames[-1]
    return f"{Path(frame.filename).name}:{frame.lineno} in {frame.name}"


def problem_response(
    status: int,
    title: str,
    detail: str | None = None,
    errors: list[ValidationIssue] | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    problem = ProblemDetail(title=title, status=status, detail=detail, errors=errors)
    return JSONResponse(
        problem.model_dump(exclude_none=True),
        status_code=status,
        headers=headers,
        media_type=PROBLEM_JSON,
    )


async def _handle_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    # Copy only loc/msg/type: Pydantic's "input" and "ctx" echo the submitted values.
    errors = [
        ValidationIssue(loc=list(error["loc"]), msg=error["msg"], type=error["type"])
        for error in exc.errors()
    ]
    # RFC 9457: with type "about:blank", the title is the status phrase from RFC 9110.
    return problem_response(
        422,
        "Unprocessable Content",
        "One or more request fields are invalid.",
        errors=errors,
    )


async def _handle_http_exception(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    title = HTTPStatus(exc.status_code).phrase
    detail = exc.detail if isinstance(exc.detail, str) and exc.detail != title else None
    return problem_response(exc.status_code, title, detail, headers=exc.headers)


async def _handle_dependency_unavailable(
    request: Request, exc: DependencyUnavailableError
) -> JSONResponse:
    logger.warning("Dependency unavailable at %s", _origin(exc))
    return problem_response(
        503,
        "Service Unavailable",
        "A required dependency is unavailable. Try again later.",
    )


async def _catch_unhandled_errors(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    # A handler registered for Exception would answer the request, but Starlette re-raises
    # the exception afterwards and the server logs its traceback. Catching it here stops it.
    try:
        return await call_next(request)
    except Exception as exc:
        logger.error("Unhandled %s at %s", type(exc).__name__, _origin(exc))
        return problem_response(
            500,
            "Internal Server Error",
            "The request could not be processed.",
        )


def register_error_handlers(app: FastAPI) -> None:
    """Make every error response follow the RFC 9457 shape."""
    app.add_exception_handler(RequestValidationError, _handle_validation_error)
    app.add_exception_handler(StarletteHTTPException, _handle_http_exception)
    app.add_exception_handler(DependencyUnavailableError, _handle_dependency_unavailable)
    app.middleware("http")(_catch_unhandled_errors)
