"""Recurring payment detection.

Unlike categorization and anomaly detection, this is deterministic
statistical grouping, not a trained model — there's nothing to fit or
version (master-prompt Phase 6 lists "recurrence detection, confidence,
API, tests", not MLflow/registry integration), so this lives entirely in
the backend service layer, the same way the insights engine will.

Algorithm, per merchant, per user:
  1. Group the user's *debit* transactions by merchant (recurring payments
     are outgoing — subscriptions, rent, bills; incoming salary is handled
     separately by analytics/insights, not here).
  2. Require at least MIN_OCCURRENCES transactions for that merchant.
  3. Compute the day-gaps between consecutive transactions (sorted
     chronologically) and take the median gap as the "typical" interval.
  4. Match that interval against known frequency buckets (weekly /
     biweekly / monthly / quarterly / yearly) with tolerance. A merchant
     whose gaps don't fall in any bucket isn't flagged — a handful of
     one-off purchases from the same merchant shouldn't be called
     "recurring" just because the count is high.
  5. Confidence combines three signals: how consistent the *interval* is
     (low variance = more confident), how consistent the *amount* is (low
     variance = more confident), and how many occurrences support it (more
     history = more confident). Master-prompt Rule 14: "Do not rely only
     on merchant names" — the confidence score is why a merchant appearing
     3 times at random intervals/amounts scores low even though the name
     matched every time.
"""

import statistics
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from app.models.recurring import RecurringDocument
from app.models.transaction import TransactionDocument
from app.repositories.recurring_repository import RecurringRepository
from app.repositories.transaction_repository import TransactionRepository

MIN_OCCURRENCES = 3
MIN_CONFIDENCE_TO_STORE = 0.3

# (label, min_days, max_days) — inclusive tolerance bands for the median
# gap between consecutive transactions from the same merchant.
FREQUENCY_BUCKETS: list[tuple[str, float, float]] = [
    ("weekly", 5, 9),
    ("biweekly", 10, 19),
    ("monthly", 25, 35),
    ("quarterly", 80, 100),
    ("yearly", 350, 380),
]


@dataclass
class RecurringCandidate:
    merchant: str
    category: str
    frequency: str
    average_amount: float
    occurrences: int
    confidence: float
    last_transaction_date: date
    next_expected_date: date


def _most_common(values: list[str]) -> str:
    return statistics.mode(values) if values else "Other"


def _match_frequency(median_gap_days: float) -> str | None:
    for label, low, high in FREQUENCY_BUCKETS:
        if low <= median_gap_days <= high:
            return label
    return None


def _to_date(value: datetime | date) -> date:
    return value.date() if isinstance(value, datetime) else value


def detect_recurring_for_merchant(
    dates: list[date], amounts: list[float], categories: list[str]
) -> RecurringCandidate | None:
    """Pure, DB-free detection logic for a single merchant's transaction
    history — kept separate from Mongo/repository concerns so it's cheap
    to unit test with synthetic dates/amounts.

    `dates`, `amounts`, and `categories` must be the same length and
    correspond index-for-index to the same merchant's transactions, in any
    order (this function sorts them).
    """
    if len(dates) < MIN_OCCURRENCES:
        return None

    order = sorted(range(len(dates)), key=lambda i: dates[i])
    sorted_dates = [dates[i] for i in order]
    sorted_amounts = [amounts[i] for i in order]
    sorted_categories = [categories[i] for i in order]

    gaps = [
        (sorted_dates[i + 1] - sorted_dates[i]).days for i in range(len(sorted_dates) - 1)
    ]
    median_gap = statistics.median(gaps)

    frequency = _match_frequency(median_gap)
    if frequency is None:
        return None

    mean_amount = statistics.fmean(sorted_amounts)
    amount_cv = (
        statistics.pstdev(sorted_amounts) / mean_amount
        if mean_amount > 0 and len(sorted_amounts) > 1
        else 0.0
    )
    mean_gap = statistics.fmean(gaps)
    interval_cv = statistics.pstdev(gaps) / mean_gap if mean_gap > 0 and len(gaps) > 1 else 0.0

    interval_regularity = max(0.0, 1 - interval_cv)
    amount_regularity = max(0.0, 1 - amount_cv)
    occurrence_factor = min(1.0, len(sorted_dates) / 6)

    confidence = round(
        0.4 * interval_regularity + 0.4 * amount_regularity + 0.2 * occurrence_factor, 4
    )
    confidence = min(1.0, max(0.0, confidence))

    if confidence < MIN_CONFIDENCE_TO_STORE:
        return None

    last_date = sorted_dates[-1]
    next_expected = last_date + timedelta(days=round(median_gap))

    return RecurringCandidate(
        merchant="",  # filled in by the caller, which owns the grouping key
        category=_most_common(sorted_categories),
        frequency=frequency,
        average_amount=round(mean_amount, 2),
        occurrences=len(sorted_dates),
        confidence=confidence,
        last_transaction_date=last_date,
        next_expected_date=next_expected,
    )


def _merchant_key(txn: TransactionDocument) -> str:
    return txn.merchant if txn.merchant else txn.description


class RecurringDetectionService:
    def __init__(
        self, transaction_repo: TransactionRepository, recurring_repo: RecurringRepository
    ) -> None:
        self._transaction_repo = transaction_repo
        self._recurring_repo = recurring_repo

    def detect_for_user(self, user_id: str) -> dict:
        transactions = [
            t
            for t in self._transaction_repo.list_all_for_user(user_id)
            if t.transaction_type == "debit"
        ]

        grouped: dict[str, list[TransactionDocument]] = {}
        for txn in transactions:
            grouped.setdefault(_merchant_key(txn), []).append(txn)

        patterns: list[RecurringDocument] = []
        for merchant, txns in grouped.items():
            dates = [_to_date(t.transaction_date) for t in txns]
            amounts = [t.amount for t in txns]
            categories = [t.category for t in txns]

            candidate = detect_recurring_for_merchant(dates, amounts, categories)
            if candidate is None:
                continue

            patterns.append(
                RecurringDocument(
                    user_id=user_id,
                    merchant=merchant,
                    category=candidate.category,
                    frequency=candidate.frequency,
                    average_amount=candidate.average_amount,
                    occurrences=candidate.occurrences,
                    confidence=candidate.confidence,
                    last_transaction_date=candidate.last_transaction_date,
                    next_expected_date=candidate.next_expected_date,
                )
            )

        self._recurring_repo.replace_all_for_user(user_id, patterns)

        return {
            "status": "completed",
            "message": (
                f"Scanned {len(transactions)} debit transactions across "
                f"{len(grouped)} merchants, found {len(patterns)} recurring patterns."
            ),
            "recurring_found": len(patterns),
            "transactions_scanned": len(transactions),
        }
