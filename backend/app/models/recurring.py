"""MongoDB document schema for the `recurring_transactions` collection.

One document per detected recurring merchant pattern per user. Like
anomalies, the whole collection is replaced wholesale for a user each time
detection re-runs (see RecurringRepository.replace_all_for_user and
RecurringDetectionService.detect_for_user), since detection always
re-evaluates a user's entire history at once rather than incrementally
updating individual patterns.
"""

from datetime import UTC, date, datetime

from pydantic import BaseModel, ConfigDict, Field


class RecurringDocument(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str | None = Field(default=None, alias="_id")
    user_id: str
    merchant: str
    category: str
    frequency: str  # "weekly" | "biweekly" | "monthly" | "quarterly" | "yearly"
    average_amount: float
    occurrences: int
    confidence: float
    last_transaction_date: date
    next_expected_date: date
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
