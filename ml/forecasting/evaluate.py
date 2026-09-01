"""Evaluate a saved forecaster version against a labeled daily-spend CSV.

Usage:
    python -m ml.forecasting.evaluate                 # evaluates the active version
    python -m ml.forecasting.evaluate --version 2
"""

import argparse
import json
from pathlib import Path

from ml.common.config import DATA_DIR
from ml.forecasting.methods import forecast
from ml.forecasting.metrics import evaluate_forecast
from ml.forecasting.train import HOLDOUT_DAYS, MODEL_NAME, load_dataset
from ml.registry import model_registry


def evaluate(version: int, dataset_path: Path) -> dict:
    metadata = model_registry.load_metadata(MODEL_NAME, version)
    if metadata is None:
        raise ValueError(f"No metadata found for {MODEL_NAME} version {version}")

    bundle, _ = (
        model_registry.load_active_pipeline(MODEL_NAME)
        if model_registry.get_active_version(MODEL_NAME) == version
        else (None, None)
    )
    if bundle is None:
        import joblib

        model_path = model_registry.get_version_dir(MODEL_NAME, version) / "model.joblib"
        bundle = joblib.load(model_path)

    method, params = bundle["method"], bundle["params"]

    df = load_dataset(dataset_path)
    per_user_metrics = []
    for _user_id, group in df.groupby("user_id"):
        series = group["daily_amount"].tolist()
        if len(series) <= HOLDOUT_DAYS + 7:
            continue
        train_series, actual = series[:-HOLDOUT_DAYS], series[-HOLDOUT_DAYS:]
        predicted = forecast(method, train_series, HOLDOUT_DAYS, params)
        per_user_metrics.append(evaluate_forecast(actual, predicted))

    import pandas as pd

    metrics = {
        key: float(pd.DataFrame(per_user_metrics)[key].mean()) for key in ("mae", "rmse", "mape")
    }
    print(f"Evaluating {MODEL_NAME} version {version} ({method}, params={params}) against {dataset_path}")
    print(json.dumps(metrics, indent=2))
    return metrics


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate a saved expense forecaster")
    parser.add_argument("--version", type=int, default=None)
    parser.add_argument(
        "--dataset", type=Path, default=DATA_DIR / "training" / "forecast_dataset.csv"
    )
    args = parser.parse_args()

    version = args.version
    if version is None:
        version = model_registry.get_active_version(MODEL_NAME)
        if version is None:
            raise SystemExit(f"No active version of {MODEL_NAME} found. Run training first.")

    if not args.dataset.exists():
        raise SystemExit(f"Dataset not found at {args.dataset}")

    evaluate(version, args.dataset)
