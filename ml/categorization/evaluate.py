"""Evaluate a saved categorization model version against a labeled CSV.

Usage:
    python -m ml.categorization.evaluate                      # evaluates the active version
    python -m ml.categorization.evaluate --version 2           # evaluates a specific version
    python -m ml.categorization.evaluate --dataset other.csv   # against a different dataset
"""

import argparse
import json
from pathlib import Path

import joblib
from sklearn.metrics import classification_report

from ml.categorization.train import MODEL_NAME, evaluate_predictions, load_dataset
from ml.common.config import DATA_DIR
from ml.preprocessing.text_preprocessing import normalize_description
from ml.registry import model_registry


def evaluate(version: int, dataset_path: Path) -> dict:
    metadata = model_registry.load_metadata(MODEL_NAME, version)
    if metadata is None:
        raise ValueError(f"No metadata found for {MODEL_NAME} version {version}")

    model_path = model_registry.get_version_dir(MODEL_NAME, version) / "model.joblib"
    pipeline = joblib.load(model_path)

    df = load_dataset(dataset_path)
    df = df.copy()
    df["clean_description"] = df["description"].apply(normalize_description)

    y_pred = pipeline.predict(df["clean_description"])
    metrics = evaluate_predictions(df["category"], y_pred)
    report = classification_report(df["category"], y_pred, zero_division=0)

    print(f"Evaluating {MODEL_NAME} version {version} against {dataset_path}")
    print(json.dumps(metrics, indent=2))
    print(report)
    return metrics


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate a saved categorization model")
    parser.add_argument(
        "--version",
        type=int,
        default=None,
        help="Model version to evaluate (defaults to the currently active version)",
    )
    parser.add_argument(
        "--dataset", type=Path, default=DATA_DIR / "training" / "categorization_dataset.csv"
    )
    args = parser.parse_args()

    version = args.version
    if version is None:
        version = model_registry.get_active_version(MODEL_NAME)
        if version is None:
            raise SystemExit(
                f"No active version of {MODEL_NAME} found. "
                "Run `python -m ml.categorization.train` first, or pass --version explicitly."
            )

    if not args.dataset.exists():
        raise SystemExit(f"Dataset not found at {args.dataset}")

    evaluate(version, args.dataset)
