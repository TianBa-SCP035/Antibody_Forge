import logging
from typing import Any

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from db.session import get_db
from modules.order_sync import service
from modules.order_sync.service import OrderSyncError

router = APIRouter()
logger = logging.getLogger(__name__)


def device_success(trace_id: str, data: dict[str, Any]) -> JSONResponse:
    return JSONResponse(
        status_code=200,
        content={"code": 0, "message": "success", "trace_id": trace_id, "data": data},
    )


def device_error(code: int, message: str, trace_id: str) -> JSONResponse:
    return JSONResponse(
        status_code=code if code >= 400 else 400,
        content={"code": code, "message": message, "trace_id": trace_id, "data": None},
    )


@router.post("/sync")
def sync_order_experiment(
    trace_id: str = Form(...),
    order_json: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> JSONResponse:
    normalized_trace_id = (trace_id or "").strip()
    try:
        data = service.receive_sync(db, trace_id, order_json)
        return device_success(normalized_trace_id, data)
    except OrderSyncError as exc:
        return device_error(exc.code, exc.message, normalized_trace_id)
    except Exception:
        logger.exception("order sync failed: trace_id=%s", normalized_trace_id)
        return device_error(500, "服务端异常", normalized_trace_id)
