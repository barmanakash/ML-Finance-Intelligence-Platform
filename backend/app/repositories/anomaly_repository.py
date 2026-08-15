"""Data-access layer for the `anomalies` collection.

Anomaly detection is re-run over a user's full history whenever new
transactions are imported (see AnomalyDetectionService), since a new
transaction can shift what "normal" looks like for a merchant or category.
Records are kept in sync with the current detection pass via upsert-or-
delete, keyed on `transaction_id` (which has a unique index — see
scripts/create_indexes.py), rather than accumulating stale duplicates from
every re-run.
"""

from typing import Any

from bson import ObjectId
from pymongo import DESCENDING
from pymongo.database import Database

from app.models.anomaly import AnomalyDocument


class AnomalyRepository:
    def __init__(self, db: Database) -> None:
        self._collection = db["anomalies"]

    def upsert(self, anomaly: AnomalyDocument) -> None:
        payload = anomaly.model_dump(by_alias=True, exclude={"id"})
        self._collection.update_one(
            {"transaction_id": anomaly.transaction_id},
            {"$set": payload},
            upsert=True,
        )

    def delete_for_transaction(self, transaction_id: str) -> None:
        self._collection.delete_one({"transaction_id": transaction_id})

    def list_for_user(
        self, user_id: str, *, skip: int = 0, limit: int = 20, severity: str | None = None
    ) -> tuple[list[AnomalyDocument], int]:
        query: dict[str, Any] = {"user_id": user_id}
        if severity:
            query["severity"] = severity
        total = self._collection.count_documents(query)
        cursor = (
            self._collection.find(query)
            .sort("anomaly_score", DESCENDING)
            .skip(skip)
            .limit(limit)
        )
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
