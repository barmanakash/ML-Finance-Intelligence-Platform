"""End-to-end forecasting tests: dataset -> train -> registry -> predict.

Uses a small synthetic multi-user daily-spend dataset and a monkeypatched
MODELS_DIR so nothing here touches the real models/ directory or MLflow
run history.
"""

from datetime import date, timedelta

import pandas as pd
import pytest

from ml.common import config as ml_config
from ml.forecasting import predict as predict_module
from ml.forecasting.train import MODEL_NAME, train
from ml.registry import model_registry


@pytest.fixture()
def tmp_models_dir(tmp_path, monkeypatch):
    models_dir = tmp_path / "models"
    monkeypatch.setattr(ml_config, "MODELS_DIR", models_dir)
    return models_dir


@pytest.fixture()
def tiny_forecast_dataset(tmp_path):
    rows = []
    start = date(2025, 1, 1)
    for user_idx in range(3):
        user_id = f"user-{user_idx}"
        for day_offset in range(60):
            current_date = start + timedelta(days=day_offset)
            amount = 100.0 + (5.0 if current_date.weekday() >= 5 else 0.0)
            rows.append({"user_id": user_id, "date": current_date.isoformat(), "daily_amount": amount})
    df = pd.DataFrame(rows)
    path = tmp_path / "forecast_dataset.csv"
    df.to_csv(path, index=False)
    return path


def test_train_selects_a_candidate_and_promotes_first_version(tmp_models_dir, tiny_forecast_dataset):
    summary = train(tiny_forecast_dataset)

    assert summary["promoted"] is True
    assert summary["version"] == 1
    assert summary["best_method"] in {
        "historical_average",
        "moving_average",
        "exponential_smoothing",
        "linear_regression",
    }
    assert summary["best_metrics"]["mae"] >= 0
    assert model_registry.get_active_version(MODEL_NAME) == 1


def test_forecaster_predicts_after_training(tmp_models_dir, tiny_forecast_dataset):
    train(tiny_forecast_dataset)

    forecaster = predict_module.ExpenseForecaster()
    assert forecaster.is_ready
    assert forecaster.active_version == 1

    start = date(2026, 1, 1)
    daily_totals = {start + timedelta(days=i): 100.0 for i in range(30)}

    result = forecaster.forecast(daily_totals, horizon_days=7)
    assert result is not None
    assert len(result.daily_predictions) == 7
    assert result.predicted_total == round(sum(result.daily_predictions), 2)
    assert result.start_date == max(daily_totals) + timedelta(days=1)
    assert result.end_date == max(daily_totals) + timedelta(days=7)


def test_forecaster_returns_none_below_minimum_history(tmp_models_dir, tiny_forecast_dataset):
    train(tiny_forecast_dataset)
    forecaster = predict_module.ExpenseForecaster()

    start = date(2026, 1, 1)
    short_history = {start + timedelta(days=i): 50.0 for i in range(5)}
    assert forecaster.forecast(short_history, horizon_days=7) is None


def test_forecaster_gracefully_reports_not_ready_when_no_model_trained(tmp_models_dir):
    forecaster = predict_module.ExpenseForecaster()
    assert not forecaster.is_ready

    start = date(2026, 1, 1)
    daily_totals = {start + timedelta(days=i): 100.0 for i in range(30)}
    assert forecaster.forecast(daily_totals, horizon_days=7) is None


def test_worse_retrain_is_not_promoted(tmp_models_dir, tiny_forecast_dataset, monkeypatch):
    train(tiny_forecast_dataset)
    first_active = model_registry.get_active_version(MODEL_NAME)
    assert first_active == 1

    monkeypatch.setattr(model_registry, "maybe_promote", lambda *a, **k: False)
    summary = train(tiny_forecast_dataset)
    assert summary["promoted"] is False
    assert model_registry.get_active_version(MODEL_NAME) == first_active
