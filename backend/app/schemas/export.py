"""Export-related Pydantic schemas (Phase 7)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class ExportSettingsResponse(BaseModel):
    products_url: str
    categories_url: str
    last_generated: datetime | None = None
    products_count: int
    categories_count: int
