"""Unit tests for the forecasting baseline methods and metrics — pure
functions, no registry/DB involved.
"""

from ml.forecasting.methods import (
    forecast_exponential_smoothing,
    forecast_historical_average,
    forecast_linear_regression,
    forecast_moving_average,
)
from ml.forecasting.metrics import evaluate_forecast, mae, mape, rmse


def test_historical_average_is_flat_and_matches_mean():
    history = [100.0, 200.0, 300.0]
    predictions = forecast_historical_average(history, horizon_days=5)
    assert len(predictions) == 5
    assert all(p == 200.0 for p in predictions)


def test_moving_average_uses_only_recent_window():
    history = [0.0, 0.0, 0.0, 0.0, 100.0, 100.0]
    predictions = forecast_moving_average(history, horizon_days=3, window=2)
    assert all(p == 100.0 for p in predictions)


def test_exponential_smoothing_is_between_min_and_max_history():
    history = [100.0, 200.0, 100.0, 200.0, 100.0]
    predictions = forecast_exponential_smoothing(history, horizon_days=3, alpha=0.3)
    assert all(min(history) <= p <= max(history) for p in predictions)


def test_linear_regression_extrapolates_upward_trend():
    history = [10.0 * i for i in range(10)]  # perfectly linear, slope 10
    predictions = forecast_linear_regression(history, horizon_days=3)
    assert predictions[0] > history[-1]
    assert predictions[1] > predictions[0]
    assert predictions[2] > predictions[1]


def test_linear_regression_never_predicts_negative():
    history = [100.0, 50.0, 0.0, 0.0, 0.0]  # steep downward trend
    predictions = forecast_linear_regression(history, horizon_days=10)
    assert all(p >= 0.0 for p in predictions)


def test_forecast_with_too_little_history_falls_back_gracefully():
    assert forecast_linear_regression([50.0], horizon_days=3) == [50.0, 50.0, 50.0]
    assert forecast_linear_regression([], horizon_days=3) == [0.0, 0.0, 0.0]


def test_metrics_are_zero_for_perfect_predictions():
    actual = [10.0, 20.0, 30.0]
    metrics = evaluate_forecast(actual, actual)
    assert metrics["mae"] == 0.0
    assert metrics["rmse"] == 0.0
    assert metrics["mape"] == 0.0


def test_mae_and_rmse_penalize_errors():
    actual = [10.0, 20.0, 30.0]
    predicted = [12.0, 18.0, 33.0]
    assert mae(actual, predicted) > 0
    assert rmse(actual, predicted) >= mae(actual, predicted)


def test_mape_ignores_zero_actual_days():
    actual = [0.0, 100.0]
    predicted = [50.0, 90.0]
    # Only the second day (actual=100) should count toward MAPE.
    assert mape(actual, predicted) == 10.0
