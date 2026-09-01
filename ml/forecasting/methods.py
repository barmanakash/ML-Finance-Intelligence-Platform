"""Forecasting baseline methods, shared identically by
ml.forecasting.train (candidate comparison) and ml.forecasting.predict
(serving) so there's no train/serve skew — mirrors the pattern used for
anomaly-detection features (ml.features.transaction_features).

Master-prompt Rule 15: "Start with simple strong baselines... Only
introduce more complex models if they actually improve evaluation." All
four methods here are classical, deterministic, and require no external
ML API. `train.py` compares them on held-out data and the winner (plus its
best hyperparameter) is what `predict.py` actually serves.

Every `forecast_*` function takes a chronologically-ordered list of daily
totals (`history`, one float per calendar day — callers must have already
filled any gap days with 0.0, see ml.forecasting.predict) and a number of
future days to predict, and returns a list of that length. Forecasts are
always non-negative, since a "predicted spend" below zero is meaningless.
"""

import numpy as np


def forecast_historical_average(history: list[float], horizon_days: int) -> list[float]:
    """Flat forecast at the all-time mean daily spend."""
    mean = float(np.mean(history)) if history else 0.0
    return [max(0.0, mean)] * horizon_days


def forecast_moving_average(history: list[float], horizon_days: int, window: int) -> list[float]:
    """Flat forecast at the mean of the most recent `window` days."""
    window = min(window, len(history)) or 1
    recent = history[-window:]
    mean = float(np.mean(recent)) if recent else 0.0
    return [max(0.0, mean)] * horizon_days


def forecast_exponential_smoothing(
    history: list[float], horizon_days: int, alpha: float
) -> list[float]:
    """Simple (non-trend, non-seasonal) exponential smoothing. The
    smoothed level after the last observed day is used as a flat forecast
    for every future day — the classical SES assumption.
    """
    if not history:
        return [0.0] * horizon_days
    level = history[0]
    for value in history[1:]:
        level = alpha * value + (1 - alpha) * level
    return [max(0.0, float(level))] * horizon_days


def forecast_linear_regression(history: list[float], horizon_days: int) -> list[float]:
    """Ordinary least squares on (day_index -> amount), extrapolated
    forward. Captures a trend that the flat methods above cannot, at the
    cost of being able to extrapolate an unrealistic trend if the history
    is short or noisy — this is exactly why train.py evaluates it
    against the flat baselines rather than assuming it's always better.
    """
    n = len(history)
    if n < 2:
        return forecast_historical_average(history, horizon_days)

    x = np.arange(n, dtype=float)
    y = np.array(history, dtype=float)
    slope, intercept = np.polyfit(x, y, 1)

    future_x = np.arange(n, n + horizon_days, dtype=float)
    predictions = slope * future_x + intercept
    return [max(0.0, float(p)) for p in predictions]


METHODS = {
    "historical_average": lambda history, horizon, params: forecast_historical_average(
        history, horizon
    ),
    "moving_average": lambda history, horizon, params: forecast_moving_average(
        history, horizon, params.get("window", 7)
    ),
    "exponential_smoothing": lambda history, horizon, params: forecast_exponential_smoothing(
        history, horizon, params.get("alpha", 0.3)
    ),
    "linear_regression": lambda history, horizon, params: forecast_linear_regression(
        history, horizon
    ),
}


def forecast(method: str, history: list[float], horizon_days: int, params: dict) -> list[float]:
    if method not in METHODS:
        raise ValueError(f"Unknown forecasting method: {method}")
    return METHODS[method](history, horizon_days, params)
