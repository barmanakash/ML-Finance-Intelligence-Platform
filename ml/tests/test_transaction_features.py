from datetime import datetime

from ml.features.transaction_features import compute_features


def test_no_history_gives_zero_zscores():
    features = compute_features(
        amount=500, category="Food", merchant="SWIGGY",
        transaction_date=datetime(2026, 1, 5), prior_transactions=[],
    )
    assert features.category_zscore == 0.0
    assert features.merchant_zscore == 0.0
    assert features.is_new_merchant == 1.0  # no prior merchants seen at all


def test_known_merchant_is_not_flagged_as_new():
    prior = [{"amount": 400, "category": "Food", "merchant": "SWIGGY"}]
    features = compute_features(
        amount=450, category="Food", merchant="SWIGGY",
        transaction_date=datetime(2026, 1, 5), prior_transactions=prior,
    )
    assert features.is_new_merchant == 0.0


def test_large_spike_produces_high_zscore():
    prior = [{"amount": 400 + i, "category": "Food", "merchant": "SWIGGY"} for i in range(-5, 6)]
    features = compute_features(
        amount=5000, category="Food", merchant="SWIGGY",
        transaction_date=datetime(2026, 1, 5), prior_transactions=prior,
    )
    assert features.category_zscore > 5
    assert features.merchant_zscore > 5


def test_weekday_flags():
    monday = datetime(2026, 1, 5)  # a Monday
    saturday = datetime(2026, 1, 10)
    weekday_features = compute_features(100, "Food", "X", monday, [])
    weekend_features = compute_features(100, "Food", "X", saturday, [])
    assert weekday_features.is_weekend == 0.0
    assert weekend_features.is_weekend == 1.0


def test_feature_vector_length_matches_names():
    from ml.features.transaction_features import FEATURE_NAMES

    features = compute_features(100, "Food", "X", datetime(2026, 1, 5), [])
    assert len(features.as_vector()) == len(FEATURE_NAMES)
