"""Idempotent seed — creates admin user from DEV_* env vars."""

from __future__ import annotations

import asyncio

import bcrypt
from loguru import logger
from sqlalchemy import select

from app.config import get_settings
from app.database import SessionLocal
from app.logging_config import setup_logging
from app.models.user import User, UserRole


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


async def seed_admin() -> None:
    settings = get_settings()
    async with SessionLocal() as session:
        result = await session.execute(select(User).where(User.email == settings.dev_email))
        existing = result.scalar_one_or_none()
        if existing is not None:
            logger.info("seed_admin_exists", email=settings.dev_email, id=str(existing.id))
            return

        user = User(
            email=settings.dev_email,
            password_hash=_hash_password(settings.dev_password),
            name=settings.dev_name,
            role=UserRole.admin,
            is_active=True,
            theme="light",
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        logger.info("seed_admin_created", email=settings.dev_email, id=str(user.id))


async def main() -> None:
    setup_logging()
    await seed_admin()


if __name__ == "__main__":
    asyncio.run(main())
