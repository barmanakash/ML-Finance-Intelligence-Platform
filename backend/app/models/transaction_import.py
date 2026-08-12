"""MongoDB document schema for the `transaction_imports` collection."""

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field


class ImportRowError(BaseModel):
    row: int
    message: str


class TransactionImportDocument(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str | None = Field(default=None, alias="_id")
    user_id: str
    filename: str
    file_hash: str
    status: str  # "completed" | "partial" | "failed"
    total_rows: int
    imported_rows: int
    failed_rows: int
    errors: list[ImportRowError] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
