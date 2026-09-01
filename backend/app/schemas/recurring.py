"""Request/response schemas for /api/v1/recurring."""

from datetime import date

from pydantic import BaseModel


class RecurringResponse(BaseModel):
    id: str
    merchant: str
    category: str
    frequency: str
    average_amount: float
    occurrences: int
    confidence: float
    last_transaction_date: date
    next_expected_date: date


class RecurringListResponse(BaseModel):
    items: list[RecurringResponse]
    total: int
    skip: int
    limit: int


class RecurringScanResponse(BaseModel):
    status: str
    message: str
    recurring_found: int
    transactions_scanned: int
