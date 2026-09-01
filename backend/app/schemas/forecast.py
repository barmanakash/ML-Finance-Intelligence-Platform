"""Request/response schemas for /api/v1/forecasts."""

from datetime import date, datetime

from pydantic import BaseModel


class ForecastResponse(BaseModel):
    period: str
    method: str
    daily_predictions: list[float]
    predicted_total: float
    start_date: date
    end_date: date
    generated_at: datetime


class ForecastListResponse(BaseModel):
    items: list[ForecastResponse]


class ForecastGenerateResponse(BaseModel):
    status: str
    message: str
    periods: dict[str, dict]
