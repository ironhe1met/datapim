"""Integration tests for Product Images CRUD."""

from __future__ import annotations

import io
from pathlib import Path
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


# --- Role fixtures ---

MANAGER_EMAIL = "img-manager@example.com"


@pytest_asyncio.fixture
async def manager_user(test_session_factory):
    from app.models.user import User, UserRole
    from app.security.passwords import hash_password

    async with test_session_factory() as session:
        user = User(
            email=MANAGER_EMAIL,
            password_hash=hash_password("manager-pass-1234"),
            name="Img Manager",
            role=UserRole.manager,
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


# --- Temp upload dir fixture (autouse) — overrides settings.upload_dir ---


@pytest_asyncio.fixture(autouse=True)
async def _temp_upload_dir(tmp_path, monkeypatch):
    from app.config import get_settings

    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)

    settings = get_settings()
    monkeypatch.setattr(settings, "upload_dir", str(upload_dir))
    yield upload_dir


# --- Sample product ---


@pytest_asyncio.fixture
async def sample_product(test_session):
    """Shared-session variant — avoids pytest-asyncio loop-scope issues."""
    from app.models.category import Category
    from app.models.product import Product

    uniq = uuid4().hex[:8]
    cat = Category(
        external_id=f"CAT-img-{uniq}",
        parent_id=None,
        name=f"Img Cat {uniq}",
        is_active=True,
        product_count=0,
    )
    test_session.add(cat)
    await test_session.commit()
    await test_session.refresh(cat)

    product = Product(
        internal_code=f"P-img-{uniq}",
        sku=f"SKU-img-{uniq}",
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


# --- Helpers ---

# Minimal valid 1x1 RGBA PNG (68 bytes).
PNG_1x1 = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
    "0000000b49444154789c6360000200000500017a5eab3f0000000049454e44ae426082"
)


def _png_bytes() -> bytes:
    return PNG_1x1


async def _upload(
    client: AsyncClient,
    headers: dict[str, str],
    product_id,
    *,
    content: bytes | None = None,
    filename: str = "a.png",
    content_type: str = "image/png",
):
    data = content if content is not None else _png_bytes()
    files = {"file": (filename, io.BytesIO(data), content_type)}
    return await client.post(
        f"/api/products/{product_id}/images",
        headers=headers,
        files=files,
    )


# --- GET /api/products/:id/images ---


async def test_list_images_empty(
    client: AsyncClient, admin_user, admin_headers, sample_product
) -> None:
    resp = await client.get(f"/api/products/{sample_product.id}/images", headers=admin_headers)
    assert resp.status_code == 200, resp.text
    assert resp.json() == {"data": []}


# --- POST /api/products/:id/images ---


async def test_upload_image_as_admin(
    client: AsyncClient, admin_user, admin_headers, sample_product, _temp_upload_dir
) -> None:
    resp = await _upload(client, admin_headers, sample_product.id, filename="photo.png")
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["mime_type"] == "image/png"
    assert body["file_name"] == "photo.png"
    assert body["file_path"].startswith("/uploads/")
    assert body["is_primary"] is True
    assert body["source"] == "upload"
    assert body["file_size"] == len(_png_bytes())

    # Confirm the file exists on disk.
    relative = body["file_path"].removeprefix("/uploads/")
    assert (Path(_temp_upload_dir) / relative).exists()


async def test_upload_image_as_manager(
    client: AsyncClient, manager_user, manager_headers, sample_product
) -> None:
    resp = await _upload(client, manager_headers, sample_product.id)
    assert resp.status_code == 403


async def test_upload_image_too_large(
    client: AsyncClient, admin_user, admin_headers, sample_product
) -> None:
    too_big = b"\x00" * (10 * 1024 * 1024 + 1)
    resp = await _upload(
        client,
        admin_headers,
        sample_product.id,
        content=too_big,
        filename="big.png",
        content_type="image/png",
    )
    assert resp.status_code == 400
    assert resp.json()["code"] == "FILE_TOO_LARGE"


async def test_upload_image_wrong_type(
    client: AsyncClient, admin_user, admin_headers, sample_product
) -> None:
    resp = await _upload(
        client,
        admin_headers,
        sample_product.id,
        content=b"hello world",
        filename="notes.txt",
        content_type="text/plain",
    )
    assert resp.status_code == 400
    assert resp.json()["code"] == "INVALID_FILE_TYPE"


async def test_upload_first_is_primary(
    client: AsyncClient, admin_user, admin_headers, sample_product
) -> None:
    resp = await _upload(client, admin_headers, sample_product.id)
    assert resp.status_code == 201
    assert resp.json()["is_primary"] is True


async def test_upload_second_not_primary(
    client: AsyncClient, admin_user, admin_headers, sample_product
) -> None:
    r1 = await _upload(client, admin_headers, sample_product.id, filename="a.png")
    r2 = await _upload(client, admin_headers, sample_product.id, filename="b.png")
    assert r1.status_code == 201 and r2.status_code == 201
    assert r1.json()["is_primary"] is True
    assert r2.json()["is_primary"] is False


# --- PATCH /api/products/:id/images/:image_id ---


async def test_update_image_set_primary(
    client: AsyncClient, admin_user, admin_headers, sample_product
) -> None:
    pid = sample_product.id
    r1 = await _upload(client, admin_headers, pid, filename="a.png")
    r2 = await _upload(client, admin_headers, pid, filename="b.png")
    first_id = r1.json()["id"]
    second_id = r2.json()["id"]

    resp = await client.patch(
        f"/api/products/{pid}/images/{second_id}",
        headers=admin_headers,
        json={"is_primary": True},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["is_primary"] is True

    # Confirm the first one is no longer primary.
    listing = await client.get(f"/api/products/{pid}/images", headers=admin_headers)
    by_id = {i["id"]: i for i in listing.json()["data"]}
    assert by_id[first_id]["is_primary"] is False
    assert by_id[second_id]["is_primary"] is True


# --- DELETE /api/products/:id/images/:image_id ---


async def test_delete_image(
    client: AsyncClient, admin_user, admin_headers, sample_product, _temp_upload_dir
) -> None:
    pid = sample_product.id
    r1 = await _upload(client, admin_headers, pid, filename="a.png")
    r2 = await _upload(client, admin_headers, pid, filename="b.png")
    primary = r1.json()
    other = r2.json()
    assert primary["is_primary"] is True and other["is_primary"] is False

    # Delete the primary.
    resp = await client.delete(f"/api/products/{pid}/images/{primary['id']}", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json() == {"message": "Deleted"}

    # Confirm file removed from disk.
    relative = primary["file_path"].removeprefix("/uploads/")
    assert not (Path(_temp_upload_dir) / relative).exists()

    # The other image should now be primary.
    listing = await client.get(f"/api/products/{pid}/images", headers=admin_headers)
    data = listing.json()["data"]
    assert len(data) == 1
    assert data[0]["id"] == other["id"]
    assert data[0]["is_primary"] is True


async def test_delete_image_as_viewer(
    client: AsyncClient, admin_user, admin_headers, sample_product, test_user, user_headers
) -> None:
    r = await _upload(client, admin_headers, sample_product.id)
    img_id = r.json()["id"]

    resp = await client.delete(
        f"/api/products/{sample_product.id}/images/{img_id}",
        headers=user_headers,
    )
    assert resp.status_code == 403
