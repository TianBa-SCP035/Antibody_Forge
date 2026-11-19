import logging

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, UploadFile
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from db.session import get_db
from modules.auth.external import require_order_sync_caller
from modules.order_sync import service, titer_import
from modules.order_sync.service import OrderSyncError
from modules.system.audit_context import AuditAction
from modules.system.audit_routes import audit

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post(
    "/sync",
    dependencies=[
        Depends(require_order_sync_caller),
        audit(AuditAction("order.experiment.sync", "回传工单数据", "update", "order_sync")),
    ],
)
def sync_order_experiment(
    background_tasks: BackgroundTasks,
    trace_id: str = Form(""),
    order_json: UploadFile | None = File(None),
    db: Session = Depends(get_db),
) -> JSONResponse:
    normalized_trace_id = (trace_id or "").strip()
    try:
        reply = service.receive_sync(db, trace_id, order_json)
    except OrderSyncError as exc:
        return JSONResponse(status_code=exc.code, content=service.device_body(exc.code, exc.message, normalized_trace_id))
    except Exception:
        logger.exception("order sync failed: trace_id=%s", normalized_trace_id)
        return JSONResponse(status_code=500, content=service.device_body(500, "服务端异常", normalized_trace_id))
    if reply.plans and reply.sync_id is not None:
        background_tasks.add_task(titer_import.run_import, reply.sync_id, reply.plans)
    return JSONResponse(status_code=reply.http_status, content=reply.body)
