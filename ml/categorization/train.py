"""Train the transaction categorization model.

Compares three classical baselines on the same TF-IDF features —
LogisticRegression, LinearSVC, and MultinomialNB — and keeps whichever
scores highest on macro-F1 (macro, not micro/accuracy, because categories
like "Rent" or "Investment" are naturally rarer than "Food"/"Shopping" and
we don't want the metric to hide poor performance on them).

The winning model is only promoted to "active" (i.e. actually served by the
backend) if it's at least as good as whatever is currently active — see
ml.registry.model_registry.maybe_promote. A bad retrain is saved to disk
for inspection but never silently degrades production categorization.

Usage:
    python -m ml.categorization.train
    python -m ml.categorization.train --dataset path/to/other.csv
"""

import argparse
import json
from pathlib import Path

import mlflow
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)
from sklearn.model_selection import train_test_split
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline
from sklearn.svm import LinearSVC

from ml.common.config import DATA_DIR, MLFLOW_EXPERIMENT_NAME, MLFLOW_TRACKING_URI, RANDOM_SEED
from ml.preprocessing.text_preprocessing import normalize_description
from ml.registry import model_registry

MODEL_NAME = "transaction-classifier"

CANDIDATES = {
    "logistic_regression": lambda: LogisticRegression(max_iter=1000, class_weight="balanced"),
    "linear_svc": lambda: LinearSVC(class_weight="balanced"),
    "multinomial_nb": lambda: MultinomialNB(),
}


def load_dataset(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    if "description" not in df.columns or "category" not in df.columns:
        raise ValueError("Dataset must have 'description' and 'category' columns")
    return df.dropna(subset=["description", "category"])


def evaluate_predictions(y_true, y_pred) -> dict:
    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "macro_f1": float(f1_score(y_true, y_pred, average="macro")),
        "macro_precision": float(precision_score(y_true, y_pred, average="macro", zero_division=0)),
        "macro_recall": float(recall_score(y_true, y_pred, average="macro", zero_division=0)),
    }


def train(dataset_path: Path) -> dict:
    df = load_dataset(dataset_path)
    df = df.copy()
    df["clean_description"] = df["description"].apply(normalize_description)

    X_train, X_test, y_train, y_test = train_test_split(
        df["clean_description"],
        df["category"],
        test_size=0.2,
        random_state=RANDOM_SEED,
        stratify=df["category"],
    )

    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    mlflow.set_experiment(MLFLOW_EXPERIMENT_NAME)

    results: dict[str, dict] = {}
    best_name: str | None = None
    best_pipeline: Pipeline | None = None
    best_metrics: dict | None = None

    for name, make_classifier in CANDIDATES.items():
        with mlflow.start_run(run_name=name):
            pipeline = Pipeline(
                [
                    ("tfidf", TfidfVectorizer(ngram_range=(1, 2), min_df=1)),
                    ("classifier", make_classifier()),
                ]
            )
            pipeline.fit(X_train, y_train)
            y_pred = pipeline.predict(X_test)
            metrics = evaluate_predictions(y_test, y_pred)

            mlflow.log_param("model_type", name)
            mlflow.log_param("dataset_rows", len(df))
            mlflow.log_param("random_seed", RANDOM_SEED)
            mlflow.log_metrics(metrics)

            results[name] = metrics
            if best_metrics is None or metrics["macro_f1"] > best_metrics["macro_f1"]:
                best_name, best_pipeline, best_metrics = name, pipeline, metrics

    assert best_pipeline is not None and best_metrics is not None and best_name is not None

    y_pred_best = best_pipeline.predict(X_test)
    report = classification_report(y_test, y_pred_best, zero_division=0)
    labels = sorted(df["category"].unique().tolist())
    matrix = confusion_matrix(y_test, y_pred_best, labels=labels).tolist()

    version = model_registry.next_version(MODEL_NAME)
    version_dir = model_registry.save_version(
        MODEL_NAME,
        version,
        best_pipeline,
        metrics=best_metrics,
        params={
            "model_type": best_name,
            "dataset_rows": len(df),
            "train_rows": len(X_train),
            "test_rows": len(X_test),
            "labels": labels,
        },
    )
    (version_dir / "classification_report.txt").write_text(report)
    (version_dir / "confusion_matrix.json").write_text(
        json.dumps({"labels": labels, "matrix": matrix}, indent=2)
    )

    promoted = model_registry.maybe_promote(MODEL_NAME, version, best_metrics)

    summary = {
        "candidates": results,
        "best_model": best_name,
        "best_metrics": best_metrics,
        "version": version,
        "promoted": promoted,
    }
    print(json.dumps(summary, indent=2))
    print(f"\n{report}")
    if not promoted:
        print(
            f"Version {version} was NOT promoted — its macro_f1 "
            f"({best_metrics['macro_f1']:.4f}) did not beat the currently active version."
        )
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train the transaction categorization model")
    parser.add_argument(
        "--dataset",
        type=Path,
        default=DATA_DIR / "training" / "categorization_dataset.csv",
        help="Path to a CSV with 'description' and 'category' columns",
    )
    args = parser.parse_args()

    if not args.dataset.exists():
        raise SystemExit(
            f"Dataset not found at {args.dataset}. "
            "Run `python -m ml.datasets.generate_categorization_dataset` first, "
            "or pass --dataset pointing at your own labeled CSV."
        )
    train(args.dataset)
