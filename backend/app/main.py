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
from app.dependencies import get_database
from app.middleware.error_handler import register_exception_handlers
from app.middleware.logging import RequestLoggingMiddleware
from app.repositories.category_repository import CategoryRepository

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
    # Resolved through the (overridable) get_database dependency rather
    # than mongodb.get_database() directly, so the test suite's mongomock
    # override (see tests/conftest.py) applies here too. Wrapped
    # defensively: a hiccup seeding defaults should never prevent the app
    # from starting (master-prompt Rule 11 wants sensible defaults to
    # exist, not a hard dependency on them existing).
    try:
        db_getter = app.dependency_overrides.get(get_database, get_database)
        CategoryRepository(db_getter()).ensure_defaults_seeded()
    except Exception:
        logging.getLogger(__name__).exception("Failed to seed default categories on startup")
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
    def ready() -> Response:
        from app.services.anomaly_detection_service import get_anomaly_detector_status
        from app.services.categorization_service import categorization_service
        from app.services.forecast_service import get_forecaster_status

        db_ready = mongodb.is_connected()
        categorizer_ready = categorization_service.is_ready
        anomaly_ready, _ = get_anomaly_detector_status()
        forecaster_ready, _ = get_forecaster_status()

        # The app is "ready" to serve traffic as soon as MongoDB is up —
        # ML models are reported for visibility (Rule 29: "Health checks
        # should verify... ML model availability") but a model that hasn't
        # been trained yet shouldn't make the whole app report unready,
        # since every ML-backed endpoint already degrades gracefully
        # (e.g. categorization falls back to "Uncategorized").
        import json

        body = {
            "ready": db_ready,
            "mongodb": db_ready,
            "models": {
                "transaction-classifier": categorizer_ready,
                "anomaly-detector": anomaly_ready,
                "expense-forecaster": forecaster_ready,
            },
        }
        status_code = 200 if db_ready else 503
        return Response(json.dumps(body), media_type="application/json", status_code=status_code)

    @app.get("/metrics", tags=["system"], summary="Prometheus metrics")
    def metrics() -> Response:
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

    return app


app = create_app()
