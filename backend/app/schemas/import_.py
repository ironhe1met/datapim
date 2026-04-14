"""Import-related Pydantic schemas (Phase 7)."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.schemas.common import PaginationMeta


class ImportLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    file_name: str
    started_at: datetime
    finished_at: datetime | None
    status: str
    products_created: int
    products_updated: int
    products_stock_changed: int
    categories_upserted: int
    errors_count: int
    error_details: list[Any] | None = None


class ImportLogListResponse(BaseModel):
    data: list[ImportLogRead]
    meta: PaginationMeta


class ImportTriggerResponse(BaseModel):
    import_id: UUID
    status: str
