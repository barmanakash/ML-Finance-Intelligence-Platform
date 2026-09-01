"""MongoDB document schema for the `expense_forecasts` collection.

One document per (user, period). Replaced wholesale for that period each
time forecasting re-runs (see ForecastRepository.replace_for_period and
ForecastService.generate_for_user) — a forecast is a snapshot as of the
user's latest data, not something to accumulate history for.
"""

from datetime import UTC, date, datetime

from pydantic import BaseModel, ConfigDict, Field


class ForecastDocument(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str | None = Field(default=None, alias="_id")
    user_id: str
    period: str  # "7d" | "30d" | "90d"
    method: str
    daily_predictions: list[float]
    predicted_total: float
    start_date: date
    end_date: date
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
