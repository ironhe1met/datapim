"""Product-related Pydantic schemas (Products CRUD, Phase 5).

Display rule (R-017): resolved fields use `custom ?? buf`.
Only `custom_*` fields + description/seo_* are editable via PATCH for v1.0 (R-020).
`buf_*` fields are read-only — modified exclusively by XML import.
"""

from __future__ import annotations

import enum
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_serializer

from app.schemas.common import PaginationMeta


class EnrichmentStatus(str, enum.Enum):
    none = "none"
    partial = "partial"
    full = "full"


# --- Nested refs ------------------------------------------------------------


class CategoryRef(BaseModel):
    """Lightweight category reference used inside product list items."""

    id: UUID
    name: str


class BreadcrumbItem(BaseModel):
    id: UUID
    name: str


class CategoryInfo(BaseModel):
    """Product-detail category block with full breadcrumb."""

    id: UUID
    name: str
    breadcrumb: list[BreadcrumbItem] = Field(default_factory=list)


class PrimaryImageRef(BaseModel):
    id: UUID
    file_path: str


class ProductImageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    file_path: str
    file_name: str
    is_primary: bool
    source: str
    sort_order: int


class ProductAttributeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    key: str
    value: str
    source: str
    sort_order: int


# --- List / Detail ----------------------------------------------------------


class ProductListItem(BaseModel):
    id: UUID
    internal_code: str
    sku: str
    name: str  # resolved: custom_name ?? buf_name
    brand: str | None  # resolved
    price: Decimal
    currency: str
    quantity: int | None
    in_stock: bool
    category: CategoryRef | None = None
    primary_image: PrimaryImageRef | None = None
    enrichment_status: EnrichmentStatus
    has_pending_review: bool

    @field_serializer("price")
    def _ser_price(self, v: Decimal) -> float:
        return float(v)


class ProductDetail(BaseModel):
    id: UUID
    internal_code: str
    sku: str

    buf_name: str
    custom_name: str | None
    name: str  # resolved

    buf_brand: str | None
    custom_brand: str | None
    brand: str | None  # resolved

    buf_country: str | None
    custom_country: str | None
    country: str | None  # resolved

    buf_price: Decimal
    buf_currency: str
    buf_quantity: int | None
    buf_in_stock: bool

    uktzed: str | None
    is_active: bool

    description: str | None
    seo_title: str | None
    seo_description: str | None

    enrichment_status: EnrichmentStatus
    has_pending_review: bool

    category: CategoryInfo | None = None
    buf_category: CategoryRef | None = None
    images: list[ProductImageRead] = Field(default_factory=list)
    attributes: list[ProductAttributeRead] = Field(default_factory=list)

    created_at: datetime
    updated_at: datetime

    @field_serializer("buf_price")
    def _ser_buf_price(self, v: Decimal) -> float:
        return float(v)


# --- Write schemas ----------------------------------------------------------


class ProductUpdate(BaseModel):
    """All fields optional. `custom_category_id` may be explicitly None → clear.

    Distinguishing "unset" vs "set to None" is done via `model_fields_set`.
    """

    custom_name: str | None = Field(default=None, max_length=500)
    custom_brand: str | None = Field(default=None, max_length=255)
    custom_country: str | None = Field(default=None, max_length=100)
    custom_category_id: UUID | None = None
    description: str | None = None
    seo_title: str | None = Field(default=None, max_length=255)
    seo_description: str | None = None


RESETTABLE_FIELDS: frozenset[str] = frozenset(
    {
        "custom_name",
        "custom_brand",
        "custom_country",
        "custom_category_id",
        "description",
        "seo_title",
        "seo_description",
    }
)


class ResetFieldRequest(BaseModel):
    field: str


# --- List response ----------------------------------------------------------


class ProductListResponse(BaseModel):
    data: list[ProductListItem]
    meta: PaginationMeta
