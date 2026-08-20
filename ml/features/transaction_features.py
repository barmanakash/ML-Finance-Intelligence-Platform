"""Feature engineering for anomaly detection.

Every feature is computed relative to a user's own transaction history up
to (but not including) the transaction being scored — this avoids leaking
future information into the baseline (see master-prompt Rule 54: "avoid
leaking future transaction information into historical baselines").

The same `compute_features` function is used at training time (via
ml.anomaly_detection.train, walking each synthetic user's history
chronologically with an expanding window) and at serving time (via
ml.anomaly_detection.predict, using a user's actual prior transactions from
MongoDB), so there's no train/serve skew.
"""

import math
from dataclasses import dataclass
from datetime import date, datetime

FEATURE_NAMES = [
    "log_amount",
    "category_zscore",
    "merchant_zscore",
    "is_new_merchant",
    "day_of_week",
    "is_weekend",
]


@dataclass
class TransactionFeatures:
    log_amount: float
    category_zscore: float
    merchant_zscore: float
    is_new_merchant: float
    day_of_week: float
    is_weekend: float

    def as_vector(self) -> list[float]:
        return [
            self.log_amount,
            self.category_zscore,
            self.merchant_zscore,
            self.is_new_merchant,
            self.day_of_week,
            self.is_weekend,
        ]


def _mean_std(values: list[float]) -> tuple[float, float]:
    if not values:
        return 0.0, 0.0
    mean = sum(values) / len(values)
    if len(values) < 2:
        return mean, 0.0
    variance = sum((v - mean) ** 2 for v in values) / (len(values) - 1)
    return mean, math.sqrt(variance)


def compute_features(
    amount: float,
    category: str,
    merchant: str | None,
    transaction_date: date | datetime,
    prior_transactions: list[dict],
) -> TransactionFeatures:
    """`prior_transactions` must be the user's transaction history strictly
    *before* `transaction_date` — each dict needs 'amount', 'category', and
    'merchant' keys. All baselines (means, stds, "known merchants") are
    computed only from this history, never from the transaction itself or
    anything after it.
    """
    log_amount = math.log1p(max(amount, 0))

    category_amounts = [t["amount"] for t in prior_transactions if t.get("category") == category]
    cat_mean, cat_std = _mean_std(category_amounts)
    category_zscore = (amount - cat_mean) / cat_std if cat_std > 0 else 0.0

    merchant_amounts = [
        t["amount"] for t in prior_transactions if merchant and t.get("merchant") == merchant
    ]
    merch_mean, merch_std = _mean_std(merchant_amounts)
    merchant_zscore = (amount - merch_mean) / merch_std if merch_std > 0 else 0.0

    known_merchants = {t.get("merchant") for t in prior_transactions if t.get("merchant")}
    is_new_merchant = 1.0 if (merchant and merchant not in known_merchants) else 0.0

    day_of_week = float(transaction_date.weekday())
    is_weekend = 1.0 if transaction_date.weekday() >= 5 else 0.0

    return TransactionFeatures(
        log_amount=log_amount,
        category_zscore=category_zscore,
        merchant_zscore=merchant_zscore,
        is_new_merchant=is_new_merchant,
        day_of_week=day_of_week,
        is_weekend=is_weekend,
    )
