"""Inference-only interface for the anomaly detector.

No training logic here — see ml.anomaly_detection.train. Unlike the
categorization model (Phase 4), which scores one transaction description at
a time, anomaly detection is always evaluated over a user's *complete*
transaction history at once: the model itself is a single, pre-trained,
globally-shared IsolationForest, but the *features* it scores are computed
relative to that specific user's own spending patterns (see
ml.features.transaction_features). Every call recomputes anomalies for the
user's whole history rather than incrementally scoring new transactions in
isolation — see app.services.anomaly_detection_service.

Explanations are deterministic and feature-based — never an LLM (see
master-prompt Rule 13). Only one reason is returned per flagged transaction:
the single most salient signal that fired, not every signal that could
apply.
"""

from dataclasses import dataclass

from ml.features.transaction_features import TransactionFeatures, compute_features
from ml.registry import model_registry

MODEL_NAME = "anomaly-detector"

MIN_TRANSACTIONS_FOR_DETECTION = 10


@dataclass
class AnomalyResult:
    is_anomaly: bool
    anomaly_score: float  # normalized to [0, 1] within this batch; higher = more anomalous
    reason: str | None = None


class AnomalyDetector:
    def __init__(self) -> None:
        bundle, metadata = model_registry.load_active_pipeline(MODEL_NAME)
        self._scaler = bundle["scaler"] if bundle else None
        self._model = bundle["model"] if bundle else None
        self._metadata = metadata

    @property
    def is_ready(self) -> bool:
        return self._model is not None

    @property
    def active_version(self) -> int | None:
        return (self._metadata or {}).get("version")

    def detect(self, transactions: list[dict]) -> list[AnomalyResult] | None:
        """`transactions` is a user's full transaction history — each dict
        needs 'amount', 'transaction_date', 'category', and 'merchant' keys.
        Returns results aligned to the *input* order, or None if there
        aren't enough transactions yet or no model has been trained.
        """
        if not self.is_ready:
            return None
        if len(transactions) < MIN_TRANSACTIONS_FOR_DETECTION:
            return None

        # Sort chronologically so each transaction's baseline only reflects
        # what came before it — see ml.features.transaction_features and
        # master-prompt Rule 54 (no leaking future info into baselines).
        order = sorted(range(len(transactions)), key=lambda i: transactions[i]["transaction_date"])

        feature_list: list[TransactionFeatures] = []
        vectors: list[list[float]] = []
        prior: list[dict] = []
        for i in order:
            t = transactions[i]
            features = compute_features(
                amount=t["amount"],
                category=t["category"],
                merchant=t.get("merchant"),
                transaction_date=t["transaction_date"],
                prior_transactions=prior,
            )
            feature_list.append(features)
            vectors.append(features.as_vector())
            prior.append(
                {"amount": t["amount"], "category": t["category"], "merchant": t.get("merchant")}
            )

        X = self._scaler.transform(vectors)
        raw_scores = self._model.decision_function(X)  # lower = more anomalous
        predictions = self._model.predict(X)  # -1 = anomaly, 1 = normal

        min_score, max_score = float(raw_scores.min()), float(raw_scores.max())
        spread = max_score - min_score

        results_by_original_index: dict[int, AnomalyResult] = {}
        for pos_in_order, original_index in enumerate(order):
            raw = float(raw_scores[pos_in_order])
            normalized = (max_score - raw) / spread if spread > 1e-9 else 0.0
            is_anomaly = bool(predictions[pos_in_order] == -1)
            reason = None
            if is_anomaly:
                t = transactions[original_index]
                reason = self._explain(
                    feature_list[pos_in_order],
                    t["amount"],
                    t["category"],
                    t.get("merchant"),
                    prior[:pos_in_order],
                )
            results_by_original_index[original_index] = AnomalyResult(
                is_anomaly=is_anomaly, anomaly_score=normalized, reason=reason
            )

        return [results_by_original_index[i] for i in range(len(transactions))]

    @staticmethod
    def _explain(
        features: TransactionFeatures,
        amount: float,
        category: str,
        merchant: str | None,
        prior_transactions: list[dict],
    ) -> str:
        if features.is_new_merchant:
            return "This merchant has not appeared in your transaction history before."

        if features.category_zscore >= 2.5:
            category_amounts = [
                t["amount"] for t in prior_transactions if t.get("category") == category
            ]
            if category_amounts:
                avg = sum(category_amounts) / len(category_amounts)
                if avg > 0:
                    multiple = amount / avg
                    return (
                        f"Amount is {multiple:.1f}x higher than your usual spending in the "
                        f"'{category}' category (your typical amount is about {avg:.0f})."
                    )

        if merchant and features.merchant_zscore >= 2.5:
            merchant_amounts = [
                t["amount"] for t in prior_transactions if t.get("merchant") == merchant
            ]
            if merchant_amounts:
                avg = sum(merchant_amounts) / len(merchant_amounts)
                if avg > 0:
                    return (
                        f"Your typical transaction amount for {merchant} is about {avg:.0f}; "
                        f"this transaction is {amount:.0f}."
                    )

        if features.is_weekend:
            return "This transaction occurred outside your typical spending pattern."

        return (
            "This transaction's overall pattern (amount, timing, merchant) is unusual "
            "compared to your history."
        )
