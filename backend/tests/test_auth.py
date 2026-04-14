"""Integration tests for the Auth module."""

from __future__ import annotations

from datetime import timedelta

import pytest
from fastapi import Depends, FastAPI
from httpx import ASGITransport, AsyncClient

from tests.conftest import ADMIN_EMAIL, ADMIN_PASSWORD

pytestmark = pytest.mark.asyncio


# --- /login ---


async def test_login_success(client: AsyncClient, admin_user) -> None:
    resp = await client.post(
        "/api/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == ADMIN_EMAIL
    assert data["user"]["role"] == "admin"
    assert data["user"]["is_active"] is True


async def test_login_case_insensitive_email(client: AsyncClient, admin_user) -> None:
    resp = await client.post(
        "/api/auth/login",
        json={"email": ADMIN_EMAIL.upper(), "password": ADMIN_PASSWORD},
    )
    assert resp.status_code == 200, resp.text


async def test_login_wrong_password(client: AsyncClient, admin_user) -> None:
    resp = await client.post(
        "/api/auth/login",
        json={"email": ADMIN_EMAIL, "password": "wrong-password"},
    )
    assert resp.status_code == 401
    assert resp.json()["code"] == "INVALID_CREDENTIALS"


async def test_login_nonexistent_email(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/auth/login",
        json={"email": "nobody@example.com", "password": "whatever12"},
    )
    assert resp.status_code == 401
    assert resp.json()["code"] == "INVALID_CREDENTIALS"


async def test_login_deactivated_user(client: AsyncClient, inactive_user) -> None:
    resp = await client.post(
        "/api/auth/login",
        json={"email": "inactive@example.com", "password": "some-pass-1234"},
    )
    assert resp.status_code == 403
    assert resp.json()["code"] == "ACCOUNT_DISABLED"


# --- /me ---


async def test_me_success(client: AsyncClient, admin_user, admin_headers) -> None:
    resp = await client.get("/api/auth/me", headers=admin_headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["email"] == ADMIN_EMAIL
    assert data["role"] == "admin"
    assert "created_at" in data


async def test_me_no_token(client: AsyncClient) -> None:
    resp = await client.get("/api/auth/me")
    assert resp.status_code == 401


async def test_me_invalid_token(client: AsyncClient) -> None:
    resp = await client.get("/api/auth/me", headers={"Authorization": "Bearer not-a-jwt"})
    assert resp.status_code == 401


async def test_me_malformed_header(client: AsyncClient) -> None:
    resp = await client.get("/api/auth/me", headers={"Authorization": "garbage"})
    assert resp.status_code == 401


async def test_me_expired_token(client: AsyncClient, admin_user) -> None:
    from app.security.jwt import create_access_token

    # Issue token that expired 1 second ago.
    token = create_access_token(admin_user.id, expires_delta=timedelta(seconds=-1))
    resp = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401


async def test_me_refresh_token_rejected_on_me(client: AsyncClient, admin_user) -> None:
    from app.security.jwt import create_refresh_token

    token = create_refresh_token(admin_user.id)
    resp = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401


# --- /refresh ---


async def test_refresh_success(client: AsyncClient, admin_user) -> None:
    login = await client.post(
        "/api/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
    )
    assert login.status_code == 200
    refresh_token = login.json()["refresh_token"]

    resp = await client.post("/api/auth/refresh", json={"refresh_token": refresh_token})
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


async def test_refresh_with_access_token(client: AsyncClient, admin_user) -> None:
    from app.security.jwt import create_access_token

    access = create_access_token(admin_user.id)
    resp = await client.post("/api/auth/refresh", json={"refresh_token": access})
    assert resp.status_code == 401
    assert resp.json()["code"] == "INVALID_TOKEN"


async def test_refresh_invalid_token(client: AsyncClient) -> None:
    resp = await client.post("/api/auth/refresh", json={"refresh_token": "not-a-token"})
    assert resp.status_code == 401


async def test_refresh_expired_token(client: AsyncClient, admin_user) -> None:
    from app.security.jwt import create_refresh_token

    token = create_refresh_token(admin_user.id, expires_delta=timedelta(seconds=-1))
    resp = await client.post("/api/auth/refresh", json={"refresh_token": token})
    assert resp.status_code == 401
    assert resp.json()["code"] == "TOKEN_EXPIRED"


# --- /logout ---


async def test_logout_requires_auth(client: AsyncClient) -> None:
    resp = await client.post("/api/auth/logout")
    assert resp.status_code == 401


async def test_logout_success(client: AsyncClient, admin_user, admin_headers) -> None:
    resp = await client.post("/api/auth/logout", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json() == {"message": "ok"}


# --- PATCH /me ---


async def test_me_update_name(client: AsyncClient, admin_user, admin_headers) -> None:
    resp = await client.patch("/api/auth/me", headers=admin_headers, json={"name": "New Name"})
    assert resp.status_code == 200, resp.text
    assert resp.json()["name"] == "New Name"


async def test_me_update_theme(client: AsyncClient, admin_user, admin_headers) -> None:
    resp = await client.patch("/api/auth/me", headers=admin_headers, json={"theme": "dark"})
    assert resp.status_code == 200, resp.text
    assert resp.json()["theme"] == "dark"


async def test_me_update_theme_invalid(client: AsyncClient, admin_user, admin_headers) -> None:
    resp = await client.patch("/api/auth/me", headers=admin_headers, json={"theme": "neon"})
    assert resp.status_code == 422


async def test_me_update_password_without_current(
    client: AsyncClient, admin_user, admin_headers
) -> None:
    resp = await client.patch(
        "/api/auth/me",
        headers=admin_headers,
        json={"password": "new-password-1234"},
    )
    assert resp.status_code in (400, 422)


async def test_me_update_password_wrong_current(
    client: AsyncClient, admin_user, admin_headers
) -> None:
    resp = await client.patch(
        "/api/auth/me",
        headers=admin_headers,
        json={
            "password": "new-password-1234",
            "current_password": "wrong-current",
        },
    )
    assert resp.status_code == 400
    assert resp.json()["code"] == "INVALID_PASSWORD"


async def test_me_update_password_correct(client: AsyncClient, admin_user, admin_headers) -> None:
    new_password = "new-admin-password-9999"
    resp = await client.patch(
        "/api/auth/me",
        headers=admin_headers,
        json={
            "password": new_password,
            "current_password": ADMIN_PASSWORD,
        },
    )
    assert resp.status_code == 200, resp.text

    # Old password no longer works.
    old_login = await client.post(
        "/api/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
    )
    assert old_login.status_code == 401

    # New password works.
    new_login = await client.post(
        "/api/auth/login",
        json={"email": ADMIN_EMAIL, "password": new_password},
    )
    assert new_login.status_code == 200


# --- RBAC ---


async def test_rbac_require_admin(
    client: AsyncClient,
    admin_user,
    test_user,
    admin_headers,
    user_headers,
    test_session_factory,
) -> None:
    """Mount a temporary endpoint guarded by require_role('admin') and verify."""
    from app.database import get_session
    from app.dependencies.auth import require_role
    from app.main import app as main_app  # noqa: F401 — ensure app is imported

    test_app = FastAPI()

    async def _override_get_session():
        async with test_session_factory() as session:
            yield session

    test_app.dependency_overrides[get_session] = _override_get_session

    @test_app.get("/admin-only")
    async def _admin_only(user=Depends(require_role("admin"))) -> dict:
        return {"ok": True, "role": user.role.value}

    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # viewer → 403
        r_forbidden = await ac.get("/admin-only", headers=user_headers)
        assert r_forbidden.status_code == 403

        # admin → 200
        r_ok = await ac.get("/admin-only", headers=admin_headers)
        assert r_ok.status_code == 200
        assert r_ok.json()["ok"] is True

        # no token → 401
        r_anon = await ac.get("/admin-only")
        assert r_anon.status_code == 401
