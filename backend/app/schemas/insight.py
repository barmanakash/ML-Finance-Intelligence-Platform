"""Request/response schemas for /api/v1/insights."""

from datetime import datetime

from pydantic import BaseModel


class InsightResponse(BaseModel):
    id: str
    type: str
    message: str
    created_at: datetime


class InsightListResponse(BaseModel):
    items: list[InsightResponse]


class InsightGenerateResponse(BaseModel):
    status: str
    message: str
    insights_found: int
