"""Integration tests for the Products CRUD module (Phase 5)."""

from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import text

pytestmark = pytest.mark.asyncio


MANAGER_EMAIL = "manager-prod@example.com"
OPERATOR_EMAIL = "operator-prod@example.com"
PASSWORD = "test-pass-1234"


# --- Override admin_user / test_user to run AFTER our autouse DB cleanup ---
# The conftest versions depend only on `test_session_factory`; ours depend
# additionally on `_auto_clean_db`, which forces the cleanup to happen first.


@pytest_asyncio.fixture
async def admin_user(test_session_factory, _auto_clean_db):
    from app.models.user import User, UserRole
    from app.security.passwords import hash_password

    from tests.conftest import ADMIN_EMAIL, ADMIN_PASSWORD

    async with test_session_factory() as session:
        user = User(
            email=ADMIN_EMAIL,
            password_hash=hash_password(ADMIN_PASSWORD),
            name="Admin Test",
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
            name="Regular User",
            role=UserRole.viewer,
            is_active=True,
            theme="light",
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


# --- Helpers ---------------------------------------------------------------


async def _clean_product_tables(test_session_factory) -> None:
    """Wipe product-related tables.

    conftest.py truncates `users`; we clear categories/products with DELETE
    (not TRUNCATE) to avoid asyncpg prepared-statement cache invalidation.
    """
    async with test_session_factory() as session:
        # Order matters (FKs): images/attributes → products → categories.
        await session.execute(text("DELETE FROM product_images"))
        await session.execute(text("DELETE FROM product_attributes"))
        await session.execute(text("DELETE FROM products"))
        await session.execute(text("DELETE FROM categories"))
        await session.commit()


@pytest_asyncio.fixture(autouse=True)
async def _auto_clean_db(test_session_factory):
    """Autouse: wipe all tables before each product test.

    Ensures no orphans from other test modules (users/categories/images)
    break our fixtures or assertions. Runs before every test regardless of
    whether it requests `admin_user` from conftest.
    """
    async with test_session_factory() as session:
        # Order matters: children → parents.
        await session.execute(text("DELETE FROM ai_reviews"))
        await session.execute(text("DELETE FROM ai_tasks"))
        await session.execute(text("DELETE FROM product_images"))
        await session.execute(text("DELETE FROM product_attributes"))
        await session.execute(text("DELETE FROM products"))
        await session.execute(text("DELETE FROM categories"))
        await session.execute(text("DELETE FROM users"))
        await session.commit()
    yield


# --- Role fixtures ---------------------------------------------------------


@pytest_asyncio.fixture
async def manager_user(test_session_factory, _auto_clean_db):
    from app.models.user import User, UserRole
    from app.security.passwords import hash_password

    async with test_session_factory() as session:
        user = User(
            email=MANAGER_EMAIL,
            password_hash=hash_password(PASSWORD),
            name="Manager Prod",
            role=UserRole.manager,
            is_active=True,
            theme="light",
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


@pytest_asyncio.fixture
async def operator_user(test_session_factory, _auto_clean_db):
    from app.models.user import User, UserRole
    from app.security.passwords import hash_password

    async with test_session_factory() as session:
        user = User(
            email=OPERATOR_EMAIL,
            password_hash=hash_password(PASSWORD),
            name="Operator Prod",
            role=UserRole.operator,
            is_active=True,
            theme="light",
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


@pytest_asyncio.fixture
async def manager_headers(manager_user) -> dict[str, str]:
    from app.security.jwt import create_access_token

    return {"Authorization": f"Bearer {create_access_token(manager_user.id)}"}


@pytest_asyncio.fixture
async def operator_headers(operator_user) -> dict[str, str]:
    from app.security.jwt import create_access_token

    return {"Authorization": f"Bearer {create_access_token(operator_user.id)}"}


# --- Domain fixtures -------------------------------------------------------


@pytest_asyncio.fixture
async def sample_category(test_session_factory):
    from app.models.category import Category

    async with test_session_factory() as session:
        cat = Category(
            external_id="EXT-CAT-001",
            parent_id=None,
            name="Інструменти",
            is_active=True,
            product_count=0,
        )
        session.add(cat)
        await session.commit()
        await session.refresh(cat)
        return cat


@pytest_asyncio.fixture
async def sample_product(test_session_factory, sample_category):
    from app.models.product import EnrichmentStatus, Product

    async with test_session_factory() as session:
        product = Product(
            internal_code="U-45GCS",
            sku="U-45GCS",
            buf_category_id=sample_category.id,
            buf_name="Дриль ударний BUF",
            custom_name=None,
            buf_brand="Bosch",
            custom_brand=None,
            buf_country="Німеччина",
            custom_country=None,
            buf_price=Decimal("1015.16"),
            buf_currency="UAH",
            buf_quantity=5,
            buf_in_stock=True,
            uktzed="8467210000",
            is_active=True,
            description=None,
            seo_title=None,
            seo_description=None,
            has_pending_review=False,
            enrichment_status=EnrichmentStatus.none,
        )
        session.add(product)
        await session.commit()
        await session.refresh(product)
        return product


@pytest_asyncio.fixture
async def enriched_product(test_session_factory, sample_category):
    from app.models.product import EnrichmentStatus, Product

    async with test_session_factory() as session:
        product = Product(
            internal_code="E-99XYZ",
            sku="E-99XYZ",
            buf_category_id=sample_category.id,
            buf_name="Шуруповерт BUF",
            custom_name="Шуруповерт PRO (підсилений)",
            buf_brand="Makita",
            custom_brand="Makita Professional",
            buf_country="Японія",
            custom_country="Японія (офіційний імпорт)",
            buf_price=Decimal("2499.00"),
            buf_currency="UAH",
            buf_quantity=2,
            buf_in_stock=True,
            uktzed="8467220000",
            is_active=True,
            description="Потужний шуруповерт для професійного використання",
            seo_title="Шуруповерт Makita PRO",
            seo_description="Купуйте якісний інструмент",
            has_pending_review=False,
            enrichment_status=EnrichmentStatus.full,
        )
        session.add(product)
        await session.commit()
        await session.refresh(product)
        return product


# --- GET /api/products (list) ---------------------------------------------


async def test_list_products_as_admin(
    client: AsyncClient, admin_user, admin_headers, sample_product
) -> None:
    resp = await client.get("/api/products", headers=admin_headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "data" in data and "meta" in data
    assert data["meta"]["total"] == 1
    assert data["data"][0]["internal_code"] == "U-45GCS"
    # Resolved name falls back to buf_name.
    assert data["data"][0]["name"] == "Дриль ударний BUF"
    assert data["data"][0]["brand"] == "Bosch"
    assert data["data"][0]["in_stock"] is True
    assert data["data"][0]["category"]["name"] == "Інструменти"
    assert data["data"][0]["primary_image"] is None
    assert data["data"][0]["enrichment_status"] == "none"


async def test_list_products_as_viewer(
    client: AsyncClient, test_user, user_headers, sample_product
) -> None:
    resp = await client.get("/api/products", headers=user_headers)
    assert resp.status_code == 200
    assert resp.json()["meta"]["total"] == 1


async def test_list_products_unauthenticated(client: AsyncClient, sample_product) -> None:
    resp = await client.get("/api/products")
    assert resp.status_code == 401


async def test_list_products_search(
    client: AsyncClient,
    admin_user,
    admin_headers,
    sample_category,
    test_session_factory,
) -> None:
    from app.models.product import EnrichmentStatus, Product

    async with test_session_factory() as session:
        session.add(
            Product(
                internal_code="CODE-A1",
                sku="SKU-A1",
                buf_category_id=sample_category.id,
                buf_name="Молоток звичайний",
                buf_price=Decimal("100"),
                buf_currency="UAH",
                buf_in_stock=True,
                enrichment_status=EnrichmentStatus.none,
            )
        )
        session.add(
            Product(
                internal_code="CODE-B2",
                sku="SKU-B2",
                buf_category_id=sample_category.id,
                buf_name="Викрутка хрестова",
                custom_name="Викрутка PH2 кастом",
                buf_price=Decimal("50"),
                buf_currency="UAH",
                buf_in_stock=True,
                enrichment_status=EnrichmentStatus.none,
            )
        )
        await session.commit()

    # Search by buf_name substring.
    r1 = await client.get("/api/products", params={"search": "Молот"}, headers=admin_headers)
    assert r1.status_code == 200
    codes1 = [p["internal_code"] for p in r1.json()["data"]]
    assert codes1 == ["CODE-A1"]

    # Search by SKU (case-insensitive).
    r2 = await client.get("/api/products", params={"search": "sku-b2"}, headers=admin_headers)
    assert r2.status_code == 200
    codes2 = [p["internal_code"] for p in r2.json()["data"]]
    assert codes2 == ["CODE-B2"]

    # Search by custom_name substring.
    r3 = await client.get("/api/products", params={"search": "кастом"}, headers=admin_headers)
    assert r3.status_code == 200
    codes3 = [p["internal_code"] for p in r3.json()["data"]]
    assert codes3 == ["CODE-B2"]


async def test_list_products_by_category(
    client: AsyncClient,
    admin_user,
    admin_headers,
    test_session_factory,
) -> None:
    """category_id filter must include descendants."""
    from app.models.category import Category
    from app.models.product import EnrichmentStatus, Product

    async with test_session_factory() as session:
        root = Category(
            external_id="TREE-ROOT",
            parent_id=None,
            name="Root",
            is_active=True,
            product_count=0,
        )
        session.add(root)
        await session.flush()

        child = Category(
            external_id="TREE-CHILD",
            parent_id=root.id,
            name="Child",
            is_active=True,
            product_count=0,
        )
        session.add(child)
        await session.flush()

        grandchild = Category(
            external_id="TREE-GC",
            parent_id=child.id,
            name="Grandchild",
            is_active=True,
            product_count=0,
        )
        session.add(grandchild)

        other = Category(
            external_id="TREE-OTHER",
            parent_id=None,
            name="Other",
            is_active=True,
            product_count=0,
        )
        session.add(other)
        await session.flush()

        session.add_all(
            [
                Product(
                    internal_code="P-ROOT",
                    sku="P-ROOT",
                    buf_category_id=root.id,
                    buf_name="At root",
                    buf_price=Decimal("10"),
                    buf_in_stock=True,
                    enrichment_status=EnrichmentStatus.none,
                ),
                Product(
                    internal_code="P-CHILD",
                    sku="P-CHILD",
                    buf_category_id=child.id,
                    buf_name="At child",
                    buf_price=Decimal("20"),
                    buf_in_stock=True,
                    enrichment_status=EnrichmentStatus.none,
                ),
                Product(
                    internal_code="P-GC",
                    sku="P-GC",
                    buf_category_id=grandchild.id,
                    buf_name="At grandchild",
                    buf_price=Decimal("30"),
                    buf_in_stock=True,
                    enrichment_status=EnrichmentStatus.none,
                ),
                Product(
                    internal_code="P-OTHER",
                    sku="P-OTHER",
                    buf_category_id=other.id,
                    buf_name="Somewhere else",
                    buf_price=Decimal("40"),
                    buf_in_stock=True,
                    enrichment_status=EnrichmentStatus.none,
                ),
            ]
        )
        await session.commit()
        root_id = root.id
        child_id = child.id

    # Filter by root → 3 descendants, excluding other.
    r_root = await client.get(
        "/api/products",
        params={"category_id": str(root_id), "per_page": 100},
        headers=admin_headers,
    )
    assert r_root.status_code == 200
    codes = {p["internal_code"] for p in r_root.json()["data"]}
    assert codes == {"P-ROOT", "P-CHILD", "P-GC"}

    # Filter by child → child + grandchild only.
    r_child = await client.get(
        "/api/products",
        params={"category_id": str(child_id), "per_page": 100},
        headers=admin_headers,
    )
    assert r_child.status_code == 200
    codes = {p["internal_code"] for p in r_child.json()["data"]}
    assert codes == {"P-CHILD", "P-GC"}


async def test_list_products_in_stock_filter(
    client: AsyncClient,
    admin_user,
    admin_headers,
    sample_category,
    test_session_factory,
) -> None:
    from app.models.product import EnrichmentStatus, Product

    async with test_session_factory() as session:
        session.add(
            Product(
                internal_code="IN-STOCK",
                sku="S1",
                buf_category_id=sample_category.id,
                buf_name="In Stock Item",
                buf_price=Decimal("10"),
                buf_in_stock=True,
                enrichment_status=EnrichmentStatus.none,
            )
        )
        session.add(
            Product(
                internal_code="OUT-STOCK",
                sku="S2",
                buf_category_id=sample_category.id,
                buf_name="Out of Stock",
                buf_price=Decimal("10"),
                buf_in_stock=False,
                enrichment_status=EnrichmentStatus.none,
            )
        )
        await session.commit()

    r_true = await client.get("/api/products", params={"in_stock": "true"}, headers=admin_headers)
    assert r_true.status_code == 200
    codes = [p["internal_code"] for p in r_true.json()["data"]]
    assert "IN-STOCK" in codes and "OUT-STOCK" not in codes

    r_false = await client.get("/api/products", params={"in_stock": "false"}, headers=admin_headers)
    codes = [p["internal_code"] for p in r_false.json()["data"]]
    assert codes == ["OUT-STOCK"]


async def test_list_products_enrichment_filter(
    client: AsyncClient,
    admin_user,
    admin_headers,
    sample_product,
    enriched_product,
) -> None:
    r_full = await client.get(
        "/api/products",
        params={"enrichment_status": "full"},
        headers=admin_headers,
    )
    assert r_full.status_code == 200
    codes = [p["internal_code"] for p in r_full.json()["data"]]
    assert codes == ["E-99XYZ"]

    r_none = await client.get(
        "/api/products",
        params={"enrichment_status": "none"},
        headers=admin_headers,
    )
    codes = [p["internal_code"] for p in r_none.json()["data"]]
    assert codes == ["U-45GCS"]


async def test_list_products_pagination(
    client: AsyncClient,
    admin_user,
    admin_headers,
    sample_category,
    test_session_factory,
) -> None:
    from app.models.product import EnrichmentStatus, Product

    async with test_session_factory() as session:
        for i in range(25):
            session.add(
                Product(
                    internal_code=f"PAGE-{i:03d}",
                    sku=f"PAGE-{i:03d}",
                    buf_category_id=sample_category.id,
                    buf_name=f"Product {i:03d}",
                    buf_price=Decimal("10"),
                    buf_in_stock=True,
                    enrichment_status=EnrichmentStatus.none,
                )
            )
        await session.commit()

    resp = await client.get(
        "/api/products",
        params={"page": 2, "per_page": 10},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["data"]) == 10
    assert data["meta"]["total"] == 25
    assert data["meta"]["last_page"] == 3
    assert data["meta"]["page"] == 2


async def test_list_products_sort_price(
    client: AsyncClient,
    admin_user,
    admin_headers,
    sample_category,
    test_session_factory,
) -> None:
    from app.models.product import EnrichmentStatus, Product

    async with test_session_factory() as session:
        for i, price in enumerate([500, 100, 300]):
            session.add(
                Product(
                    internal_code=f"SORT-{i}",
                    sku=f"SORT-{i}",
                    buf_category_id=sample_category.id,
                    buf_name=f"Sortable {i}",
                    buf_price=Decimal(price),
                    buf_in_stock=True,
                    enrichment_status=EnrichmentStatus.none,
                )
            )
        await session.commit()

    asc = await client.get(
        "/api/products",
        params={"sort_by": "price", "sort_order": "asc"},
        headers=admin_headers,
    )
    codes_asc = [p["internal_code"] for p in asc.json()["data"]]
    assert codes_asc == ["SORT-1", "SORT-2", "SORT-0"]

    desc = await client.get(
        "/api/products",
        params={"sort_by": "price", "sort_order": "desc"},
        headers=admin_headers,
    )
    codes_desc = [p["internal_code"] for p in desc.json()["data"]]
    assert codes_desc == ["SORT-0", "SORT-2", "SORT-1"]


# --- GET /api/products/:id -------------------------------------------------


async def test_get_product(client: AsyncClient, admin_user, admin_headers, sample_product) -> None:
    resp = await client.get(f"/api/products/{sample_product.id}", headers=admin_headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["internal_code"] == "U-45GCS"
    assert data["buf_name"] == "Дриль ударний BUF"
    assert data["custom_name"] is None
    assert data["name"] == "Дриль ударний BUF"
    assert data["buf_brand"] == "Bosch"
    assert data["brand"] == "Bosch"
    assert data["category"]["name"] == "Інструменти"
    assert data["category"]["breadcrumb"][-1]["name"] == "Інструменти"
    assert data["images"] == []
    assert data["attributes"] == []


async def test_get_product_not_found(client: AsyncClient, admin_user, admin_headers) -> None:
    resp = await client.get(f"/api/products/{uuid4()}", headers=admin_headers)
    assert resp.status_code == 404
    assert resp.json()["code"] == "NOT_FOUND"


async def test_get_product_resolved_name(
    client: AsyncClient, admin_user, admin_headers, enriched_product
) -> None:
    resp = await client.get(f"/api/products/{enriched_product.id}", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    # Resolution must prefer custom.
    assert data["custom_name"] == "Шуруповерт PRO (підсилений)"
    assert data["name"] == "Шуруповерт PRO (підсилений)"
    assert data["buf_name"] == "Шуруповерт BUF"
    assert data["brand"] == "Makita Professional"
    assert data["country"] == "Японія (офіційний імпорт)"


async def test_get_product_fallback_name(
    client: AsyncClient, admin_user, admin_headers, sample_product
) -> None:
    resp = await client.get(f"/api/products/{sample_product.id}", headers=admin_headers)
    data = resp.json()
    assert data["custom_name"] is None
    assert data["name"] == data["buf_name"]


# --- PATCH /api/products/:id ----------------------------------------------


async def test_update_product_as_admin(
    client: AsyncClient, admin_user, admin_headers, sample_product
) -> None:
    resp = await client.patch(
        f"/api/products/{sample_product.id}",
        headers=admin_headers,
        json={
            "custom_name": "Дриль Professional",
            "description": "AI-generated опис",
        },
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["custom_name"] == "Дриль Professional"
    assert data["name"] == "Дриль Professional"
    assert data["buf_name"] == "Дриль ударний BUF"  # unchanged
    assert data["description"] == "AI-generated опис"


async def test_update_product_as_operator(
    client: AsyncClient, operator_user, operator_headers, sample_product
) -> None:
    resp = await client.patch(
        f"/api/products/{sample_product.id}",
        headers=operator_headers,
        json={"custom_brand": "Bosch Premium"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["brand"] == "Bosch Premium"


async def test_update_product_as_manager(
    client: AsyncClient, manager_user, manager_headers, sample_product
) -> None:
    resp = await client.patch(
        f"/api/products/{sample_product.id}",
        headers=manager_headers,
        json={"custom_name": "nope"},
    )
    assert resp.status_code == 403


async def test_update_product_as_viewer(
    client: AsyncClient, test_user, user_headers, sample_product
) -> None:
    resp = await client.patch(
        f"/api/products/{sample_product.id}",
        headers=user_headers,
        json={"custom_name": "nope"},
    )
    assert resp.status_code == 403


async def test_update_product_reparent(
    client: AsyncClient,
    admin_user,
    admin_headers,
    sample_product,
    test_session_factory,
) -> None:
    from app.models.category import Category

    async with test_session_factory() as session:
        new_cat = Category(
            external_id="RE-PARENT",
            parent_id=None,
            name="New Category",
            is_active=True,
            product_count=0,
        )
        session.add(new_cat)
        await session.commit()
        await session.refresh(new_cat)
        new_cat_id = new_cat.id

    resp = await client.patch(
        f"/api/products/{sample_product.id}",
        headers=admin_headers,
        json={"custom_category_id": str(new_cat_id)},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["category"]["id"] == str(new_cat_id)
    assert resp.json()["category"]["name"] == "New Category"


async def test_update_product_invalid_category(
    client: AsyncClient, admin_user, admin_headers, sample_product
) -> None:
    resp = await client.patch(
        f"/api/products/{sample_product.id}",
        headers=admin_headers,
        json={"custom_category_id": str(uuid4())},
    )
    assert resp.status_code == 404
    assert resp.json()["code"] == "CATEGORY_NOT_FOUND"


async def test_update_product_clear_custom_category_restores_buf(
    client: AsyncClient,
    admin_user,
    admin_headers,
    sample_product,
    test_session_factory,
) -> None:
    """Clearing custom_category_id now falls back to BUF (no longer rejected)."""
    from app.models.category import Category

    # Override with a fresh category first.
    async with test_session_factory() as session:
        other = Category(
            external_id="OTHER-CAT",
            parent_id=None,
            name="Other Category",
            is_active=True,
            product_count=0,
        )
        session.add(other)
        await session.commit()
        await session.refresh(other)
        other_id = other.id

    r_override = await client.patch(
        f"/api/products/{sample_product.id}",
        headers=admin_headers,
        json={"custom_category_id": str(other_id)},
    )
    assert r_override.status_code == 200
    assert r_override.json()["category"]["id"] == str(other_id)

    # Now clear the override.
    resp = await client.patch(
        f"/api/products/{sample_product.id}",
        headers=admin_headers,
        json={"custom_category_id": None},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    # Resolved category went back to BUF (sample_category "Інструменти").
    assert data["category"]["name"] == "Інструменти"
    assert data["buf_category"]["name"] == "Інструменти"


async def test_update_product_not_found(
    client: AsyncClient, admin_user, admin_headers, sample_category
) -> None:
    resp = await client.patch(
        f"/api/products/{uuid4()}",
        headers=admin_headers,
        json={"custom_name": "ghost"},
    )
    assert resp.status_code == 404
    assert resp.json()["code"] == "NOT_FOUND"


# --- POST /api/products/:id/reset-field ------------------------------------


async def test_reset_field(
    client: AsyncClient, admin_user, admin_headers, enriched_product
) -> None:
    resp = await client.post(
        f"/api/products/{enriched_product.id}/reset-field",
        headers=admin_headers,
        json={"field": "custom_name"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["custom_name"] is None
    # Display now falls back to buf_name.
    assert data["name"] == data["buf_name"] == "Шуруповерт BUF"


async def test_reset_field_invalid_field(
    client: AsyncClient, admin_user, admin_headers, sample_product
) -> None:
    resp = await client.post(
        f"/api/products/{sample_product.id}/reset-field",
        headers=admin_headers,
        json={"field": "buf_name"},
    )
    assert resp.status_code == 400
    assert resp.json()["code"] == "INVALID_FIELD"


async def test_reset_field_buf_name_rejected(
    client: AsyncClient, admin_user, admin_headers, sample_product
) -> None:
    """BUF fields remain non-resettable — import owns them."""
    resp = await client.post(
        f"/api/products/{sample_product.id}/reset-field",
        headers=admin_headers,
        json={"field": "buf_category_id"},
    )
    assert resp.status_code == 400
    assert resp.json()["code"] == "INVALID_FIELD"


async def test_reset_field_as_viewer(
    client: AsyncClient, test_user, user_headers, enriched_product
) -> None:
    resp = await client.post(
        f"/api/products/{enriched_product.id}/reset-field",
        headers=user_headers,
        json={"field": "custom_name"},
    )
    assert resp.status_code == 403


# --- BUF / custom category split (R-017 extension) ------------------------


async def test_detail_exposes_buf_category(
    client: AsyncClient, admin_user, admin_headers, sample_product, sample_category
) -> None:
    """Product detail must include a `buf_category` block alongside resolved `category`."""
    resp = await client.get(f"/api/products/{sample_product.id}", headers=admin_headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["buf_category"] is not None
    assert data["buf_category"]["id"] == str(sample_category.id)
    assert data["buf_category"]["name"] == sample_category.name
    # Resolved equals BUF when no override is set.
    assert data["category"]["id"] == data["buf_category"]["id"]


async def test_override_category_does_not_touch_buf(
    client: AsyncClient,
    admin_user,
    admin_headers,
    sample_product,
    sample_category,
    test_session_factory,
) -> None:
    """PATCH custom_category_id must leave buf_category unchanged."""
    from app.models.category import Category

    async with test_session_factory() as session:
        override = Category(
            external_id="CAT-OVR",
            parent_id=None,
            name="Override Category",
            is_active=True,
            product_count=0,
        )
        session.add(override)
        await session.commit()
        await session.refresh(override)
        override_id = override.id

    resp = await client.patch(
        f"/api/products/{sample_product.id}",
        headers=admin_headers,
        json={"custom_category_id": str(override_id)},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    # Resolved category reflects the override.
    assert data["category"]["id"] == str(override_id)
    assert data["category"]["name"] == "Override Category"
    # BUF is untouched.
    assert data["buf_category"] is not None
    assert data["buf_category"]["id"] == str(sample_category.id)
    assert data["buf_category"]["name"] == sample_category.name


async def test_reset_custom_category_restores_buf(
    client: AsyncClient,
    admin_user,
    admin_headers,
    sample_product,
    sample_category,
    test_session_factory,
) -> None:
    """After override, reset-field on custom_category_id brings BUF back."""
    from app.models.category import Category

    async with test_session_factory() as session:
        override = Category(
            external_id="CAT-RESET",
            parent_id=None,
            name="Temp Override",
            is_active=True,
            product_count=0,
        )
        session.add(override)
        await session.commit()
        await session.refresh(override)
        override_id = override.id

    # Apply override.
    r1 = await client.patch(
        f"/api/products/{sample_product.id}",
        headers=admin_headers,
        json={"custom_category_id": str(override_id)},
    )
    assert r1.status_code == 200
    assert r1.json()["category"]["id"] == str(override_id)

    # Reset via the reset-field endpoint.
    r2 = await client.post(
        f"/api/products/{sample_product.id}/reset-field",
        headers=admin_headers,
        json={"field": "custom_category_id"},
    )
    assert r2.status_code == 200, r2.text
    data = r2.json()
    # Category collapses back to BUF.
    assert data["category"]["id"] == str(sample_category.id)
    assert data["buf_category"]["id"] == str(sample_category.id)
    assert data["category"]["id"] == data["buf_category"]["id"]


# --- Bulk update -----------------------------------------------------------


async def _seed_brand_with_children(test_session_factory, brand_name: str, child_count: int):
    """Create one root 'brand' category + N children, return (brand_cat, children_ids)."""
    from app.models.category import Category

    async with test_session_factory() as session:
        brand = Category(
            external_id=f"EXT-{brand_name}",
            parent_id=None,
            name=brand_name,
            is_active=True,
            product_count=0,
        )
        session.add(brand)
        await session.commit()
        await session.refresh(brand)
        children = []
        for i in range(child_count):
            child = Category(
                external_id=f"EXT-{brand_name}-CH{i}",
                parent_id=brand.id,
                name=f"{brand_name} sub {i}",
                is_active=True,
                product_count=0,
            )
            session.add(child)
            children.append(child)
        await session.commit()
        for c in children:
            await session.refresh(c)
        return brand, children


async def _seed_products_in_categories(test_session_factory, cats_with_counts):
    """cats_with_counts: list of (category, n_products). Returns total created."""
    from app.models.product import EnrichmentStatus, Product

    total = 0
    async with test_session_factory() as session:
        for cat, n in cats_with_counts:
            for i in range(n):
                p = Product(
                    internal_code=f"BULK-{cat.external_id}-{i}",
                    sku=f"SKU-BULK-{cat.external_id}-{i}",
                    buf_category_id=cat.id,
                    buf_name=f"Product {i}",
                    buf_price=Decimal("100.00"),
                    buf_currency="UAH",
                    buf_in_stock=True,
                    is_active=True,
                    has_pending_review=False,
                    enrichment_status=EnrichmentStatus.none,
                )
                session.add(p)
                total += 1
        await session.commit()
    return total


async def test_bulk_update_brand_recursive(
    client: AsyncClient, admin_user, admin_headers, test_session_factory
):
    brand, children = await _seed_brand_with_children(test_session_factory, "JET", 2)
    # 3 in root, 2 in each of 2 children = 7 total
    await _seed_products_in_categories(
        test_session_factory, [(brand, 3), (children[0], 2), (children[1], 2)]
    )

    resp = await client.post(
        "/api/products/bulk-update",
        headers=admin_headers,
        json={
            "filter": {"buf_category_id": str(brand.id), "include_descendants": True},
            "set": {"custom_brand": "JET"},
        },
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["matched"] == 7
    assert data["updated"] == 7
    assert len(data["sample"]) == 5

    # Verify db state.
    list_resp = await client.get(
        f"/api/products?category_id={brand.id}&per_page=100", headers=admin_headers
    )
    items = list_resp.json()["data"]
    # The /products list filters by resolved category, so children's products
    # don't show up under the root unless we reassign — instead query each row.
    for item in items:
        assert item["brand"] == "JET"


async def test_bulk_update_dry_run(
    client: AsyncClient, admin_user, admin_headers, test_session_factory
):
    brand, _ = await _seed_brand_with_children(test_session_factory, "AEG", 0)
    await _seed_products_in_categories(test_session_factory, [(brand, 4)])

    resp = await client.post(
        "/api/products/bulk-update",
        headers=admin_headers,
        json={
            "filter": {"buf_category_id": str(brand.id)},
            "set": {"custom_brand": "AEG"},
            "dry_run": True,
        },
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["matched"] == 4
    assert data["updated"] == 0  # dry_run

    # Confirm nothing was actually written.
    list_resp = await client.get(
        f"/api/products?category_id={brand.id}", headers=admin_headers
    )
    for item in list_resp.json()["data"]:
        assert item["brand"] is None


async def test_bulk_update_requires_admin(
    client: AsyncClient, admin_user, operator_headers, test_session_factory
):
    brand, _ = await _seed_brand_with_children(test_session_factory, "Bosch", 0)
    resp = await client.post(
        "/api/products/bulk-update",
        headers=operator_headers,
        json={
            "filter": {"buf_category_id": str(brand.id)},
            "set": {"custom_brand": "Bosch"},
        },
    )
    assert resp.status_code == 403


async def test_bulk_update_unknown_category(
    client: AsyncClient, admin_user, admin_headers
):
    resp = await client.post(
        "/api/products/bulk-update",
        headers=admin_headers,
        json={
            "filter": {"buf_category_id": "00000000-0000-0000-0000-000000000000"},
            "set": {"custom_brand": "X"},
        },
    )
    assert resp.status_code == 404
