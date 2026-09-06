"""Application configuration, loaded from environment variables / .env."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_ENV = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    """Typed application settings. See .env.example for the full variable list."""

    model_config = SettingsConfigDict(
        env_file=str(ROOT_ENV),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Application
    app_name: str = "Finance Intelligence Platform"
    app_version: str = "1.0.0"
    debug: bool = False
    environment: str = "development"
    log_level: str = "INFO"

    # MongoDB
    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_database: str = "finance_ml"
    mongodb_min_pool_size: int = 5
    mongodb_max_pool_size: int = 50

    # JWT
    jwt_secret_key: str = "change-me-in-production-please-set-a-long-secret"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30

    # HTTP rate limiting
    rate_limit_enabled: bool = True
    rate_limit_max_requests: int = 300
    rate_limit_window_seconds: int = 60

    # MLflow
    mlflow_tracking_uri: str = "http://mlflow:5000"

    # CORS
    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:3002",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
        "http://127.0.0.1:3002",
    ]

    # File upload
    max_upload_size_mb: int = 10


@lru_cache
def get_settings() -> Settings:
    """Cached settings accessor so we parse the environment only once."""
    return Settings()
