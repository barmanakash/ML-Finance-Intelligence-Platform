"""MongoDB document schema for the `users` collection."""

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserDocument(BaseModel):
    """Internal representation of a user document. Never returned directly
    from the API — see `app.schemas.user.UserResponse` for the public shape.
    """

    model_config = ConfigDict(populate_by_name=True)

    id: str | None = Field(default=None, alias="_id")
    email: EmailStr
    hashed_password: str
    full_name: str
    is_active: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
