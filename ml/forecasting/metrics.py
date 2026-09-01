"""Time-series forecast evaluation metrics: MAE, RMSE, MAPE.

Shared by ml.forecasting.train (candidate comparison) and
ml.forecasting.evaluate (standalone re-evaluation of a saved version).
"""

import numpy as np


def mae(y_true: list[float], y_pred: list[float]) -> float:
    return float(np.mean(np.abs(np.array(y_true) - np.array(y_pred))))


def rmse(y_true: list[float], y_pred: list[float]) -> float:
    return float(np.sqrt(np.mean((np.array(y_true) - np.array(y_pred)) ** 2)))


def mape(y_true: list[float], y_pred: list[float]) -> float:
    """Mean Absolute Percentage Error. Days with zero actual spend are
    excluded from the denominator (a %-error against zero is undefined),
    matching standard practice for sparse daily spending data.
    """
    y_true_arr = np.array(y_true)
    y_pred_arr = np.array(y_pred)
    mask = y_true_arr != 0
    if not mask.any():
        return 0.0
    errors = np.abs((y_true_arr[mask] - y_pred_arr[mask]) / y_true_arr[mask])
    return float(np.mean(errors) * 100)


def evaluate_forecast(y_true: list[float], y_pred: list[float]) -> dict:
    return {"mae": mae(y_true, y_pred), "rmse": rmse(y_true, y_pred), "mape": mape(y_true, y_pred)}
