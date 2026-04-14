"""Pydantic Settings — loaded from .env with validation at startup."""

from __future__ import annotations

import secrets
import warnings
from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment."""

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Environment ---
    environment: str = Field(default="development")
    log_level: str = Field(default="INFO")

    # --- Database ---
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/datapim"
    )
    postgres_user: str = "postgres"
    postgres_password: str = "postgres"
    postgres_db: str = "datapim"

    # --- Dev account (for seed) ---
    dev_email: str = "admin@example.com"
    dev_password: str = "changeme"
    dev_name: str = "Admin"

    # --- App ---
    port: int = 8000
    cors_origins: str = "http://localhost:5174"

    # --- JWT ---
    jwt_secret: str = ""
    jwt_access_expires_minutes: int = 1440  # 24h
    jwt_refresh_expires_days: int = 7

    # --- Storage ---
    upload_dir: str = "./uploads"
    inbox_dir: str = "./inbox"

    # --- XML import / export ---
    xml_import_dir: Path = Field(
        default=Path("/home/ironhelmet/projects/business/datapim/inbox/xml")
    )
    api_url: str = Field(default="http://localhost:8000")

    # --- AI providers (optional) ---
    anthropic_api_key: str = ""
    openai_api_key: str = ""

    @field_validator("database_url", mode="before")
    @classmethod
    def _coerce_async_driver(cls, v: str) -> str:
        """Ensure asyncpg driver prefix."""
        if not v:
            return v
        if v.startswith("postgresql://"):
            return v.replace("postgresql://", "postgresql+asyncpg://", 1)
        return v

    @field_validator("jwt_secret", mode="after")
    @classmethod
    def _ensure_jwt_secret(cls, v: str) -> str:
        if not v:
            generated = secrets.token_urlsafe(48)
            warnings.warn(
                "JWT_SECRET was empty; generated an ephemeral value. "
                "Set JWT_SECRET in .env for stable tokens across restarts.",
                stacklevel=2,
            )
            return generated
        return v

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def upload_path(self) -> Path:
        p = Path(self.upload_dir)
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def inbox_path(self) -> Path:
        p = Path(self.inbox_dir)
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def sync_database_url(self) -> str:
        """Alembic autogenerate can run with async driver, but this helper is kept handy."""
        return self.database_url.replace("postgresql+asyncpg://", "postgresql://", 1)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
