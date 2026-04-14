"""Product model — BUF + custom override pattern."""

from __future__ import annotations

import enum
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Index, Integer, Numeric, String, Text, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.category import Category


class EnrichmentStatus(str, enum.Enum):
    none = "none"
    partial = "partial"
    full = "full"


class Product(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "products"

    internal_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    sku: Mapped[str] = mapped_column(String(100), nullable=False)

    # Category override pattern (R-017): BUF column is owned by the XML import,
    # custom column is user-controlled. Resolved value = custom ?? buf.
    buf_category_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("categories.id", ondelete="SET NULL"),
        nullable=True,
    )
    custom_category_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("categories.id", ondelete="SET NULL"),
        nullable=True,
    )

    buf_category: Mapped[Category | None] = relationship(
        "Category",
        foreign_keys=[buf_category_id],
        lazy="selectin",
    )
    custom_category: Mapped[Category | None] = relationship(
        "Category",
        foreign_keys=[custom_category_id],
        lazy="selectin",
    )

    buf_name: Mapped[str] = mapped_column(String(500), nullable=False)
    custom_name: Mapped[str | None] = mapped_column(String(500), nullable=True)

    buf_brand: Mapped[str | None] = mapped_column(String(255), nullable=True)
    custom_brand: Mapped[str | None] = mapped_column(String(255), nullable=True)

    buf_country: Mapped[str | None] = mapped_column(String(100), nullable=True)
    custom_country: Mapped[str | None] = mapped_column(String(100), nullable=True)

    buf_price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    buf_currency: Mapped[str] = mapped_column(String(3), nullable=False, default="UAH")
    buf_quantity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    buf_in_stock: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    uktzed: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    seo_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    seo_description: Mapped[str | None] = mapped_column(Text, nullable=True)

    has_pending_review: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    enrichment_status: Mapped[EnrichmentStatus] = mapped_column(
        SAEnum(EnrichmentStatus, name="enrichment_status"),
        nullable=False,
        default=EnrichmentStatus.none,
    )

    __table_args__ = (
        Index("idx_products_internal_code", "internal_code", unique=True),
        Index("idx_products_buf_category_id", "buf_category_id"),
        Index("idx_products_custom_category_id", "custom_category_id"),
        Index("idx_products_buf_in_stock", "buf_in_stock"),
        Index("idx_products_is_active", "is_active"),
        Index("idx_products_enrichment_status", "enrichment_status"),
        Index("idx_products_has_pending_review", "has_pending_review"),
    )

    # --- Resolved accessors -------------------------------------------------

    @hybrid_property
    def category_id(self) -> uuid.UUID | None:
        """Resolved category_id: custom override wins, falls back to BUF.

        Usable both in Python (`product.category_id`) and in SQL expressions
        (`Product.category_id.in_(...)` → COALESCE(custom, buf)).
        """
        return self.custom_category_id or self.buf_category_id

    @category_id.expression  # type: ignore[no-redef]
    def category_id(cls):  # noqa: N805
        return func.coalesce(cls.custom_category_id, cls.buf_category_id)

    @property
    def category(self) -> Category | None:
        """Resolved Category ORM instance (custom ?? buf)."""
        return self.custom_category or self.buf_category
