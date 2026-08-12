"""MongoDB document schema for the `transactions` collection."""

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field


class TransactionDocument(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str | None = Field(default=None, alias="_id")
    user_id: str
    transaction_date: datetime
    description: str
    merchant: str | None = None
    amount: float
    currency: str = "INR"
    transaction_type: str  # "debit" | "credit"
    category: str = "Uncategorized"
    category_confidence: float | None = None
    is_anomaly: bool = False
    anomaly_score: float | None = None
    import_id: str
    reference: str | None = None
    # sha256(user_id|date|description|amount|type) — reserved for future
    # content-level duplicate detection (e.g. re-imports from a different file).
    content_hash: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
