import pandas as pd

from ml.features.anomaly_features import FEATURE_COLUMNS, build_features


def _sample_transactions():
    return [
        {"amount": 400, "transaction_date": "2026-01-01", "category": "Food", "merchant": "SWIGGY", "description": "SWIGGY ORDER"},
        {"amount": 420, "transaction_date": "2026-01-05", "category": "Food", "merchant": "SWIGGY", "description": "SWIGGY ORDER"},
        {"amount": 450, "transaction_date": "2026-01-10", "category": "Food", "merchant": "ZOMATO", "description": "ZOMATO DELIVERY"},
        {"amount": 15000, "transaction_date": "2026-01-15", "category": "Food", "merchant": "SWIGGY", "description": "SWIGGY ORDER"},
        {"amount": 900, "transaction_date": "2026-01-20", "category": "Groceries", "merchant": "BIGBASKET", "description": "BIGBASKET"},
        {"amount": 5000, "transaction_date": "2026-01-25", "category": "Other", "merchant": None, "description": "UNKNOWN MERCHANT PAYMENT"},
    ]


def test_build_features_returns_all_columns():
    df = build_features(_sample_transactions())
    for col in FEATURE_COLUMNS:
        assert col in df.columns
    assert len(df) == 6


def test_new_merchant_flagged_correctly():
    df = build_features(_sample_transactions())
    # ZOMATO and the None-merchant row each appear exactly once.
    zomato_row = df[df["merchant_key"] == "ZOMATO"].iloc[0]
    swiggy_row = df[df["merchant_key"] == "SWIGGY"].iloc[0]
    assert zomato_row["is_new_merchant"] == 1
    assert swiggy_row["is_new_merchant"] == 0  # SWIGGY appears 3 times


def test_amount_zscore_flags_the_outlier():
    df = build_features(_sample_transactions())
    outlier_row = df[df["amount"] == 15000].iloc[0]
    normal_row = df[df["amount"] == 400].iloc[0]
    assert outlier_row["amount_zscore_category"] > normal_row["amount_zscore_category"]
    assert outlier_row["amount_zscore_category"] > 1.0


def test_single_occurrence_group_gets_neutral_zscore():
    # A category/merchant with only one transaction has no variance to
    # compute a meaningful deviation from — should be 0, not NaN or inf.
    df = build_features(_sample_transactions())
    other_row = df[df["category"] == "Other"].iloc[0]
    assert other_row["amount_zscore_category"] == 0.0
    assert not pd.isna(other_row["amount_zscore_category"])
