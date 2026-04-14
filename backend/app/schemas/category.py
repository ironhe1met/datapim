"""Category-related Pydantic schemas (Categories CRUD)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CategoryBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)


class CategoryCreate(CategoryBase):
    parent_id: UUID | None = None
    external_id: str | None = Field(default=None, max_length=50)


class CategoryUpdate(BaseModel):
    """All fields optional; `parent_id` explicitly may be set to None (root).

    Distinguishing "unset" vs "set to None" is done via `model_fields_set`
    in the service layer.
    """

    name: str | None = Field(default=None, min_length=1, max_length=255)
    parent_id: UUID | None = None


class CategoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    external_id: str
    name: str
    parent_id: UUID | None
    is_active: bool
    product_count: int
    created_at: datetime
    updated_at: datetime


class CategoryTreeNode(CategoryRead):
    children: list[CategoryTreeNode] = Field(default_factory=list)


CategoryTreeNode.model_rebuild()


class CategoryChildRef(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    product_count: int


class CategoryBreadcrumbItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str


class CategoryDetail(CategoryRead):
    children: list[CategoryChildRef] = Field(default_factory=list)
    breadcrumb: list[CategoryBreadcrumbItem] = Field(default_factory=list)


class CategoryListResponse(BaseModel):
    data: list[CategoryRead]


class CategoryTreeResponse(BaseModel):
    data: list[CategoryTreeNode]
