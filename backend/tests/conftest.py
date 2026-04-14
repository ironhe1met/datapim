"""Pytest fixtures — async test DB + httpx client + auth helpers."""

from __future__ import annotations

import os
from collections.abc import AsyncGenerator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/datapim_test",
)
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("JWT_SECRET", "test-secret-do-not-use-in-prod")


_SCHEMA_READY = False


@pytest_asyncio.fixture
async def test_engine():
    """Function-scoped engine — avoids asyncpg cross-loop issues with pytest-asyncio."""
    from app.models import Base  # noqa: WPS433

    global _SCHEMA_READY

    url = os.environ["DATABASE_URL"]
    engine = create_async_engine(url, future=True, poolclass=None)

    # Create schema once per test session (tracked via module-level flag),
    # but use a per-function engine to avoid loop-bound connection pools.
    if not _SCHEMA_READY:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
        _SCHEMA_READY = True
    else:
        # Clean data between tests.
        from sqlalchemy import text

        async with engine.begin() as conn:
            await conn.execute(text("TRUNCATE TABLE users, categories RESTART IDENTITY CASCADE"))

    try:
        yield engine
    finally:
        await engine.dispose()


@pytest_asyncio.fixture
async def test_session_factory(test_engine):
    return async_sessionmaker(test_engine, expire_on_commit=False, class_=AsyncSession)


@pytest_asyncio.fixture
async def test_session(test_session_factory) -> AsyncGenerator[AsyncSession, None]:
    async with test_session_factory() as session:
        yield session


@pytest_asyncio.fixture
async def client(test_session_factory) -> AsyncGenerator[AsyncClient, None]:
    from app.database import get_session
    from app.main import app

    async def _override_get_session() -> AsyncGenerator[AsyncSession, None]:
        async with test_session_factory() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_session] = _override_get_session
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac
    finally:
        app.dependency_overrides.pop(get_session, None)


# --- Auth helpers ---

ADMIN_EMAIL = "admin-test@example.com"
ADMIN_PASSWORD = "admin-pass-1234"
USER_EMAIL = "user-test@example.com"
USER_PASSWORD = "user-pass-1234"


@pytest_asyncio.fixture
async def admin_user(test_session_factory):
    from app.models.user import User, UserRole
    from app.security.passwords import hash_password

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
async def test_user(test_session_factory):
    from app.models.user import User, UserRole
    from app.security.passwords import hash_password

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


@pytest_asyncio.fixture
async def inactive_user(test_session_factory):
    from app.models.user import User, UserRole
    from app.security.passwords import hash_password

    async with test_session_factory() as session:
        user = User(
            email="inactive@example.com",
            password_hash=hash_password("some-pass-1234"),
            name="Inactive",
            role=UserRole.viewer,
            is_active=False,
            theme="light",
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


@pytest_asyncio.fixture
async def admin_headers(admin_user) -> dict[str, str]:
    from app.security.jwt import create_access_token

    token = create_access_token(admin_user.id)
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def user_headers(test_user) -> dict[str, str]:
    from app.security.jwt import create_access_token

    token = create_access_token(test_user.id)
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def authenticated_client(client: AsyncClient, admin_headers: dict[str, str]) -> AsyncClient:
    client.headers.update(admin_headers)
    return client
