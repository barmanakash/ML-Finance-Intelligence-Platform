"""Inference-only interface for the anomaly detector.

No training logic here — see ml.anomaly_detection.train. This is what the
backend's AnomalyDetectionService wraps.

Explanations are generated deterministically from the same engineered
features the model scored on (feature-threshold rules), not by the model
itself or any generative process — see master-prompt Rule 13. An anomaly
score is never presented as a fraud determination; "is_anomaly" means
"unusual relative to this person's own history," full stop.
"""

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from ml.anomaly_detection.features import FEATURE_COLUMNS, compute_features
from ml.registry import model_registry

MODEL_NAME = "anomaly-detector"

# Anomaly scores are min-max normalized to [0, 1] within each scoring batch;
# these cutoffs turn that continuous score into the three severity buckets
# the API and UI use (Rule 12).
SEVERITY_HIGH = 0.75
SEVERITY_MEDIUM = 0.5

ZSCORE_EXPLANATION_THRESHOLD = 2.0


@dataclass
class AnomalyResult:
    index: int
    is_anomaly: bool
    anomaly_score: float
    severity: str
    reasons: list[str] = field(default_factory=list)


class AnomalyDetector:
    def __init__(self) -> None:
        self._pipeline, self._metadata = model_registry.load_active_pipeline(MODEL_NAME)

    @property
    def is_ready(self) -> bool:
        return self._pipeline is not None

    @property
    def active_version(self) -> int | None:
        return (self._metadata or {}).get("version")

    def score_transactions(self, transactions: pd.DataFrame) -> list[AnomalyResult]:
        """`transactions` needs columns: amount, category, merchant,
        transaction_date — and should be a single user's *complete* history,
        since features are computed relative to that history (see
        ml.anomaly_detection.features).
        """
        n = len(transactions)
        if not self.is_ready or n == 0:
            return [
                AnomalyResult(index=i, is_anomaly=False, anomaly_score=0.0, severity="none")
                for i in range(n)
            ]

        features = compute_features(transactions)
        X = features[FEATURE_COLUMNS]

        raw_predictions = self._pipeline.predict(X)  # -1 = anomaly, 1 = normal
        # sklearn's score_samples: higher = more normal. Flip so higher = more
        # unusual, then min-max normalize to a 0..1 "anomaly score" per batch.
        raw_scores = -self._pipeline.score_samples(X)
        lo, hi = raw_scores.min(), raw_scores.max()
        normalized = (raw_scores - lo) / (hi - lo) if hi > lo else np.zeros_like(raw_scores)

        results = []
        for i in range(n):
            is_anomaly = bool(raw_predictions[i] == -1)
            score = float(normalized[i])
            severity = self._severity(score, is_anomaly)
            reasons = self._explain(features.iloc[i], transactions.iloc[i]) if is_anomaly else []
            results.append(
                AnomalyResult(
                    index=i, is_anomaly=is_anomaly, anomaly_score=score, severity=severity, reasons=reasons
                )
            )
        return results

    @staticmethod
    def _severity(score: float, is_anomaly: bool) -> str:
        if not is_anomaly:
            return "none"
        if score >= SEVERITY_HIGH:
            return "high"
        if score >= SEVERITY_MEDIUM:
            return "medium"
        return "low"

    @staticmethod
    def _explain(feature_row: pd.Series, transaction_row: pd.Series) -> list[str]:
        reasons: list[str] = []
        merchant = transaction_row.get("merchant") or "this merchant"
        category = transaction_row.get("category") or "this category"

        if feature_row["is_new_merchant"] == 1:
            reasons.append("This merchant has not appeared in your transaction history before.")
        if feature_row["merchant_amount_zscore"] > ZSCORE_EXPLANATION_THRESHOLD:
            reasons.append(f"Amount is significantly higher than your typical spending with {merchant}.")
        if feature_row["category_amount_zscore"] > ZSCORE_EXPLANATION_THRESHOLD:
            reasons.append(f"Amount is significantly higher than your usual spending in the {category} category.")
        if not reasons:
            reasons.append("This transaction doesn't match your usual spending pattern.")
        return reasons[:3]
