"""MongoDB connection lifecycle management.

A single `MongoDBConnection` instance is created at import time and reused
across the app. `connect()`/`disconnect()` are called from the FastAPI
lifespan handler in `app.main`, so the client is created once per process
and connection pooling is handled by PyMongo itself.
"""

import logging

from pymongo import MongoClient
from pymongo.database import Database
from pymongo.errors import ConnectionFailure

from app.config import get_settings

logger = logging.getLogger(__name__)


class MongoDBConnection:
    """Owns the MongoDB client lifecycle for the application."""

    def __init__(self) -> None:
        self._client: MongoClient | None = None

    def connect(self) -> None:
        settings = get_settings()
        self._client = MongoClient(
            settings.mongodb_uri,
            minPoolSize=settings.mongodb_min_pool_size,
            maxPoolSize=settings.mongodb_max_pool_size,
            serverSelectionTimeoutMS=5000,
        )
        try:
            self._client.admin.command("ping")
        except ConnectionFailure:
            logger.exception("Failed to connect to MongoDB at %s", settings.mongodb_uri)
            raise
        logger.info("Connected to MongoDB database '%s'", settings.mongodb_database)

    def disconnect(self) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None
            logger.info("MongoDB connection closed")

    def is_connected(self) -> bool:
        if self._client is None:
            return False
        try:
            self._client.admin.command("ping")
            return True
        except Exception:
            return False

    def get_database(self) -> Database:
        if self._client is None:
            raise RuntimeError("MongoDB client is not connected. Call connect() first.")
        settings = get_settings()
        return self._client[settings.mongodb_database]


# Module-level singleton used by the app's lifespan and dependencies.
mongodb = MongoDBConnection()
