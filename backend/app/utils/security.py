"""Password hashing (Argon2id via pwdlib) and JWT issuing/verification."""

from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from pwdlib import PasswordHash

from app.config import get_settings

# PasswordHash.recommended() uses Argon2id as the primary hasher.
_password_hasher = PasswordHash.recommended()


def hash_password(password: str) -> str:
    return _password_hasher.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    return _password_hasher.verify(password, hashed)


def create_access_token(subject: str, expires_minutes: int | None = None) -> str:
    """Issue a signed JWT for `subject` (the user's id)."""
    settings = get_settings()
    minutes = (
    expires_minutes
    if expires_minutes is not None
    else settings.jwt_access_token_expire_minutes
)
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": subject,
        "iat": now,
        "exp": now + timedelta(minutes=minutes),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode and verify a JWT. Raises jwt.PyJWTError subclasses on failure."""
    settings = get_settings()
    return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
