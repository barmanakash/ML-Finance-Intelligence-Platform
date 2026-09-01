"""Inference-only interface for expense forecasting.

No training/selection logic here — see ml.forecasting.train. The active
(method, params) pair is loaded from the registry once and applied fresh to
whichever user's own daily-spend history is passed in, the same "shared
model, per-user features" pattern as ml.anomaly_detection.predict.

Explanations of *why* a forecast is what it is are intentionally not
generated here — master-prompt Rule 15 only asks for the predicted number
plus (where supported) a sense of confidence/uncertainty, which for these
classical baselines is better expressed as "insufficient data" than a
fabricated confidence interval this pipeline hasn't actually estimated.
"""

from dataclasses import dataclass
from datetime import date, timedelta

from ml.forecasting.methods import forecast as run_forecast
from ml.registry import model_registry

MODEL_NAME = "expense-forecaster"

# Below this many distinct calendar days of history, a forecast would be
# extrapolating from almost nothing — master-prompt Rule 15: "Do not
# pretend forecasting is accurate when insufficient historical data exists."
MIN_HISTORY_DAYS = 14


@dataclass
class ForecastResult:
    method: str
    daily_predictions: list[float]
    predicted_total: float
    start_date: date
    end_date: date


def _fill_daily_series(daily_totals: dict[date, float]) -> list[float]:
    """Turns a possibly-sparse {date: amount} map into a continuous,
    chronologically-ordered list with 0.0 on any day the user had no
    (debit) transactions — a forecasting method must see "no spend that
    day" explicitly, not silently skip over it, or it will overestimate
    the average.
    """
    if not daily_totals:
        return []
    start, end = min(daily_totals), max(daily_totals)
    days = (end - start).days + 1
    return [daily_totals.get(start + timedelta(days=i), 0.0) for i in range(days)]


class ExpenseForecaster:
    def __init__(self) -> None:
        bundle, metadata = model_registry.load_active_pipeline(MODEL_NAME)
        self._method = bundle["method"] if bundle else None
        self._params = bundle["params"] if bundle else {}
        self._metadata = metadata

    @property
    def is_ready(self) -> bool:
        return self._method is not None

    @property
    def active_version(self) -> int | None:
        return (self._metadata or {}).get("version")

    def forecast(
        self, daily_totals: dict[date, float], horizon_days: int
    ) -> ForecastResult | None:
        """`daily_totals` maps each date with at least one transaction to
        that day's total debit amount. Returns None if the model isn't
        trained yet or the user doesn't have enough distinct history —
        callers (see app.services.forecast_service) turn that into the
        "Insufficient historical data for reliable forecast." message from
        master-prompt Rule 15 rather than an error.
        """
        if not self.is_ready:
            return None

        series = _fill_daily_series(daily_totals)
        if len(series) < MIN_HISTORY_DAYS:
            return None

        predictions = run_forecast(self._method, series, horizon_days, self._params)
        last_date = max(daily_totals)

        return ForecastResult(
            method=self._method,
            daily_predictions=predictions,
            predicted_total=round(sum(predictions), 2),
            start_date=last_date + timedelta(days=1),
            end_date=last_date + timedelta(days=horizon_days),
        )
