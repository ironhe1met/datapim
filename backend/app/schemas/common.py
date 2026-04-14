"""Common/shared Pydantic schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class PaginationMeta(BaseModel):
    total: int = Field(ge=0)
    page: int = Field(ge=1)
    per_page: int = Field(ge=1)
    last_page: int = Field(ge=1)
