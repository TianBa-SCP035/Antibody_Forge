from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from models.mega_automation import MegaFlowWorkOrder, MegaFlowWorkOrderDispatch

from modules.mega_automation.content import clean_text
from modules.mega_automation.dispatch import TERMINAL_DISPATCH_STATUSES

logger = logging.getLogger(__name__)

LABILLION_STATUS_ALIASES: dict[str, str] = {
    "pending": "pending",
    "running": "running",
    "paused": "paused",
    "finished": "finished",
    "aborted": "aborted",
}

ORDER_TERMINAL_STATUSES = frozenset({"completed", "execution_failed", "cancelled"})
PRE_DISPATCH_ORDER_STATUSES = frozenset({"draft", "validated", "failed"})


def normalize_labillion_status(value: Any) -> str:
    return LABILLION_STATUS_ALIASES.get(clean_text(value).lower(), "")


def apply_labillion_status(
    order: MegaFlowWorkOrder,
    dispatch: MegaFlowWorkOrderDispatch,
    labillion_status: str,
) -> bool:
    if labillion_status == "pending":
        return _apply_pending(order, dispatch)
    if labillion_status == "running":
        return _apply_running(order, dispatch)
    if labillion_status == "paused":
        return _apply_paused(order, dispatch)
    if labillion_status == "finished":
        return _apply_finished(order, dispatch)
    if labillion_status == "aborted":
        return _apply_aborted(order, dispatch)
    return False


def handle_labillion_status_push(db: Session, data: dict[str, Any]) -> dict[str, Any]:
    """接收 Labillion 状态推送，按 dispatchId 更新工单与下发记录。"""
    dispatch_id = clean_text(data.get("dispatchId"))
    run_id = clean_text(data.get("runId"))
    labillion_status = normalize_labillion_status(data.get("status"))

    if not dispatch_id:
        logger.warning("labillion callback ignored: missing dispatchId body=%s", data)
        return {"applied": False, "reason": "missing_dispatch_id"}

    if not labillion_status:
        logger.warning(
            "labillion callback ignored: unknown status=%s dispatchId=%s",
            data.get("status"),
            dispatch_id,
        )
        return {"applied": False, "reason": "unknown_status", "dispatchId": dispatch_id}

    dispatch = db.scalar(
        select(MegaFlowWorkOrderDispatch)
        .where(MegaFlowWorkOrderDispatch.dispatchId == dispatch_id)
        .with_for_update()
    )
    if not dispatch:
        logger.warning("labillion callback ignored: dispatch not found dispatchId=%s", dispatch_id)
        return {"applied": False, "reason": "dispatch_not_found", "dispatchId": dispatch_id}

    order = db.scalar(
        select(MegaFlowWorkOrder)
        .where(MegaFlowWorkOrder.id == dispatch.work_order_id)
        .with_for_update()
    )
    if not order:
        logger.warning(
            "labillion callback ignored: work order missing dispatchId=%s work_order_id=%s",
            dispatch_id,
            dispatch.work_order_id,
        )
        return {"applied": False, "reason": "work_order_not_found", "dispatchId": dispatch_id}

    if order.status in ORDER_TERMINAL_STATUSES:
        logger.info(
            "labillion callback skipped: order already terminal status=%s dispatchId=%s",
            order.status,
            dispatch_id,
        )
        return {
            "applied": False,
            "reason": "order_terminal",
            "dispatchId": dispatch_id,
            "order_status": order.status,
        }

    if order.status in PRE_DISPATCH_ORDER_STATUSES:
        logger.warning(
            "labillion callback skipped: order not dispatched status=%s dispatchId=%s",
            order.status,
            dispatch_id,
        )
        return {
            "applied": False,
            "reason": "order_not_dispatched",
            "dispatchId": dispatch_id,
            "order_status": order.status,
        }

    if dispatch.status in TERMINAL_DISPATCH_STATUSES:
        logger.info(
            "labillion callback skipped: dispatch already terminal status=%s dispatchId=%s",
            dispatch.status,
            dispatch_id,
        )
        return {
            "applied": False,
            "reason": "dispatch_terminal",
            "dispatchId": dispatch_id,
            "dispatch_status": dispatch.status,
        }

    changed = apply_labillion_status(order, dispatch, labillion_status)
    if changed:
        db.commit()
        logger.info(
            "labillion callback applied: dispatchId=%s runId=%s labillion=%s order=%s dispatch=%s pause=%s",
            dispatch_id,
            run_id or "-",
            labillion_status,
            order.status,
            dispatch.status,
            dispatch.pause_state or "",
        )
    else:
        db.rollback()
        logger.info(
            "labillion callback noop: dispatchId=%s labillion=%s",
            dispatch_id,
            labillion_status,
        )

    return {
        "applied": changed,
        "dispatchId": dispatch_id,
        "labillion_status": labillion_status,
        "order_status": order.status,
        "dispatch_status": dispatch.status,
        "pause_state": dispatch.pause_state or "",
    }


def _apply_pending(
    order: MegaFlowWorkOrder,
    dispatch: MegaFlowWorkOrderDispatch,
) -> bool:
    if (
        order.status == "sent"
        and dispatch.status == "pending"
        and not dispatch.pause_state
    ):
        return False

    order.status = "sent"
    order.error_message = None
    dispatch.status = "pending"
    dispatch.pause_state = None
    return True


def _apply_running(
    order: MegaFlowWorkOrder,
    dispatch: MegaFlowWorkOrderDispatch,
) -> bool:
    if (
        order.status == "running"
        and dispatch.status == "running"
        and not dispatch.pause_state
    ):
        return False

    order.status = "running"
    order.error_message = None
    dispatch.status = "running"
    dispatch.pause_state = None
    return True


def _apply_paused(
    order: MegaFlowWorkOrder,
    dispatch: MegaFlowWorkOrderDispatch,
) -> bool:
    if order.status == "paused" and dispatch.pause_state == "paused":
        return False

    order.status = "paused"
    order.error_message = None
    if dispatch.status == "pending":
        dispatch.status = "running"
    dispatch.pause_state = "paused"
    return True


def _apply_finished(
    order: MegaFlowWorkOrder,
    dispatch: MegaFlowWorkOrderDispatch,
) -> bool:
    if order.status == "completed" and dispatch.status == "completed":
        return False

    order.status = "completed"
    order.error_message = None
    dispatch.status = "completed"
    dispatch.pause_state = None
    return True


def _apply_aborted(
    order: MegaFlowWorkOrder,
    dispatch: MegaFlowWorkOrderDispatch,
) -> bool:
    if order.status == "execution_failed" and dispatch.status == "failed":
        return False

    order.status = "execution_failed"
    if not order.error_message:
        order.error_message = "设备执行中止"
    dispatch.status = "failed"
    dispatch.pause_state = None
    return True
