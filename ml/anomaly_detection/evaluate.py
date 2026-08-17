"""Evaluate the anomaly-detection pipeline's mechanics against a synthetic
dataset with injected (not verified-fraud) anomalies — see
ml/datasets/generate_anomaly_dataset.py for exactly what that means and why
the resulting numbers are a sanity check, not a real-world accuracy claim.

Usage:
    python -m ml.anomaly_detection.evaluate
    python -m ml.anomaly_detection.evaluate --dataset path/to/other.csv --contamination 0.1
"""

import argparse
import json
from pathlib import Path

import pandas as pd
from sklearn.metrics import classification_report, f1_score, precision_score, recall_score

from ml.anomaly_detection.predict import MIN_TRANSACTIONS_FOR_DETECTION, AnomalyDetector
from ml.common.config import DATA_DIR


def evaluate(dataset_path: Path, contamination: float = 0.08) -> dict:
    df = pd.read_csv(dataset_path, parse_dates=["transaction_date"])
    transactions = df.to_dict(orient="records")

    detector = AnomalyDetector(contamination=contamination)
    results = detector.detect(transactions)
    if results is None:
        raise SystemExit(
            f"Dataset has too few rows for detection (need >= {MIN_TRANSACTIONS_FOR_DETECTION})."
        )

    y_true = df["is_injected_anomaly"].tolist()
    y_pred = [1 if r.is_anomaly else 0 for r in results]

    metrics = {
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, zero_division=0)),
        "f1": float(f1_score(y_true, y_pred, zero_division=0)),
        "flagged_count": int(sum(y_pred)),
        "true_anomaly_count": int(sum(y_true)),
        "total_transactions": len(y_true),
        "contamination": contamination,
    }
    print(json.dumps(metrics, indent=2))
    print(classification_report(y_true, y_pred, target_names=["normal", "anomaly"], zero_division=0))
    return metrics


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate the anomaly detection pipeline")
    parser.add_argument(
        "--dataset", type=Path, default=DATA_DIR / "training" / "anomaly_eval_dataset.csv"
    )
    parser.add_argument("--contamination", type=float, default=0.08)
    args = parser.parse_args()

    if not args.dataset.exists():
        raise SystemExit(
            f"Dataset not found at {args.dataset}. "
            "Run `python -m ml.datasets.generate_anomaly_dataset` first."
        )
    evaluate(args.dataset, args.contamination)
