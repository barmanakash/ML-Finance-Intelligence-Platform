"""Request/response schemas for /api/v1/imports."""

from datetime import datetime

from pydantic import BaseModel


class ImportRowErrorResponse(BaseModel):
    row: int
    message: str


class ImportResponse(BaseModel):
    id: str
    filename: str
    status: str
    total_rows: int
    imported_rows: int
    failed_rows: int
    errors: list[ImportRowErrorResponse]
    created_at: datetime


class ImportListResponse(BaseModel):
    items: list[ImportResponse]
    total: int
    skip: int
    limit: int
