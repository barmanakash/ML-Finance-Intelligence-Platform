"""FastAPI application factory + lifespan.

Wires together: MongoDB connection lifecycle, CORS, request logging,
structured error handling, versioned API routes, Prometheus metrics, and
liveness/readiness health checks.
"""

import logging
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from starlette.responses import Response

from app.api.v1.router import api_router
from app.config import get_settings
from app.database import mongodb
from app.middleware.error_handler import register_exception_handlers
from app.middleware.logging import RequestLoggingMiddleware

settings = get_settings()
logging.basicConfig(level=settings.log_level)

REQUEST_COUNT = Counter(
    "http_requests_total", "Total HTTP requests", ["method", "path", "status_code"]
)
REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds", "HTTP request latency in seconds", ["method", "path"]
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    mongodb.connect()
    yield
    mongodb.disconnect()


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RequestLoggingMiddleware)

    register_exception_handlers(app)
    app.include_router(api_router)

    @app.middleware("http")
    async def metrics_middleware(request: Request, call_next):  # type: ignore[no-untyped-def]
        start = time.perf_counter()
        response = await call_next(request)
        duration = time.perf_counter() - start
        path = request.url.path
        REQUEST_COUNT.labels(request.method, path, response.status_code).inc()
        REQUEST_LATENCY.labels(request.method, path).observe(duration)
        return response

    @app.get("/health", tags=["system"], summary="Liveness check")
    def health() -> dict:
        return {
            "status": "healthy",
            "mongodb": "connected" if mongodb.is_connected() else "disconnected",
            "version": settings.app_version,
        }

    @app.get("/ready", tags=["system"], summary="Readiness check")
    def ready() -> dict:
        return {"ready": mongodb.is_connected()}

    @app.get("/metrics", tags=["system"], summary="Prometheus metrics")
    def metrics() -> Response:
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

    return app


app = create_app()
