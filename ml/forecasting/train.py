"""Train (select + tune) the expense forecasting method.

There's no model to "fit" in the neural-network sense here — the four
candidates in ml.forecasting.methods are all classical statistical
baselines (master-prompt Rule 15: "Start with simple strong baselines...
Only introduce more complex models if they actually improve evaluation").
What this script actually does is a small grid search: try every
candidate (and, for the ones with a hyperparameter, every value in a small
grid) against every synthetic user's time-aware holdout, and keep whichever
scores the lowest mean MAE across all users.

Time-aware validation (master-prompt Rule 54: never let future information
leak into a prediction): for every user, the last HOLDOUT_DAYS days are
held out entirely; every candidate forecasts *forward* from only the days
before that, exactly like ml.forecasting.predict does in production against
a real user's actual history.

The winning (method, params) pair — not a per-user fitted object — is what
gets saved to the registry and served by ml.forecasting.predict: at inference
time the chosen method is applied fresh to whichever user's own history is
passed in, the same way ml.anomaly_detection re-fits IsolationForest-derived
z-scores per user rather than reusing one user's baseline for another.

Usage:
    python -m ml.forecasting.train
    python -m ml.forecasting.train --dataset path/to/other.csv
"""

import argparse
import json
from pathlib import Path

import mlflow
import pandas as pd

from ml.common.config import DATA_DIR, MLFLOW_TRACKING_URI, RANDOM_SEED
from ml.forecasting.methods import forecast
from ml.forecasting.metrics import evaluate_forecast
from ml.registry import model_registry

MODEL_NAME = "expense-forecaster"
EXPERIMENT_NAME = "expense-forecasting"
HOLDOUT_DAYS = 14

CANDIDATE_GRID: list[tuple[str, dict]] = [
    ("historical_average", {}),
    ("moving_average", {"window": 3}),
    ("moving_average", {"window": 7}),
    ("moving_average", {"window": 14}),
    ("exponential_smoothing", {"alpha": 0.1}),
    ("exponential_smoothing", {"alpha": 0.3}),
    ("exponential_smoothing", {"alpha": 0.5}),
    ("linear_regression", {}),
]


def load_dataset(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, parse_dates=["date"])
    required = {"user_id", "date", "daily_amount"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Dataset is missing required columns: {sorted(missing)}")
    return df.sort_values(["user_id", "date"]).reset_index(drop=True)


def evaluate_candidate(df: pd.DataFrame, method: str, params: dict) -> dict:
    """Mean MAE/RMSE/MAPE across every user's held-out last HOLDOUT_DAYS days."""
    per_user_metrics = []
    for _user_id, group in df.groupby("user_id"):
        series = group["daily_amount"].tolist()
        if len(series) <= HOLDOUT_DAYS + 7:
            continue  # not enough history to both train and hold out meaningfully
        train_series = series[:-HOLDOUT_DAYS]
        actual = series[-HOLDOUT_DAYS:]
        predicted = forecast(method, train_series, HOLDOUT_DAYS, params)
        per_user_metrics.append(evaluate_forecast(actual, predicted))

    if not per_user_metrics:
        raise ValueError("No user had enough history to evaluate against.")

    return {
        key: float(pd.DataFrame(per_user_metrics)[key].mean())
        for key in ("mae", "rmse", "mape")
    }


def train(dataset_path: Path) -> dict:
    df = load_dataset(dataset_path)

    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    mlflow.set_experiment(EXPERIMENT_NAME)

    results: dict[str, dict] = {}
    best_key: str | None = None
    best_method: str | None = None
    best_params: dict | None = None
    best_metrics: dict | None = None

    for method, params in CANDIDATE_GRID:
        key = f"{method}" + (f"(params={params})" if params else "")
        with mlflow.start_run(run_name=key):
            metrics = evaluate_candidate(df, method, params)

            mlflow.log_param("method", method)
            for param_name, param_value in params.items():
                mlflow.log_param(param_name, param_value)
            mlflow.log_param("holdout_days", HOLDOUT_DAYS)
            mlflow.log_param("random_seed", RANDOM_SEED)
            mlflow.log_metrics(metrics)

            results[key] = {"method": method, "params": params, **metrics}
            if best_metrics is None or metrics["mae"] < best_metrics["mae"]:
                best_key, best_method, best_params, best_metrics = key, method, params, metrics

    assert best_method is not None and best_params is not None and best_metrics is not None

    version = model_registry.next_version(MODEL_NAME)
    bundle = {"method": best_method, "params": best_params}
    registry_metrics = {**best_metrics, "mae_negated": -best_metrics["mae"]}
    model_registry.save_version(
        MODEL_NAME,
        version,
        bundle,
        metrics=registry_metrics,
        params={
            "method": best_method,
            **best_params,
            "holdout_days": HOLDOUT_DAYS,
            "dataset_rows": len(df),
            "dataset_users": df["user_id"].nunique(),
        },
    )

    # Lower MAE is better, but model_registry.maybe_promote promotes on
    # ">=", so we compare on the negated MAE ("mae_negated") instead of
    # touching the shared registry's comparison direction for every other
    # model (categorization/anomaly both promote on "higher is better").
    promoted = model_registry.maybe_promote(MODEL_NAME, version, registry_metrics, metric_key="mae_negated")

    summary = {
        "candidates": results,
        "best_candidate": best_key,
        "best_method": best_method,
        "best_params": best_params,
        "best_metrics": best_metrics,
        "version": version,
        "promoted": promoted,
    }
    print(json.dumps(summary, indent=2))
    if not promoted:
        print(
            f"Version {version} was NOT promoted — its MAE ({best_metrics['mae']:.2f}) "
            "did not beat the currently active version."
        )
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Select and tune the expense forecasting method")
    parser.add_argument(
        "--dataset", type=Path, default=DATA_DIR / "training" / "forecast_dataset.csv"
    )
    args = parser.parse_args()

    if not args.dataset.exists():
        raise SystemExit(
            f"Dataset not found at {args.dataset}. "
            "Run `python -m ml.datasets.generate_forecast_dataset` first."
        )
    train(args.dataset)
