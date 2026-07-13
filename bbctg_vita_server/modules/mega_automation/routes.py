from collections.abc import Callable
import logging
from typing import Any

from fastapi import APIRouter, Body, Depends
from sqlalchemy.orm import Session

from core.response import error, success
from db.session import get_db
from models.system import SysUser
from modules.auth.dependencies import get_current_user
from modules.mega_automation import service
from modules.system.permissions import require_permission

router = APIRouter()
logger = logging.getLogger(__name__)


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


@router.get("/flow-work-orders/meta")
def flow_work_order_meta(
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
) -> dict:
    require_permission(db, current_user, "mega.page.flow_work_order")
    return _run(db, service.get_meta)


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
