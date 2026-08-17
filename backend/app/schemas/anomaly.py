"""Request/response schemas for /api/v1/anomalies."""

from datetime import datetime

from pydantic import BaseModel


class AnomalyResponse(BaseModel):
    id: str
    transaction_id: str
    anomaly_score: float
    severity: str
    reason: str
    created_at: datetime


class AnomalyListResponse(BaseModel):
    items: list[AnomalyResponse]
    total: int
    skip: int
    limit: int


class AnomalyScanResponse(BaseModel):
    status: str
    message: str
    anomalies_found: int
    transactions_scanned: int
