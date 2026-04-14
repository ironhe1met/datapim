"""Dashboard-related Pydantic schemas (Phase 8a).

Read-only aggregate stats for the Dashboard page.
`pending_reviews` and `ai_tasks_today` are hardcoded `0` for v1.0
(AI reviews / AI tasks ship in v1.2, per R-020).
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class LastImportInfo(BaseModel):
    """Summary of the most recent import for the dashboard card."""

    id: UUID
    date: datetime
    status: str
    products_created: int
    products_updated: int


class DashboardStatsResponse(BaseModel):
    """Aggregate stats rendered on the dashboard landing page."""

    products_total: int
    products_in_stock: int
    products_enriched: int
    products_no_description: int
    products_with_images: int
    pending_reviews: int
    categories_total: int
    last_import: LastImportInfo | None
    ai_tasks_today: int
