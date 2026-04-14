"""AI review model (v1.2+, included now per R-018)."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDPrimaryKeyMixin


class AIReviewStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    partial = "partial"


class AIReview(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "ai_reviews"

    ai_task_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("ai_tasks.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    status: Mapped[AIReviewStatus] = mapped_column(
        SAEnum(AIReviewStatus, name="ai_review_status"),
        nullable=False,
        default=AIReviewStatus.pending,
    )
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    changes_applied: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("idx_ai_reviews_ai_task_id", "ai_task_id", unique=True),
        Index("idx_ai_reviews_status", "status"),
        Index("idx_ai_reviews_reviewed_by", "reviewed_by"),
    )
