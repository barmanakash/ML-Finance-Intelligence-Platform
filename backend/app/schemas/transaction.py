"""Request/response schemas for /api/v1/transactions."""

from datetime import datetime

from pydantic import BaseModel


class TransactionResponse(BaseModel):
    id: str
    transaction_date: datetime
    description: str
    merchant: str | None
    amount: float
    currency: str
    transaction_type: str
    category: str
    is_anomaly: bool
    anomaly_score: float | None
    import_id: str
    reference: str | None
    created_at: datetime


class TransactionListResponse(BaseModel):
    items: list[TransactionResponse]
    total: int
    skip: int
    limit: int
