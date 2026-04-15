"""Product CRUD business logic (Phase 5).

v1.0 scope (R-020): list + detail + PATCH custom_* + reset-field.
No create (manual create deferred to v1.1), no delete (products never deleted,
see R-014 — BUF items merely flip `buf_in_stock`).

Override pattern (R-017): resolved display value is `COALESCE(custom_*, buf_*)`.
`buf_*` fields are READ-ONLY here — they are updated exclusively by XML import.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import Select, case, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.category import Category
from app.models.product import Product
from app.models.product_attribute import ProductAttribute
from app.models.product_image import ProductImage
from app.schemas.product import (
    RESETTABLE_FIELDS,
    BreadcrumbItem,
    BulkUpdateRequest,
    BulkUpdateResponse,
    BulkUpdateSampleItem,
    CategoryInfo,
    CategoryRef,
    EnrichmentStatus,
    PrimaryImageRef,
    ProductAttributeRead,
    ProductDetail,
    ProductImageRead,
    ProductListItem,
    ProductUpdate,
)

# --- Exceptions ------------------------------------------------------------


def _not_found_exc() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={"error": "Товар не знайдено", "code": "NOT_FOUND"},
    )


def _category_not_found_exc() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={"error": "Категорію не знайдено", "code": "CATEGORY_NOT_FOUND"},
    )


def _invalid_field_exc(field: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail={
            "error": f"Поле '{field}' не можна скинути",
            "code": "INVALID_FIELD",
        },
    )


# --- Helpers ---------------------------------------------------------------


def _resolved_name_expr():
    return func.coalesce(Product.custom_name, Product.buf_name)


async def _descendant_category_ids(db: AsyncSession, root_id: UUID) -> list[UUID]:
    """Return `root_id` + all descendants by walking parent_id breadth-first."""
    all_cats = list((await db.execute(select(Category.id, Category.parent_id))).all())
    children_map: dict[UUID | None, list[UUID]] = {}
    for cid, pid in all_cats:
        children_map.setdefault(pid, []).append(cid)

    result: list[UUID] = [root_id]
    queue: list[UUID] = [root_id]
    while queue:
        current = queue.pop(0)
        for child in children_map.get(current, []):
            result.append(child)
            queue.append(child)
    return result


def _apply_sort(stmt: Select, sort_by: str, sort_order: str) -> Select:
    direction = "desc" if sort_order.lower() == "desc" else "asc"
    if sort_by == "price":
        col = Product.buf_price
    elif sort_by == "name":
        col = _resolved_name_expr()
    else:  # created_at (default)
        col = Product.created_at
    return stmt.order_by(col.desc() if direction == "desc" else col.asc())


# --- List ------------------------------------------------------------------


async def list_products(
    db: AsyncSession,
    page: int,
    per_page: int,
    search: str | None = None,
    category_id: UUID | None = None,
    in_stock: bool | None = None,
    enrichment_status: str | None = None,
    has_pending_review: bool | None = None,
    brand: str | None = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
) -> tuple[list[ProductListItem], int]:
    """Return (items, total) with resolved display fields + nested refs."""
    filters = []

    if search:
        pattern = f"%{search.lower()}%"
        filters.append(
            or_(
                func.lower(Product.buf_name).like(pattern),
                func.lower(func.coalesce(Product.custom_name, "")).like(pattern),
                func.lower(Product.sku).like(pattern),
                func.lower(Product.internal_code).like(pattern),
            )
        )

    if category_id is not None:
        ids = await _descendant_category_ids(db, category_id)
        # Match the resolved category (custom ?? buf) — same as display.
        filters.append(func.coalesce(Product.custom_category_id, Product.buf_category_id).in_(ids))

    if in_stock is not None:
        filters.append(Product.buf_in_stock == in_stock)

    if enrichment_status is not None:
        filters.append(Product.enrichment_status == EnrichmentStatus(enrichment_status))

    if has_pending_review is not None:
        filters.append(Product.has_pending_review == has_pending_review)

    if brand is not None and brand:
        # Match resolved brand (custom_brand ?? buf_brand) exactly.
        filters.append(
            func.coalesce(Product.custom_brand, Product.buf_brand) == brand
        )

    # Total
    count_stmt = select(func.count(Product.id))
    if filters:
        count_stmt = count_stmt.where(*filters)
    total = int((await db.execute(count_stmt)).scalar_one())

    # Page slice
    offset = (page - 1) * per_page
    stmt = select(Product)
    if filters:
        stmt = stmt.where(*filters)
    stmt = _apply_sort(stmt, sort_by, sort_order).offset(offset).limit(per_page)

    products = list((await db.execute(stmt)).scalars().all())
    if not products:
        return [], total

    # Bulk-load primary images. Categories come from buf/custom_category
    # relationships (lazy="selectin") — no need for an extra query.
    product_ids = [p.id for p in products]

    # Primary image per product: pick is_primary=True first, fall back to lowest
    # sort_order. Single grouped query keeps this O(1) round trips.
    img_stmt = (
        select(ProductImage)
        .where(ProductImage.product_id.in_(product_ids))
        .order_by(
            ProductImage.product_id,
            case((ProductImage.is_primary.is_(True), 0), else_=1),
            ProductImage.sort_order.asc(),
            ProductImage.created_at.asc(),
        )
    )
    primary_by_product: dict[UUID, ProductImage] = {}
    for img in (await db.execute(img_stmt)).scalars().all():
        primary_by_product.setdefault(img.product_id, img)

    items: list[ProductListItem] = []
    for p in products:
        cat = p.category  # resolved Category ORM (custom ?? buf)
        img = primary_by_product.get(p.id)
        items.append(
            ProductListItem(
                id=p.id,
                internal_code=p.internal_code,
                sku=p.sku,
                name=p.custom_name or p.buf_name,
                brand=p.custom_brand or p.buf_brand,
                price=p.buf_price,
                currency=p.buf_currency,
                quantity=p.buf_quantity,
                in_stock=p.buf_in_stock,
                category=CategoryRef(id=cat.id, name=cat.name) if cat else None,
                primary_image=(
                    PrimaryImageRef(id=img.id, file_path=img.file_path) if img else None
                ),
                enrichment_status=EnrichmentStatus(p.enrichment_status.value),
                has_pending_review=p.has_pending_review,
            )
        )
    return items, total


# --- Get -------------------------------------------------------------------


async def get_product(db: AsyncSession, product_id: UUID) -> Product | None:
    stmt = select(Product).where(Product.id == product_id)
    return (await db.execute(stmt)).scalar_one_or_none()


async def _get_category_breadcrumb(db: AsyncSession, category: Category) -> list[Category]:
    """Walk up parent_id chain; return list from root → category (inclusive)."""
    chain: list[Category] = [category]
    seen: set[UUID] = {category.id}
    current = category
    while current.parent_id is not None:
        if current.parent_id in seen:  # pragma: no cover - cycle guard
            break
        parent = (
            await db.execute(select(Category).where(Category.id == current.parent_id))
        ).scalar_one_or_none()
        if parent is None:
            break
        chain.append(parent)
        seen.add(parent.id)
        current = parent
    chain.reverse()
    return chain


async def build_product_detail(db: AsyncSession, product: Product) -> ProductDetail:
    """Assemble the full detail payload including resolved fields + children."""
    # Resolved category (custom ?? buf) — for display.
    category_info: CategoryInfo | None = None
    resolved_category = product.category
    if resolved_category is not None:
        crumbs = await _get_category_breadcrumb(db, resolved_category)
        category_info = CategoryInfo(
            id=resolved_category.id,
            name=resolved_category.name,
            breadcrumb=[BreadcrumbItem(id=c.id, name=c.name) for c in crumbs],
        )

    # BUF category — shown in the BUF read-only block.
    buf_category_ref: CategoryRef | None = None
    if product.buf_category is not None:
        buf_category_ref = CategoryRef(
            id=product.buf_category.id,
            name=product.buf_category.name,
        )

    images = list(
        (
            await db.execute(
                select(ProductImage)
                .where(ProductImage.product_id == product.id)
                .order_by(
                    ProductImage.is_primary.desc(),
                    ProductImage.sort_order.asc(),
                    ProductImage.created_at.asc(),
                )
            )
        )
        .scalars()
        .all()
    )

    attributes = list(
        (
            await db.execute(
                select(ProductAttribute)
                .where(ProductAttribute.product_id == product.id)
                .order_by(ProductAttribute.sort_order.asc(), ProductAttribute.key.asc())
            )
        )
        .scalars()
        .all()
    )

    return ProductDetail(
        id=product.id,
        internal_code=product.internal_code,
        sku=product.sku,
        buf_name=product.buf_name,
        custom_name=product.custom_name,
        name=product.custom_name or product.buf_name,
        buf_brand=product.buf_brand,
        custom_brand=product.custom_brand,
        brand=product.custom_brand or product.buf_brand,
        buf_country=product.buf_country,
        custom_country=product.custom_country,
        country=product.custom_country or product.buf_country,
        buf_price=product.buf_price,
        buf_currency=product.buf_currency,
        buf_quantity=product.buf_quantity,
        buf_in_stock=product.buf_in_stock,
        uktzed=product.uktzed,
        is_active=product.is_active,
        description=product.description,
        seo_title=product.seo_title,
        seo_description=product.seo_description,
        enrichment_status=EnrichmentStatus(product.enrichment_status.value),
        has_pending_review=product.has_pending_review,
        category=category_info,
        buf_category=buf_category_ref,
        images=[ProductImageRead.model_validate(i) for i in images],
        attributes=[ProductAttributeRead.model_validate(a) for a in attributes],
        created_at=product.created_at,
        updated_at=product.updated_at,
    )


# --- Update ----------------------------------------------------------------


async def update_product(db: AsyncSession, product_id: UUID, data: ProductUpdate) -> Product:
    """Update only custom_* / description / seo_* / custom_category_id.

    `buf_*` fields are never touched here (R-020 — import owns them).
    """
    product = await get_product(db, product_id)
    if product is None:
        raise _not_found_exc()

    fields_set = data.model_fields_set

    if "custom_name" in fields_set:
        product.custom_name = data.custom_name
    if "custom_brand" in fields_set:
        product.custom_brand = data.custom_brand
    if "custom_country" in fields_set:
        product.custom_country = data.custom_country
    if "description" in fields_set:
        product.description = data.description
    if "seo_title" in fields_set:
        product.seo_title = data.seo_title
    if "seo_description" in fields_set:
        product.seo_description = data.seo_description

    if "custom_category_id" in fields_set:
        new_cat_id = data.custom_category_id
        if new_cat_id is None:
            # Clearing the override → fall back to BUF category.
            # Only reject if BUF is also empty (shouldn't happen in practice).
            if product.buf_category_id is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "error": "Не можна видалити категорію товару",
                        "code": "CATEGORY_REQUIRED",
                    },
                )
            product.custom_category_id = None
        else:
            cat = (
                await db.execute(select(Category).where(Category.id == new_cat_id))
            ).scalar_one_or_none()
            if cat is None:
                raise _category_not_found_exc()
            product.custom_category_id = new_cat_id

    db.add(product)
    await db.commit()
    await db.refresh(product)
    return product


# --- Reset field -----------------------------------------------------------


async def reset_field(db: AsyncSession, product_id: UUID, field: str) -> Product:
    """Clear a single override field → display falls back to `buf_*`.

    All override columns (`custom_*`, including `custom_category_id`) are
    resettable now that category has a proper BUF/custom split.
    """
    if field not in RESETTABLE_FIELDS:
        raise _invalid_field_exc(field)

    product = await get_product(db, product_id)
    if product is None:
        raise _not_found_exc()

    setattr(product, field, None)
    db.add(product)
    await db.commit()
    await db.refresh(product)
    return product


# --- Bulk update -----------------------------------------------------------


_BULK_MAX_ROWS = 5000


async def bulk_update(db: AsyncSession, data: BulkUpdateRequest) -> BulkUpdateResponse:
    """Apply same custom_* values to every product matching the filter.

    v1.0 supports filter by `buf_category_id` (with optional descendant walk).
    Set fields are limited to `custom_brand`, `custom_country`, `custom_category_id`
    (R-017 — buf_* are import-owned).

    Refuses to commit if the matched count exceeds `_BULK_MAX_ROWS` to prevent
    accidental "set custom_brand for entire DB". Use a tighter filter or split.
    """
    # 1. Resolve target category set.
    target_cat = (
        await db.execute(select(Category).where(Category.id == data.filter.buf_category_id))
    ).scalar_one_or_none()
    if target_cat is None:
        raise _category_not_found_exc()

    if data.filter.include_descendants:
        cat_ids = await _descendant_category_ids(db, data.filter.buf_category_id)
    else:
        cat_ids = [data.filter.buf_category_id]

    # 2. Validate custom_category_id exists if provided.
    set_fields = data.set.model_fields_set
    if "custom_category_id" in set_fields and data.set.custom_category_id is not None:
        exists = (
            await db.execute(
                select(Category.id).where(Category.id == data.set.custom_category_id)
            )
        ).scalar_one_or_none()
        if exists is None:
            raise _category_not_found_exc()

    # 3. Match preview.
    matched_q = select(Product).where(Product.buf_category_id.in_(cat_ids))
    matched_rows = list((await db.execute(matched_q)).scalars().all())
    matched = len(matched_rows)

    if matched > _BULK_MAX_ROWS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": f"Занадто багато товарів ({matched}). Максимум {_BULK_MAX_ROWS} за один виклик.",
                "code": "BULK_TOO_MANY",
            },
        )

    sample = [
        BulkUpdateSampleItem(
            id=p.id,
            internal_code=p.internal_code,
            name=p.custom_name or p.buf_name,
        )
        for p in matched_rows[:5]
    ]

    if data.dry_run or matched == 0:
        return BulkUpdateResponse(matched=matched, updated=0, sample=sample)

    # 4. Build SET clause from explicitly-set fields only.
    values: dict = {}
    if "custom_brand" in set_fields:
        values["custom_brand"] = data.set.custom_brand
    if "custom_country" in set_fields:
        values["custom_country"] = data.set.custom_country
    if "custom_category_id" in set_fields:
        values["custom_category_id"] = data.set.custom_category_id

    if not values:
        return BulkUpdateResponse(matched=matched, updated=0, sample=sample)

    # 5. Apply.
    await db.execute(
        update(Product).where(Product.buf_category_id.in_(cat_ids)).values(**values)
    )
    await db.commit()
    return BulkUpdateResponse(matched=matched, updated=matched, sample=sample)


# --- Distinct brands -------------------------------------------------------


async def list_brands(db: AsyncSession) -> list[dict]:
    """Distinct resolved brands with product counts.

    Sorted by name. Empty/null brands collapsed into one "(без бренду)" bucket.
    """
    resolved = func.coalesce(Product.custom_brand, Product.buf_brand)
    stmt = (
        select(resolved.label("name"), func.count(Product.id).label("cnt"))
        .group_by(resolved)
        .order_by(resolved.asc().nulls_last())
    )
    rows = (await db.execute(stmt)).all()
    return [
        {"name": (name or "").strip() or "(без бренду)", "count": int(cnt)}
        for (name, cnt) in rows
    ]
