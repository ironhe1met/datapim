"""Integration tests for Product Attributes CRUD."""

from __future__ import annotations

from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


# --- Role fixtures (copied minimal set from test_users.py) ---

MANAGER_EMAIL = "attr-manager@example.com"
OPERATOR_EMAIL = "attr-operator@example.com"


@pytest_asyncio.fixture
async def manager_user(test_session_factory):
    from app.models.user import User, UserRole
    from app.security.passwords import hash_password

    async with test_session_factory() as session:
        user = User(
            email=MANAGER_EMAIL,
            password_hash=hash_password("manager-pass-1234"),
            name="Attr Manager",
            role=UserRole.manager,
            is_active=True,
            theme="light",
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


@pytest_asyncio.fixture
async def operator_user(test_session_factory):
    from app.models.user import User, UserRole
    from app.security.passwords import hash_password

    async with test_session_factory() as session:
        user = User(
            email=OPERATOR_EMAIL,
            password_hash=hash_password("operator-pass-1234"),
            name="Attr Operator",
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

    token = create_access_token(manager_user.id)
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def operator_headers(operator_user) -> dict[str, str]:
    from app.security.jwt import create_access_token

    token = create_access_token(operator_user.id)
    return {"Authorization": f"Bearer {token}"}


# --- Sample product (direct DB insert). Unique per test via uuid-based codes. ---


@pytest_asyncio.fixture
async def sample_product(test_session):
    """Create a category + product using the shared test_session.

    Depending on `test_session` (not `test_session_factory` directly) avoids
    re-entrant engine creation in pytest-asyncio when multiple fixtures
    open the factory within the same test.
    """
    from app.models.category import Category
    from app.models.product import Product

    uniq = uuid4().hex[:8]
    cat = Category(
        external_id=f"CAT-attr-{uniq}",
        parent_id=None,
        name=f"Attr Cat {uniq}",
        is_active=True,
        product_count=0,
    )
    test_session.add(cat)
    await test_session.commit()
    await test_session.refresh(cat)

    product = Product(
        internal_code=f"P-attr-{uniq}",
        sku=f"SKU-attr-{uniq}",
        buf_category_id=cat.id,
        buf_name=f"Sample Product {uniq}",
        buf_price=0,
        buf_currency="UAH",
        buf_in_stock=True,
        is_active=True,
    )
    test_session.add(product)
    await test_session.commit()
    await test_session.refresh(product)
    return product


# --- GET /api/products/:id/attributes ---


async def test_list_attributes(
    client: AsyncClient, admin_user, admin_headers, sample_product
) -> None:
    resp = await client.get(
        f"/api/products/{sample_product.id}/attributes",
        headers=admin_headers,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "data" in data
    assert data["data"] == []


# --- POST /api/products/:id/attributes ---


async def test_create_attribute_as_admin(
    client: AsyncClient, admin_user, admin_headers, sample_product
) -> None:
    resp = await client.post(
        f"/api/products/{sample_product.id}/attributes",
        headers=admin_headers,
        json={"key": "Вага", "value": "5 кг"},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["key"] == "Вага"
    assert body["value"] == "5 кг"
    assert body["source"] == "manual"
    assert body["sort_order"] == 1
    assert "id" in body


async def test_create_attribute_as_operator(
    client: AsyncClient, operator_user, operator_headers, sample_product
) -> None:
    resp = await client.post(
        f"/api/products/{sample_product.id}/attributes",
        headers=operator_headers,
        json={"key": "Колір", "value": "Синій"},
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["source"] == "manual"


async def test_create_attribute_as_manager(
    client: AsyncClient, manager_user, manager_headers, sample_product
) -> None:
    resp = await client.post(
        f"/api/products/{sample_product.id}/attributes",
        headers=manager_headers,
        json={"key": "Вага", "value": "5 кг"},
    )
    assert resp.status_code == 403


async def test_create_attribute_duplicate_key(
    client: AsyncClient, admin_user, admin_headers, sample_product
) -> None:
    pid = sample_product.id
    r1 = await client.post(
        f"/api/products/{pid}/attributes",
        headers=admin_headers,
        json={"key": "Вага", "value": "5 кг"},
    )
    assert r1.status_code == 201

    # Case-insensitive duplicate.
    r2 = await client.post(
        f"/api/products/{pid}/attributes",
        headers=admin_headers,
        json={"key": "ВАГА", "value": "10 кг"},
    )
    assert r2.status_code == 409
    assert r2.json()["code"] == "DUPLICATE_KEY"


async def test_create_attribute_product_not_found(
    client: AsyncClient, admin_user, admin_headers
) -> None:
    resp = await client.post(
        f"/api/products/{uuid4()}/attributes",
        headers=admin_headers,
        json={"key": "X", "value": "Y"},
    )
    assert resp.status_code == 404
    assert resp.json()["code"] == "NOT_FOUND"


# --- PATCH /api/products/:id/attributes/:attr_id ---


async def test_update_attribute(
    client: AsyncClient, admin_user, admin_headers, sample_product
) -> None:
    pid = sample_product.id
    create = await client.post(
        f"/api/products/{pid}/attributes",
        headers=admin_headers,
        json={"key": "Вага", "value": "5 кг"},
    )
    attr_id = create.json()["id"]

    resp = await client.patch(
        f"/api/products/{pid}/attributes/{attr_id}",
        headers=admin_headers,
        json={"value": "7 кг", "sort_order": 99},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["key"] == "Вага"
    assert body["value"] == "7 кг"
    assert body["sort_order"] == 99


async def test_update_attribute_key_conflict(
    client: AsyncClient, admin_user, admin_headers, sample_product
) -> None:
    pid = sample_product.id
    a = await client.post(
        f"/api/products/{pid}/attributes",
        headers=admin_headers,
        json={"key": "Вага", "value": "5"},
    )
    b = await client.post(
        f"/api/products/{pid}/attributes",
        headers=admin_headers,
        json={"key": "Колір", "value": "Червоний"},
    )
    assert a.status_code == 201 and b.status_code == 201

    # Try to rename B to conflict with A (case-insensitive).
    resp = await client.patch(
        f"/api/products/{pid}/attributes/{b.json()['id']}",
        headers=admin_headers,
        json={"key": "ВАГА"},
    )
    assert resp.status_code == 409
    assert resp.json()["code"] == "DUPLICATE_KEY"


async def test_update_attribute_not_found(
    client: AsyncClient, admin_user, admin_headers, sample_product
) -> None:
    resp = await client.patch(
        f"/api/products/{sample_product.id}/attributes/{uuid4()}",
        headers=admin_headers,
        json={"value": "X"},
    )
    assert resp.status_code == 404


# --- DELETE /api/products/:id/attributes/:attr_id ---


async def test_delete_attribute(
    client: AsyncClient, admin_user, admin_headers, sample_product
) -> None:
    pid = sample_product.id
    create = await client.post(
        f"/api/products/{pid}/attributes",
        headers=admin_headers,
        json={"key": "Вага", "value": "5 кг"},
    )
    attr_id = create.json()["id"]

    resp = await client.delete(
        f"/api/products/{pid}/attributes/{attr_id}",
        headers=admin_headers,
    )
    assert resp.status_code == 200
    assert resp.json() == {"message": "Deleted"}

    # Confirm gone via list.
    listing = await client.get(f"/api/products/{pid}/attributes", headers=admin_headers)
    assert all(a["id"] != attr_id for a in listing.json()["data"])


async def test_delete_attribute_as_viewer(
    client: AsyncClient, admin_user, admin_headers, sample_product, test_user, user_headers
) -> None:
    create = await client.post(
        f"/api/products/{sample_product.id}/attributes",
        headers=admin_headers,
        json={"key": "Вага", "value": "5"},
    )
    attr_id = create.json()["id"]

    resp = await client.delete(
        f"/api/products/{sample_product.id}/attributes/{attr_id}",
        headers=user_headers,
    )
    assert resp.status_code == 403
