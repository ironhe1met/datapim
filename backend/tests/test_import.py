"""Integration tests for XML import (Phase 7)."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select, text

pytestmark = pytest.mark.asyncio


# --- DB cleanup (same pattern as test_products.py) -------------------------


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
            email="manager-imp@example.com",
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
            email="viewer-imp@example.com",
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


# --- parse_price -----------------------------------------------------------


def test_parse_price_integer():
    from app.utils.price_parser import parse_price

    assert parse_price("999") == Decimal("999")


def test_parse_price_comma_and_nbsp():
    from app.utils.price_parser import parse_price

    assert parse_price("1\u00a0015,16") == Decimal("1015.16")
    assert parse_price("1 015,16") == Decimal("1015.16")
    # Narrow NBSP variant.
    assert parse_price("1\u202f015,16") == Decimal("1015.16")


def test_parse_price_dot():
    from app.utils.price_parser import parse_price

    assert parse_price("123.45") == Decimal("123.45")


def test_parse_price_empty_and_none():
    from app.utils.price_parser import parse_price

    assert parse_price("") is None
    assert parse_price(None) is None
    assert parse_price("   ") is None


def test_parse_price_bad_input():
    from app.utils.price_parser import parse_price

    assert parse_price("abc") is None


# --- XML parser ------------------------------------------------------------


def _write_products_xml(tmp_path: Path) -> Path:
    xml = """<?xml version="1.0" encoding="UTF-8"?>
<Catalog generated_at="2026-04-09T13:43">
    <Product>
        <internal_code>ABC-1</internal_code>
        <sku>SKU-1                 </sku>
        <name>Test product one</name>
        <brand>Bosch</brand>
        <category_id>CAT-1</category_id>
        <uktzed>1234567890</uktzed>
        <country_of_origin>Україна</country_of_origin>
        <quantity>3</quantity>
        <in_stock>true</in_stock>
        <price_rrp>1 015,16</price_rrp>
        <currency>UAH</currency>
        <updated_at>2026-04-09T13:43</updated_at>
        <is_active>true</is_active>
    </Product>
    <Product>
        <internal_code>ABC-2</internal_code>
        <sku>SKU-2</sku>
        <name>Test product two</name>
        <brand/>
        <category_id>CAT-1</category_id>
        <uktzed/>
        <country_of_origin/>
        <quantity/>
        <in_stock>false</in_stock>
        <price_rrp>0</price_rrp>
        <currency>UAH</currency>
        <updated_at>2026-04-09T13:43</updated_at>
        <is_active>true</is_active>
    </Product>
</Catalog>
"""
    path = tmp_path / "TMC.xml"
    path.write_text(xml, encoding="utf-8")
    return path


def _write_categories_xml(tmp_path: Path) -> Path:
    xml = """<?xml version="1.0" encoding="UTF-8"?>
<Categories generated_at="2026-04-09T13:49">
    <category>
        <id>CAT-ROOT</id>
        <parent_id/>
        <name>Root</name>
        <is_active>true</is_active>
        <updated_at>2026-04-09T13:49</updated_at>
    </category>
    <category>
        <id>CAT-1</id>
        <parent_id>CAT-ROOT</parent_id>
        <name>Інструменти</name>
        <is_active>true</is_active>
        <updated_at>2026-04-09T13:49</updated_at>
    </category>
    <category>
        <id>CAT-1</id>
        <parent_id>CAT-ROOT</parent_id>
        <name>Інструменти</name>
        <is_active>true</is_active>
        <updated_at>2026-04-09T13:49</updated_at>
    </category>
</Categories>
"""
    path = tmp_path / "TMCC.xml"
    path.write_text(xml, encoding="utf-8")
    return path


def test_iter_products_fixture(tmp_path):
    from app.utils.xml_parser import iter_products

    path = _write_products_xml(tmp_path)
    rows = list(iter_products(path))
    assert len(rows) == 2
    # SKU trailing spaces stripped.
    assert rows[0]["sku"] == "SKU-1"
    assert rows[0]["price_rrp"] == Decimal("1015.16")
    assert rows[0]["in_stock"] is True
    assert rows[0]["quantity"] == 3
    assert rows[0]["country_of_origin"] == "Україна"
    assert rows[1]["in_stock"] is False
    assert rows[1]["quantity"] is None
    assert rows[1]["brand"] is None


def test_iter_categories_fixture(tmp_path):
    from app.utils.xml_parser import iter_categories

    path = _write_categories_xml(tmp_path)
    rows = list(iter_categories(path))
    # Feed contains 3 rows including the CAT-1 duplicate — parser yields them
    # all; dedup is the import service's responsibility.
    assert len(rows) == 3
    assert rows[0]["id"] == "CAT-ROOT"
    assert rows[0]["parent_id"] is None
    assert rows[1]["id"] == "CAT-1"
    assert rows[1]["parent_id"] == "CAT-ROOT"


# --- import_service --------------------------------------------------------


async def _run_import(test_session_factory, xml_dir: Path):
    from app.services.import_service import run_import

    async with test_session_factory() as session:
        return await run_import(session, xml_dir)


async def test_import_creates_in_stock_product(test_session_factory, tmp_path):
    from app.models.product import Product

    _write_categories_xml(tmp_path)
    _write_products_xml(tmp_path)

    log = await _run_import(test_session_factory, tmp_path)
    assert log.status.value == "completed"
    assert log.categories_upserted == 2  # CAT-ROOT + CAT-1 (dedup)
    assert log.products_created == 1  # only ABC-1 (in_stock=true)
    assert log.errors_count == 0

    async with test_session_factory() as session:
        rows = (await session.execute(select(Product))).scalars().all()
        codes = [p.internal_code for p in rows]
        assert codes == ["ABC-1"]
        assert rows[0].buf_price == Decimal("1015.16")
        assert rows[0].sku == "SKU-1"


async def test_import_skips_new_when_out_of_stock(test_session_factory, tmp_path):
    _write_categories_xml(tmp_path)
    _write_products_xml(tmp_path)

    log = await _run_import(test_session_factory, tmp_path)
    # ABC-2 is out-of-stock and new, so must not be created.
    assert log.products_created == 1


async def test_import_preserves_custom_fields_on_update(test_session_factory, tmp_path):
    """Import never touches custom_* — override pattern R-017."""
    from app.models.category import Category
    from app.models.product import EnrichmentStatus, Product

    _write_categories_xml(tmp_path)
    _write_products_xml(tmp_path)

    # First import creates the product.
    await _run_import(test_session_factory, tmp_path)

    # Operator enriches: sets custom_name + description.
    async with test_session_factory() as session:
        p = (
            await session.execute(select(Product).where(Product.internal_code == "ABC-1"))
        ).scalar_one()
        p.custom_name = "Custom enriched name"
        p.custom_brand = "Custom brand"
        p.description = "Human-written description"
        p.enrichment_status = EnrichmentStatus.full
        await session.commit()

    # Re-import — buf_* should refresh, custom_* + description must persist.
    await _run_import(test_session_factory, tmp_path)

    async with test_session_factory() as session:
        p = (
            await session.execute(select(Product).where(Product.internal_code == "ABC-1"))
        ).scalar_one()
        assert p.custom_name == "Custom enriched name"
        assert p.custom_brand == "Custom brand"
        assert p.description == "Human-written description"
        assert p.enrichment_status.value == "full"
        assert p.buf_name == "Test product one"  # from XML

        # Category link still resolved — import owns BUF.
        assert p.buf_category_id is not None
        cat = (
            await session.execute(select(Category).where(Category.id == p.buf_category_id))
        ).scalar_one()
        assert cat.external_id == "CAT-1"


async def test_import_category_dedup(test_session_factory, tmp_path):
    from app.models.category import Category

    _write_categories_xml(tmp_path)
    # No products — only categories matter here.
    (tmp_path / "TMC.xml").write_text(
        "<?xml version='1.0' encoding='UTF-8'?><Catalog/>", encoding="utf-8"
    )
    log = await _run_import(test_session_factory, tmp_path)
    assert log.status.value == "completed"

    async with test_session_factory() as session:
        cats = (
            (await session.execute(select(Category).order_by(Category.external_id))).scalars().all()
        )
        ids = [c.external_id for c in cats]
        # Duplicate CAT-1 in feed → only one row.
        assert ids == sorted(set(ids))
        assert set(ids) == {"CAT-ROOT", "CAT-1"}


async def test_import_stock_changed_counter(test_session_factory, tmp_path):
    from app.models.product import Product

    _write_categories_xml(tmp_path)
    _write_products_xml(tmp_path)

    await _run_import(test_session_factory, tmp_path)

    # Flip ABC-2 to in_stock=true by rewriting the XML.
    xml2 = (tmp_path / "TMC.xml").read_text(encoding="utf-8")
    xml2 = xml2.replace(
        "<internal_code>ABC-2</internal_code>\n        <sku>SKU-2</sku>",
        "<internal_code>ABC-1</internal_code>\n        <sku>SKU-1-OOS</sku>",
    )
    # Actually simplest: rebuild a minimal XML that flips ABC-1 to out-of-stock.
    flipped = """<?xml version="1.0" encoding="UTF-8"?>
<Catalog>
    <Product>
        <internal_code>ABC-1</internal_code>
        <sku>SKU-1</sku>
        <name>Test product one</name>
        <brand>Bosch</brand>
        <category_id>CAT-1</category_id>
        <uktzed/>
        <country_of_origin/>
        <quantity/>
        <in_stock>false</in_stock>
        <price_rrp>1 015,16</price_rrp>
        <currency>UAH</currency>
        <updated_at>2026-04-09T13:43</updated_at>
        <is_active>true</is_active>
    </Product>
</Catalog>
"""
    (tmp_path / "TMC.xml").write_text(flipped, encoding="utf-8")
    log = await _run_import(test_session_factory, tmp_path)
    assert log.products_stock_changed == 1

    async with test_session_factory() as session:
        p = (
            await session.execute(select(Product).where(Product.internal_code == "ABC-1"))
        ).scalar_one()
        assert p.buf_in_stock is False


# --- HTTP routes -----------------------------------------------------------


async def test_trigger_requires_admin(client: AsyncClient, viewer_user, viewer_headers):
    resp = await client.post("/api/import/trigger", headers=viewer_headers)
    assert resp.status_code == 403


async def test_trigger_rejects_manager(client: AsyncClient, manager_user, manager_headers):
    resp = await client.post("/api/import/trigger", headers=manager_headers)
    assert resp.status_code == 403


async def test_trigger_returns_202(
    client: AsyncClient, admin_user, admin_headers, tmp_path, monkeypatch
):
    # Point the settings at a tiny tmp xml_dir so the background task can
    # finish fast without importing the real 16 MB file.
    from app.config import get_settings

    _write_categories_xml(tmp_path)
    _write_products_xml(tmp_path)

    settings = get_settings()
    monkeypatch.setattr(settings, "xml_import_dir", tmp_path)

    resp = await client.post("/api/import/trigger", headers=admin_headers)
    assert resp.status_code == 202, resp.text
    body = resp.json()
    assert body["status"] == "running"
    assert "import_id" in body


async def test_list_logs_as_admin(
    client: AsyncClient, admin_user, admin_headers, test_session_factory
):
    from app.models.import_log import ImportLog, ImportStatus

    async with test_session_factory() as session:
        session.add(ImportLog(file_name="/tmp/xml", status=ImportStatus.completed))
        session.add(ImportLog(file_name="/tmp/xml", status=ImportStatus.failed))
        await session.commit()

    resp = await client.get("/api/import/logs", headers=admin_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["meta"]["total"] == 2
    assert len(body["data"]) == 2


async def test_list_logs_as_manager(client: AsyncClient, manager_user, manager_headers):
    resp = await client.get("/api/import/logs", headers=manager_headers)
    assert resp.status_code == 200
    assert resp.json()["meta"]["total"] == 0


async def test_list_logs_as_viewer_forbidden(client: AsyncClient, viewer_user, viewer_headers):
    resp = await client.get("/api/import/logs", headers=viewer_headers)
    assert resp.status_code == 403


async def test_get_log_detail(client: AsyncClient, admin_user, admin_headers, test_session_factory):
    from app.models.import_log import ImportLog, ImportStatus

    async with test_session_factory() as session:
        row = ImportLog(
            file_name="/tmp/xml",
            status=ImportStatus.completed,
            products_created=5,
            errors_count=1,
            error_details=[{"type": "test_error", "msg": "hi"}],
        )
        session.add(row)
        await session.commit()
        await session.refresh(row)
        log_id = row.id

    resp = await client.get(f"/api/import/logs/{log_id}", headers=admin_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["products_created"] == 5
    assert body["error_details"] == [{"type": "test_error", "msg": "hi"}]


async def test_get_log_not_found(client: AsyncClient, admin_user, admin_headers):
    from uuid import uuid4

    resp = await client.get(f"/api/import/logs/{uuid4()}", headers=admin_headers)
    assert resp.status_code == 404
