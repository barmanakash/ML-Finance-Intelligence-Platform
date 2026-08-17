"""Unsupervised anomaly scoring for a user's transaction history.

Unlike categorization, there is no persisted global model here: what counts
as anomalous is relative to *this user's* own spending history (master
prompt Rule 12), so the IsolationForest is fit fresh on each call against
the transactions passed in, rather than loaded from a registry. This is
cheap at the transaction volumes a personal-finance app deals with
(hundreds to low thousands of rows) and avoids the much harder problem of
a single global model generalizing across everyone's very different
spending patterns.

No training logic lives here in the persisted-artifact sense — see
ml/anomaly_detection/train.py for why that script is a documented no-op,
and ml/anomaly_detection/evaluate.py for how this pipeline's *mechanics*
(not real-world accuracy) are sanity-checked.
"""

from dataclasses import dataclass

import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

from ml.features.anomaly_features import FEATURE_COLUMNS, build_features

# IsolationForest needs a reasonable amount of history to fit a meaningful
# model; below this, every transaction is "unusual" simply because there's
# no pattern yet to compare against.
MIN_TRANSACTIONS_FOR_DETECTION = 10


@dataclass
class AnomalyResult:
    index: int
    anomaly_score: float  # 0..1, higher = more anomalous
    is_anomaly: bool
    reason: str


class AnomalyDetector:
    def __init__(self, contamination: float = 0.05, random_state: int = 42) -> None:
        self.contamination = contamination
        self.random_state = random_state

    def detect(self, transactions: list[dict]) -> list[AnomalyResult] | None:
        """Returns None if there isn't enough history for a meaningful fit
        (see MIN_TRANSACTIONS_FOR_DETECTION) — callers should treat that as
        "insufficient data", not an error.
        """
        if len(transactions) < MIN_TRANSACTIONS_FOR_DETECTION:
            return None

        df = build_features(transactions)
        X = df[FEATURE_COLUMNS].to_numpy()
        X_scaled = StandardScaler().fit_transform(X)

        model = IsolationForest(contamination=self.contamination, random_state=self.random_state)
        predictions = model.fit_predict(X_scaled)  # -1 = anomaly, 1 = normal
        raw_scores = model.decision_function(X_scaled)  # higher = more normal

        score_min, score_max = raw_scores.min(), raw_scores.max()
        span = score_max - score_min
        normalized = (
            (score_max - raw_scores) / span if span > 0 else np.zeros_like(raw_scores)
        )

        results = []
        for i in range(len(df)):
            row = df.iloc[i]
            is_anomaly = bool(predictions[i] == -1)
            score = float(normalized[i])
            reason = self._explain(row) if is_anomaly else ""
            results.append(
                AnomalyResult(index=i, anomaly_score=score, is_anomaly=is_anomaly, reason=reason)
            )
        return results

    @staticmethod
    def _explain(row) -> str:
        """Deterministic, feature-level explanation — not an external AI
        call (master prompt Rule 13). Picks whichever single factor
        deviates most, rather than dumping every signal on the user.
        """
        candidates: list[tuple[float, str]] = []

        if row["amount_zscore_category"] >= 2:
            candidates.append(
                (
                    abs(row["amount_zscore_category"]),
                    f"Amount ({row['amount']:.2f}) is well above your usual spending "
                    f"in the '{row['category']}' category.",
                )
            )
        if row["amount_zscore_merchant"] >= 2:
            candidates.append(
                (
                    abs(row["amount_zscore_merchant"]),
                    f"This transaction is significantly higher than your typical "
                    f"amount for this merchant.",
                )
            )
        if row["is_new_merchant"]:
            candidates.append(
                (1.5, "This merchant has not appeared in your transaction history before.")
            )

        if not candidates:
            return "This transaction differs from your typical spending pattern."

        candidates.sort(key=lambda c: c[0], reverse=True)
        return candidates[0][1]
