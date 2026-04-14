"""Integration tests for the Dashboard stats endpoint (Phase 8a)."""

from __future__ import annotations

from datetime import UTC
from decimal import Decimal

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import text

pytestmark = pytest.mark.asyncio


PASSWORD = "test-pass-1234"
MANAGER_EMAIL = "manager-dash@example.com"
OPERATOR_EMAIL = "operator-dash@example.com"


# --- DB cleanup (same pattern as test_products.py / test_import.py) --------


@pytest_asyncio.fixture(autouse=True)
async def _auto_clean_db(test_session_factory):
    async with test_session_factory() as session:
        await session.execute(text("DELETE FROM import_logs"))
        await session.execute(text("DELETE FROM ai_reviews"))
        await session.execute(text("DELETE FROM ai_tasks"))
        await session.execute(text("DELETE FROM product_images"))
        await session.execute(text("DELETE FROM product_attributes"))
        await session.execute(text("DELETE FROM products"))
        await session.execute(text("DELETE FROM categories"))
        await session.execute(text("DELETE FROM users"))
        await session.commit()
    yield


# --- User fixtures (override conftest so they run after cleanup) -----------


@pytest_asyncio.fixture
async def admin_user(test_session_factory, _auto_clean_db):
    from app.models.user import User, UserRole
    from app.security.passwords import hash_password
    from tests.conftest import ADMIN_EMAIL, ADMIN_PASSWORD

    async with test_session_factory() as session:
        user = User(
            email=ADMIN_EMAIL,
            password_hash=hash_password(ADMIN_PASSWORD),
            name="Admin Dash",
            role=UserRole.admin,
            is_active=True,
            theme="light",
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


@pytest_asyncio.fixture
async def test_user(test_session_factory, _auto_clean_db):
    from app.models.user import User, UserRole
    from app.security.passwords import hash_password
    from tests.conftest import USER_EMAIL, USER_PASSWORD

    async with test_session_factory() as session:
        user = User(
            email=USER_EMAIL,
            password_hash=hash_password(USER_PASSWORD),
            name="Viewer Dash",
            role=UserRole.viewer,
            is_active=True,
            theme="light",
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


# --- Domain helpers --------------------------------------------------------


async def _add_product(
    session,
    *,
    internal_code: str,
    in_stock: bool = True,
    description: str | None = None,
):
    from app.models.product import EnrichmentStatus, Product

    product = Product(
        internal_code=internal_code,
        sku=internal_code,
        buf_category_id=None,
        buf_name=f"Товар {internal_code}",
        buf_price=Decimal("100.00"),
        buf_currency="UAH",
        buf_in_stock=in_stock,
        is_active=True,
        description=description,
        enrichment_status=(EnrichmentStatus.full if description else EnrichmentStatus.none),
    )
    session.add(product)
    await session.flush()
    return product


# --- Tests -----------------------------------------------------------------


async def test_stats_unauthenticated(client: AsyncClient) -> None:
    resp = await client.get("/api/dashboard/stats")
    assert resp.status_code == 401


async def test_stats_as_viewer(client: AsyncClient, test_user, user_headers) -> None:
    resp = await client.get("/api/dashboard/stats", headers=user_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    # Shape check — all required keys must be present.
    for key in (
        "products_total",
        "products_in_stock",
        "products_enriched",
        "products_no_description",
        "products_with_images",
        "pending_reviews",
        "categories_total",
        "last_import",
        "ai_tasks_today",
    ):
        assert key in body


async def test_stats_empty_db(client: AsyncClient, admin_user, admin_headers) -> None:
    resp = await client.get("/api/dashboard/stats", headers=admin_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["products_total"] == 0
    assert body["products_in_stock"] == 0
    assert body["products_enriched"] == 0
    assert body["products_no_description"] == 0
    assert body["products_with_images"] == 0
    assert body["pending_reviews"] == 0
    assert body["categories_total"] == 0
    assert body["last_import"] is None
    assert body["ai_tasks_today"] == 0


async def test_stats_counts_products(
    client: AsyncClient,
    admin_user,
    admin_headers,
    test_session_factory,
) -> None:
    async with test_session_factory() as session:
        await _add_product(session, internal_code="P-001", in_stock=True, description="desc A")
        await _add_product(session, internal_code="P-002", in_stock=True, description=None)
        await _add_product(session, internal_code="P-003", in_stock=False, description="")
        await _add_product(session, internal_code="P-004", in_stock=False, description="desc B")
        await session.commit()

    resp = await client.get("/api/dashboard/stats", headers=admin_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["products_total"] == 4
    assert body["products_in_stock"] == 2
    # Enriched: P-001 + P-004 (non-empty description).
    assert body["products_enriched"] == 2
    # No description: P-002 (NULL) + P-003 ('').
    assert body["products_no_description"] == 2


async def test_stats_counts_images(
    client: AsyncClient,
    admin_user,
    admin_headers,
    test_session_factory,
) -> None:
    from app.models.product_image import ImageSource, ProductImage

    async with test_session_factory() as session:
        p1 = await _add_product(session, internal_code="IMG-001")
        p2 = await _add_product(session, internal_code="IMG-002")
        await _add_product(session, internal_code="IMG-003")
        # p1 has two images (distinct count must still be 1 for p1).
        session.add(
            ProductImage(
                product_id=p1.id,
                file_path="/uploads/p1-a.jpg",
                file_name="p1-a.jpg",
                file_size=100,
                mime_type="image/jpeg",
                is_primary=True,
                source=ImageSource.upload,
                sort_order=0,
            )
        )
        session.add(
            ProductImage(
                product_id=p1.id,
                file_path="/uploads/p1-b.jpg",
                file_name="p1-b.jpg",
                file_size=100,
                mime_type="image/jpeg",
                is_primary=False,
                source=ImageSource.upload,
                sort_order=1,
            )
        )
        session.add(
            ProductImage(
                product_id=p2.id,
                file_path="/uploads/p2.jpg",
                file_name="p2.jpg",
                file_size=100,
                mime_type="image/jpeg",
                is_primary=True,
                source=ImageSource.upload,
                sort_order=0,
            )
        )
        await session.commit()

    resp = await client.get("/api/dashboard/stats", headers=admin_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["products_total"] == 3
    assert body["products_with_images"] == 2


async def test_stats_last_import(
    client: AsyncClient,
    admin_user,
    admin_headers,
    test_session_factory,
) -> None:
    from datetime import datetime, timedelta

    from app.models.import_log import ImportLog, ImportStatus

    older = datetime.now(UTC) - timedelta(hours=2)
    newer = datetime.now(UTC) - timedelta(minutes=5)

    async with test_session_factory() as session:
        session.add(
            ImportLog(
                file_name="/tmp/old.xml",
                started_at=older,
                status=ImportStatus.completed,
                products_created=10,
                products_updated=20,
            )
        )
        session.add(
            ImportLog(
                file_name="/tmp/new.xml",
                started_at=newer,
                status=ImportStatus.completed,
                products_created=150,
                products_updated=1200,
            )
        )
        await session.commit()

    resp = await client.get("/api/dashboard/stats", headers=admin_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["last_import"] is not None
    assert body["last_import"]["status"] == "completed"
    assert body["last_import"]["products_created"] == 150
    assert body["last_import"]["products_updated"] == 1200


async def test_stats_categories_total(
    client: AsyncClient,
    admin_user,
    admin_headers,
    test_session_factory,
) -> None:
    from app.models.category import Category

    async with test_session_factory() as session:
        for i in range(3):
            session.add(
                Category(
                    external_id=f"EXT-{i}",
                    parent_id=None,
                    name=f"Category {i}",
                    is_active=True,
                    product_count=0,
                )
            )
        await session.commit()

    resp = await client.get("/api/dashboard/stats", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["categories_total"] == 3
