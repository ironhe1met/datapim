"""Categories CRUD endpoints.

Read access: any authenticated user (admin, operator, manager, viewer).
Write access (create/update): admin, operator.
No delete — categories are import-driven (R-015).
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.dependencies.auth import get_current_user, require_role
from app.models.user import User
from app.schemas.category import (
    CategoryCreate,
    CategoryDetail,
    CategoryListResponse,
    CategoryRead,
    CategoryTreeResponse,
    CategoryUpdate,
)
from app.services import category_service

router = APIRouter()


@router.get("")
async def list_categories(
    tree: bool = Query(False),
    db: AsyncSession = Depends(get_session),
    _user: User = Depends(get_current_user),
) -> CategoryTreeResponse | CategoryListResponse:
    if tree:
        nodes = await category_service.list_categories_tree(db)
        return CategoryTreeResponse(data=nodes)

    items = await category_service.list_categories_flat(db)
    return CategoryListResponse(data=[CategoryRead.model_validate(c) for c in items])


@router.get("/{category_id}", response_model=CategoryDetail)
async def get_category(
    category_id: UUID,
    db: AsyncSession = Depends(get_session),
    _user: User = Depends(get_current_user),
) -> CategoryDetail:
    category, children, breadcrumb = await category_service.get_category_with_details(
        db, category_id
    )
    return CategoryDetail(
        id=category.id,
        external_id=category.external_id,
        name=category.name,
        parent_id=category.parent_id,
        is_active=category.is_active,
        product_count=category.product_count,
        exclude_from_export=category.exclude_from_export,
        created_at=category.created_at,
        updated_at=category.updated_at,
        children=[{"id": c.id, "name": c.name, "product_count": c.product_count} for c in children],
        breadcrumb=[{"id": b.id, "name": b.name} for b in breadcrumb],
    )


@router.post("", response_model=CategoryRead, status_code=status.HTTP_201_CREATED)
async def create_category(
    body: CategoryCreate,
    db: AsyncSession = Depends(get_session),
    actor: User = Depends(require_role("admin", "operator")),
) -> CategoryRead:
    category = await category_service.create_category(db, body)
    logger.info(
        "category_created",
        category_id=str(category.id),
        external_id=category.external_id,
        parent_id=str(category.parent_id) if category.parent_id else None,
        actor_id=str(actor.id),
    )
    return CategoryRead.model_validate(category)


@router.patch("/{category_id}", response_model=CategoryRead)
async def update_category(
    category_id: UUID,
    body: CategoryUpdate,
    db: AsyncSession = Depends(get_session),
    actor: User = Depends(require_role("admin", "operator")),
) -> CategoryRead:
    category = await category_service.update_category(db, category_id, body)
    logger.info(
        "category_updated",
        category_id=str(category.id),
        actor_id=str(actor.id),
    )
    return CategoryRead.model_validate(category)


@router.delete("/{category_id}")
async def delete_category(
    category_id: UUID,
    db: AsyncSession = Depends(get_session),
    actor: User = Depends(require_role("admin")),
) -> dict[str, str]:
    await category_service.delete_category(db, category_id)
    logger.info("category_deleted", category_id=str(category_id), actor_id=str(actor.id))
    return {"message": "Category deleted"}
