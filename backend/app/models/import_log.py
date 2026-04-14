"""Import log model."""

from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, String, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDPrimaryKeyMixin


class ImportStatus(str, enum.Enum):
    running = "running"
    completed = "completed"
    failed = "failed"


class ImportLog(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "import_logs"

    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[ImportStatus] = mapped_column(
        SAEnum(ImportStatus, name="import_status"),
        nullable=False,
        default=ImportStatus.running,
    )
    products_created: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    products_updated: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    products_stock_changed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    categories_upserted: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    errors_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_details: Mapped[list | None] = mapped_column(JSONB, nullable=True)

    __table_args__ = (Index("idx_import_logs_started_at", "started_at"),)
