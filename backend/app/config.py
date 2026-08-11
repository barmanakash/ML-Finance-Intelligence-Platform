"""Application configuration, loaded from environment variables / .env."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed application settings. See .env.example for the full variable list."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

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
    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30

    # MLflow
    mlflow_tracking_uri: str = "http://mlflow:5000"

    # CORS
    cors_origins: list[str] = ["http://localhost:3000"]

    # File upload
    max_upload_size_mb: int = 10


@lru_cache
def get_settings() -> Settings:
    """Cached settings accessor so we parse the environment only once."""
    return Settings()
