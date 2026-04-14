"""Pagination helpers."""

from __future__ import annotations

import math

from app.schemas.common import PaginationMeta


def offset_limit(page: int, per_page: int) -> tuple[int, int]:
    """Return (offset, limit) for page/per_page (1-based pages)."""
    offset = (page - 1) * per_page
    return offset, per_page


def build_meta(total: int, page: int, per_page: int) -> PaginationMeta:
    """Build PaginationMeta. last_page is at least 1 even when total == 0."""
    last_page = max(1, math.ceil(total / per_page)) if per_page > 0 else 1
    return PaginationMeta(total=total, page=page, per_page=per_page, last_page=last_page)
