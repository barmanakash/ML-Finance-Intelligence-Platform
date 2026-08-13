"""The real active model (if any) is process-global, so these tests only
assert the graceful-fallback contract, not a specific trained model's
behavior — a fresh checkout has no trained model yet, and the service must
degrade to "Uncategorized" rather than error.
"""

from app.services.categorization_service import categorization_service


def test_categorize_returns_uncategorized_when_no_model_ready():
    if categorization_service.is_ready:
        # A model happens to be trained in this environment; the
        # not-ready contract can't be exercised here, so just sanity-check
        # the ready path instead of asserting a false premise.
        prediction = categorization_service.categorize("SWIGGY ORDER")
        assert isinstance(prediction.category, str)
        assert 0.0 <= prediction.confidence <= 1.0
        return

    prediction = categorization_service.categorize("SWIGGY ORDER")
    assert prediction.category == "Uncategorized"
    assert prediction.confidence == 0.0


def test_categorize_batch_matches_input_length():
    descriptions = ["SWIGGY ORDER", "UBER RIDE", "AMAZON PURCHASE"]
    predictions = categorization_service.categorize_batch(descriptions)
    assert len(predictions) == len(descriptions)
    for prediction in predictions:
        assert isinstance(prediction.category, str)
        assert 0.0 <= prediction.confidence <= 1.0


def test_categorize_batch_empty_list_returns_empty():
    assert categorization_service.categorize_batch([]) == []
