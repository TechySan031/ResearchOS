"""Global exception handler for the FastAPI application.

Catches ``ResearchOSError`` subtypes and unhandled exceptions, serializing
them into consistent JSON error responses with the appropriate HTTP status
code and correlation ID.
"""

from __future__ import annotations

from typing import Any

import structlog
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.constants import CORRELATION_ID_HEADER
from app.core.exceptions import ResearchOSError

logger = structlog.stdlib.get_logger(__name__)


def add_exception_handlers(app: FastAPI) -> None:
    """Register global exception handlers on the FastAPI app.

    Args:
        app: The FastAPI application instance.
    """

    @app.exception_handler(ResearchOSError)
    async def handle_researchos_error(
        request: Request,
        exc: ResearchOSError,
    ) -> JSONResponse:
        """Handle any ``ResearchOSError`` subtype."""
        correlation_id = request.headers.get(
            CORRELATION_ID_HEADER,
            "unknown",
        )

        logger.warning(
            "error.domain",
            error_type=exc.__class__.__name__,
            detail=exc.detail,
            status_code=exc.status_code,
            context=exc.context,
            correlation_id=correlation_id,
        )

        body: dict[str, Any] = exc.to_dict()
        body["correlation_id"] = correlation_id

        return JSONResponse(
            status_code=exc.status_code,
            content=body,
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(
        request: Request,
        exc: Exception,
    ) -> JSONResponse:
        """Catch-all for unhandled exceptions — always returns 500."""
        correlation_id = request.headers.get(
            CORRELATION_ID_HEADER,
            "unknown",
        )

        logger.exception(
            "error.unhandled",
            error_type=exc.__class__.__name__,
            detail=str(exc),
            correlation_id=correlation_id,
        )

        return JSONResponse(
            status_code=500,
            content={
                "error": "InternalServerError",
                "detail": "An unexpected internal error occurred.",
                "correlation_id": correlation_id,
            },
        )
