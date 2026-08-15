"""Data-access layer for the `transactions` collection."""

from typing import Any

from bson import ObjectId
from pymongo import DESCENDING
from pymongo.database import Database

from app.models.transaction import TransactionDocument


class TransactionRepository:
    def __init__(self, db: Database) -> None:
        self._collection = db["transactions"]

    def bulk_create(self, transactions: list[TransactionDocument]) -> int:
        if not transactions:
            return 0
        payload = [t.model_dump(by_alias=True, exclude={"id"}) for t in transactions]
        result = self._collection.insert_many(payload)
        return len(result.inserted_ids)

    def list_for_user(
        self,
        user_id: str,
        *,
        skip: int = 0,
        limit: int = 50,
        category: str | None = None,
        transaction_type: str | None = None,
        import_id: str | None = None,
    ) -> tuple[list[TransactionDocument], int]:
        query: dict[str, Any] = {"user_id": user_id}
        if category:
            query["category"] = category
        if transaction_type:
            query["transaction_type"] = transaction_type
        if import_id:
            query["import_id"] = import_id

        total = self._collection.count_documents(query)
        cursor = (
            self._collection.find(query)
            .sort("transaction_date", DESCENDING)
            .skip(skip)
            .limit(limit)
        )
        items = [self._to_model(doc) for doc in cursor]
        return items, total

    def get_by_id(self, transaction_id: str, user_id: str) -> TransactionDocument | None:
        if not ObjectId.is_valid(transaction_id):
            return None
        doc = self._collection.find_one({"_id": ObjectId(transaction_id), "user_id": user_id})
        return self._to_model(doc) if doc else None

    def list_all_for_user(self, user_id: str) -> list[TransactionDocument]:
        """Fetch a user's complete transaction history, unpaginated.

        Used by anomaly detection, which needs full context (every
        merchant/category the user has ever transacted with) to compute
        correct z-score baselines — a paginated page would silently corrupt
        those statistics.
        """
        cursor = self._collection.find({"user_id": user_id})
        return [self._to_model(doc) for doc in cursor]

    def update_anomaly_fields(self, transaction_id: str, is_anomaly: bool, anomaly_score: float) -> None:
        if not ObjectId.is_valid(transaction_id):
            return
        self._collection.update_one(
            {"_id": ObjectId(transaction_id)},
            {"$set": {"is_anomaly": is_anomaly, "anomaly_score": anomaly_score}},
        )

    @staticmethod
    def _to_model(doc: dict[str, Any]) -> TransactionDocument:
        doc = dict(doc)
        doc["_id"] = str(doc["_id"])
        return TransactionDocument.model_validate(doc)
