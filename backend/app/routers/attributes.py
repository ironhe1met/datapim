"""Product attribute CRUD endpoints."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, status
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.dependencies.auth import require_role
from app.models.user import User
from app.schemas.attribute import (
    AttributeCreate,
    AttributeListResponse,
    AttributeRead,
    AttributeUpdate,
)
from app.services import attribute_service

router = APIRouter(prefix="/api/products/{product_id}/attributes")


@router.get("", response_model=AttributeListResponse)
async def list_attributes(
    product_id: UUID,
    db: AsyncSession = Depends(get_session),
    _user: User = Depends(require_role("admin", "operator", "manager", "viewer")),
) -> AttributeListResponse:
    items = await attribute_service.list_attributes(db, product_id)
    return AttributeListResponse(data=[AttributeRead.model_validate(a) for a in items])


@router.post("", response_model=AttributeRead, status_code=status.HTTP_201_CREATED)
async def create_attribute(
    product_id: UUID,
    body: AttributeCreate,
    db: AsyncSession = Depends(get_session),
    actor: User = Depends(require_role("admin", "operator")),
) -> AttributeRead:
    attr = await attribute_service.create_attribute(db, product_id, body)
    logger.info(
        "attribute_created",
        attribute_id=str(attr.id),
        product_id=str(product_id),
        key=attr.key,
        actor_id=str(actor.id),
    )
    return AttributeRead.model_validate(attr)


@router.patch("/{attr_id}", response_model=AttributeRead)
async def update_attribute(
    product_id: UUID,
    attr_id: UUID,
    body: AttributeUpdate,
    db: AsyncSession = Depends(get_session),
    actor: User = Depends(require_role("admin", "operator")),
) -> AttributeRead:
    attr = await attribute_service.update_attribute(db, product_id, attr_id, body)
    logger.info(
        "attribute_updated",
        attribute_id=str(attr.id),
        product_id=str(product_id),
        actor_id=str(actor.id),
    )
    return AttributeRead.model_validate(attr)


@router.delete("/{attr_id}")
async def delete_attribute(
    product_id: UUID,
    attr_id: UUID,
    db: AsyncSession = Depends(get_session),
    actor: User = Depends(require_role("admin", "operator")),
) -> dict[str, str]:
    await attribute_service.delete_attribute(db, product_id, attr_id)
    logger.info(
        "attribute_deleted",
        attribute_id=str(attr_id),
        product_id=str(product_id),
        actor_id=str(actor.id),
    )
    return {"message": "Deleted"}
