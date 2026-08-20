"""Data-access layer for the `anomalies` collection."""

from typing import Any

from bson import ObjectId
from pymongo import DESCENDING
from pymongo.database import Database

from app.models.anomaly import AnomalyDocument


class AnomalyRepository:
    def __init__(self, db: Database) -> None:
        self._collection = db["anomalies"]

    def replace_all_for_user(self, user_id: str, anomalies: list[AnomalyDocument]) -> int:
        """Wipes this user's previous anomaly records and inserts the
        freshly recomputed set. Anomaly detection always re-scores a user's
        *entire* history in one pass (see
        AnomalyDetectionService.detect_for_user), so the anomalies
        collection should reflect only the latest scan — otherwise stale
        records from earlier scans would accumulate forever.
        """
        self._collection.delete_many({"user_id": user_id})
        if not anomalies:
            return 0
        payload = [a.model_dump(by_alias=True, exclude={"id"}) for a in anomalies]
        result = self._collection.insert_many(payload)
        return len(result.inserted_ids)

    def list_for_user(
        self, user_id: str, *, skip: int = 0, limit: int = 50, severity: str | None = None
    ) -> tuple[list[AnomalyDocument], int]:
        query: dict[str, Any] = {"user_id": user_id}
        if severity:
            query["severity"] = severity
        total = self._collection.count_documents(query)
        cursor = self._collection.find(query).sort("created_at", DESCENDING).skip(skip).limit(limit)
        return [self._to_model(d) for d in cursor], total

    def get_by_id(self, anomaly_id: str, user_id: str) -> AnomalyDocument | None:
        if not ObjectId.is_valid(anomaly_id):
            return None
        doc = self._collection.find_one({"_id": ObjectId(anomaly_id), "user_id": user_id})
        return self._to_model(doc) if doc else None

    @staticmethod
    def _to_model(doc: dict[str, Any]) -> AnomalyDocument:
        doc = dict(doc)
        doc["_id"] = str(doc["_id"])
        return AnomalyDocument.model_validate(doc)
