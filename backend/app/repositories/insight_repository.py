"""Data-access layer for the `insights` collection."""

from typing import Any

from bson import ObjectId
from pymongo import DESCENDING
from pymongo.database import Database

from app.models.insight import InsightDocument


class InsightRepository:
    def __init__(self, db: Database) -> None:
        self._collection = db["insights"]

    def replace_all_for_user(self, user_id: str, insights: list[InsightDocument]) -> int:
        self._collection.delete_many({"user_id": user_id})
        if not insights:
            return 0
        payload = [i.model_dump(by_alias=True, exclude={"id"}) for i in insights]
        result = self._collection.insert_many(payload)
        return len(result.inserted_ids)

    def list_for_user(self, user_id: str) -> list[InsightDocument]:
        cursor = self._collection.find({"user_id": user_id}).sort("created_at", DESCENDING)
        return [self._to_model(d) for d in cursor]

    def get_by_id(self, insight_id: str, user_id: str) -> InsightDocument | None:
        if not ObjectId.is_valid(insight_id):
            return None
        doc = self._collection.find_one({"_id": ObjectId(insight_id), "user_id": user_id})
        return self._to_model(doc) if doc else None

    @staticmethod
    def _to_model(doc: dict[str, Any]) -> InsightDocument:
        doc = dict(doc)
        doc["_id"] = str(doc["_id"])
        return InsightDocument.model_validate(doc)
