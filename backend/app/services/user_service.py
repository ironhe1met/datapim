"""User CRUD business logic."""

from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserRole
from app.schemas.user import UserCreate, UserUpdate
from app.security.passwords import hash_password
from app.utils.pagination import offset_limit


async def list_users(
    db: AsyncSession,
    page: int,
    per_page: int,
    search: str | None = None,
    role: str | None = None,
    is_active: bool | None = None,
) -> tuple[list[User], int]:
    """Return (items, total) matching the given filters, ordered by created_at DESC."""
    filters = []
    if search:
        pattern = f"%{search.lower()}%"
        filters.append(
            or_(
                func.lower(User.email).like(pattern),
                func.lower(User.name).like(pattern),
            )
        )
    if role is not None:
        filters.append(User.role == UserRole(role))
    if is_active is not None:
        filters.append(User.is_active == is_active)

    count_stmt = select(func.count(User.id))
    if filters:
        count_stmt = count_stmt.where(*filters)
    total = (await db.execute(count_stmt)).scalar_one()

    offset, limit = offset_limit(page, per_page)
    stmt = select(User)
    if filters:
        stmt = stmt.where(*filters)
    stmt = stmt.order_by(User.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(stmt)
    items = list(result.scalars().all())
    return items, int(total)


async def get_user(db: AsyncSession, user_id: UUID) -> User | None:
    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def _email_taken(
    db: AsyncSession, email: str, *, exclude_user_id: UUID | None = None
) -> bool:
    stmt = select(User.id).where(func.lower(User.email) == email.lower())
    if exclude_user_id is not None:
        stmt = stmt.where(User.id != exclude_user_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none() is not None


def _duplicate_email_exc() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail={"error": "Email вже зайнятий", "code": "DUPLICATE_EMAIL"},
    )


def _not_found_exc() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={"error": "Користувача не знайдено", "code": "NOT_FOUND"},
    )


async def create_user(db: AsyncSession, data: UserCreate) -> User:
    if await _email_taken(db, data.email):
        raise _duplicate_email_exc()

    user = User(
        email=data.email,
        password_hash=hash_password(data.password),
        name=data.name,
        role=UserRole(data.role.value),
        is_active=True,
        theme="light",
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def update_user(db: AsyncSession, user_id: UUID, data: UserUpdate) -> User:
    user = await get_user(db, user_id)
    if user is None:
        raise _not_found_exc()

    if data.email is not None and data.email.lower() != user.email.lower():
        if await _email_taken(db, data.email, exclude_user_id=user.id):
            raise _duplicate_email_exc()
        user.email = data.email

    if data.name is not None:
        user.name = data.name

    if data.role is not None:
        user.role = UserRole(data.role.value)

    if data.password is not None:
        user.password_hash = hash_password(data.password)

    if data.is_active is not None:
        user.is_active = data.is_active

    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def deactivate_user(db: AsyncSession, user_id: UUID) -> User:
    user = await get_user(db, user_id)
    if user is None:
        raise _not_found_exc()

    if user.is_active:
        user.is_active = False
        db.add(user)
        await db.commit()
        await db.refresh(user)
    return user
