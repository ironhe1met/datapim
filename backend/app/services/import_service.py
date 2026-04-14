"""XML import service (Phase 7).

Reads BUF-format `TMC.xml` (products) and `TMCC.xml` (categories) from a
configured folder and upserts the normalised data into our tables.

Key rules:
- Import NEVER touches `custom_*` fields (R-017 override pattern).
- New products are only created when `in_stock=true` (per dev plan).
- Categories are keyed by `external_id`; duplicates in the feed are deduped
  (last-wins); orphan parents are silently left as NULL.
- Work happens in chunks of 500 records to keep transactions small.
"""

from __future__ import annotations

import asyncio
import traceback
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import UUID

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.category import Category
from app.models.import_log import ImportLog, ImportStatus
from app.models.product import EnrichmentStatus, Product

_BATCH_SIZE = 500


# --- Public API ------------------------------------------------------------


async def run_import(session: AsyncSession, xml_dir: Path) -> ImportLog:
    """Run a full import cycle against the given session + xml_dir.

    Creates an ImportLog row at start, updates it with counters at the end.
    Returns the committed ImportLog.
    """
    log_row = ImportLog(
        file_name=_describe_dir(xml_dir),
        status=ImportStatus.running,
    )
    session.add(log_row)
    await session.commit()
    await session.refresh(log_row)
    return await _execute_import(session, log_row, xml_dir)


async def resume_import(session: AsyncSession, import_id: UUID, xml_dir: Path) -> ImportLog:
    """Continue an import whose `ImportLog` row has already been created.

    Used by the HTTP trigger endpoint so the client can receive the id
    synchronously while the worker finishes asynchronously.
    """
    row = (
        await session.execute(select(ImportLog).where(ImportLog.id == import_id))
    ).scalar_one_or_none()
    if row is None:
        raise ValueError(f"ImportLog {import_id} not found")
    return await _execute_import(session, row, xml_dir)


async def _execute_import(session: AsyncSession, log_row: ImportLog, xml_dir: Path) -> ImportLog:
    errors: list[dict[str, Any]] = []
    counters = {
        "products_created": 0,
        "products_updated": 0,
        "products_stock_changed": 0,
        "categories_upserted": 0,
    }

    try:
        categories_file = xml_dir / "TMCC.xml"
        products_file = xml_dir / "TMC.xml"

        if categories_file.exists():
            cats_upserted = await _import_categories(session, categories_file, errors)
            counters["categories_upserted"] = cats_upserted

        if products_file.exists():
            created, updated, stock_changed = await _import_products(session, products_file, errors)
            counters["products_created"] = created
            counters["products_updated"] = updated
            counters["products_stock_changed"] = stock_changed
        else:
            errors.append({"type": "missing_file", "file": str(products_file)})

        log_row.status = ImportStatus.completed
    except Exception as exc:  # noqa: BLE001
        logger.opt(exception=exc).error("import_failed")
        errors.append(
            {
                "type": "exception",
                "message": str(exc),
                "traceback": traceback.format_exc(),
            }
        )
        log_row.status = ImportStatus.failed

    log_row.finished_at = datetime.now(UTC)
    log_row.products_created = counters["products_created"]
    log_row.products_updated = counters["products_updated"]
    log_row.products_stock_changed = counters["products_stock_changed"]
    log_row.categories_upserted = counters["categories_upserted"]
    log_row.errors_count = len(errors)
    log_row.error_details = errors or None

    session.add(log_row)
    await session.commit()
    await session.refresh(log_row)
    return log_row


async def trigger_import_background(xml_dir: Path) -> UUID:
    """Start `run_import` in a freshly-created session and return the log id.

    The session must NOT be shared with a request — FastAPI closes request
    sessions as soon as the handler returns, which would cut us off mid-import.
    """
    # Import here to avoid circular imports during test setup.
    from app.database import SessionLocal

    return await _run_with_factory(SessionLocal, xml_dir)


async def _run_with_factory(factory: async_sessionmaker[AsyncSession], xml_dir: Path) -> UUID:
    async with factory() as session:
        log_row = await run_import(session, xml_dir)
        return log_row.id


def schedule_import_task(factory: async_sessionmaker[AsyncSession], xml_dir: Path) -> asyncio.Task:
    """Create an asyncio.Task that runs the import with its own session.

    Used by the HTTP handler so we can register it via BackgroundTasks while
    still getting isolation from the request session.
    """
    coro = _run_with_factory(factory, xml_dir)
    return asyncio.create_task(coro)


# --- Helpers ---------------------------------------------------------------


def _describe_dir(xml_dir: Path) -> str:
    name = str(xml_dir)
    # DB column is String(255) — keep well under the limit.
    return name[-255:]


# --- Categories ------------------------------------------------------------


async def _import_categories(
    session: AsyncSession,
    path: Path,
    errors: list[dict[str, Any]],
) -> int:
    """Two-pass category upsert.

    Pass 1: dedupe the feed by external_id (last-wins) and upsert every row
    without touching `parent_id`.
    Pass 2: resolve parent_external_id → internal UUID using the now-complete
    external_id index and write parent_id links.
    """
    from app.utils.xml_parser import iter_categories

    # Pass 1 — collect & dedupe. Skip is_active=false (BUF flag for deleted).
    feed: dict[str, dict[str, Any]] = {}
    for raw in iter_categories(path):
        ext_id = raw.get("id") or ""
        if not ext_id:
            errors.append({"type": "category_missing_id", "name": raw.get("name") or ""})
            continue
        if not bool(raw.get("is_active", True)):
            continue  # BUF-deleted category — don't import.
        feed[ext_id] = raw  # last-wins overwrites earlier duplicates.

    if not feed:
        return 0

    # Bulk-load existing rows keyed by external_id.
    existing = (
        (await session.execute(select(Category).where(Category.external_id.in_(list(feed.keys())))))
        .scalars()
        .all()
    )
    by_ext: dict[str, Category] = {c.external_id: c for c in existing}

    upserted = 0
    batch = 0
    for ext_id, raw in feed.items():
        name = raw.get("name") or ""
        is_active = bool(raw.get("is_active", True))
        if ext_id in by_ext:
            cat = by_ext[ext_id]
            cat.name = name
            cat.is_active = is_active
        else:
            cat = Category(
                external_id=ext_id,
                parent_id=None,
                name=name,
                is_active=is_active,
                product_count=0,
            )
            session.add(cat)
            by_ext[ext_id] = cat
        upserted += 1
        batch += 1
        if batch >= _BATCH_SIZE:
            await session.flush()
            batch = 0
    await session.flush()

    # Pass 2 — resolve parents.
    # We need internal UUIDs, so refresh anything newly-added to populate `.id`.
    for cat in by_ext.values():
        if cat.id is None:  # pragma: no cover — flush assigns id
            await session.refresh(cat)

    batch = 0
    for ext_id, raw in feed.items():
        parent_ext = raw.get("parent_id")
        if not parent_ext:
            by_ext[ext_id].parent_id = None
            continue
        parent = by_ext.get(parent_ext)
        if parent is None:
            errors.append(
                {
                    "type": "category_orphan_parent",
                    "external_id": ext_id,
                    "parent_external_id": parent_ext,
                }
            )
            by_ext[ext_id].parent_id = None
            continue
        by_ext[ext_id].parent_id = parent.id
        batch += 1
        if batch >= _BATCH_SIZE:
            await session.flush()
            batch = 0

    await session.commit()
    return upserted


# --- Products --------------------------------------------------------------


async def _import_products(
    session: AsyncSession,
    path: Path,
    errors: list[dict[str, Any]],
) -> tuple[int, int, int]:
    """Streaming upsert of products.

    Returns (created, updated, stock_changed).
    """
    from app.utils.xml_parser import iter_products

    # Map external category ids → internal UUIDs for FK lookup.
    cat_rows = (await session.execute(select(Category.id, Category.external_id))).all()
    cat_map: dict[str, UUID] = {ext: cid for cid, ext in cat_rows}

    created = 0
    updated = 0
    stock_changed = 0
    batch = 0

    for raw in iter_products(path):
        internal_code = raw.get("internal_code") or ""
        if not internal_code:
            errors.append({"type": "product_missing_internal_code", "sku": raw.get("sku") or "", "name": raw.get("name") or ""})
            continue

        if not bool(raw.get("is_active", True)):
            continue  # BUF-deleted product — don't import.

        cat_ext = raw.get("category_id")
        category_uuid: UUID | None = cat_map.get(cat_ext) if cat_ext else None
        if cat_ext and category_uuid is None:
            # Category was filtered out (inactive) or unknown — skip the product.
            continue

        existing = (
            await session.execute(select(Product).where(Product.internal_code == internal_code))
        ).scalar_one_or_none()

        in_stock = bool(raw.get("in_stock"))
        price = raw.get("price_rrp")
        if not isinstance(price, Decimal):
            price = Decimal("0")

        if existing is None:
            # New product — only create if currently in stock.
            if not in_stock:
                continue
            product = Product(
                internal_code=internal_code,
                sku=raw.get("sku") or "",
                buf_category_id=category_uuid,
                buf_name=raw.get("name") or "",
                custom_name=None,
                buf_brand=raw.get("brand"),
                custom_brand=None,
                buf_country=raw.get("country_of_origin"),
                custom_country=None,
                buf_price=price,
                buf_currency=raw.get("currency") or "UAH",
                buf_quantity=raw.get("quantity"),
                buf_in_stock=True,
                uktzed=raw.get("uktzed"),
                is_active=bool(raw.get("is_active", True)),
                description=None,
                seo_title=None,
                seo_description=None,
                has_pending_review=False,
                enrichment_status=EnrichmentStatus.none,
            )
            session.add(product)
            created += 1
        else:
            prev_in_stock = existing.buf_in_stock
            # Update only BUF fields — custom_* is sacred.
            existing.sku = raw.get("sku") or existing.sku
            existing.buf_category_id = category_uuid
            existing.buf_name = raw.get("name") or existing.buf_name
            existing.buf_brand = raw.get("brand")
            existing.buf_country = raw.get("country_of_origin")
            existing.buf_price = price
            existing.buf_currency = raw.get("currency") or "UAH"
            existing.buf_quantity = raw.get("quantity")
            existing.buf_in_stock = in_stock
            existing.uktzed = raw.get("uktzed")
            existing.is_active = bool(raw.get("is_active", True))
            updated += 1
            if prev_in_stock != in_stock:
                stock_changed += 1

        batch += 1
        if batch >= _BATCH_SIZE:
            await session.commit()
            batch = 0

    if batch > 0:
        await session.commit()
    return created, updated, stock_changed


# --- Query helpers ---------------------------------------------------------


async def list_logs(
    session: AsyncSession, *, page: int, per_page: int
) -> tuple[list[ImportLog], int]:
    from sqlalchemy import func

    total = int((await session.execute(select(func.count(ImportLog.id)))).scalar_one())
    offset = (page - 1) * per_page
    rows = (
        (
            await session.execute(
                select(ImportLog)
                .order_by(ImportLog.started_at.desc())
                .offset(offset)
                .limit(per_page)
            )
        )
        .scalars()
        .all()
    )
    return list(rows), total


async def get_log(session: AsyncSession, log_id: UUID) -> ImportLog | None:
    return (
        await session.execute(select(ImportLog).where(ImportLog.id == log_id))
    ).scalar_one_or_none()
