"""Product image CRUD endpoints."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, File, UploadFile, status
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.dependencies.auth import require_role
from app.models.user import User
from app.schemas.image import (
    ImageListResponse,
    ImageRead,
    ImageUpdate,
)
from app.services import image_service

router = APIRouter(prefix="/api/products/{product_id}/images")


@router.get("", response_model=ImageListResponse)
async def list_images(
    product_id: UUID,
    db: AsyncSession = Depends(get_session),
    _user: User = Depends(require_role("admin", "operator", "manager", "viewer")),
) -> ImageListResponse:
    items = await image_service.list_images(db, product_id)
    return ImageListResponse(data=[ImageRead.model_validate(i) for i in items])


@router.post("", response_model=ImageRead, status_code=status.HTTP_201_CREATED)
async def upload_image(
    product_id: UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_session),
    actor: User = Depends(require_role("admin", "operator")),
) -> ImageRead:
    image = await image_service.upload_image(db, product_id, file)
    logger.info(
        "image_uploaded",
        image_id=str(image.id),
        product_id=str(product_id),
        file_name=image.file_name,
        file_size=image.file_size,
        actor_id=str(actor.id),
    )
    return ImageRead.model_validate(image)


@router.patch("/{image_id}", response_model=ImageRead)
async def update_image(
    product_id: UUID,
    image_id: UUID,
    body: ImageUpdate,
    db: AsyncSession = Depends(get_session),
    actor: User = Depends(require_role("admin", "operator")),
) -> ImageRead:
    image = await image_service.update_image(db, product_id, image_id, body)
    logger.info(
        "image_updated",
        image_id=str(image.id),
        product_id=str(product_id),
        actor_id=str(actor.id),
    )
    return ImageRead.model_validate(image)


@router.delete("/{image_id}")
async def delete_image(
    product_id: UUID,
    image_id: UUID,
    db: AsyncSession = Depends(get_session),
    actor: User = Depends(require_role("admin", "operator")),
) -> dict[str, str]:
    await image_service.delete_image(db, product_id, image_id)
    logger.info(
        "image_deleted",
        image_id=str(image_id),
        product_id=str(product_id),
        actor_id=str(actor.id),
    )
    return {"message": "Deleted"}
