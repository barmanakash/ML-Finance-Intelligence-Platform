"""Request/response schemas for /api/v1/categories."""

from datetime import datetime

from pydantic import BaseModel, Field


class CategoryResponse(BaseModel):
    id: str
    name: str
    is_default: bool
    created_at: datetime


class CategoryListResponse(BaseModel):
    items: list[CategoryResponse]


class CategoryCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=50)
