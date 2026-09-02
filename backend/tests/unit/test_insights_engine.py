"""Unit tests for the deterministic insight rules — built directly against
pandas DataFrames via _transactions_to_frame, using fake transaction
objects, so each rule's threshold logic can be tested precisely without
depending on real calendar dates or a live database.
"""

from dataclasses import dataclass
from datetime import datetime

from app.services.insights_engine import InsightsEngine, _transactions_to_frame


@dataclass
class FakeTxn:
    transaction_date: datetime
    amount: float
    category: str
    description: str
    merchant: str
    transaction_type: str = "debit"


def _engine():
    # Rules under test don't touch the repos directly (generate() does),
    # so None is fine for this file's direct _rule_* calls.
    return InsightsEngine(None, None, None)  # type: ignore[arg-type]


def test_category_increase_fires_above_threshold():
    txns = [
        FakeTxn(datetime(2026, 1, 10), 200.0, "Food", "Restaurant", "Restaurant"),
        FakeTxn(datetime(2026, 2, 10), 300.0, "Food", "Restaurant", "Restaurant"),  # +50%
    ]
    df = _transactions_to_frame(txns)
    result = _engine()._rule_category_increase(df)
    assert result is not None
    assert result[0] == "category_increase"
    assert "Food" in result[1]
    assert "50%" in result[1]


def test_category_increase_ignores_tiny_baseline():
    txns = [
        FakeTxn(datetime(2026, 1, 10), 10.0, "Food", "Snack", "Snack"),
        FakeTxn(datetime(2026, 2, 10), 50.0, "Food", "Snack", "Snack"),  # +400% but tiny baseline
    ]
    df = _transactions_to_frame(txns)
    assert _engine()._rule_category_increase(df) is None


def test_category_increase_needs_two_months():
    txns = [FakeTxn(datetime(2026, 1, 10), 500.0, "Food", "x", "x")]
    df = _transactions_to_frame(txns)
    assert _engine()._rule_category_increase(df) is None


def test_category_share_fires_for_dominant_category():
    txns = [
        FakeTxn(datetime(2026, 1, 5), 900.0, "Rent", "Rent", "Landlord"),
        FakeTxn(datetime(2026, 1, 10), 100.0, "Food", "Snack", "Snack"),
    ]
    df = _transactions_to_frame(txns)
    result = _engine()._rule_category_share(df)
    assert result is not None
    assert "Rent" in result[1]
    assert "90%" in result[1]


def test_largest_expense_picks_max_amount_this_month():
    txns = [
        FakeTxn(datetime(2026, 1, 5), 50.0, "Food", "Snack", "Snack Shop"),
        FakeTxn(datetime(2026, 1, 6), 5000.0, "Shopping", "Laptop", "Electronics Store"),
    ]
    df = _transactions_to_frame(txns)
    result = _engine()._rule_largest_expense(df)
    assert result is not None
    assert "Electronics Store" in result[1]
    assert "5000" in result[1]


def test_consecutive_increase_requires_four_strictly_increasing_months():
    txns = [
        FakeTxn(datetime(2026, 1, 5), 100.0, "Food", "x", "x"),
        FakeTxn(datetime(2026, 2, 5), 200.0, "Food", "x", "x"),
        FakeTxn(datetime(2026, 3, 5), 300.0, "Food", "x", "x"),
        FakeTxn(datetime(2026, 4, 5), 400.0, "Food", "x", "x"),
    ]
    df = _transactions_to_frame(txns)
    result = _engine()._rule_consecutive_monthly_increase(df)
    assert result is not None
    assert result[0] == "consecutive_increase"


def test_consecutive_increase_does_not_fire_on_a_dip():
    txns = [
        FakeTxn(datetime(2026, 1, 5), 400.0, "Food", "x", "x"),
        FakeTxn(datetime(2026, 2, 5), 200.0, "Food", "x", "x"),  # dip
        FakeTxn(datetime(2026, 3, 5), 300.0, "Food", "x", "x"),
        FakeTxn(datetime(2026, 4, 5), 400.0, "Food", "x", "x"),
    ]
    df = _transactions_to_frame(txns)
    assert _engine()._rule_consecutive_monthly_increase(df) is None


def test_empty_history_produces_no_insights_and_does_not_crash():
    df = _transactions_to_frame([])
    engine = _engine()
    assert engine._rule_category_increase(df) is None
    assert engine._rule_category_share(df) is None
    assert engine._rule_weekend_spending(df) is None
    assert engine._rule_largest_expense(df) is None
    assert engine._rule_consecutive_monthly_increase(df) is None


def test_credit_transactions_are_excluded_from_frame():
    txns = [
        FakeTxn(datetime(2026, 1, 5), 65000.0, "Salary", "Salary", "Employer", transaction_type="credit"),
        FakeTxn(datetime(2026, 1, 6), 100.0, "Food", "Snack", "Snack Shop"),
    ]
    df = _transactions_to_frame(txns)
    assert df["amount"].sum() == 100.0
