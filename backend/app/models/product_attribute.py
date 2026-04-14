"""Product attribute model (characteristics)."""

from __future__ import annotations

import enum
import uuid

from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class AttributeSource(str, enum.Enum):
    manual = "manual"
    ai = "ai"


class ProductAttribute(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "product_attributes"

    product_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
    )
    key: Mapped[str] = mapped_column(String(100), nullable=False)
    value: Mapped[str] = mapped_column(String(500), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    source: Mapped[AttributeSource] = mapped_column(
        SAEnum(AttributeSource, name="attribute_source"),
        nullable=False,
        default=AttributeSource.manual,
    )

    __table_args__ = (
        Index("idx_product_attributes_product_id", "product_id"),
        UniqueConstraint("product_id", "key", name="uq_product_attributes_product_key"),
    )
