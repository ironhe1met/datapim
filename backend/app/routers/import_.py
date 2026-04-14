"""XML import HTTP router (Phase 7)."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import SessionLocal, get_session
from app.dependencies.auth import require_role
from app.models.user import User
from app.schemas.import_ import (
    ImportLogListResponse,
    ImportLogRead,
    ImportTriggerResponse,
)
from app.services import import_service
from app.utils.pagination import build_meta

router = APIRouter()


def _import_background_worker() -> None:
    """Wrapper for BackgroundTasks — schedules the async import task.

    FastAPI calls sync background callables in a thread; async ones in the
    loop. We use the sync form so we can grab the current event loop and
    schedule our own task with its own session.
    """
    # Not used — retained as documentation of intent. See trigger() below.


@router.post(
    "/trigger",
    response_model=ImportTriggerResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def trigger(
    background_tasks: BackgroundTasks,
    _user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_session),
) -> ImportTriggerResponse:
    """Create an `ImportLog` row and kick off the import in the background.

    We create the log row eagerly (using the request's session) so the client
    receives the UUID immediately. The actual parsing/upsert runs in a
    background task with its own freshly-created session.
    """
    settings = get_settings()
    xml_dir = settings.xml_import_dir

    from app.models.import_log import ImportLog, ImportStatus

    log_row = ImportLog(file_name=str(xml_dir)[-255:], status=ImportStatus.running)
    db.add(log_row)
    await db.commit()
    await db.refresh(log_row)
    import_id = log_row.id

    async def _runner() -> None:
        try:
            async with SessionLocal() as bg_session:
                await import_service.resume_import(bg_session, import_id, xml_dir)
        except Exception as exc:  # noqa: BLE001
            logger.exception("import_background_failed")
            # Last-ditch: mark the ImportLog as failed so UI doesn't show stale "running".
            from datetime import UTC, datetime

            from app.models.import_log import ImportLog, ImportStatus

            try:
                async with SessionLocal() as rescue_session:
                    row = await rescue_session.get(ImportLog, import_id)
                    if row is not None and row.status == ImportStatus.running:
                        row.status = ImportStatus.failed
                        row.finished_at = datetime.now(UTC)
                        row.errors_count = (row.errors_count or 0) + 1
                        row.error_details = [
                            {"type": "background_task_failed", "message": str(exc)[:500]}
                        ]
                        await rescue_session.commit()
            except Exception:  # noqa: BLE001
                logger.exception("import_background_rescue_also_failed")

    background_tasks.add_task(_runner)

    logger.info("import_triggered", import_id=str(import_id), xml_dir=str(xml_dir))
    return ImportTriggerResponse(import_id=import_id, status="running")


@router.get("/logs", response_model=ImportLogListResponse)
async def list_logs(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_session),
    _user: User = Depends(require_role("admin", "manager")),
) -> ImportLogListResponse:
    rows, total = await import_service.list_logs(db, page=page, per_page=per_page)
    return ImportLogListResponse(
        data=[ImportLogRead.model_validate(r) for r in rows],
        meta=build_meta(total=total, page=page, per_page=per_page),
    )


@router.get("/logs/{log_id}", response_model=ImportLogRead)
async def get_log_detail(
    log_id: UUID,
    db: AsyncSession = Depends(get_session),
    _user: User = Depends(require_role("admin", "manager")),
) -> ImportLogRead:
    row = await import_service.get_log(db, log_id)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "Import log not found", "code": "NOT_FOUND"},
        )
    return ImportLogRead.model_validate(row)
