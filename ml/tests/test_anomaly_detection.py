from datetime import datetime, timedelta

from ml.anomaly_detection.predict import MIN_TRANSACTIONS_FOR_DETECTION, AnomalyDetector


def _normal_history(n: int = 20):
    base = datetime(2026, 1, 1)
    transactions = []
    for i in range(n):
        transactions.append(
            {
                "amount": 400 + (i % 5) * 20,
                "transaction_date": base + timedelta(days=i),
                "category": "Food",
                "merchant": "SWIGGY",
                "description": "SWIGGY ORDER",
            }
        )
    return transactions


def test_returns_none_below_minimum_transaction_count():
    detector = AnomalyDetector()
    few = _normal_history(MIN_TRANSACTIONS_FOR_DETECTION - 1)
    assert detector.detect(few) is None


def test_detects_an_injected_amount_spike():
    transactions = _normal_history(25)
    transactions.append(
        {
            "amount": 50000,  # wildly outside the ~400-480 normal range
            "transaction_date": datetime(2026, 2, 1),
            "category": "Food",
            "merchant": "SWIGGY",
            "description": "SWIGGY ORDER",
        }
    )
    detector = AnomalyDetector(contamination=0.1)
    results = detector.detect(transactions)
    assert results is not None
    assert len(results) == len(transactions)

    spike_result = results[-1]
    assert spike_result.is_anomaly is True
    assert 0.0 <= spike_result.anomaly_score <= 1.0
    assert spike_result.reason != ""


def test_normal_transactions_mostly_not_flagged():
    transactions = _normal_history(30)
    detector = AnomalyDetector(contamination=0.05)
    results = detector.detect(transactions)
    assert results is not None
    flagged = [r for r in results if r.is_anomaly]
    # contamination=0.05 on 30 uniform-pattern rows should flag only a
    # small minority, not the majority.
    assert len(flagged) < len(transactions) / 2


def test_non_anomalous_results_have_empty_reason():
    transactions = _normal_history(20)
    detector = AnomalyDetector(contamination=0.05)
    results = detector.detect(transactions)
    assert results is not None
    for r in results:
        if not r.is_anomaly:
            assert r.reason == ""
