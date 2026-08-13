"""Inference-only interface for the transaction categorizer.

No training logic here — see ml.categorization.train. This is what the
backend's CategorizationService wraps (app/services/categorization_service.py).
"""

from dataclasses import dataclass

from ml.preprocessing.text_preprocessing import normalize_description
from ml.registry import model_registry

MODEL_NAME = "transaction-classifier"


@dataclass
class CategoryPrediction:
    category: str
    confidence: float


class TransactionClassifier:
    def __init__(self) -> None:
        self._pipeline, self._metadata = model_registry.load_active_pipeline(MODEL_NAME)

    @property
    def is_ready(self) -> bool:
        return self._pipeline is not None

    @property
    def active_version(self) -> int | None:
        return (self._metadata or {}).get("version")

    def predict(self, description: str) -> CategoryPrediction:
        return self.predict_batch([description])[0]

    def predict_batch(self, descriptions: list[str]) -> list[CategoryPrediction]:
        if not self.is_ready:
            return [
                CategoryPrediction(category="Uncategorized", confidence=0.0) for _ in descriptions
            ]
        if not descriptions:
            return []

        cleaned = [normalize_description(d) for d in descriptions]
        predictions = self._pipeline.predict(cleaned)
        confidences = self._confidence_scores(cleaned)

        return [
            CategoryPrediction(category=str(pred), confidence=float(conf))
            for pred, conf in zip(predictions, confidences)
        ]

    def _confidence_scores(self, cleaned: list[str]) -> list[float]:
        if hasattr(self._pipeline, "predict_proba"):
            probs = self._pipeline.predict_proba(cleaned)
            return probs.max(axis=1).tolist()

        classifier = self._pipeline.named_steps.get("classifier")
        if classifier is not None and hasattr(classifier, "decision_function"):
            import numpy as np

            scores = np.atleast_2d(self._pipeline.decision_function(cleaned))
            # Softmax over decision scores as an approximate confidence —
            # LinearSVC has no predict_proba, only a margin per class.
            exp_scores = np.exp(scores - scores.max(axis=1, keepdims=True))
            probs = exp_scores / exp_scores.sum(axis=1, keepdims=True)
            return probs.max(axis=1).tolist()

        return [1.0 for _ in cleaned]
