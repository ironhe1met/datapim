"""XML export service (Phase 7).

Generates public product and category catalogues. Only in-stock + active
products are emitted; category feed is filtered to categories that contain
at least one such product.
"""

from __future__ import annotations

from datetime import UTC, datetime
from xml.etree import ElementTree as ET
from xml.etree.ElementTree import Element

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.category import Category
from app.models.product import Product
from app.models.product_image import ProductImage


def _iso(dt: datetime | None) -> str:
    return (dt or datetime.now(UTC)).strftime("%Y-%m-%dT%H:%M")


def _child(parent: Element, tag: str, text: str | None) -> Element:
    el = ET.SubElement(parent, tag)
    el.text = "" if text is None else text
    return el


async def generate_products_xml(session: AsyncSession) -> str:
    """Produce the `<Catalog>` XML for public consumption.

    Filters:
      - buf_in_stock = True
      - is_active = True

    Resolved fields (custom ?? buf): name, brand, country.
    Adds category external_id/name and the primary image URL if any.
    """
    settings = get_settings()
    api_base = settings.api_url.rstrip("/")

    stmt = select(Product).where(
        Product.buf_in_stock.is_(True),
        Product.is_active.is_(True),
    )
    products = list((await session.execute(stmt)).scalars().all())

    # Resolved category per product (custom ?? buf) comes via the model
    # relationships (selectin), but we still need a map for external_id lookup.
    cat_ids = {p.category_id for p in products if p.category_id is not None}
    cat_map: dict = {}
    if cat_ids:
        cats = (
            (await session.execute(select(Category).where(Category.id.in_(cat_ids))))
            .scalars()
            .all()
        )
        cat_map = {c.id: c for c in cats}

    primary_by_product: dict = {}
    if products:
        product_ids = [p.id for p in products]
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
        for img in (await session.execute(img_stmt)).scalars().all():
            primary_by_product.setdefault(img.product_id, img)

    root = Element("Catalog", attrib={"generated_at": _iso(None)})

    for p in products:
        product_el = ET.SubElement(root, "Product")
        _child(product_el, "internal_code", p.internal_code)
        _child(product_el, "sku", p.sku)
        _child(product_el, "name", p.custom_name or p.buf_name)
        _child(product_el, "brand", (p.custom_brand or p.buf_brand) or "")
        _child(product_el, "description", p.description or "")

        cat = cat_map.get(p.category_id) if p.category_id else None
        _child(product_el, "category_id", cat.external_id if cat else "")
        _child(product_el, "category_name", cat.name if cat else "")

        _child(product_el, "uktzed", p.uktzed or "")
        _child(product_el, "country_of_origin", (p.custom_country or p.buf_country) or "")
        _child(product_el, "price_rrp", f"{p.buf_price:.2f}")
        _child(product_el, "currency", p.buf_currency or "UAH")
        _child(product_el, "in_stock", "true" if p.buf_in_stock else "false")

        img = primary_by_product.get(p.id)
        if img is not None:
            image_url = f"{api_base}/uploads/{img.file_path.lstrip('/')}"
        else:
            image_url = ""
        _child(product_el, "image_url", image_url)

        _child(product_el, "updated_at", _iso(p.updated_at))

    return _tostring(root)


async def generate_categories_xml(session: AsyncSession) -> str:
    """Produce the `<Categories>` XML.

    Only categories that contain at least one active + in-stock product are
    included.
    """
    stmt = (
        select(Category)
        .join(
            Product,
            func.coalesce(Product.custom_category_id, Product.buf_category_id) == Category.id,
        )
        .where(Product.buf_in_stock.is_(True), Product.is_active.is_(True))
        .distinct()
    )
    cats = list((await session.execute(stmt)).scalars().all())

    # Map internal UUID → external_id for parent lookup.
    if cats:
        parent_ids = {c.parent_id for c in cats if c.parent_id is not None}
        parent_ext_map: dict = {}
        if parent_ids:
            parents = (
                (await session.execute(select(Category).where(Category.id.in_(parent_ids))))
                .scalars()
                .all()
            )
            parent_ext_map = {c.id: c.external_id for c in parents}
    else:
        parent_ext_map = {}

    root = Element("Categories", attrib={"generated_at": _iso(None)})

    for c in cats:
        cat_el = ET.SubElement(root, "Category")
        _child(cat_el, "id", c.external_id)
        parent_ext = parent_ext_map.get(c.parent_id) if c.parent_id else ""
        _child(cat_el, "parent_id", parent_ext or "")
        _child(cat_el, "name", c.name)

    return _tostring(root)


async def export_settings(session: AsyncSession) -> dict:
    """Counts for the admin dashboard."""
    products_count = int(
        (
            await session.execute(
                select(func.count(Product.id)).where(
                    Product.buf_in_stock.is_(True), Product.is_active.is_(True)
                )
            )
        ).scalar_one()
    )
    categories_count = int(
        (
            await session.execute(
                select(func.count(func.distinct(Category.id)))
                .select_from(Category)
                .join(
                    Product,
                    func.coalesce(Product.custom_category_id, Product.buf_category_id)
                    == Category.id,
                )
                .where(Product.buf_in_stock.is_(True), Product.is_active.is_(True))
            )
        ).scalar_one()
    )
    return {
        "products_url": "/export/products.xml",
        "categories_url": "/export/categories.xml",
        "last_generated": None,
        "products_count": products_count,
        "categories_count": categories_count,
    }


def _tostring(root: Element) -> str:
    """Serialise with an XML declaration. ElementTree escapes text automatically."""
    return ET.tostring(root, encoding="unicode", xml_declaration=True)
