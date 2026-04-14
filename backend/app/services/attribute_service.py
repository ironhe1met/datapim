"""Product attribute CRUD business logic."""

from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Product
from app.models.product_attribute import AttributeSource, ProductAttribute
from app.schemas.attribute import AttributeCreate, AttributeUpdate


def _product_not_found_exc() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={"error": "Продукт не знайдено", "code": "NOT_FOUND"},
    )


def _not_found_exc() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={"error": "Атрибут не знайдено", "code": "NOT_FOUND"},
    )


def _duplicate_key_exc() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail={"error": "Атрибут з таким ключем вже існує", "code": "DUPLICATE_KEY"},
    )


async def _product_exists(db: AsyncSession, product_id: UUID) -> bool:
    stmt = select(Product.id).where(Product.id == product_id)
    return (await db.execute(stmt)).scalar_one_or_none() is not None


async def _key_taken(
    db: AsyncSession,
    product_id: UUID,
    key: str,
    *,
    exclude_attr_id: UUID | None = None,
) -> bool:
    stmt = select(ProductAttribute.id).where(
        ProductAttribute.product_id == product_id,
        func.lower(ProductAttribute.key) == key.lower(),
    )
    if exclude_attr_id is not None:
        stmt = stmt.where(ProductAttribute.id != exclude_attr_id)
    return (await db.execute(stmt)).scalar_one_or_none() is not None


async def list_attributes(db: AsyncSession, product_id: UUID) -> list[ProductAttribute]:
    stmt = (
        select(ProductAttribute)
        .where(ProductAttribute.product_id == product_id)
        .order_by(ProductAttribute.sort_order.asc(), ProductAttribute.created_at.asc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def _next_sort_order(db: AsyncSession, product_id: UUID) -> int:
    stmt = select(func.max(ProductAttribute.sort_order)).where(
        ProductAttribute.product_id == product_id
    )
    current = (await db.execute(stmt)).scalar_one_or_none()
    return (current or 0) + 1


async def create_attribute(
    db: AsyncSession, product_id: UUID, data: AttributeCreate
) -> ProductAttribute:
    if not await _product_exists(db, product_id):
        raise _product_not_found_exc()

    if await _key_taken(db, product_id, data.key):
        raise _duplicate_key_exc()

    attr = ProductAttribute(
        product_id=product_id,
        key=data.key,
        value=data.value,
        sort_order=await _next_sort_order(db, product_id),
        source=AttributeSource.manual,
    )
    db.add(attr)
    await db.commit()
    await db.refresh(attr)
    return attr


async def _get_attribute(
    db: AsyncSession, product_id: UUID, attr_id: UUID
) -> ProductAttribute | None:
    stmt = select(ProductAttribute).where(
        ProductAttribute.id == attr_id,
        ProductAttribute.product_id == product_id,
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def update_attribute(
    db: AsyncSession,
    product_id: UUID,
    attr_id: UUID,
    data: AttributeUpdate,
) -> ProductAttribute:
    if not await _product_exists(db, product_id):
        raise _product_not_found_exc()

    attr = await _get_attribute(db, product_id, attr_id)
    if attr is None:
        raise _not_found_exc()

    fields_set = data.model_fields_set

    if "key" in fields_set and data.key is not None:
        if data.key.lower() != attr.key.lower() and await _key_taken(
            db, product_id, data.key, exclude_attr_id=attr.id
        ):
            raise _duplicate_key_exc()
        attr.key = data.key

    if "value" in fields_set and data.value is not None:
        attr.value = data.value

    if "sort_order" in fields_set and data.sort_order is not None:
        attr.sort_order = data.sort_order

    db.add(attr)
    await db.commit()
    await db.refresh(attr)
    return attr


async def delete_attribute(db: AsyncSession, product_id: UUID, attr_id: UUID) -> None:
    if not await _product_exists(db, product_id):
        raise _product_not_found_exc()

    attr = await _get_attribute(db, product_id, attr_id)
    if attr is None:
        raise _not_found_exc()

    await db.delete(attr)
    await db.commit()
