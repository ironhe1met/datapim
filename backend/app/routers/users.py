"""Users CRUD endpoints (admin-only create/update/delete; admin+manager read)."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.dependencies.auth import require_role
from app.models.user import User
from app.schemas.user import (
    UserCreate,
    UserListResponse,
    UserRead,
    UserUpdate,
)
from app.services import user_service
from app.utils.pagination import build_meta

router = APIRouter()


@router.get("", response_model=UserListResponse)
async def list_users(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    search: str | None = Query(None),
    role: str | None = Query(None),
    is_active: bool | None = Query(None),
    db: AsyncSession = Depends(get_session),
    _user: User = Depends(require_role("admin", "manager")),
) -> UserListResponse:
    items, total = await user_service.list_users(
        db,
        page=page,
        per_page=per_page,
        search=search,
        role=role,
        is_active=is_active,
    )
    return UserListResponse(
        data=[UserRead.model_validate(u) for u in items],
        meta=build_meta(total=total, page=page, per_page=per_page),
    )


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def create_user(
    body: UserCreate,
    db: AsyncSession = Depends(get_session),
    actor: User = Depends(require_role("admin")),
) -> UserRead:
    user = await user_service.create_user(db, body)
    logger.info(
        "user_created",
        user_id=str(user.id),
        email=user.email,
        role=user.role.value,
        actor_id=str(actor.id),
    )
    return UserRead.model_validate(user)


@router.get("/{user_id}", response_model=UserRead)
async def get_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_session),
    _user: User = Depends(require_role("admin", "manager")),
) -> UserRead:
    user = await user_service.get_user(db, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "Користувача не знайдено", "code": "NOT_FOUND"},
        )
    return UserRead.model_validate(user)


@router.patch("/{user_id}", response_model=UserRead)
async def update_user(
    user_id: UUID,
    body: UserUpdate,
    db: AsyncSession = Depends(get_session),
    actor: User = Depends(require_role("admin")),
) -> UserRead:
    user = await user_service.update_user(db, user_id, body)
    logger.info(
        "user_updated",
        user_id=str(user.id),
        actor_id=str(actor.id),
    )
    return UserRead.model_validate(user)


@router.delete("/{user_id}")
async def deactivate_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_session),
    actor: User = Depends(require_role("admin")),
) -> dict[str, str]:
    if actor.id == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "Cannot deactivate yourself", "code": "SELF_DEACTIVATE"},
        )
    await user_service.deactivate_user(db, user_id)
    logger.info("user_deactivated", user_id=str(user_id), actor_id=str(actor.id))
    return {"message": "User deactivated"}
