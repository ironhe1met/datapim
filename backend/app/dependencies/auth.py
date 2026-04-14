"""FastAPI auth dependencies — current user + role guard."""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from typing import Any
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models.user import User
from app.security.jwt import TOKEN_TYPE_ACCESS, decode_token
from app.services.auth_service import get_user_by_id

bearer_scheme = HTTPBearer(auto_error=False)


def _unauthorized(detail: str = "Unauthorized") -> HTTPException:
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_session),
) -> User:
    if credentials is None:
        raise _unauthorized("Missing Authorization header")

    token = credentials.credentials
    try:
        payload = decode_token(token)
    except JWTError as exc:
        # expired tokens raise ExpiredSignatureError (subclass of JWTError)
        raise _unauthorized("Invalid or expired token") from exc

    if payload.get("type") != TOKEN_TYPE_ACCESS:
        raise _unauthorized("Wrong token type")

    sub = payload.get("sub")
    if not sub:
        raise _unauthorized("Invalid token payload")

    try:
        user_id = UUID(sub)
    except (TypeError, ValueError) as exc:
        raise _unauthorized("Invalid token subject") from exc

    user = await get_user_by_id(db, user_id)
    if user is None:
        raise _unauthorized("User not found")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Акаунт деактивовано")

    return user


def require_role(
    *allowed_roles: str,
) -> Callable[[User], Coroutine[Any, Any, User]]:
    """Return a dependency that enforces the user's role is one of `allowed_roles`."""

    allowed = set(allowed_roles)

    async def _dep(user: User = Depends(get_current_user)) -> User:
        role_value = user.role.value if hasattr(user.role, "value") else str(user.role)
        if role_value not in allowed:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
        return user

    return _dep
