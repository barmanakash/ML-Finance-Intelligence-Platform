"""End-to-end anomaly-detection tests: dataset -> train -> registry -> predict.

Uses a tiny synthetic per-user dataset and a monkeypatched MODELS_DIR so
nothing here touches the real models/ directory or MLflow run history.
"""

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
def tiny_anomaly_dataset(tmp_path):
    rows = []
    # Three synthetic users, each with a routine pattern plus one obvious
    # outlier (a rare merchant with a much larger amount).
    for u in range(3):
        user_id = f"user-{u}"
        for i in range(20):
            rows.append(
                {
                    "user_id": user_id,
                    "transaction_date": f"2026-01-{(i % 28) + 1:02d}",
                    "category": "Food",
                    "merchant": "SWIGGY",
                    "amount": 300 + (i % 5) * 10,
                    "is_synthetic_anomaly": 0,
                }
            )
        rows.append(
            {
                "user_id": user_id,
                "transaction_date": "2026-01-15",
                "category": "Other",
                "merchant": "RARE LUXURY STORE",
                "amount": 50000,
                "is_synthetic_anomaly": 1,
            }
        )
    df = pd.DataFrame(rows)
    path = tmp_path / "dataset.csv"
    df.to_csv(path, index=False)
    return path


def test_train_produces_valid_metrics_and_promotes_first_version(tmp_models_dir, tiny_anomaly_dataset):
    summary = train(tiny_anomaly_dataset)

    assert summary["promoted"] is True
    assert summary["version"] == 1
    assert 0.0 <= summary["metrics"]["predicted_anomaly_rate"] <= 1.0
    assert 0.0 <= summary["metrics"]["precision"] <= 1.0
    assert 0.0 <= summary["metrics"]["recall"] <= 1.0
    assert model_registry.get_active_version(MODEL_NAME) == 1


def test_trained_model_flags_obvious_outlier(tmp_models_dir, tiny_anomaly_dataset):
    train(tiny_anomaly_dataset)

    detector = predict_module.AnomalyDetector()
    assert detector.is_ready
    assert detector.active_version == 1

    history = pd.DataFrame(
        [
            {"amount": 300, "category": "Food", "merchant": "SWIGGY", "transaction_date": "2026-01-01"},
            {"amount": 310, "category": "Food", "merchant": "SWIGGY", "transaction_date": "2026-01-05"},
            {"amount": 290, "category": "Food", "merchant": "SWIGGY", "transaction_date": "2026-01-10"},
            {"amount": 320, "category": "Food", "merchant": "SWIGGY", "transaction_date": "2026-01-12"},
            {"amount": 60000, "category": "Other", "merchant": "BRAND NEW RARE STORE", "transaction_date": "2026-01-20"},
        ]
    )
    results = detector.score_transactions(history)

    assert len(results) == 5
    for r in results:
        assert 0.0 <= r.anomaly_score <= 1.0
        assert r.severity in {"none", "low", "medium", "high"}

    # The obvious outlier (new merchant, huge amount) must be flagged with
    # a non-empty, deterministic explanation.
    outlier = results[-1]
    assert outlier.is_anomaly is True
    assert outlier.severity in {"medium", "high"}
    assert len(outlier.reasons) > 0
    assert any("merchant" in reason.lower() for reason in outlier.reasons)


def test_worse_retrain_is_not_promoted(tmp_models_dir, tiny_anomaly_dataset, monkeypatch):
    train(tiny_anomaly_dataset)
    first_active = model_registry.get_active_version(MODEL_NAME)
    assert first_active == 1

    monkeypatch.setattr(model_registry, "maybe_promote", lambda *a, **k: False)
    summary = train(tiny_anomaly_dataset)
    assert summary["promoted"] is False
    assert model_registry.get_active_version(MODEL_NAME) == first_active


def test_detector_gracefully_reports_not_ready_when_no_model_trained(tmp_models_dir):
    detector = predict_module.AnomalyDetector()
    assert not detector.is_ready
    assert detector.active_version is None

    history = pd.DataFrame(
        [{"amount": 100, "category": "Food", "merchant": "SWIGGY", "transaction_date": "2026-01-01"}]
    )
    results = detector.score_transactions(history)
    assert results[0].is_anomaly is False
    assert results[0].anomaly_score == 0.0
    assert results[0].severity == "none"


def test_score_transactions_handles_empty_history(tmp_models_dir, tiny_anomaly_dataset):
    train(tiny_anomaly_dataset)
    detector = predict_module.AnomalyDetector()
    results = detector.score_transactions(pd.DataFrame(columns=["amount", "category", "merchant", "transaction_date"]))
    assert results == []
