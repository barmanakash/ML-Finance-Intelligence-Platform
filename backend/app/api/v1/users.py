"""GET /api/v1/users/me."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.dependencies import get_current_user
from app.models.user import UserDocument
from app.schemas.user import UserResponse

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserResponse, summary="Get the current authenticated user")
def get_me(current_user: Annotated[UserDocument, Depends(get_current_user)]) -> UserResponse:
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        is_active=current_user.is_active,
        created_at=current_user.created_at,
    )
