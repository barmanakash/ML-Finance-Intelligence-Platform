"""End-to-end anomaly-detection tests: dataset -> train -> registry -> detect.

Uses a small synthetic dataset (fewer users/transactions than the real
generator, for test speed) with the same generation logic and a
monkeypatched MODELS_DIR so nothing here touches the real models/ directory
or MLflow run history.
"""

from datetime import datetime, timedelta

import pandas as pd
import pytest

from ml.anomaly_detection import predict as predict_module
from ml.anomaly_detection.train import MODEL_NAME, train
from ml.common import config as ml_config
from ml.registry import model_registry


@pytest.fixture()
def tmp_models_dir(tmp_path, monkeypatch):
    models_dir = tmp_path / "models"
    monkeypatch.setattr(ml_config, "MODELS_DIR", models_dir)
    return models_dir


@pytest.fixture()
def small_anomaly_dataset(tmp_path):
    rows = []
    merchant_base = {("SWIGGY", "Food"): 400, ("UBER", "Transportation"): 200}
    for user_idx in range(4):
        user_id = f"user-{user_idx}"
        current_date = datetime(2026, 1, 1)
        for i in range(60):
            current_date += timedelta(days=1)
            is_anomaly = i in (55, 58)  # deterministic injected anomalies near the end
            if is_anomaly:
                merchant, category = "SWIGGY", "Food"
                amount = 400 * 10
            else:
                merchant, category = ("SWIGGY", "Food") if i % 2 == 0 else ("UBER", "Transportation")
                base = merchant_base[(merchant, category)]
                amount = base + (i % 5) * 2
            rows.append(
                {
                    "user_id": user_id,
                    "date": current_date.strftime("%Y-%m-%d"),
                    "description": merchant,
                    "merchant": merchant,
                    "category": category,
                    "amount": amount,
                    "is_injected_anomaly": int(is_anomaly),
                }
            )
    df = pd.DataFrame(rows)
    path = tmp_path / "anomaly_dataset.csv"
    df.to_csv(path, index=False)
    return path


def _make_history(n: int, base_amount: float = 400.0, merchant: str = "SWIGGY", category: str = "Food") -> list[dict]:
    start = datetime(2026, 1, 1)
    return [
        {
            "amount": base_amount + (i % 5),
            "transaction_date": start + timedelta(days=i),
            "category": category,
            "merchant": merchant,
        }
        for i in range(n)
    ]


def test_train_produces_valid_metrics_and_promotes_first_version(tmp_models_dir, small_anomaly_dataset):
    summary = train(small_anomaly_dataset)

    assert summary["promoted"] is True
    assert summary["version"] == 1
    for key in ("precision", "recall", "f1", "flagged_rate", "injected_rate"):
        assert key in summary["metrics"]
        assert 0.0 <= summary["metrics"][key] <= 1.0
    assert model_registry.get_active_version(MODEL_NAME) == 1


def test_detector_returns_none_below_minimum_history(tmp_models_dir, small_anomaly_dataset):
    train(small_anomaly_dataset)
    detector = predict_module.AnomalyDetector()
    assert detector.is_ready

    short_history = _make_history(predict_module.MIN_TRANSACTIONS_FOR_DETECTION - 1)
    assert detector.detect(short_history) is None


def test_detector_scores_full_history_and_preserves_order(tmp_models_dir, small_anomaly_dataset):
    train(small_anomaly_dataset)
    detector = predict_module.AnomalyDetector()
    assert detector.active_version == 1

    history = _make_history(30)
    # Inject one obvious anomaly: a brand-new merchant with a huge amount.
    history.append(
        {
            "amount": 50000,
            "transaction_date": datetime(2026, 3, 1),
            "category": "Shopping",
            "merchant": "LUXURY WATCH BOUTIQUE",
        }
    )

    results = detector.detect(history)
    assert results is not None
    assert len(results) == len(history)  # order preserved, one result per input row

    flagged = results[-1]  # the injected anomaly is the last element we appended
    assert flagged.is_anomaly is True
    assert 0.0 <= flagged.anomaly_score <= 1.0
    assert flagged.reason is not None
    assert "has not appeared" in flagged.reason

    for result in results[:-1]:
        assert isinstance(result.is_anomaly, bool)
        assert 0.0 <= result.anomaly_score <= 1.0


def test_detector_gracefully_reports_not_ready_when_no_model_trained(tmp_models_dir):
    detector = predict_module.AnomalyDetector()
    assert not detector.is_ready
    assert detector.detect(_make_history(20)) is None
