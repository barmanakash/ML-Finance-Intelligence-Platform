"""Registers FastAPI exception handlers that emit the documented error shape:

{"error": {"code": "...", "message": "...", "request_id": "..."}}

Stack traces are never returned to the client; in non-debug mode unexpected
errors are collapsed to a generic message and logged server-side instead.
"""

import logging

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.exceptions import AppException

logger = logging.getLogger("app.errors")


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppException)
    async def handle_app_exception(request: Request, exc: AppException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "request_id": getattr(request.state, "request_id", None),
                }
            },
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "One or more fields failed validation.",
                    "details": exc.errors(),
                    "request_id": getattr(request.state, "request_id", None),
                }
            },
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        logger.exception(
            "unhandled_exception request_id=%s", getattr(request.state, "request_id", None)
        )
        settings = get_settings()
        message = str(exc) if settings.debug else "An unexpected error occurred."
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": message,
                    "request_id": getattr(request.state, "request_id", None),
                }
            },
        )
