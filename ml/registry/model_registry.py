"""Lightweight file-based model registry.

Each model version lives at models/<model_name>/<version>/ containing
model.joblib + metadata.json (metrics, params, timestamp). A pointer file
models/<model_name>/active.txt records which version is currently "active" —
that's the version the backend serves.

This keeps the registry usable both by standalone training scripts (no DB
needed) and by the backend service reading the same mounted `models/`
directory (see docker-compose.yml: `./models:/app/models`).

`MODELS_DIR` is read from `ml.common.config` at call time (not bound to a
module-level constant here) so tests can monkeypatch it to a temp directory
without touching the real models/ folder.
"""

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import joblib

from ml.common import config as ml_config


def _model_dir(model_name: str) -> Path:
    return ml_config.MODELS_DIR / model_name


def get_version_dir(model_name: str, version: int) -> Path:
    return _model_dir(model_name) / str(version)


def next_version(model_name: str) -> int:
    base = _model_dir(model_name)
    if not base.exists():
        return 1
    existing = [int(p.name) for p in base.iterdir() if p.is_dir() and p.name.isdigit()]
    return max(existing, default=0) + 1


def save_version(
    model_name: str, version: int, pipeline: Any, metrics: dict, params: dict
) -> Path:
    version_dir = get_version_dir(model_name, version)
    version_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipeline, version_dir / "model.joblib")
    metadata = {
        "model_name": model_name,
        "version": version,
        "metrics": metrics,
        "params": params,
        "created_at": datetime.now(UTC).isoformat(),
    }
    with (version_dir / "metadata.json").open("w") as f:
        json.dump(metadata, f, indent=2)
    return version_dir


def load_metadata(model_name: str, version: int) -> dict | None:
    path = get_version_dir(model_name, version) / "metadata.json"
    if not path.exists():
        return None
    with path.open() as f:
        return json.load(f)


def get_active_version(model_name: str) -> int | None:
    active_file = _model_dir(model_name) / "active.txt"
    if not active_file.exists():
        return None
    content = active_file.read_text().strip()
    return int(content) if content else None


def set_active_version(model_name: str, version: int) -> None:
    base = _model_dir(model_name)
    base.mkdir(parents=True, exist_ok=True)
    (base / "active.txt").write_text(str(version))


def load_active_pipeline(model_name: str) -> tuple[Any | None, dict | None]:
    version = get_active_version(model_name)
    if version is None:
        return None, None
    model_path = get_version_dir(model_name, version) / "model.joblib"
    if not model_path.exists():
        return None, None
    pipeline = joblib.load(model_path)
    metadata = load_metadata(model_name, version)
    return pipeline, metadata


def maybe_promote(
    model_name: str, new_version: int, new_metrics: dict, metric_key: str = "macro_f1"
) -> bool:
    """Promote `new_version` to active only if its `metric_key` is >= the
    currently active version's (or there is no active version yet).

    This is the guardrail from master-prompt Rule 44: a retrain never
    silently replaces a better production model with a worse one.
    """
    current_version = get_active_version(model_name)
    if current_version is None:
        set_active_version(model_name, new_version)
        return True

    current_metadata = load_metadata(model_name, current_version)
    current_score = (current_metadata or {}).get("metrics", {}).get(metric_key, float("-inf"))
    new_score = new_metrics.get(metric_key, float("-inf"))

    if new_score >= current_score:
        set_active_version(model_name, new_version)
        return True
    return False
