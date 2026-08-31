"""Data-access layer for the `recurring_transactions` collection."""

from typing import Any

from bson import ObjectId
from pymongo import DESCENDING
from pymongo.database import Database

from app.models.recurring import RecurringDocument


class RecurringRepository:
    def __init__(self, db: Database) -> None:
        self._collection = db["recurring_transactions"]

    def replace_all_for_user(self, user_id: str, patterns: list[RecurringDocument]) -> int:
        """Wipes this user's previously detected recurring patterns and
        inserts the freshly recomputed set. Detection always re-evaluates a
        user's *entire* history in one pass (see
        RecurringDetectionService.detect_for_user), so this collection
        should reflect only the latest scan — otherwise stale patterns from
        merchants the user no longer transacts with would accumulate
        forever.
        """
        self._collection.delete_many({"user_id": user_id})
        if not patterns:
            return 0
        payload = [p.model_dump(by_alias=True, exclude={"id"}) for p in patterns]
        result = self._collection.insert_many(payload)
        return len(result.inserted_ids)

    def list_for_user(
        self, user_id: str, *, skip: int = 0, limit: int = 50
    ) -> tuple[list[RecurringDocument], int]:
        query: dict[str, Any] = {"user_id": user_id}
        total = self._collection.count_documents(query)
        cursor = (
            self._collection.find(query)
            .sort("confidence", DESCENDING)
            .skip(skip)
            .limit(limit)
        )
        return [self._to_model(d) for d in cursor], total

    def get_by_id(self, recurring_id: str, user_id: str) -> RecurringDocument | None:
        if not ObjectId.is_valid(recurring_id):
            return None
        doc = self._collection.find_one({"_id": ObjectId(recurring_id), "user_id": user_id})
        return self._to_model(doc) if doc else None

    @staticmethod
    def _to_model(doc: dict[str, Any]) -> RecurringDocument:
        doc = dict(doc)
        doc["_id"] = str(doc["_id"])
        return RecurringDocument.model_validate(doc)
