"""Unit tests for the pure (DB-free) recurring-detection algorithm."""

from datetime import date, timedelta

from app.services.recurring_detection_service import (
    MIN_OCCURRENCES,
    detect_recurring_for_merchant,
)


def _monthly_dates(n: int, start: date = date(2026, 1, 5)) -> list[date]:
    return [start + timedelta(days=30 * i) for i in range(n)]


def test_returns_none_below_min_occurrences():
    dates = _monthly_dates(MIN_OCCURRENCES - 1)
    amounts = [649.0] * len(dates)
    categories = ["Subscription"] * len(dates)
    assert detect_recurring_for_merchant(dates, amounts, categories) is None


def test_detects_consistent_monthly_subscription():
    dates = _monthly_dates(6)
    amounts = [649.0] * 6
    categories = ["Subscription"] * 6

    result = detect_recurring_for_merchant(dates, amounts, categories)

    assert result is not None
    assert result.frequency == "monthly"
    assert result.occurrences == 6
    assert result.average_amount == 649.0
    assert result.confidence > 0.8
    assert result.next_expected_date > dates[-1]


def test_detects_weekly_pattern():
    dates = [date(2026, 1, 1) + timedelta(days=7 * i) for i in range(5)]
    amounts = [200.0, 210.0, 195.0, 205.0, 200.0]
    categories = ["Food"] * 5

    result = detect_recurring_for_merchant(dates, amounts, categories)

    assert result is not None
    assert result.frequency == "weekly"


def test_irregular_intervals_are_not_flagged():
    # Random one-off purchases from the same merchant, no regular cadence.
    dates = [date(2026, 1, 1), date(2026, 1, 3), date(2026, 3, 20), date(2026, 3, 21)]
    amounts = [500.0, 50.0, 3000.0, 20.0]
    categories = ["Shopping"] * 4

    result = detect_recurring_for_merchant(dates, amounts, categories)

    assert result is None


def test_highly_variable_amount_lowers_confidence_below_threshold():
    # Regular monthly cadence, but wildly different amounts each time —
    # shouldn't be confidently called a fixed recurring payment.
    dates = _monthly_dates(4)
    amounts = [50.0, 5000.0, 100.0, 8000.0]
    categories = ["Shopping"] * 4

    result = detect_recurring_for_merchant(dates, amounts, categories)

    assert result is None or result.confidence < 0.6


def test_next_expected_date_uses_median_gap():
    dates = _monthly_dates(4)  # gaps of 30, 30, 30 days
    amounts = [100.0] * 4
    categories = ["Bills"] * 4

    result = detect_recurring_for_merchant(dates, amounts, categories)

    assert result is not None
    assert result.next_expected_date == dates[-1] + timedelta(days=30)
