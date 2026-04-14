"""XML export HTTP router (Phase 7).

Public endpoints at `/export/*`, admin-only settings at `/api/export/*`.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.dependencies.auth import require_role
from app.models.user import User
from app.schemas.export import ExportSettingsResponse
from app.services import export_service

router = APIRouter()


@router.get("/export/products.xml", include_in_schema=True)
async def export_products_xml(
    db: AsyncSession = Depends(get_session),
) -> Response:
    xml = await export_service.generate_products_xml(db)
    return Response(content=xml, media_type="application/xml")


@router.get("/export/categories.xml", include_in_schema=True)
async def export_categories_xml(
    db: AsyncSession = Depends(get_session),
) -> Response:
    xml = await export_service.generate_categories_xml(db)
    return Response(content=xml, media_type="application/xml")


@router.get("/api/export/settings", response_model=ExportSettingsResponse)
async def export_settings(
    db: AsyncSession = Depends(get_session),
    _user: User = Depends(require_role("admin", "manager")),
) -> ExportSettingsResponse:
    payload = await export_service.export_settings(db)
    return ExportSettingsResponse(**payload)
