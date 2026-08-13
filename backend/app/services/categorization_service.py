"""Wraps ml.categorization.predict.TransactionClassifier for use inside the
backend. The model is loaded once at process start and reused across
requests — sklearn/joblib deserialization isn't cheap enough to redo per
request.

No training logic lives here — see ml/categorization/train.py. If no model
has ever been trained (fresh checkout), `is_ready` is False and callers get
"Uncategorized" back instead of an error, so the import pipeline and the
rest of the app work fine before Phase 4's training step has ever been run.

Path note: docker-compose mounts ./ml -> /app/ml and ./models -> /app/models
alongside the backend app (see docker-compose.yml), so `import ml...` just
works in Docker since /app is on sys.path. For local (non-Docker) dev where
`ml/` lives one level above `backend/`, the except branch below adds the
repo root to sys.path as a fallback.
"""

import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

try:
    from ml.categorization.predict import CategoryPrediction, TransactionClassifier
except ImportError:
    _repo_root = Path(__file__).resolve().parents[3]
    if str(_repo_root) not in sys.path:
        sys.path.insert(0, str(_repo_root))
    from ml.categorization.predict import CategoryPrediction, TransactionClassifier  # noqa: E402


class CategorizationService:
    def __init__(self) -> None:
        try:
            self._classifier: TransactionClassifier | None = TransactionClassifier()
        except Exception:
            logger.exception(
                "Failed to load categorization model; falling back to 'Uncategorized'"
            )
            self._classifier = None

    @property
    def is_ready(self) -> bool:
        return self._classifier is not None and self._classifier.is_ready

    @property
    def active_version(self) -> int | None:
        return self._classifier.active_version if self._classifier else None

    def categorize(self, description: str) -> CategoryPrediction:
        if not self.is_ready:
            return CategoryPrediction(category="Uncategorized", confidence=0.0)
        assert self._classifier is not None
        return self._classifier.predict(description)

    def categorize_batch(self, descriptions: list[str]) -> list[CategoryPrediction]:
        if not self.is_ready:
            return [
                CategoryPrediction(category="Uncategorized", confidence=0.0) for _ in descriptions
            ]
        assert self._classifier is not None
        return self._classifier.predict_batch(descriptions)


# Loaded once at import time and reused. See module docstring for the
# fallback-to-"Uncategorized" behavior when no model has been trained yet.
categorization_service = CategorizationService()
