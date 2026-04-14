"""JWT encode/decode using python-jose (HS256)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from jose import jwt

from app.config import get_settings

ALGORITHM = "HS256"
TOKEN_TYPE_ACCESS = "access"
TOKEN_TYPE_REFRESH = "refresh"


def _now() -> datetime:
    return datetime.now(UTC)


def _encode(
    user_id: UUID | str,
    token_type: str,
    expires_delta: timedelta,
) -> str:
    settings = get_settings()
    now = _now()
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "type": token_type,
        "iat": int(now.timestamp()),
        "exp": int((now + expires_delta).timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)


def create_access_token(
    user_id: UUID | str,
    expires_delta: timedelta | None = None,
) -> str:
    settings = get_settings()
    delta = expires_delta or timedelta(minutes=settings.jwt_access_expires_minutes)
    return _encode(user_id, TOKEN_TYPE_ACCESS, delta)


def create_refresh_token(
    user_id: UUID | str,
    expires_delta: timedelta | None = None,
) -> str:
    settings = get_settings()
    delta = expires_delta or timedelta(days=settings.jwt_refresh_expires_days)
    return _encode(user_id, TOKEN_TYPE_REFRESH, delta)


def decode_token(token: str) -> dict[str, Any]:
    """Decode a JWT. Raises `jose.JWTError` (or subclass) on invalid/expired."""
    settings = get_settings()
    return jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM])
