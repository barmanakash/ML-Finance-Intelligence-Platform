"""Shared configuration for the ml/ package.

Paths are computed relative to this file's location rather than hardcoded,
so the same code works whether it's running standalone (repo checked out
locally) or inside the backend container (where docker-compose mounts
./ml -> /app/ml and ./models -> /app/models alongside the backend app).
"""

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODELS_DIR = PROJECT_ROOT / "models"
DATA_DIR = PROJECT_ROOT / "data"

# Falls back to a local SQLite-backed MLflow store so training scripts work
# without the docker-compose `mlflow` service running (MLflow 3.x deprecated
# the plain file-store backend). In Docker, MLFLOW_TRACKING_URI is set via
# .env and points at the real mlflow server instead.
MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", f"sqlite:///{(PROJECT_ROOT / 'mlflow.db').as_posix()}")
MLFLOW_EXPERIMENT_NAME = "transaction-categorization"

RANDOM_SEED = 42
