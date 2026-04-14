"""Dashboard aggregate stats (Phase 8a).

v1.0 shortcuts (R-020):
- `pending_reviews` — hardcoded 0 (AI reviews land in v1.2).
- `ai_tasks_today` — hardcoded 0 (AI tasks land in v1.2).

Note: the individual COUNT queries are awaited sequentially because a
single `AsyncSession` cannot run concurrent statements on one asyncpg
connection. With indexed / small tables the total latency is still
negligible compared to the network round-trip from the browser.
"""

from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.category import Category
from app.models.import_log import ImportLog
from app.models.product import Product
from app.models.product_image import ProductImage
from app.schemas.dashboard import DashboardStatsResponse, LastImportInfo


async def _count_products_total(session: AsyncSession) -> int:
    stmt = select(func.count()).select_from(Product)
    return int((await session.execute(stmt)).scalar_one())


async def _count_products_in_stock(session: AsyncSession) -> int:
    stmt = select(func.count()).select_from(Product).where(Product.buf_in_stock.is_(True))
    return int((await session.execute(stmt)).scalar_one())


async def _count_products_enriched(session: AsyncSession) -> int:
    stmt = (
        select(func.count())
        .select_from(Product)
        .where(Product.description.is_not(None), Product.description != "")
    )
    return int((await session.execute(stmt)).scalar_one())


async def _count_products_no_description(session: AsyncSession) -> int:
    stmt = (
        select(func.count())
        .select_from(Product)
        .where(or_(Product.description.is_(None), Product.description == ""))
    )
    return int((await session.execute(stmt)).scalar_one())


async def _count_products_with_images(session: AsyncSession) -> int:
    stmt = select(func.count(func.distinct(ProductImage.product_id)))
    return int((await session.execute(stmt)).scalar_one())


async def _count_categories_total(session: AsyncSession) -> int:
    stmt = select(func.count()).select_from(Category)
    return int((await session.execute(stmt)).scalar_one())


async def _fetch_last_import(session: AsyncSession) -> LastImportInfo | None:
    stmt = select(ImportLog).order_by(ImportLog.started_at.desc()).limit(1)
    row = (await session.execute(stmt)).scalar_one_or_none()
    if row is None:
        return None
    status_value = row.status.value if hasattr(row.status, "value") else str(row.status)
    return LastImportInfo(
        id=row.id,
        date=row.started_at,
        status=status_value,
        products_created=row.products_created,
        products_updated=row.products_updated,
    )


async def get_stats(session: AsyncSession) -> DashboardStatsResponse:
    """Aggregate dashboard counters in one call.

    `pending_reviews` / `ai_tasks_today` are hardcoded zeros — those tables
    exist but the UI concept of "pending review" / "today's AI work" ships
    with v1.2 (R-020). Hardcoding keeps the contract stable without lying
    about counts.
    """
    products_total = await _count_products_total(session)
    products_in_stock = await _count_products_in_stock(session)
    products_enriched = await _count_products_enriched(session)
    products_no_description = await _count_products_no_description(session)
    products_with_images = await _count_products_with_images(session)
    categories_total = await _count_categories_total(session)
    last_import = await _fetch_last_import(session)

    return DashboardStatsResponse(
        products_total=products_total,
        products_in_stock=products_in_stock,
        products_enriched=products_enriched,
        products_no_description=products_no_description,
        products_with_images=products_with_images,
        pending_reviews=0,
        categories_total=categories_total,
        last_import=last_import,
        ai_tasks_today=0,
    )
