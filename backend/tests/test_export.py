"""Integration tests for XML export (Phase 7)."""

from __future__ import annotations

from decimal import Decimal

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import text
from xml.etree import ElementTree as ET

pytestmark = pytest.mark.asyncio


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


@pytest_asyncio.fixture
async def admin_user(test_session_factory, _auto_clean_db):
    from app.models.user import User, UserRole
    from app.security.passwords import hash_password

    from tests.conftest import ADMIN_EMAIL, ADMIN_PASSWORD

    async with test_session_factory() as session:
        user = User(
            email=ADMIN_EMAIL,
            password_hash=hash_password(ADMIN_PASSWORD),
            name="Admin",
            role=UserRole.admin,
            is_active=True,
            theme="light",
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


@pytest_asyncio.fixture
async def manager_user(test_session_factory, _auto_clean_db):
    from app.models.user import User, UserRole
    from app.security.passwords import hash_password

    async with test_session_factory() as session:
        user = User(
            email="manager-exp@example.com",
            password_hash=hash_password("pass-1234-pass"),
            name="Manager",
            role=UserRole.manager,
            is_active=True,
            theme="light",
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


@pytest_asyncio.fixture
async def viewer_user(test_session_factory, _auto_clean_db):
    from app.models.user import User, UserRole
    from app.security.passwords import hash_password

    async with test_session_factory() as session:
        user = User(
            email="viewer-exp@example.com",
            password_hash=hash_password("pass-1234-pass"),
            name="Viewer",
            role=UserRole.viewer,
            is_active=True,
            theme="light",
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


@pytest_asyncio.fixture
async def admin_headers(admin_user) -> dict[str, str]:
    from app.security.jwt import create_access_token

    return {"Authorization": f"Bearer {create_access_token(admin_user.id)}"}


@pytest_asyncio.fixture
async def manager_headers(manager_user) -> dict[str, str]:
    from app.security.jwt import create_access_token

    return {"Authorization": f"Bearer {create_access_token(manager_user.id)}"}


@pytest_asyncio.fixture
async def viewer_headers(viewer_user) -> dict[str, str]:
    from app.security.jwt import create_access_token

    return {"Authorization": f"Bearer {create_access_token(viewer_user.id)}"}


# --- Seed helpers ----------------------------------------------------------


async def _seed_basic(test_session_factory):
    """Two categories, three products (two in-stock, one out)."""
    from app.models.category import Category
    from app.models.product import EnrichmentStatus, Product

    async with test_session_factory() as session:
        root = Category(
            external_id="CAT-ROOT",
            name="Root",
            parent_id=None,
            is_active=True,
            product_count=0,
        )
        session.add(root)
        await session.flush()

        child = Category(
            external_id="CAT-1",
            name="Інструменти & приладдя",
            parent_id=root.id,
            is_active=True,
            product_count=0,
        )
        session.add(child)
        await session.flush()

        session.add_all(
            [
                Product(
                    internal_code="IN-1",
                    sku="SKU-IN-1",
                    buf_category_id=child.id,
                    buf_name="Дриль BUF",
                    custom_name="Дриль Pro",
                    buf_brand="Bosch",
                    custom_brand=None,
                    buf_country="Germany",
                    custom_country=None,
                    buf_price=Decimal("1015.16"),
                    buf_currency="UAH",
                    buf_quantity=3,
                    buf_in_stock=True,
                    uktzed="8467210000",
                    is_active=True,
                    description="Description <with> & special",
                    enrichment_status=EnrichmentStatus.full,
                ),
                Product(
                    internal_code="IN-2",
                    sku="SKU-IN-2",
                    buf_category_id=child.id,
                    buf_name="Викрутка",
                    buf_brand=None,
                    buf_country=None,
                    buf_price=Decimal("99.00"),
                    buf_currency="UAH",
                    buf_in_stock=True,
                    is_active=True,
                    enrichment_status=EnrichmentStatus.none,
                ),
                Product(
                    internal_code="OUT-1",
                    sku="SKU-OUT-1",
                    buf_category_id=child.id,
                    buf_name="Out-of-stock item",
                    buf_price=Decimal("10.00"),
                    buf_currency="UAH",
                    buf_in_stock=False,
                    is_active=True,
                    enrichment_status=EnrichmentStatus.none,
                ),
            ]
        )
        await session.commit()


# --- /export/products.xml --------------------------------------------------


async def test_export_products_public_only_in_stock(client: AsyncClient, test_session_factory):
    await _seed_basic(test_session_factory)
    resp = await client.get("/export/products.xml")
    assert resp.status_code == 200, resp.text
    assert resp.headers["content-type"].startswith("application/xml")

    root = ET.fromstring(resp.text)
    assert root.tag == "Catalog"
    codes = [p.findtext("internal_code") for p in root.findall("Product")]
    assert set(codes) == {"IN-1", "IN-2"}


async def test_export_products_resolves_custom_over_buf(client: AsyncClient, test_session_factory):
    await _seed_basic(test_session_factory)
    resp = await client.get("/export/products.xml")
    root = ET.fromstring(resp.text)
    in1 = next(p for p in root.findall("Product") if p.findtext("internal_code") == "IN-1")
    # custom_name overrides buf_name.
    assert in1.findtext("name") == "Дриль Pro"
    # No custom_brand — falls back to buf_brand.
    assert in1.findtext("brand") == "Bosch"
    assert in1.findtext("price_rrp") == "1015.16"
    assert in1.findtext("category_id") == "CAT-1"
    # category_name contains special chars → must have been escaped+unescaped correctly.
    assert in1.findtext("category_name") == "Інструменти & приладдя"


async def test_export_products_empty_catalog(client: AsyncClient, test_session_factory):
    resp = await client.get("/export/products.xml")
    assert resp.status_code == 200
    root = ET.fromstring(resp.text)
    assert root.tag == "Catalog"
    assert root.findall("Product") == []


async def test_export_xml_escaping(client: AsyncClient, test_session_factory):
    """Special chars (& < >) must appear escaped in the wire format."""
    await _seed_basic(test_session_factory)
    resp = await client.get("/export/products.xml")
    # Description had `<with> & special`; must round-trip through the parser.
    root = ET.fromstring(resp.text)
    in1 = next(p for p in root.findall("Product") if p.findtext("internal_code") == "IN-1")
    assert in1.findtext("description") == "Description <with> & special"
    # And the serialisation itself must not contain raw angle brackets inside text.
    assert "&amp;" in resp.text
    assert "&lt;with&gt;" in resp.text


# --- /export/categories.xml -----------------------------------------------


async def test_export_categories_only_with_in_stock(client: AsyncClient, test_session_factory):
    await _seed_basic(test_session_factory)
    resp = await client.get("/export/categories.xml")
    assert resp.status_code == 200
    root = ET.fromstring(resp.text)
    ids = [c.findtext("id") for c in root.findall("Category")]
    # Only CAT-1 has in-stock products; CAT-ROOT has none directly.
    assert ids == ["CAT-1"]
    parent = root.find("Category").findtext("parent_id")
    assert parent == "CAT-ROOT"


# --- /api/export/settings --------------------------------------------------


async def test_export_settings_admin(
    client: AsyncClient, admin_user, admin_headers, test_session_factory
):
    await _seed_basic(test_session_factory)
    resp = await client.get("/api/export/settings", headers=admin_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["products_count"] == 2
    assert body["categories_count"] == 1
    assert body["products_url"] == "/export/products.xml"


async def test_export_settings_manager(
    client: AsyncClient, manager_user, manager_headers, test_session_factory
):
    resp = await client.get("/api/export/settings", headers=manager_headers)
    assert resp.status_code == 200
    assert resp.json()["products_count"] == 0


async def test_export_settings_viewer_forbidden(client: AsyncClient, viewer_user, viewer_headers):
    resp = await client.get("/api/export/settings", headers=viewer_headers)
    assert resp.status_code == 403
