"""Dashboard stats endpoint (Phase 8a).

Scope (R-020): read-only aggregate stats for any authenticated role
(admin, operator, manager, viewer). No filtering / no time range for v1.0
— the dashboard simply mirrors the current database state.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.dashboard import DashboardStatsResponse
from app.services import dashboard_service

router = APIRouter()


@router.get("/stats", response_model=DashboardStatsResponse)
async def get_dashboard_stats(
    session: AsyncSession = Depends(get_session),
    _user: User = Depends(get_current_user),
) -> DashboardStatsResponse:
    return await dashboard_service.get_stats(session)
