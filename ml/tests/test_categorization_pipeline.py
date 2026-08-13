"""End-to-end ML tests: dataset -> train -> registry -> predict.

Uses a tiny synthetic dataset and a monkeypatched MODELS_DIR so nothing here
touches the real models/ directory or the real MLflow run history.
"""

import pandas as pd
import pytest

from ml.categorization import predict as predict_module
from ml.categorization.train import MODEL_NAME, train
from ml.common import config as ml_config
from ml.registry import model_registry


@pytest.fixture()
def tmp_models_dir(tmp_path, monkeypatch):
    models_dir = tmp_path / "models"
    monkeypatch.setattr(ml_config, "MODELS_DIR", models_dir)
    return models_dir


@pytest.fixture()
def tiny_dataset(tmp_path):
    samples = {
        "Food": ["SWIGGY ORDER", "ZOMATO DELIVERY", "MCDONALDS MEAL", "DOMINOS PIZZA ORDER"] * 5,
        "Shopping": ["AMAZON PURCHASE", "FLIPKART ORDER", "MYNTRA BUY", "AJIO SALE"] * 5,
        "Transportation": ["UBER RIDE", "OLA CABS TRIP", "RAPIDO BIKE", "PETROL PUMP FUEL"] * 5,
    }
    rows = [
        {"description": d, "category": category}
        for category, descriptions in samples.items()
        for d in descriptions
    ]
    df = pd.DataFrame(rows)
    path = tmp_path / "dataset.csv"
    df.to_csv(path, index=False)
    return path


def test_train_produces_valid_metrics_and_promotes_first_version(tmp_models_dir, tiny_dataset):
    summary = train(tiny_dataset)

    assert summary["promoted"] is True
    assert summary["version"] == 1
    assert 0.0 <= summary["best_metrics"]["macro_f1"] <= 1.0
    assert summary["best_model"] in {"logistic_regression", "linear_svc", "multinomial_nb"}
    assert set(summary["candidates"].keys()) == {
        "logistic_regression",
        "linear_svc",
        "multinomial_nb",
    }
    assert model_registry.get_active_version(MODEL_NAME) == 1


def test_trained_model_loads_and_predicts_valid_schema(tmp_models_dir, tiny_dataset):
    train(tiny_dataset)

    classifier = predict_module.TransactionClassifier()
    assert classifier.is_ready
    assert classifier.active_version == 1

    predictions = classifier.predict_batch(["SWIGGY FOOD ORDER", "UBER TRIP TO AIRPORT"])
    assert len(predictions) == 2
    for pred in predictions:
        assert pred.category in {"Food", "Shopping", "Transportation"}
        assert 0.0 <= pred.confidence <= 1.0


def test_worse_retrain_is_not_promoted(tmp_models_dir, tiny_dataset, monkeypatch):
    train(tiny_dataset)
    first_active = model_registry.get_active_version(MODEL_NAME)
    assert first_active == 1

    # Simulate a retrain that scores worse than production, regardless of
    # what this particular run actually measured, to test the promotion
    # guardrail in isolation from run-to-run model variance.
    monkeypatch.setattr(model_registry, "maybe_promote", lambda *a, **k: False)

    summary = train(tiny_dataset)
    assert summary["promoted"] is False
    assert model_registry.get_active_version(MODEL_NAME) == first_active


def test_classifier_gracefully_reports_not_ready_when_no_model_trained(tmp_models_dir):
    classifier = predict_module.TransactionClassifier()
    assert not classifier.is_ready
    assert classifier.active_version is None

    predictions = classifier.predict_batch(["SOME DESCRIPTION"])
    assert predictions[0].category == "Uncategorized"
    assert predictions[0].confidence == 0.0
