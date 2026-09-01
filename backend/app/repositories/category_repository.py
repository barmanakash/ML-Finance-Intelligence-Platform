"""Data-access layer for the `categories` collection."""

from typing import Any

from bson import ObjectId
from pymongo import ASCENDING
from pymongo.database import Database

from app.models.category import DEFAULT_CATEGORY_NAMES, CategoryDocument


class CategoryRepository:
    def __init__(self, db: Database) -> None:
        self._collection = db["categories"]

    def ensure_defaults_seeded(self) -> None:
        """Idempotently inserts the system-default categories (user_id=None)
        if they don't already exist. Safe to call on every app startup —
        see app.main's lifespan — since it only inserts names that are
        missing, relying on the (name, user_id) unique index as a
        second line of defense against races.
        """
        existing = {
            doc["name"] for doc in self._collection.find({"user_id": None}, {"name": 1})
        }
        missing = [name for name in DEFAULT_CATEGORY_NAMES if name not in existing]
        if not missing:
            return
        docs = [
            CategoryDocument(user_id=None, name=name, is_default=True).model_dump(
                by_alias=True, exclude={"id"}
            )
            for name in missing
        ]
        self._collection.insert_many(docs)

    def list_for_user(self, user_id: str) -> list[CategoryDocument]:
        """System defaults plus this user's own custom categories, sorted
        alphabetically with defaults first.
        """
        cursor = self._collection.find(
            {"$or": [{"user_id": None}, {"user_id": user_id}]}
        ).sort([("is_default", -1), ("name", ASCENDING)])
        return [self._to_model(d) for d in cursor]

    def create_custom(self, user_id: str, name: str) -> CategoryDocument:
        doc = CategoryDocument(user_id=user_id, name=name, is_default=False)
        result = self._collection.insert_one(doc.model_dump(by_alias=True, exclude={"id"}))
        doc.id = str(result.inserted_id)
        return doc

    def get_by_id(self, category_id: str, user_id: str) -> CategoryDocument | None:
        if not ObjectId.is_valid(category_id):
            return None
        doc = self._collection.find_one({"_id": ObjectId(category_id), "user_id": user_id})
        return self._to_model(doc) if doc else None

    def delete_custom(self, category_id: str, user_id: str) -> bool:
        """Only deletes a category owned by this user — system defaults
        (user_id=None) never match this filter, so they can't be deleted
        through this method regardless of what id is passed in.
        """
        if not ObjectId.is_valid(category_id):
            return False
        result = self._collection.delete_one({"_id": ObjectId(category_id), "user_id": user_id})
        return result.deleted_count > 0

    def name_exists_for_user(self, user_id: str, name: str) -> bool:
        return (
            self._collection.count_documents(
                {"name": name, "$or": [{"user_id": None}, {"user_id": user_id}]}
            )
            > 0
        )

    @staticmethod
    def _to_model(doc: dict[str, Any]) -> CategoryDocument:
        doc = dict(doc)
        doc["_id"] = str(doc["_id"])
        return CategoryDocument.model_validate(doc)
