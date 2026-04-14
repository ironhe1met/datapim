"""Auth business logic — authenticate, fetch by id."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.security.passwords import verify_password


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    """Case-insensitive lookup."""
    stmt = select(User).where(func.lower(User.email) == email.lower())
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_user_by_id(db: AsyncSession, user_id: UUID) -> User | None:
    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def authenticate(db: AsyncSession, email: str, password: str) -> User | None:
    """Return User on success (active + valid password), else None.

    Note: callers should differentiate between "not found / wrong password" (→ 401)
    and "found but is_active=False" (→ 403). This helper returns None for the
    wrong-credentials case. Use `get_user_by_email` + `verify_password` directly
    if you need to distinguish inactive users.
    """
    user = await get_user_by_email(db, email)
    if user is None:
        return None
    if not user.is_active:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user
