"""Shared pytest fixtures.

Uses mongomock so the test suite never needs a real MongoDB instance.
The MongoDB connection lifecycle (`mongodb.connect`/`disconnect`) is patched
to no-ops, and `get_database` is overridden to return the in-memory client,
so `TestClient(app)` can drive the full FastAPI app — including lifespan —
without any external services.
"""

import mongomock
import pytest
from fastapi.testclient import TestClient

from app.database import mongodb
from app.dependencies import get_database
from app.main import app


@pytest.fixture()
def test_db():
    return mongomock.MongoClient()["finance_ml_test"]


@pytest.fixture()
def client(test_db, monkeypatch):
    monkeypatch.setattr(mongodb, "connect", lambda: None)
    monkeypatch.setattr(mongodb, "disconnect", lambda: None)
    monkeypatch.setattr(mongodb, "is_connected", lambda: True)

    app.dependency_overrides[get_database] = lambda: test_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
