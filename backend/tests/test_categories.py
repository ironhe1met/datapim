"""Integration tests for the Categories CRUD module."""

from __future__ import annotations

from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


# --- Extra role fixtures (mirrors tests/test_users.py) ---


MANAGER_EMAIL = "cat-manager@example.com"
MANAGER_PASSWORD = "manager-pass-1234"
OPERATOR_EMAIL = "cat-operator@example.com"
OPERATOR_PASSWORD = "operator-pass-1234"


@pytest_asyncio.fixture
async def manager_user(test_session_factory):
    from app.models.user import User, UserRole
    from app.security.passwords import hash_password

    async with test_session_factory() as session:
        user = User(
            email=MANAGER_EMAIL,
            password_hash=hash_password(MANAGER_PASSWORD),
            name="Cat Manager",
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
            password_hash=hash_password(OPERATOR_PASSWORD),
            name="Cat Operator",
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


# --- Category fixtures ---


async def _make_category(
    session_factory,
    *,
    external_id: str,
    name: str,
    parent_id=None,
):
    from app.models.category import Category

    async with session_factory() as session:
        cat = Category(
            external_id=external_id,
            name=name,
            parent_id=parent_id,
            is_active=True,
            product_count=0,
        )
        session.add(cat)
        await session.commit()
        await session.refresh(cat)
        return cat


@pytest_asyncio.fixture
async def root_category(test_session_factory):
    return await _make_category(test_session_factory, external_id="EXT-ROOT", name="Root")


@pytest_asyncio.fixture
async def child_category(test_session_factory, root_category):
    return await _make_category(
        test_session_factory,
        external_id="EXT-CHILD",
        name="Child",
        parent_id=root_category.id,
    )


@pytest_asyncio.fixture
async def category_tree(test_session_factory):
    """Build a small tree:

    Root A
      Child A1
        Grandchild A1a
      Child A2
    Root B
    """
    from app.models.category import Category

    async with test_session_factory() as session:
        root_a = Category(external_id="A", name="Root A", product_count=0, is_active=True)
        session.add(root_a)
        await session.commit()
        await session.refresh(root_a)

        child_a1 = Category(
            external_id="A1",
            name="Child A1",
            parent_id=root_a.id,
            product_count=0,
            is_active=True,
        )
        child_a2 = Category(
            external_id="A2",
            name="Child A2",
            parent_id=root_a.id,
            product_count=0,
            is_active=True,
        )
        root_b = Category(
            external_id="B",
            name="Root B",
            product_count=0,
            is_active=True,
        )
        session.add_all([child_a1, child_a2, root_b])
        await session.commit()
        await session.refresh(child_a1)
        await session.refresh(child_a2)
        await session.refresh(root_b)

        grandchild = Category(
            external_id="A1a",
            name="Grandchild A1a",
            parent_id=child_a1.id,
            product_count=0,
            is_active=True,
        )
        session.add(grandchild)
        await session.commit()
        await session.refresh(grandchild)

        return {
            "root_a": root_a,
            "child_a1": child_a1,
            "child_a2": child_a2,
            "grandchild": grandchild,
            "root_b": root_b,
        }


# --- GET /api/categories (flat) ---


async def test_list_flat_as_admin(
    client: AsyncClient, admin_user, admin_headers, category_tree
) -> None:
    resp = await client.get("/api/categories", headers=admin_headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "data" in data
    names = [c["name"] for c in data["data"]]
    # Sorted by name ascending.
    assert names == sorted(names)
    assert {"Root A", "Root B", "Child A1", "Child A2", "Grandchild A1a"} <= set(names)


async def test_list_flat_as_viewer(
    client: AsyncClient, test_user, user_headers, category_tree
) -> None:
    resp = await client.get("/api/categories", headers=user_headers)
    assert resp.status_code == 200
    assert len(resp.json()["data"]) == 5


async def test_list_flat_unauthenticated(client: AsyncClient) -> None:
    resp = await client.get("/api/categories")
    assert resp.status_code == 401


# --- GET /api/categories?tree=true ---


async def test_list_tree_as_admin(
    client: AsyncClient, admin_user, admin_headers, category_tree
) -> None:
    resp = await client.get("/api/categories", params={"tree": "true"}, headers=admin_headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    # Two roots.
    assert len(data) == 2
    root_a = next(n for n in data if n["name"] == "Root A")
    root_b = next(n for n in data if n["name"] == "Root B")

    assert len(root_b["children"]) == 0
    assert len(root_a["children"]) == 2
    child_names = {c["name"] for c in root_a["children"]}
    assert child_names == {"Child A1", "Child A2"}

    child_a1 = next(c for c in root_a["children"] if c["name"] == "Child A1")
    assert len(child_a1["children"]) == 1
    assert child_a1["children"][0]["name"] == "Grandchild A1a"


async def test_list_tree_empty(client: AsyncClient, admin_user, admin_headers) -> None:
    resp = await client.get("/api/categories", params={"tree": "true"}, headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json() == {"data": []}


# --- GET /api/categories/:id ---


async def test_get_single_with_children_and_breadcrumb(
    client: AsyncClient, admin_user, admin_headers, category_tree
) -> None:
    child_a1_id = category_tree["child_a1"].id
    resp = await client.get(f"/api/categories/{child_a1_id}", headers=admin_headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["name"] == "Child A1"
    # Direct children.
    assert len(data["children"]) == 1
    assert data["children"][0]["name"] == "Grandchild A1a"
    # Breadcrumb root -> this.
    bc_names = [b["name"] for b in data["breadcrumb"]]
    assert bc_names == ["Root A", "Child A1"]


async def test_get_single_not_found(client: AsyncClient, admin_user, admin_headers) -> None:
    resp = await client.get(f"/api/categories/{uuid4()}", headers=admin_headers)
    assert resp.status_code == 404
    assert resp.json()["code"] == "NOT_FOUND"


# --- POST /api/categories ---


async def test_create_as_admin(client: AsyncClient, admin_user, admin_headers) -> None:
    payload = {"name": "New Cat", "external_id": "EXT-NEW"}
    resp = await client.post("/api/categories", headers=admin_headers, json=payload)
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["name"] == "New Cat"
    assert data["external_id"] == "EXT-NEW"
    assert data["parent_id"] is None
    assert data["is_active"] is True
    assert data["product_count"] == 0


async def test_create_as_operator(client: AsyncClient, operator_user, operator_headers) -> None:
    resp = await client.post(
        "/api/categories",
        headers=operator_headers,
        json={"name": "By Operator"},
    )
    assert resp.status_code == 201, resp.text


async def test_create_as_manager(client: AsyncClient, manager_user, manager_headers) -> None:
    resp = await client.post("/api/categories", headers=manager_headers, json={"name": "Nope"})
    assert resp.status_code == 403


async def test_create_as_viewer(client: AsyncClient, test_user, user_headers) -> None:
    resp = await client.post("/api/categories", headers=user_headers, json={"name": "Nope"})
    assert resp.status_code == 403


async def test_create_with_parent(
    client: AsyncClient, admin_user, admin_headers, root_category
) -> None:
    resp = await client.post(
        "/api/categories",
        headers=admin_headers,
        json={"name": "Subcat", "parent_id": str(root_category.id)},
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["parent_id"] == str(root_category.id)


async def test_create_with_nonexistent_parent(
    client: AsyncClient, admin_user, admin_headers
) -> None:
    resp = await client.post(
        "/api/categories",
        headers=admin_headers,
        json={"name": "Orphan", "parent_id": str(uuid4())},
    )
    assert resp.status_code == 404
    assert resp.json()["code"] == "PARENT_NOT_FOUND"


async def test_create_auto_external_id(client: AsyncClient, admin_user, admin_headers) -> None:
    resp = await client.post(
        "/api/categories",
        headers=admin_headers,
        json={"name": "Auto EXT"},
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["external_id"].startswith("USER-")
    assert len(data["external_id"]) == len("USER-") + 8


# --- PATCH /api/categories/:id ---


async def test_update_rename(client: AsyncClient, admin_user, admin_headers, root_category) -> None:
    resp = await client.patch(
        f"/api/categories/{root_category.id}",
        headers=admin_headers,
        json={"name": "Renamed Root"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["name"] == "Renamed Root"


async def test_update_reparent(
    client: AsyncClient, admin_user, admin_headers, category_tree
) -> None:
    # Move Root B underneath Root A.
    root_a_id = category_tree["root_a"].id
    root_b_id = category_tree["root_b"].id
    resp = await client.patch(
        f"/api/categories/{root_b_id}",
        headers=admin_headers,
        json={"parent_id": str(root_a_id)},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["parent_id"] == str(root_a_id)


async def test_update_reparent_to_none(
    client: AsyncClient, admin_user, admin_headers, category_tree
) -> None:
    # Detach Child A1 from Root A → becomes root.
    child_a1_id = category_tree["child_a1"].id
    resp = await client.patch(
        f"/api/categories/{child_a1_id}",
        headers=admin_headers,
        json={"parent_id": None},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["parent_id"] is None


async def test_update_reparent_cycle_self(
    client: AsyncClient, admin_user, admin_headers, root_category
) -> None:
    resp = await client.patch(
        f"/api/categories/{root_category.id}",
        headers=admin_headers,
        json={"parent_id": str(root_category.id)},
    )
    assert resp.status_code == 400
    assert resp.json()["code"] == "INVALID_PARENT"


async def test_update_reparent_cycle_descendant(
    client: AsyncClient, admin_user, admin_headers, category_tree
) -> None:
    # Try to make Root A a child of its own grandchild → cycle.
    root_a_id = category_tree["root_a"].id
    grandchild_id = category_tree["grandchild"].id
    resp = await client.patch(
        f"/api/categories/{root_a_id}",
        headers=admin_headers,
        json={"parent_id": str(grandchild_id)},
    )
    assert resp.status_code == 400
    assert resp.json()["code"] == "INVALID_PARENT"


async def test_update_as_manager(
    client: AsyncClient, manager_user, manager_headers, root_category
) -> None:
    resp = await client.patch(
        f"/api/categories/{root_category.id}",
        headers=manager_headers,
        json={"name": "Hacked"},
    )
    assert resp.status_code == 403


async def test_update_not_found(client: AsyncClient, admin_user, admin_headers) -> None:
    resp = await client.patch(
        f"/api/categories/{uuid4()}",
        headers=admin_headers,
        json={"name": "Ghost"},
    )
    assert resp.status_code == 404
    assert resp.json()["code"] == "NOT_FOUND"
