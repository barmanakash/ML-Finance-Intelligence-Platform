"""POST /api/v1/auth/register, /login, /logout."""

from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.dependencies import get_current_user, get_user_repository
from app.models.user import UserDocument
from app.repositories.user_repository import UserRepository
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse
from app.schemas.user import UserResponse
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


def get_auth_service(
    user_repo: Annotated[UserRepository, Depends(get_user_repository)],
) -> AuthService:
    return AuthService(user_repo)


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
)
def register(
    payload: RegisterRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> UserResponse:
    user = auth_service.register(payload)
    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        created_at=user.created_at,
    )


@router.post("/login", response_model=TokenResponse, summary="Exchange credentials for a JWT")
def login(
    payload: LoginRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> TokenResponse:
    return auth_service.authenticate(payload)


@router.post("/logout", summary="Sign out the current session")
def logout(current_user: Annotated[UserDocument, Depends(get_current_user)]) -> dict[str, str]:
    # JWT auth is stateless: logging out means the client discards its token.
    # This endpoint exists as a single, auditable place for clients to call on sign-out.
    return {"message": "Logged out successfully"}
