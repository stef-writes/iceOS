"""Central error types and FastAPI exception handlers."""

from __future__ import annotations

import logging
from typing import Any, Dict

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError

logger = logging.getLogger(__name__)


class APIError(Exception):
    """Custom exception that carries an HTTP status code and detail message."""

    def __init__(
        self, detail: str, status_code: int = 400, extra: Dict[str, Any] | None = None
    ):
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code
        self.extra = extra or {}


class SkillExecutionError(Exception):
    """Raised by *Skill* implementations on functional failures.

    Separating this from *APIError* keeps domain-specific logic distinct from
    transport-level concerns, yet allows orchestrator layers to treat all
    skill-level exceptions uniformly.
    """


# ---------------------------------------------------------------------------
# FastAPI integration helpers
# ---------------------------------------------------------------------------


def add_exception_handlers(app: FastAPI) -> None:
    """Register global exception handlers on *app*."""

    @app.exception_handler(APIError)
    async def _api_error_handler(_: Request, exc: APIError) -> JSONResponse:
        logger.error("APIError: %s", exc.detail)
        payload = {"detail": exc.detail, **exc.extra}
        return JSONResponse(status_code=exc.status_code, content=payload)

    @app.exception_handler(ValidationError)
    async def _validation_error_handler(
        _: Request, exc: ValidationError
    ) -> JSONResponse:
        logger.error("ValidationError: %s", exc.errors())
        return JSONResponse(status_code=422, content={"detail": exc.errors()})

    # Fallback – keep last so that specific handlers above win.
    @app.exception_handler(Exception)
    async def _unhandled_error_handler(_: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled server error: %s", exc)
        return JSONResponse(
            status_code=500, content={"detail": "Internal server error"}
        )
