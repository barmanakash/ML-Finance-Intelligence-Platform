"""Feature engineering for unsupervised anomaly detection.

Features are computed relative to the *user's own transaction history*
passed in — there is no global/pretrained scaling, since what counts as
"unusual" is inherently user-specific (master-prompt Rule 12): a ₹5,000
transaction might be ordinary for one user and wildly out of pattern for
another.
"""

import numpy as np
import pandas as pd

FEATURE_COLUMNS = [
    "log_amount",
    "day_of_week",
    "day_of_month",
    "is_new_merchant",
    "merchant_frequency",
    "category_frequency",
    "amount_zscore_category",
    "amount_zscore_merchant",
]


def build_features(transactions: list[dict]) -> pd.DataFrame:
    """`transactions` is a list of dicts with at least: amount (float),
    transaction_date (datetime-like), category (str), merchant (str | None),
    description (str).

    Returns a DataFrame with one row per input transaction (same order),
    containing the numeric FEATURE_COLUMNS plus the original fields needed
    to build human-readable explanations later.
    """
    df = pd.DataFrame(transactions).copy()
    df["merchant_key"] = df["merchant"].fillna(df["description"])
    df["log_amount"] = np.log1p(df["amount"].abs())

    dates = pd.to_datetime(df["transaction_date"])
    df["day_of_week"] = dates.dt.dayofweek
    df["day_of_month"] = dates.dt.day

    merchant_counts = df["merchant_key"].value_counts()
    df["merchant_frequency"] = df["merchant_key"].map(merchant_counts)
    df["is_new_merchant"] = (df["merchant_frequency"] == 1).astype(int)

    category_counts = df["category"].value_counts()
    df["category_frequency"] = df["category"].map(category_counts)

    category_stats = df.groupby("category")["amount"].agg(["mean", "std"])
    merchant_stats = df.groupby("merchant_key")["amount"].agg(["mean", "std"])

    df["amount_zscore_category"] = _zscores(df, category_stats, "category")
    df["amount_zscore_merchant"] = _zscores(df, merchant_stats, "merchant_key")

    return df


def _zscores(df: pd.DataFrame, stats: pd.DataFrame, key_col: str) -> pd.Series:
    means = df[key_col].map(stats["mean"])
    stds = df[key_col].map(stats["std"]).fillna(0)
    # A group with only one member (or zero variance) has std=0/NaN — there's
    # no meaningful deviation to compute, so those rows get a neutral 0
    # rather than a division error or an inflated score.
    safe_stds = stds.replace(0, np.nan)
    z = (df["amount"] - means) / safe_stds
    return z.fillna(0.0)
