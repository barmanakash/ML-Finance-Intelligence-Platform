"""GET /api/v1/categories, POST /api/v1/categories,
DELETE /api/v1/categories/{id}.

Category *logic* (what the default set is, uniqueness rules) lives in
app.models.category / app.repositories.category_repository — this module
only translates HTTP <-> repository calls (master-prompt Rule 11: "Do not
hardcode category logic inside the API").
"""

from typing import Annotated

from fastapi import APIRouter, Depends, status
from pymongo.database import Database

from app.dependencies import get_current_user, get_database
from app.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.models.category import CategoryDocument
from app.models.user import UserDocument
from app.repositories.category_repository import CategoryRepository
from app.schemas.category import CategoryCreateRequest, CategoryListResponse, CategoryResponse

router = APIRouter(prefix="/categories", tags=["categories"])


def _to_response(doc: CategoryDocument) -> CategoryResponse:
    return CategoryResponse(
        id=doc.id, name=doc.name, is_default=doc.is_default, created_at=doc.created_at
    )


@router.get(
    "", response_model=CategoryListResponse, summary="List system + custom categories"
)
def list_categories(
    current_user: Annotated[UserDocument, Depends(get_current_user)],
    db: Annotated[Database, Depends(get_database)],
) -> CategoryListResponse:
    repo = CategoryRepository(db)
    items = repo.list_for_user(current_user.id)
    return CategoryListResponse(items=[_to_response(i) for i in items])


@router.post(
    "",
    response_model=CategoryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a custom category",
)
def create_category(
    payload: CategoryCreateRequest,
    current_user: Annotated[UserDocument, Depends(get_current_user)],
    db: Annotated[Database, Depends(get_database)],
) -> CategoryResponse:
    repo = CategoryRepository(db)
    name = payload.name.strip()
    if repo.name_exists_for_user(current_user.id, name):
        raise ConflictError(f"A category named '{name}' already exists")
    created = repo.create_custom(current_user.id, name)
    return _to_response(created)


@router.delete(
    "/{category_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a custom category (system defaults cannot be deleted)",
)
def delete_category(
    category_id: str,
    current_user: Annotated[UserDocument, Depends(get_current_user)],
    db: Annotated[Database, Depends(get_database)],
) -> None:
    repo = CategoryRepository(db)
    existing = repo.get_by_id(category_id, current_user.id)
    if existing is None:
        # Could be a system default (user_id=None never matches get_by_id's
        # per-user filter) or a category belonging to someone else — either
        # way it can't be deleted through this endpoint.
        raise NotFoundError("Category not found, or it is a system default and cannot be deleted")
    if existing.is_default:
        raise ForbiddenError("System default categories cannot be deleted")
    repo.delete_custom(category_id, current_user.id)
