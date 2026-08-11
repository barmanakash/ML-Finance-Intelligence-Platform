import jwt
import pytest

from app.utils.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_hash_password_produces_verifiable_hash():
    hashed = hash_password("correct-horse-battery-staple")
    assert hashed != "correct-horse-battery-staple"
    assert verify_password("correct-horse-battery-staple", hashed)


def test_verify_password_rejects_wrong_password():
    hashed = hash_password("correct-horse-battery-staple")
    assert not verify_password("wrong-password", hashed)


def test_access_token_roundtrip():
    token = create_access_token(subject="user-123")
    payload = decode_access_token(token)
    assert payload["sub"] == "user-123"


def test_expired_token_raises():
    token = create_access_token(subject="user-123", expires_minutes=-1)
    with pytest.raises(jwt.ExpiredSignatureError):
        decode_access_token(token)


def test_tampered_token_is_rejected():
    token = create_access_token(subject="user-123")
    tampered = token[:-1] + ("A" if token[-1] != "A" else "B")
    with pytest.raises(jwt.InvalidTokenError):
        decode_access_token(tampered)
