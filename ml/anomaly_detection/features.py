"""Feature engineering for the anomaly detector.

Features are computed relative to a user's own transaction history so the
model measures "unusual for this person," not an absolute currency
threshold — the same ₹5,000 transaction can be routine for one person and
a 10x outlier for another. This means `compute_features` must always be
called with a user's *complete* transaction history (not a single batch),
or the merchant/category statistics it computes will be wrong.

Used identically by ml.anomaly_detection.train (on synthetic per-user
histories) and ml.anomaly_detection.predict (on a real user's history via
the backend), so there's no train/serve skew.
"""

import numpy as np
import pandas as pd

FEATURE_COLUMNS = [
    "log_amount",
    "category_amount_zscore",
    "merchant_amount_zscore",
    "merchant_frequency_ratio",
    "category_frequency_ratio",
    "is_new_merchant",
    "day_of_week",
    "day_of_month",
]


def compute_features(transactions: pd.DataFrame) -> pd.DataFrame:
    """`transactions` needs columns: amount, category, merchant, transaction_date.

    Returns a DataFrame with FEATURE_COLUMNS, one row per input row, in the
    same order as the input (safe to zip back against the original rows).
    """
    df = transactions.reset_index(drop=True).copy()
    df["merchant"] = df["merchant"].fillna("UNKNOWN_MERCHANT")
    df["amount"] = df["amount"].astype(float)
    df["transaction_date"] = pd.to_datetime(df["transaction_date"])

    df["log_amount"] = np.log1p(df["amount"])

    category_stats = df.groupby("category")["amount"].agg(["mean", "std", "count"])
    merchant_stats = df.groupby("merchant")["amount"].agg(["mean", "std", "count"])

    df["category_amount_zscore"] = _zscore(df, category_stats, "category")
    df["merchant_amount_zscore"] = _zscore(df, merchant_stats, "merchant")

    total = len(df)
    merchant_counts = df["merchant"].map(merchant_stats["count"])
    category_counts = df["category"].map(category_stats["count"])
    df["merchant_frequency_ratio"] = merchant_counts / total
    df["category_frequency_ratio"] = category_counts / total
    df["is_new_merchant"] = (merchant_counts <= 1).astype(int)

    df["day_of_week"] = df["transaction_date"].dt.dayofweek
    df["day_of_month"] = df["transaction_date"].dt.day

    return df[FEATURE_COLUMNS]


def _zscore(df: pd.DataFrame, stats: pd.DataFrame, key: str) -> pd.Series:
    means = df[key].map(stats["mean"])
    stds = df[key].map(stats["std"])
    counts = df[key].map(stats["count"])
    # A single occurrence has no meaningful std (NaN); fall back to 1.0 so
    # the raw deviation still contributes signal instead of dividing by zero.
    safe_stds = stds.where((counts > 1) & (stds > 0), other=1.0)
    return (df["amount"] - means) / safe_stds
