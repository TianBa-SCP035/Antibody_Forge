from collections.abc import Callable
import logging
from typing import Any

from fastapi import APIRouter, Body, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from core.response import error, success
from db.session import get_db
from models.system import SysUser
from modules.auth.dependencies import get_current_user
from modules.mega_automation import callback, service
from modules.system.permissions import require_permission

router = APIRouter()
logger = logging.getLogger(__name__)


def labillion_callback_success(data: dict[str, Any] | None = None) -> JSONResponse:
    return JSONResponse(status_code=200, content={"success": True, "data": data or {}})


def _run(db: Session, operation: Callable[[], Any]) -> dict:
    try:
        return success(operation())
    except ValueError as exc:
        db.rollback()
        return error(str(exc))
    except Exception:
        db.rollback()
        logger.exception("mega automation request failed")
        return error("服务端异常，请稍后重试")


@router.post("/labillion/callback")
def labillion_status_callback(
    data: dict | None = Body(default=None),
    db: Session = Depends(get_db),
) -> JSONResponse:
    """Labillion 订单状态推送；无需登录，响应须在 5 秒内返回 2xx。"""
    try:
        result = callback.handle_labillion_status_push(db, data or {})
        return labillion_callback_success(result)
    except Exception:
        db.rollback()
        logger.exception("labillion callback failed body=%s", data)
        return labillion_callback_success({"applied": False, "reason": "internal_error"})


@router.get("/flow-work-orders/meta")
def flow_work_order_meta(
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
) -> dict:
    require_permission(db, current_user, "mega.page.flow_work_order")
    return _run(db, service.get_meta)


@router.post("/flow-work-orders/by-source")
def flow_work_orders_by_source(
    data: dict,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
) -> dict:
    require_permission(db, current_user, "mega.page.flow_work_order")
    return _run(db, lambda: service.get_work_orders_by_source(db, data or {}))


@router.post("/flow-work-orders/list")
def flow_work_order_list(
    data: dict,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
) -> dict:
    require_permission(db, current_user, "mega.page.flow_work_order")
    return _run(db, lambda: service.get_work_order_list(db, data or {}))


@router.get("/flow-work-orders/{order_id}")
def flow_work_order_detail(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
) -> dict:
    require_permission(db, current_user, "mega.page.flow_work_order")
    return _run(db, lambda: service.get_work_order_detail(db, order_id))


@router.post("/flow-work-orders/{order_id}/sync-labillion-status")
def flow_work_order_sync_labillion_status(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
) -> dict:
    require_permission(db, current_user, "mega.page.flow_work_order")
    return _run(db, lambda: service.sync_work_order_labillion_status(db, order_id))


@router.get("/flow-work-orders/{order_id}/active-payload")
def flow_work_order_active_payload(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
) -> dict:
    require_permission(db, current_user, "mega.page.flow_work_order")
    return _run(db, lambda: service.get_active_dispatch_payload(db, order_id))


@router.post("/flow-work-orders/save")
def flow_work_order_save(
    data: dict,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
) -> dict:
    require_permission(db, current_user, "mega.flow_work_order.edit")
    return _run(db, lambda: service.save_work_order(db, data or {}, current_user))


@router.post("/flow-work-orders/{order_id}/validate")
def flow_work_order_validate(
    order_id: int,
    data: dict | None = Body(default=None),
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
) -> dict:
    require_permission(db, current_user, "mega.flow_work_order.edit")
    return _run(db, lambda: service.validate_work_order(db, order_id, data))


@router.post("/flow-work-orders/{order_id}/dispatch")
def flow_work_order_dispatch(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
) -> dict:
    require_permission(db, current_user, "mega.flow_work_order.dispatch")
    return _run(db, lambda: service.dispatch_work_order(db, order_id, current_user))


@router.post("/flow-work-orders/{order_id}/pause")
def flow_work_order_pause(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
) -> dict:
    require_permission(db, current_user, "mega.flow_work_order.dispatch")
    return _run(db, lambda: service.pause_work_order(db, order_id))


@router.post("/flow-work-orders/{order_id}/resume")
def flow_work_order_resume(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
) -> dict:
    require_permission(db, current_user, "mega.flow_work_order.dispatch")
    return _run(db, lambda: service.resume_work_order(db, order_id))


@router.post("/flow-work-orders/{order_id}/pause-ack")
def flow_work_order_pause_ack(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
) -> dict:
    require_permission(db, current_user, "mega.flow_work_order.dispatch")
    return _run(db, lambda: service.acknowledge_pause_work_order(db, order_id))


@router.post("/flow-work-orders/{order_id}/resume-ack")
def flow_work_order_resume_ack(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
) -> dict:
    require_permission(db, current_user, "mega.flow_work_order.dispatch")
    return _run(db, lambda: service.acknowledge_resume_work_order(db, order_id))


@router.post("/flow-work-orders/{order_id}/confirm-execution")
def flow_work_order_confirm_execution(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
) -> dict:
    require_permission(db, current_user, "mega.flow_work_order.dispatch")
    return _run(db, lambda: service.confirm_dispatch_execution(db, order_id))


@router.post("/flow-work-orders/{order_id}/complete")
def flow_work_order_complete(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
) -> dict:
    require_permission(db, current_user, "mega.flow_work_order.dispatch")
    return _run(db, lambda: service.complete_work_order(db, order_id))


@router.post("/flow-work-orders/{order_id}/fail")
def flow_work_order_fail(
    order_id: int,
    data: dict | None = Body(default=None),
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
) -> dict:
    require_permission(db, current_user, "mega.flow_work_order.dispatch")
    return _run(
        db,
        lambda: service.fail_work_order(
            db,
            order_id,
            str((data or {}).get("error_message") or ""),
        ),
    )


@router.post("/flow-work-orders/{order_id}/delete")
def flow_work_order_delete(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
) -> dict:
    require_permission(db, current_user, "mega.flow_work_order.edit")
    return _run(db, lambda: service.delete_work_order(db, order_id))


@router.post("/flow-work-orders/{order_id}/cancel")
def flow_work_order_cancel(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
) -> dict:
    require_permission(db, current_user, "mega.flow_work_order.edit")
    return _run(db, lambda: service.cancel_work_order(db, order_id))
