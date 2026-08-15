"""Train the transaction anomaly detector.

IsolationForest is unsupervised — it never sees the `is_synthetic_anomaly`
label. That label exists purely so this script can report a rough
precision/recall sanity check against known-injected outliers after
training. Real anomaly detection has no ground truth in production; this
metric is a pipeline health check, not a claim about real-world accuracy.

Features are computed per-user (see ml.anomaly_detection.features) because
"unusual" is relative to each person's own spending pattern, then
concatenated across all synthetic users before fitting a single global
model + StandardScaler, saved together as one sklearn Pipeline.

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
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from ml.anomaly_detection.features import FEATURE_COLUMNS, compute_features
from ml.common.config import DATA_DIR, MLFLOW_EXPERIMENT_NAME, MLFLOW_TRACKING_URI, RANDOM_SEED
from ml.registry import model_registry

MODEL_NAME = "anomaly-detector"
CONTAMINATION = 0.05


def load_dataset(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, parse_dates=["transaction_date"])
    required = {"user_id", "transaction_date", "category", "merchant", "amount"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Dataset is missing required columns: {sorted(missing)}")
    return df


def build_feature_table(df: pd.DataFrame) -> pd.DataFrame:
    """Compute features per user (their own history only) and stitch the
    results back together, keeping the synthetic-anomaly label alongside
    for evaluation (not used in training).
    """
    feature_frames = []
    for _user_id, group in df.groupby("user_id"):
        group = group.reset_index(drop=True)
        features = compute_features(group)
        if "is_synthetic_anomaly" in group.columns:
            features = features.assign(is_synthetic_anomaly=group["is_synthetic_anomaly"].values)
        feature_frames.append(features)
    return pd.concat(feature_frames, ignore_index=True)


def train(dataset_path: Path) -> dict:
    df = load_dataset(dataset_path)
    feature_table = build_feature_table(df)

    X = feature_table[FEATURE_COLUMNS]
    has_labels = "is_synthetic_anomaly" in feature_table.columns
    y_true = feature_table["is_synthetic_anomaly"] if has_labels else None

    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    mlflow.set_experiment(MLFLOW_EXPERIMENT_NAME.replace("categorization", "anomaly-detection"))

    with mlflow.start_run(run_name="isolation_forest"):
        pipeline = Pipeline(
            [
                ("scaler", StandardScaler()),
                (
                    "iforest",
                    IsolationForest(
                        n_estimators=200,
                        contamination=CONTAMINATION,
                        random_state=RANDOM_SEED,
                    ),
                ),
            ]
        )
        pipeline.fit(X)  # unsupervised — y_true is never passed in

        raw_predictions = pipeline.predict(X)  # -1 = anomaly, 1 = normal
        y_pred = (raw_predictions == -1).astype(int)

        metrics = {"predicted_anomaly_rate": float(y_pred.mean())}
        if has_labels:
            metrics.update(
                {
                    "precision": float(precision_score(y_true, y_pred, zero_division=0)),
                    "recall": float(recall_score(y_true, y_pred, zero_division=0)),
                    "f1": float(f1_score(y_true, y_pred, zero_division=0)),
                }
            )
        else:
            # No ground truth available (e.g. training on real data) — fall
            # back to a neutral score so the promotion guardrail still has
            # something to compare against.
            metrics["f1"] = 0.0

        mlflow.log_param("model_type", "isolation_forest")
        mlflow.log_param("contamination", CONTAMINATION)
        mlflow.log_param("n_estimators", 200)
        mlflow.log_param("dataset_rows", len(feature_table))
        mlflow.log_param("random_seed", RANDOM_SEED)
        mlflow.log_metrics(metrics)

    version = model_registry.next_version(MODEL_NAME)
    version_dir = model_registry.save_version(
        MODEL_NAME,
        version,
        pipeline,
        metrics=metrics,
        params={
            "model_type": "isolation_forest",
            "contamination": CONTAMINATION,
            "dataset_rows": len(feature_table),
            "feature_columns": FEATURE_COLUMNS,
            "has_synthetic_labels": has_labels,
        },
    )
    (version_dir / "metrics.json").write_text(json.dumps(metrics, indent=2))

    promoted = model_registry.maybe_promote(MODEL_NAME, version, metrics, metric_key="f1")

    summary = {"metrics": metrics, "version": version, "promoted": promoted}
    print(json.dumps(summary, indent=2))
    if has_labels:
        print(
            "\nNote: precision/recall above are a sanity check against synthetic "
            "injected outliers, not a real-world accuracy claim. IsolationForest "
            "never saw these labels during training."
        )
    if not promoted:
        print(
            f"Version {version} was NOT promoted — its f1 ({metrics['f1']:.4f}) "
            "did not beat the currently active version."
        )
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train the transaction anomaly detector")
    parser.add_argument(
        "--dataset",
        type=Path,
        default=DATA_DIR / "training" / "anomaly_dataset.csv",
        help="Path to a CSV with user_id, transaction_date, category, merchant, amount columns",
    )
    args = parser.parse_args()

    if not args.dataset.exists():
        raise SystemExit(
            f"Dataset not found at {args.dataset}. "
            "Run `python -m ml.datasets.generate_anomaly_dataset` first."
        )
    train(args.dataset)
