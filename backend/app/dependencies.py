"""FastAPI dependency providers: database access and current-user resolution."""

from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pymongo.database import Database

from app.database import mongodb
from app.models.user import UserDocument
from app.repositories.user_repository import UserRepository
from app.utils.security import decode_access_token

_bearer_scheme = HTTPBearer(auto_error=False)


def get_database() -> Database:
    return mongodb.get_database()


def get_user_repository(db: Annotated[Database, Depends(get_database)]) -> UserRepository:
    return UserRepository(db)


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)],
    user_repo: Annotated[UserRepository, Depends(get_user_repository)],
) -> UserDocument:
    if credentials is None:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = decode_access_token(credentials.credentials)
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except jwt.InvalidTokenError as exc:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token payload")

    user = user_repo.get_by_id(user_id)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User no longer exists")
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "User account is disabled")
    return user
