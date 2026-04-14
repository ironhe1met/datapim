"""Product attribute Pydantic schemas."""

from __future__ import annotations

import enum
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AttributeSource(str, enum.Enum):
    manual = "manual"
    ai = "ai"


class AttributeBase(BaseModel):
    key: str = Field(min_length=1, max_length=100)
    value: str = Field(min_length=1, max_length=500)


class AttributeCreate(AttributeBase):
    """User-created attributes always have source='manual' (set in service)."""


class AttributeUpdate(BaseModel):
    key: str | None = Field(default=None, min_length=1, max_length=100)
    value: str | None = Field(default=None, min_length=1, max_length=500)
    sort_order: int | None = None


class AttributeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    key: str
    value: str
    source: AttributeSource
    sort_order: int
    created_at: datetime
    updated_at: datetime


class AttributeListResponse(BaseModel):
    data: list[AttributeRead]
