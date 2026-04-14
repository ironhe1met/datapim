"""AI task model (v1.2+, included now per R-018)."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, Numeric, String, Text, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDPrimaryKeyMixin


class AITaskType(str, enum.Enum):
    text = "text"
    image = "image"


class AITaskStatus(str, enum.Enum):
    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class AITask(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "ai_tasks"

    product_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    type: Mapped[AITaskType] = mapped_column(
        SAEnum(AITaskType, name="ai_task_type"),
        nullable=False,
    )
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[AITaskStatus] = mapped_column(
        SAEnum(AITaskStatus, name="ai_task_status"),
        nullable=False,
        default=AITaskStatus.pending,
    )
    input_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    output_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    cost_usd: Mapped[float | None] = mapped_column(Numeric(8, 4), nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("idx_ai_tasks_product_id", "product_id"),
        Index("idx_ai_tasks_user_id", "user_id"),
        Index("idx_ai_tasks_status", "status"),
        Index("idx_ai_tasks_type", "type"),
        Index("idx_ai_tasks_created_at", "created_at"),
    )
