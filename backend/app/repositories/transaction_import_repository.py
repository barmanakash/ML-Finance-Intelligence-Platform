"""Data-access layer for the `transaction_imports` collection."""

from typing import Any

from bson import ObjectId
from pymongo import DESCENDING
from pymongo.database import Database
from pymongo.errors import DuplicateKeyError

from app.models.transaction_import import TransactionImportDocument


class TransactionImportRepository:
    def __init__(self, db: Database) -> None:
        self._collection = db["transaction_imports"]

    def create(self, record: TransactionImportDocument) -> TransactionImportDocument:
        payload = record.model_dump(by_alias=True, exclude={"id"})
        try:
            result = self._collection.insert_one(payload)
        except DuplicateKeyError as exc:
            raise ValueError("This file has already been imported") from exc
        return record.model_copy(update={"id": str(result.inserted_id)})

    def get_by_hash(self, user_id: str, file_hash: str) -> TransactionImportDocument | None:
        doc = self._collection.find_one({"user_id": user_id, "file_hash": file_hash})
        return self._to_model(doc) if doc else None

    def list_for_user(
        self, user_id: str, *, skip: int = 0, limit: int = 20
    ) -> tuple[list[TransactionImportDocument], int]:
        query = {"user_id": user_id}
        total = self._collection.count_documents(query)
        cursor = self._collection.find(query).sort("created_at", DESCENDING).skip(skip).limit(limit)
        items = [self._to_model(doc) for doc in cursor]
        return items, total

    def get_by_id(self, import_id: str, user_id: str) -> TransactionImportDocument | None:
        if not ObjectId.is_valid(import_id):
            return None
        doc = self._collection.find_one({"_id": ObjectId(import_id), "user_id": user_id})
        return self._to_model(doc) if doc else None

    @staticmethod
    def _to_model(doc: dict[str, Any]) -> TransactionImportDocument:
        doc = dict(doc)
        doc["_id"] = str(doc["_id"])
        return TransactionImportDocument.model_validate(doc)
