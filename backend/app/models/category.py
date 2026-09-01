"""MongoDB document schema for the `categories` collection.

System-default categories have `user_id = None`; a user can additionally
add their own custom categories (`user_id` set), matching the unique
index on (name, user_id) in scripts/create_indexes.py. Users cannot delete
or rename system defaults — only their own custom entries — so the
category list transaction categorization relies on can't be silently
broken by an accidental delete.
"""

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field

# Mirrors the label set ml/datasets/generate_categorization_dataset.py
# trains the classifier on (master-prompt Rule 11). Kept as a plain
# constant here rather than importing from ml/ — this is presentation-layer
# data (what a user can pick from), not a model artifact, and the backend
# shouldn't take on an ml/ import just to read a list of strings.
DEFAULT_CATEGORY_NAMES: list[str] = [
    "Food",
    "Groceries",
    "Transportation",
    "Travel",
    "Shopping",
    "Entertainment",
    "Bills",
    "Utilities",
    "Healthcare",
    "Education",
    "Rent",
    "Salary",
    "Investment",
    "Transfer",
    "Subscription",
    "Cash Withdrawal",
    "Other",
]


class CategoryDocument(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str | None = Field(default=None, alias="_id")
    user_id: str | None = None  # None = system default, visible to everyone
    name: str
    is_default: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
