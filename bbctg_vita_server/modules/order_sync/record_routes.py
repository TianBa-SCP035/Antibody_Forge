"""镁伽结果回传记录：列表、详情、原文下载、重新处理，以及按流式工单查回传检测板。"""

from urllib.parse import quote

from fastapi import APIRouter, BackgroundTasks, Depends
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from core.response import success
from db.session import get_db
from modules.auth.permissions import require
from modules.order_sync import service, titer_import

router = APIRouter()

RECORD_READ = require("mega.page.flow_work_order")


@router.post("/list", dependencies=[RECORD_READ])
def order_sync_list(
    data: dict,
    db: Session = Depends(get_db),
) -> dict:
    return success(service.get_sync_list(db, data or {}))


@router.get("/boards", dependencies=[RECORD_READ])
def order_sync_work_order_boards(
    work_order_id: int,
    db: Session = Depends(get_db),
) -> dict:
    return success({"items": service.get_work_order_boards(db, work_order_id)})


@router.get("/{sync_id}", dependencies=[RECORD_READ])
def order_sync_detail(
    sync_id: int,
    db: Session = Depends(get_db),
) -> dict:
    return success(service.get_sync_detail(db, sync_id))


@router.get("/{sync_id}/raw", dependencies=[RECORD_READ])
def order_sync_raw(
    sync_id: int,
    db: Session = Depends(get_db),
) -> FileResponse:
    path, filename = service.get_raw_file(db, sync_id)
    return FileResponse(
        path,
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"},
    )


@router.post(
    "/{sync_id}/reprocess",
    dependencies=[require("mega.flow_work_order.edit", audit="重新处理镁伽回传")],
)
def order_sync_reprocess(
    sync_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> dict:
    detail, plans = service.reprocess_sync(db, sync_id)
    if plans:
        background_tasks.add_task(titer_import.run_import, sync_id, plans)
    return success(detail)
