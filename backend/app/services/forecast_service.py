"""Wraps ml.forecasting.predict.ExpenseForecaster for use inside the
backend. Same import-path fallback pattern as the other ML-backed
services (categorization, anomaly detection) — works directly in Docker
(docker-compose mounts ./ml -> /app/ml), falls back to adding the repo
root to sys.path for local (non-Docker) dev.
"""

import logging
import sys
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path

logger = logging.getLogger(__name__)

try:
    from ml.forecasting.predict import MIN_HISTORY_DAYS, ExpenseForecaster
except ImportError:
    _repo_root = Path(__file__).resolve().parents[3]
    if str(_repo_root) not in sys.path:
        sys.path.insert(0, str(_repo_root))
    from ml.forecasting.predict import MIN_HISTORY_DAYS, ExpenseForecaster  # noqa: E402

from app.models.forecast import ForecastDocument
from app.repositories.forecast_repository import ForecastRepository
from app.repositories.transaction_repository import TransactionRepository

# (period label -> horizon in days), matching master-prompt Rule 15:
# "Forecast: next 7 days, next 30 days, next 3 months."
PERIODS: dict[str, int] = {"7d": 7, "30d": 30, "90d": 90}

# Loaded once at process start and reused across requests, same rationale
# as the categorization/anomaly singletons.
_forecaster = ExpenseForecaster()


def get_forecaster_status() -> tuple[bool, int | None]:
    """Used by GET /api/v1/ml/models to report registry status."""
    return _forecaster.is_ready, _forecaster.active_version


def _to_daily_totals(transactions) -> dict[date, float]:
    totals: dict[date, float] = defaultdict(float)
    for txn in transactions:
        txn_date = txn.transaction_date
        day = txn_date.date() if isinstance(txn_date, datetime) else txn_date
        totals[day] += txn.amount
    return dict(totals)


class ForecastService:
    def __init__(
        self, transaction_repo: TransactionRepository, forecast_repo: ForecastRepository
    ) -> None:
        self._transaction_repo = transaction_repo
        self._forecast_repo = forecast_repo
        self._forecaster = _forecaster

    def generate_for_user(self, user_id: str) -> dict:
        transactions = [
            t
            for t in self._transaction_repo.list_all_for_user(user_id)
            if t.transaction_type == "debit"
        ]
        daily_totals = _to_daily_totals(transactions)

        if not self._forecaster.is_ready:
            return {
                "status": "model_unavailable",
                "message": "No trained forecasting model is available yet.",
                "periods": {},
            }

        distinct_days = len(daily_totals)
        if distinct_days < MIN_HISTORY_DAYS:
            for period in PERIODS:
                self._forecast_repo.clear_period(user_id, period)
            return {
                "status": "insufficient_data",
                "message": (
                    f"Insufficient historical data for reliable forecast. "
                    f"Need at least {MIN_HISTORY_DAYS} days of transaction history "
                    f"(have {distinct_days})."
                ),
                "periods": {},
            }

        periods_result: dict[str, dict] = {}
        for period, horizon_days in PERIODS.items():
            result = self._forecaster.forecast(daily_totals, horizon_days)
            if result is None:
                self._forecast_repo.clear_period(user_id, period)
                continue

            doc = ForecastDocument(
                user_id=user_id,
                period=period,
                method=result.method,
                daily_predictions=result.daily_predictions,
                predicted_total=result.predicted_total,
                start_date=result.start_date,
                end_date=result.end_date,
            )
            self._forecast_repo.replace_for_period(user_id, period, doc)
            periods_result[period] = {
                "predicted_total": result.predicted_total,
                "method": result.method,
            }

        return {
            "status": "completed",
            "message": f"Generated forecasts for {len(periods_result)} period(s).",
            "periods": periods_result,
        }
