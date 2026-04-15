"""Integration tests for the Users CRUD module."""

from __future__ import annotations

from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import AsyncClient

from tests.conftest import ADMIN_EMAIL

pytestmark = pytest.mark.asyncio


# --- Extra fixtures for roles not covered in conftest.py ---


MANAGER_EMAIL = "manager-test@example.com"
MANAGER_PASSWORD = "manager-pass-1234"
OPERATOR_EMAIL = "operator-test@example.com"
OPERATOR_PASSWORD = "operator-pass-1234"


@pytest_asyncio.fixture
async def manager_user(test_session_factory):
    from app.models.user import User, UserRole
    from app.security.passwords import hash_password

    async with test_session_factory() as session:
        user = User(
            email=MANAGER_EMAIL,
            password_hash=hash_password(MANAGER_PASSWORD),
            name="Manager Test",
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
            name="Operator Test",
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


# Helper to create many users directly via DB.
async def _create_users_bulk(
    test_session_factory, count: int, role: str = "viewer", prefix: str = "bulk"
) -> None:
    from app.models.user import User, UserRole
    from app.security.passwords import hash_password

    async with test_session_factory() as session:
        for i in range(count):
            session.add(
                User(
                    email=f"{prefix}-{i}@example.com",
                    password_hash=hash_password("some-pass-1234"),
                    name=f"{prefix.capitalize()} {i}",
                    role=UserRole(role),
                    is_active=True,
                    theme="light",
                )
            )
        await session.commit()


# --- GET /api/users — list / RBAC / filters ---


async def test_list_users_as_admin(client: AsyncClient, admin_user, admin_headers) -> None:
    resp = await client.get("/api/users", headers=admin_headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "data" in data and "meta" in data
    emails = [u["email"] for u in data["data"]]
    assert ADMIN_EMAIL in emails
    assert data["meta"]["total"] >= 1


async def test_list_users_as_manager(
    client: AsyncClient, admin_user, manager_user, manager_headers
) -> None:
    resp = await client.get("/api/users", headers=manager_headers)
    assert resp.status_code == 200
    assert resp.json()["meta"]["total"] >= 2


async def test_list_users_as_operator(client: AsyncClient, operator_user, operator_headers) -> None:
    resp = await client.get("/api/users", headers=operator_headers)
    assert resp.status_code == 403


async def test_list_users_as_viewer(client: AsyncClient, test_user, user_headers) -> None:
    resp = await client.get("/api/users", headers=user_headers)
    assert resp.status_code == 403


async def test_list_users_unauthorized(client: AsyncClient) -> None:
    resp = await client.get("/api/users")
    assert resp.status_code == 401


async def test_list_users_pagination(
    client: AsyncClient,
    admin_user,
    admin_headers,
    test_session_factory,
) -> None:
    await _create_users_bulk(test_session_factory, 55, prefix="page")
    resp = await client.get("/api/users", params={"page": 1, "per_page": 10}, headers=admin_headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert len(data["data"]) == 10
    # 55 bulk + 1 admin = 56 → ceil(56/10) = 6 last_page
    assert data["meta"]["total"] == 56
    assert data["meta"]["last_page"] == 6
    assert data["meta"]["page"] == 1
    assert data["meta"]["per_page"] == 10

    # Last page should have 6 items.
    last = await client.get("/api/users", params={"page": 6, "per_page": 10}, headers=admin_headers)
    assert last.status_code == 200
    assert len(last.json()["data"]) == 6


async def test_list_users_search(
    client: AsyncClient, admin_user, admin_headers, test_session_factory
) -> None:
    from app.models.user import User, UserRole
    from app.security.passwords import hash_password

    async with test_session_factory() as session:
        session.add(
            User(
                email="alice.wonder@example.com",
                password_hash=hash_password("alice-pass-1234"),
                name="Alice Wonderland",
                role=UserRole.viewer,
                is_active=True,
                theme="light",
            )
        )
        session.add(
            User(
                email="bob@example.com",
                password_hash=hash_password("bob-pass-1234"),
                name="Bob Builder",
                role=UserRole.viewer,
                is_active=True,
                theme="light",
            )
        )
        await session.commit()

    # Search by name.
    r1 = await client.get("/api/users", params={"search": "alice"}, headers=admin_headers)
    assert r1.status_code == 200
    emails1 = [u["email"] for u in r1.json()["data"]]
    assert "alice.wonder@example.com" in emails1
    assert "bob@example.com" not in emails1

    # Search by email substring (case-insensitive).
    r2 = await client.get("/api/users", params={"search": "WONDER"}, headers=admin_headers)
    assert r2.status_code == 200
    emails2 = [u["email"] for u in r2.json()["data"]]
    assert "alice.wonder@example.com" in emails2


async def test_list_users_filter_by_role(
    client: AsyncClient,
    admin_user,
    manager_user,
    operator_user,
    test_user,
    admin_headers,
) -> None:
    resp = await client.get("/api/users", params={"role": "manager"}, headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert all(u["role"] == "manager" for u in data["data"])
    assert data["meta"]["total"] == 1


async def test_list_users_filter_is_active(
    client: AsyncClient, admin_user, inactive_user, admin_headers
) -> None:
    r_active = await client.get("/api/users", params={"is_active": "true"}, headers=admin_headers)
    assert r_active.status_code == 200
    assert all(u["is_active"] is True for u in r_active.json()["data"])

    r_inactive = await client.get(
        "/api/users", params={"is_active": "false"}, headers=admin_headers
    )
    assert r_inactive.status_code == 200
    data = r_inactive.json()["data"]
    assert len(data) == 1
    assert data[0]["email"] == "inactive@example.com"
    assert data[0]["is_active"] is False


# --- POST /api/users ---


async def test_create_user_as_admin(client: AsyncClient, admin_user, admin_headers) -> None:
    payload = {
        "email": "new-user@example.com",
        "name": "New User",
        "password": "new-pass-1234",
        "role": "operator",
    }
    resp = await client.post("/api/users", headers=admin_headers, json=payload)
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["email"] == "new-user@example.com"
    assert data["role"] == "operator"
    assert data["is_active"] is True
    assert data["theme"] == "light"
    assert "id" in data
    assert "created_at" in data
    assert "password" not in data
    assert "password_hash" not in data


async def test_create_user_duplicate_email(client: AsyncClient, admin_user, admin_headers) -> None:
    # Case-insensitive duplicate (ADMIN_EMAIL already exists).
    payload = {
        "email": ADMIN_EMAIL.upper(),
        "name": "Dup",
        "password": "dup-pass-1234",
        "role": "viewer",
    }
    resp = await client.post("/api/users", headers=admin_headers, json=payload)
    assert resp.status_code == 409
    assert resp.json()["code"] == "DUPLICATE_EMAIL"


async def test_create_user_as_operator(
    client: AsyncClient, operator_user, operator_headers
) -> None:
    payload = {
        "email": "nope@example.com",
        "name": "Nope",
        "password": "nope-pass-1234",
        "role": "viewer",
    }
    resp = await client.post("/api/users", headers=operator_headers, json=payload)
    assert resp.status_code == 403


async def test_create_user_validation_short_password(
    client: AsyncClient, admin_user, admin_headers
) -> None:
    resp = await client.post(
        "/api/users",
        headers=admin_headers,
        json={"email": "short@example.com", "name": "Short", "password": "x", "role": "viewer"},
    )
    assert resp.status_code == 422


async def test_create_user_validation_invalid_email(
    client: AsyncClient, admin_user, admin_headers
) -> None:
    resp = await client.post(
        "/api/users",
        headers=admin_headers,
        json={
            "email": "not-an-email",
            "name": "Bad",
            "password": "bad-pass-1234",
            "role": "viewer",
        },
    )
    assert resp.status_code == 422


# --- GET /api/users/:id ---


async def test_get_user_as_admin(client: AsyncClient, admin_user, admin_headers) -> None:
    resp = await client.get(f"/api/users/{admin_user.id}", headers=admin_headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["email"] == ADMIN_EMAIL


async def test_get_user_as_manager(
    client: AsyncClient, admin_user, manager_user, manager_headers
) -> None:
    resp = await client.get(f"/api/users/{admin_user.id}", headers=manager_headers)
    assert resp.status_code == 200


async def test_get_user_as_operator(
    client: AsyncClient, admin_user, operator_user, operator_headers
) -> None:
    resp = await client.get(f"/api/users/{admin_user.id}", headers=operator_headers)
    assert resp.status_code == 403


async def test_get_user_not_found(client: AsyncClient, admin_user, admin_headers) -> None:
    resp = await client.get(f"/api/users/{uuid4()}", headers=admin_headers)
    assert resp.status_code == 404
    assert resp.json()["code"] == "NOT_FOUND"


# --- PATCH /api/users/:id ---


async def test_update_user_as_admin(
    client: AsyncClient, admin_user, test_user, admin_headers
) -> None:
    resp = await client.patch(
        f"/api/users/{test_user.id}",
        headers=admin_headers,
        json={"name": "Renamed", "role": "manager"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["name"] == "Renamed"
    assert data["role"] == "manager"


async def test_update_user_email_conflict(
    client: AsyncClient, admin_user, test_user, admin_headers
) -> None:
    resp = await client.patch(
        f"/api/users/{test_user.id}",
        headers=admin_headers,
        json={"email": ADMIN_EMAIL},
    )
    assert resp.status_code == 409
    assert resp.json()["code"] == "DUPLICATE_EMAIL"


async def test_update_user_password(
    client: AsyncClient, admin_user, test_user, admin_headers
) -> None:
    new_password = "brand-new-pass-9999"
    resp = await client.patch(
        f"/api/users/{test_user.id}",
        headers=admin_headers,
        json={"password": new_password},
    )
    assert resp.status_code == 200, resp.text

    # Verify the new password works for login.
    from tests.conftest import USER_EMAIL

    login = await client.post(
        "/api/auth/login",
        json={"email": USER_EMAIL, "password": new_password},
    )
    assert login.status_code == 200, login.text


async def test_update_user_as_operator(
    client: AsyncClient, admin_user, operator_user, operator_headers
) -> None:
    resp = await client.patch(
        f"/api/users/{admin_user.id}",
        headers=operator_headers,
        json={"name": "Hacked"},
    )
    assert resp.status_code == 403


async def test_update_user_not_found(client: AsyncClient, admin_user, admin_headers) -> None:
    resp = await client.patch(
        f"/api/users/{uuid4()}",
        headers=admin_headers,
        json={"name": "Ghost"},
    )
    assert resp.status_code == 404
    assert resp.json()["code"] == "NOT_FOUND"


# --- DELETE /api/users/:id (soft delete) ---


async def test_deactivate_user_as_admin(
    client: AsyncClient, admin_user, test_user, admin_headers
) -> None:
    resp = await client.delete(f"/api/users/{test_user.id}", headers=admin_headers)
    assert resp.status_code == 200, resp.text
    assert resp.json() == {"message": "User deactivated"}

    # Confirm is_active=False via GET.
    check = await client.get(f"/api/users/{test_user.id}", headers=admin_headers)
    assert check.status_code == 200
    assert check.json()["is_active"] is False


async def test_deactivate_user_cannot_deactivate_self(
    client: AsyncClient, admin_user, admin_headers
) -> None:
    resp = await client.delete(f"/api/users/{admin_user.id}", headers=admin_headers)
    assert resp.status_code == 400
    assert resp.json()["code"] == "SELF_DEACTIVATE"


async def test_deactivate_user_as_operator(
    client: AsyncClient, admin_user, operator_user, operator_headers
) -> None:
    resp = await client.delete(f"/api/users/{admin_user.id}", headers=operator_headers)
    assert resp.status_code == 403


async def test_deactivate_user_not_found(client: AsyncClient, admin_user, admin_headers) -> None:
    resp = await client.delete(f"/api/users/{uuid4()}", headers=admin_headers)
    assert resp.status_code == 404
    assert resp.json()["code"] == "NOT_FOUND"


async def test_deactivated_user_cannot_login(
    client: AsyncClient, admin_user, test_user, admin_headers
) -> None:
    """Soft-delete a user then confirm login returns 403 ACCOUNT_DISABLED."""
    from tests.conftest import USER_EMAIL, USER_PASSWORD

    # Deactivate the test user.
    del_resp = await client.delete(f"/api/users/{test_user.id}", headers=admin_headers)
    assert del_resp.status_code == 200

    # Login should now fail with 403.
    login = await client.post(
        "/api/auth/login",
        json={"email": USER_EMAIL, "password": USER_PASSWORD},
    )
    assert login.status_code == 403
    assert login.json()["code"] == "ACCOUNT_DISABLED"


# --- Reactivate + hard delete ----------------------------------------------


async def test_reactivate_user(client: AsyncClient, admin_user, admin_headers):
    create = await client.post(
        "/api/users",
        headers=admin_headers,
        json={
            "email": "reactivate@example.com",
            "name": "R",
            "password": "Pass1234!",
            "role": "viewer",
        },
    )
    uid = create.json()["id"]

    deact = await client.delete(f"/api/users/{uid}", headers=admin_headers)
    assert deact.status_code == 200

    react = await client.post(f"/api/users/{uid}/reactivate", headers=admin_headers)
    assert react.status_code == 200
    assert react.json()["is_active"] is True


async def test_hard_delete_user(client: AsyncClient, admin_user, admin_headers):
    create = await client.post(
        "/api/users",
        headers=admin_headers,
        json={
            "email": "harddel@example.com",
            "name": "H",
            "password": "Pass1234!",
            "role": "viewer",
        },
    )
    uid = create.json()["id"]

    # Cannot hard-delete an active user.
    early = await client.delete(f"/api/users/{uid}/permanent", headers=admin_headers)
    assert early.status_code == 400, early.text

    # Deactivate, then hard-delete works.
    await client.delete(f"/api/users/{uid}", headers=admin_headers)
    perm = await client.delete(f"/api/users/{uid}/permanent", headers=admin_headers)
    assert perm.status_code == 200

    # User is gone.
    gone = await client.get(f"/api/users/{uid}", headers=admin_headers)
    assert gone.status_code == 404


async def test_hard_delete_self_blocked(client: AsyncClient, admin_user, admin_headers):
    me = await client.get("/api/auth/me", headers=admin_headers)
    self_id = me.json()["id"]
    resp = await client.delete(f"/api/users/{self_id}/permanent", headers=admin_headers)
    assert resp.status_code == 400
