"""Products CRUD endpoints (Phase 5).

Scope (R-020 for v1.0):
- Read: any authenticated user.
- PATCH custom_*: admin, operator.
- POST reset-field: admin, operator.
- No create (v1.1), no delete (R-014 — products are never deleted).
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.dependencies.auth import get_current_user, require_role
from app.models.user import User
from app.schemas.product import (
    ProductDetail,
    ProductListItem,
    ProductListResponse,
    ProductUpdate,
    ResetFieldRequest,
)
from app.services import product_service
from app.utils.pagination import build_meta

router = APIRouter()


@router.get("", response_model=ProductListResponse)
async def list_products(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    search: str | None = Query(None),
    category_id: UUID | None = Query(None),
    in_stock: bool | None = Query(None),
    enrichment_status: str | None = Query(None, pattern="^(none|partial|full)$"),
    has_pending_review: bool | None = Query(None),
    sort_by: str = Query("created_at", pattern="^(name|price|created_at)$"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    db: AsyncSession = Depends(get_session),
    _user: User = Depends(get_current_user),
) -> ProductListResponse:
    items, total = await product_service.list_products(
        db,
        page=page,
        per_page=per_page,
        search=search,
        category_id=category_id,
        in_stock=in_stock,
        enrichment_status=enrichment_status,
        has_pending_review=has_pending_review,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    data: list[ProductListItem] = items
    return ProductListResponse(
        data=data,
        meta=build_meta(total=total, page=page, per_page=per_page),
    )


@router.get("/{product_id}", response_model=ProductDetail)
async def get_product(
    product_id: UUID,
    db: AsyncSession = Depends(get_session),
    _user: User = Depends(get_current_user),
) -> ProductDetail:
    product = await product_service.get_product(db, product_id)
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "Товар не знайдено", "code": "NOT_FOUND"},
        )
    return await product_service.build_product_detail(db, product)


@router.patch("/{product_id}", response_model=ProductDetail)
async def update_product(
    product_id: UUID,
    body: ProductUpdate,
    db: AsyncSession = Depends(get_session),
    actor: User = Depends(require_role("admin", "operator")),
) -> ProductDetail:
    product = await product_service.update_product(db, product_id, body)
    logger.info(
        "product_updated",
        product_id=str(product.id),
        actor_id=str(actor.id),
        fields=list(body.model_fields_set),
    )
    return await product_service.build_product_detail(db, product)


@router.post("/{product_id}/reset-field", response_model=ProductDetail)
async def reset_product_field(
    product_id: UUID,
    body: ResetFieldRequest,
    db: AsyncSession = Depends(get_session),
    actor: User = Depends(require_role("admin", "operator")),
) -> ProductDetail:
    product = await product_service.reset_field(db, product_id, body.field)
    logger.info(
        "product_field_reset",
        product_id=str(product.id),
        field=body.field,
        actor_id=str(actor.id),
    )
    return await product_service.build_product_detail(db, product)
