"""Data-access layer for the `users` collection.

No PyMongo queries should live outside of this file for user data — routes
and services depend on this repository, never on the collection directly.
"""

from typing import Any

from bson import ObjectId
from pymongo.database import Database
from pymongo.errors import DuplicateKeyError

from app.models.user import UserDocument


class UserRepository:
    def __init__(self, db: Database) -> None:
        self._collection = db["users"]

    def create(self, user: UserDocument) -> UserDocument:
        payload = user.model_dump(by_alias=True, exclude={"id"})
        try:
            result = self._collection.insert_one(payload)
        except DuplicateKeyError as exc:
            raise ValueError("A user with this email already exists") from exc
        return user.model_copy(update={"id": str(result.inserted_id)})

    def get_by_email(self, email: str) -> UserDocument | None:
        doc = self._collection.find_one({"email": email})
        return self._to_model(doc)

    def get_by_id(self, user_id: str) -> UserDocument | None:
        if not ObjectId.is_valid(user_id):
            return None
        doc = self._collection.find_one({"_id": ObjectId(user_id)})
        return self._to_model(doc)

    @staticmethod
    def _to_model(doc: dict[str, Any] | None) -> UserDocument | None:
        if doc is None:
            return None
        doc = dict(doc)
        doc["_id"] = str(doc["_id"])
        return UserDocument.model_validate(doc)
