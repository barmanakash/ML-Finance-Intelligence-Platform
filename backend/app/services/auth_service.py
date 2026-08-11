"""Business logic for registration and login.

Routes depend on this service, never on the repository directly, so HTTP
concerns stay out of the business logic.
"""

from app.config import get_settings
from app.exceptions import ConflictError, UnauthorizedError
from app.models.user import UserDocument
from app.repositories.user_repository import UserRepository
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse
from app.utils.security import create_access_token, hash_password, verify_password


class AuthService:
    def __init__(self, user_repo: UserRepository) -> None:
        self._user_repo = user_repo

    def register(self, payload: RegisterRequest) -> UserDocument:
        existing = self._user_repo.get_by_email(payload.email)
        if existing is not None:
            raise ConflictError("A user with this email is already registered")

        user = UserDocument(
            email=payload.email,
            hashed_password=hash_password(payload.password),
            full_name=payload.full_name,
        )
        return self._user_repo.create(user)

    def authenticate(self, payload: LoginRequest) -> TokenResponse:
        user = self._user_repo.get_by_email(payload.email)
        if user is None or not verify_password(payload.password, user.hashed_password):
            raise UnauthorizedError("Incorrect email or password")
        if not user.is_active:
            raise UnauthorizedError("User account is disabled")

        settings = get_settings()
        token = create_access_token(subject=user.id)
        return TokenResponse(
            access_token=token,
            expires_in=settings.jwt_access_token_expire_minutes * 60,
        )
