"""Evaluate a saved anomaly-detector version against a labeled CSV.

Usage:
    python -m ml.anomaly_detection.evaluate                     # evaluates the active version
    python -m ml.anomaly_detection.evaluate --version 2
    python -m ml.anomaly_detection.evaluate --dataset other.csv
"""

import argparse
import json
from pathlib import Path

import joblib
from sklearn.metrics import f1_score, precision_score, recall_score

from ml.anomaly_detection.features import FEATURE_COLUMNS
from ml.anomaly_detection.train import MODEL_NAME, build_feature_table, load_dataset
from ml.common.config import DATA_DIR
from ml.registry import model_registry


def evaluate(version: int, dataset_path: Path) -> dict:
    metadata = model_registry.load_metadata(MODEL_NAME, version)
    if metadata is None:
        raise ValueError(f"No metadata found for {MODEL_NAME} version {version}")

    model_path = model_registry.get_version_dir(MODEL_NAME, version) / "model.joblib"
    pipeline = joblib.load(model_path)

    df = load_dataset(dataset_path)
    feature_table = build_feature_table(df)
    X = feature_table[FEATURE_COLUMNS]

    y_pred = (pipeline.predict(X) == -1).astype(int)
    metrics = {"predicted_anomaly_rate": float(y_pred.mean())}

    if "is_synthetic_anomaly" in feature_table.columns:
        y_true = feature_table["is_synthetic_anomaly"]
        metrics.update(
            {
                "precision": float(precision_score(y_true, y_pred, zero_division=0)),
                "recall": float(recall_score(y_true, y_pred, zero_division=0)),
                "f1": float(f1_score(y_true, y_pred, zero_division=0)),
            }
        )

    print(f"Evaluating {MODEL_NAME} version {version} against {dataset_path}")
    print(json.dumps(metrics, indent=2))
    return metrics


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate a saved anomaly-detector version")
    parser.add_argument("--version", type=int, default=None)
    parser.add_argument("--dataset", type=Path, default=DATA_DIR / "training" / "anomaly_dataset.csv")
    args = parser.parse_args()

    version = args.version
    if version is None:
        version = model_registry.get_active_version(MODEL_NAME)
        if version is None:
            raise SystemExit(f"No active version of {MODEL_NAME} found. Run training first.")

    if not args.dataset.exists():
        raise SystemExit(f"Dataset not found at {args.dataset}")

    evaluate(version, args.dataset)
