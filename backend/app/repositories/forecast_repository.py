"""Data-access layer for the `expense_forecasts` collection."""

from typing import Any

from pymongo.database import Database

from app.models.forecast import ForecastDocument


class ForecastRepository:
    def __init__(self, db: Database) -> None:
        self._collection = db["expense_forecasts"]

    def replace_for_period(self, user_id: str, period: str, forecast: ForecastDocument) -> None:
        """A forecast is a point-in-time snapshot re-derived from the
        user's current transaction history — keeping old forecasts around
        would just be stale predictions, so each re-run replaces the
        single document for that (user, period) pair.
        """
        self._collection.delete_many({"user_id": user_id, "period": period})
        payload = forecast.model_dump(by_alias=True, exclude={"id"})
        self._collection.insert_one(payload)

    def clear_period(self, user_id: str, period: str) -> None:
        """Used when a period can no longer be forecast (e.g. the user's
        history dropped below the minimum) so a stale forecast isn't left
        behind implying more confidence than currently exists.
        """
        self._collection.delete_many({"user_id": user_id, "period": period})

    def list_for_user(self, user_id: str) -> list[ForecastDocument]:
        cursor = self._collection.find({"user_id": user_id})
        return [self._to_model(d) for d in cursor]

    def get_by_period(self, user_id: str, period: str) -> ForecastDocument | None:
        doc = self._collection.find_one({"user_id": user_id, "period": period})
        return self._to_model(doc) if doc else None

    @staticmethod
    def _to_model(doc: dict[str, Any]) -> ForecastDocument:
        doc = dict(doc)
        doc["_id"] = str(doc["_id"])
        return ForecastDocument.model_validate(doc)
