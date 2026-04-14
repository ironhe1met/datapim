"""Product image CRUD business logic."""

from __future__ import annotations

import uuid as uuidlib
from pathlib import Path
from uuid import UUID

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.product import Product
from app.models.product_image import ImageSource, ProductImage
from app.schemas.image import ImageUpdate

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

ALLOWED_MIME_TYPES: dict[str, set[str]] = {
    "image/png": {".png"},
    "image/jpeg": {".jpg", ".jpeg"},
    "image/webp": {".webp"},
}


def _product_not_found_exc() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={"error": "Продукт не знайдено", "code": "NOT_FOUND"},
    )


def _not_found_exc() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={"error": "Зображення не знайдено", "code": "NOT_FOUND"},
    )


def _invalid_file_type_exc() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail={
            "error": "Непідтримуваний формат (png, jpeg, webp)",
            "code": "INVALID_FILE_TYPE",
        },
    )


def _file_too_large_exc() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail={
            "error": "Файл занадто великий (max 10MB)",
            "code": "FILE_TOO_LARGE",
        },
    )


async def _product_exists(db: AsyncSession, product_id: UUID) -> bool:
    stmt = select(Product.id).where(Product.id == product_id)
    return (await db.execute(stmt)).scalar_one_or_none() is not None


async def list_images(db: AsyncSession, product_id: UUID) -> list[ProductImage]:
    stmt = (
        select(ProductImage)
        .where(ProductImage.product_id == product_id)
        .order_by(ProductImage.sort_order.asc(), ProductImage.created_at.asc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def _get_image(db: AsyncSession, product_id: UUID, image_id: UUID) -> ProductImage | None:
    stmt = select(ProductImage).where(
        ProductImage.id == image_id,
        ProductImage.product_id == product_id,
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def _count_images(db: AsyncSession, product_id: UUID) -> int:
    stmt = select(func.count(ProductImage.id)).where(ProductImage.product_id == product_id)
    return int((await db.execute(stmt)).scalar_one())


async def _next_sort_order(db: AsyncSession, product_id: UUID) -> int:
    stmt = select(func.max(ProductImage.sort_order)).where(ProductImage.product_id == product_id)
    current = (await db.execute(stmt)).scalar_one_or_none()
    return (current or 0) + 1


def _validate_upload(file: UploadFile, size: int) -> tuple[str, str]:
    """Return (mime_type, extension). Raises 400 if invalid."""
    if size > MAX_FILE_SIZE:
        raise _file_too_large_exc()

    mime_type = (file.content_type or "").lower()
    if mime_type not in ALLOWED_MIME_TYPES:
        raise _invalid_file_type_exc()

    filename = file.filename or ""
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_MIME_TYPES[mime_type]:
        raise _invalid_file_type_exc()

    return mime_type, ext


async def upload_image(db: AsyncSession, product_id: UUID, file: UploadFile) -> ProductImage:
    if not await _product_exists(db, product_id):
        raise _product_not_found_exc()

    contents = await file.read()
    size = len(contents)
    mime_type, ext = _validate_upload(file, size)

    settings = get_settings()
    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)

    new_name = f"{uuidlib.uuid4().hex}{ext}"
    disk_path = upload_dir / new_name
    with open(disk_path, "wb") as fh:
        fh.write(contents)

    existing = await _count_images(db, product_id)
    is_primary = existing == 0

    image = ProductImage(
        product_id=product_id,
        file_path=f"/uploads/{new_name}",
        file_name=file.filename or new_name,
        file_size=size,
        mime_type=mime_type,
        is_primary=is_primary,
        source=ImageSource.upload,
        sort_order=await _next_sort_order(db, product_id),
    )
    db.add(image)
    await db.commit()
    await db.refresh(image)
    return image


async def update_image(
    db: AsyncSession,
    product_id: UUID,
    image_id: UUID,
    data: ImageUpdate,
) -> ProductImage:
    if not await _product_exists(db, product_id):
        raise _product_not_found_exc()

    image = await _get_image(db, product_id, image_id)
    if image is None:
        raise _not_found_exc()

    fields_set = data.model_fields_set

    if "is_primary" in fields_set and data.is_primary is not None:
        if data.is_primary:
            # Unset primary on all other images of this product.
            others = await db.execute(
                select(ProductImage).where(
                    ProductImage.product_id == product_id,
                    ProductImage.id != image.id,
                    ProductImage.is_primary.is_(True),
                )
            )
            for other in others.scalars().all():
                other.is_primary = False
                db.add(other)
        image.is_primary = data.is_primary

    if "sort_order" in fields_set and data.sort_order is not None:
        image.sort_order = data.sort_order

    db.add(image)
    await db.commit()
    await db.refresh(image)
    return image


def _remove_file_best_effort(file_path: str) -> None:
    """Delete file referenced by public URL. Best-effort (never raises)."""
    if not file_path.startswith("/uploads/"):
        return
    settings = get_settings()
    relative = file_path[len("/uploads/") :]
    disk_path = Path(settings.upload_dir) / relative
    try:
        if disk_path.exists():
            disk_path.unlink()
    except OSError:
        pass


async def delete_image(db: AsyncSession, product_id: UUID, image_id: UUID) -> None:
    if not await _product_exists(db, product_id):
        raise _product_not_found_exc()

    image = await _get_image(db, product_id, image_id)
    if image is None:
        raise _not_found_exc()

    was_primary = image.is_primary
    file_path = image.file_path

    await db.delete(image)
    await db.commit()

    _remove_file_best_effort(file_path)

    if was_primary:
        stmt = (
            select(ProductImage)
            .where(ProductImage.product_id == product_id)
            .order_by(ProductImage.sort_order.asc(), ProductImage.created_at.asc())
            .limit(1)
        )
        result = await db.execute(stmt)
        next_primary = result.scalar_one_or_none()
        if next_primary is not None:
            next_primary.is_primary = True
            db.add(next_primary)
            await db.commit()
