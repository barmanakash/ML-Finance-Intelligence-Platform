"""MongoDB document schema for the `anomalies` collection."""

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field


class AnomalyDocument(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str | None = Field(default=None, alias="_id")
    user_id: str
    transaction_id: str
    anomaly_score: float
    severity: str  # "low" | "medium" | "high"
    reasons: list[str]
    amount: float
    merchant: str | None = None
    category: str
    transaction_date: datetime
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
