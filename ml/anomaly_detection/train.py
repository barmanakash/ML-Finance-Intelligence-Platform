"""Train the transaction anomaly detector (Isolation Forest).

Unsupervised: the model never sees `is_injected_anomaly` during fitting.
That label exists purely so this script can report precision/recall against
known-injected anomalies as a sanity check on the pipeline — real-world
anomaly detection has no ground truth, so this evaluation is illustrative,
not a guarantee of real-world performance (master-prompt Rule 43:
unsupervised anomaly detection does not automatically equal fraud
detection).

Per-user features are computed chronologically with an expanding window —
each transaction is scored only against that user's *prior* transactions —
to avoid leaking future information into the baseline (Rule 54). See
ml.features.transaction_features for the actual feature computation, which
is shared with ml.anomaly_detection.predict to avoid train/serve skew.

Usage:
    python -m ml.anomaly_detection.train
    python -m ml.anomaly_detection.train --dataset path/to/other.csv
"""

import argparse
import json
from pathlib import Path

import mlflow
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.metrics import f1_score, precision_score, recall_score
from sklearn.preprocessing import StandardScaler

from ml.common.config import DATA_DIR, MLFLOW_TRACKING_URI, RANDOM_SEED
from ml.features.transaction_features import FEATURE_NAMES, compute_features
from ml.registry import model_registry

MODEL_NAME = "anomaly-detector"
EXPERIMENT_NAME = "anomaly-detection"
CONTAMINATION = 0.05  # expected anomaly rate; set slightly above the injected rate


def load_dataset(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, parse_dates=["date"])
    required = {"user_id", "date", "merchant", "category", "amount", "is_injected_anomaly"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Dataset is missing required columns: {sorted(missing)}")
    return df.sort_values(["user_id", "date"]).reset_index(drop=True)


def build_feature_matrix(df: pd.DataFrame) -> tuple[list[list[float]], list[int]]:
    """Walk each user's history chronologically, computing every
    transaction's features against only that user's *prior* rows."""
    feature_rows: list[list[float]] = []
    labels: list[int] = []

    for _user_id, group in df.groupby("user_id"):
        prior: list[dict] = []
        for _, row in group.iterrows():
            features = compute_features(
                amount=row["amount"],
                category=row["category"],
                merchant=row["merchant"],
                transaction_date=row["date"],
                prior_transactions=prior,
            )
            feature_rows.append(features.as_vector())
            labels.append(int(row["is_injected_anomaly"]))
            prior.append(
                {"amount": row["amount"], "category": row["category"], "merchant": row["merchant"]}
            )

    return feature_rows, labels


def train(dataset_path: Path) -> dict:
    df = load_dataset(dataset_path)
    X, y_true = build_feature_matrix(df)

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    mlflow.set_experiment(EXPERIMENT_NAME)

    with mlflow.start_run(run_name="isolation_forest"):
        model = IsolationForest(n_estimators=200, contamination=CONTAMINATION, random_state=RANDOM_SEED)
        model.fit(X_scaled)

        raw_predictions = model.predict(X_scaled)  # -1 = anomaly, 1 = normal
        y_pred = [1 if p == -1 else 0 for p in raw_predictions]

        metrics = {
            "precision": float(precision_score(y_true, y_pred, zero_division=0)),
            "recall": float(recall_score(y_true, y_pred, zero_division=0)),
            "f1": float(f1_score(y_true, y_pred, zero_division=0)),
            "flagged_rate": float(sum(y_pred) / len(y_pred)) if y_pred else 0.0,
            "injected_rate": float(sum(y_true) / len(y_true)) if y_true else 0.0,
        }

        mlflow.log_param("n_estimators", 200)
        mlflow.log_param("contamination", CONTAMINATION)
        mlflow.log_param("dataset_rows", len(df))
        mlflow.log_param("random_seed", RANDOM_SEED)
        mlflow.log_metrics(metrics)

        pipeline_bundle = {"scaler": scaler, "model": model, "feature_names": FEATURE_NAMES}

        version = model_registry.next_version(MODEL_NAME)
        model_registry.save_version(
            MODEL_NAME,
            version,
            pipeline_bundle,
            metrics=metrics,
            params={
                "n_estimators": 200,
                "contamination": CONTAMINATION,
                "dataset_rows": len(df),
                "feature_names": FEATURE_NAMES,
            },
        )

        promoted = model_registry.maybe_promote(MODEL_NAME, version, metrics, metric_key="f1")

        summary = {"metrics": metrics, "version": version, "promoted": promoted}
        print(json.dumps(summary, indent=2))
        if not promoted:
            print(
                f"Version {version} was NOT promoted — its f1 ({metrics['f1']:.4f}) "
                "did not beat the currently active version."
            )
        return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train the transaction anomaly detector")
    parser.add_argument(
        "--dataset", type=Path, default=DATA_DIR / "training" / "anomaly_dataset.csv"
    )
    args = parser.parse_args()

    if not args.dataset.exists():
        raise SystemExit(
            f"Dataset not found at {args.dataset}. "
            "Run `python -m ml.datasets.generate_anomaly_dataset` first."
        )
    train(args.dataset)
