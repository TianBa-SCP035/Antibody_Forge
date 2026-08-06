from __future__ import annotations

import logging
import time
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from integrations.labillion import LabillionError, is_labillion_enabled, query_order_statuses
from models.mega_automation import MegaFlowWorkOrder, MegaFlowWorkOrderDispatch

from modules.mega_automation.content import clean_text
from modules.mega_automation.callback import (
    ORDER_TERMINAL_STATUSES,
    PRE_DISPATCH_ORDER_STATUSES,
    apply_labillion_status,
    normalize_labillion_status,
)
from modules.mega_automation.dispatch import TERMINAL_DISPATCH_STATUSES

logger = logging.getLogger(__name__)

SYNCABLE_ORDER_STATUSES = frozenset({"sent", "running", "paused"})
SYNC_THROTTLE_SECONDS = 600
_QUERY_BATCH_SIZE = 50

_last_sync_at: dict[int, float] = {}


def _is_throttled(work_order_id: int) -> bool:
    last_at = _last_sync_at.get(int(work_order_id))
    if not last_at:
        return False
    return (time.time() - last_at) < SYNC_THROTTLE_SECONDS


def _mark_synced(work_order_id: int) -> None:
    _last_sync_at[int(work_order_id)] = time.time()


def _get_syncable_dispatch(
    db: Session,
    order_id: int,
    *,
    for_update: bool = False,
) -> MegaFlowWorkOrderDispatch | None:
    stmt = (
        select(MegaFlowWorkOrderDispatch)
        .where(
            MegaFlowWorkOrderDispatch.work_order_id == int(order_id),
            MegaFlowWorkOrderDispatch.status.notin_(TERMINAL_DISPATCH_STATUSES),
        )
        .order_by(MegaFlowWorkOrderDispatch.id.desc())
    )
    if for_update:
        stmt = stmt.with_for_update()
    return db.scalar(stmt)


def _extract_running_progress(entry: dict[str, Any], labillion_status: str) -> str:
    if labillion_status != "running":
        return ""
    value = entry.get("progress")
    if value is None:
        return ""
    text = clean_text(value).rstrip("%")
    return text or ""


def _apply_query_entry(
    order: MegaFlowWorkOrder,
    dispatch: MegaFlowWorkOrderDispatch,
    entry: dict[str, Any],
) -> bool:
    labillion_status = normalize_labillion_status(entry.get("status"))
    if not labillion_status:
        return False

    if order.status in ORDER_TERMINAL_STATUSES:
        return False
    if order.status in PRE_DISPATCH_ORDER_STATUSES:
        return False
    if dispatch.status in TERMINAL_DISPATCH_STATUSES:
        return False

    return apply_labillion_status(order, dispatch, labillion_status)


def sync_work_order_labillion_status(
    db: Session,
    order_id: int,
    *,
    force: bool = False,
) -> dict[str, Any]:
    from modules.mega_automation.service import get_work_order_detail

    if not is_labillion_enabled():
        return {"applied": False, "reason": "labillion_disabled"}

    order = db.scalar(
        select(MegaFlowWorkOrder).where(MegaFlowWorkOrder.id == int(order_id)).with_for_update()
    )
    if not order:
        raise ValueError("流式工单不存在")

    if order.status not in SYNCABLE_ORDER_STATUSES:
        return {
            "applied": False,
            "reason": "order_not_syncable",
            "order_status": order.status,
            "item": get_work_order_detail(db, order.id),
        }

    if not force and _is_throttled(order.id):
        return {
            "applied": False,
            "reason": "throttled",
            "item": get_work_order_detail(db, order.id),
        }

    dispatch = _get_syncable_dispatch(db, order.id, for_update=True)
    if not dispatch:
        return {
            "applied": False,
            "reason": "dispatch_not_found",
            "item": get_work_order_detail(db, order.id),
        }

    try:
        statuses = query_order_statuses([dispatch.dispatchId])
    except LabillionError as exc:
        logger.warning(
            "labillion query failed: order_id=%s dispatchId=%s error=%s",
            order.id,
            dispatch.dispatchId,
            exc,
        )
        return {
            "applied": False,
            "reason": "labillion_error",
            "message": str(exc),
            "item": get_work_order_detail(db, order.id),
        }

    entry = statuses.get(dispatch.dispatchId)
    if not entry:
        logger.info(
            "labillion query empty: order_id=%s dispatchId=%s",
            order.id,
            dispatch.dispatchId,
        )
        _mark_synced(order.id)
        return {
            "applied": False,
            "reason": "not_found_in_labillion",
            "item": get_work_order_detail(db, order.id),
        }

    changed = _apply_query_entry(order, dispatch, entry)
    labillion_status = normalize_labillion_status(entry.get("status"))
    execution_progress = _extract_running_progress(entry, labillion_status)
    if changed:
        db.commit()
        logger.info(
            "labillion query applied: order_id=%s dispatchId=%s status=%s progress=%s",
            order.id,
            dispatch.dispatchId,
            labillion_status,
            execution_progress or "",
        )
    else:
        db.rollback()

    _mark_synced(order.id)
    return {
        "applied": changed,
        "dispatchId": dispatch.dispatchId,
        "labillion_status": labillion_status,
        "execution_progress": execution_progress,
        "item": get_work_order_detail(db, order.id),
    }


def sync_non_terminal_work_orders(db: Session) -> dict[str, Any]:
    if not is_labillion_enabled():
        logger.info("labillion status sync job skipped: LABILLION_BASE_URL not configured")
        return {"skipped": True, "reason": "labillion_disabled"}

    rows = db.execute(
        select(
            MegaFlowWorkOrder.id,
            MegaFlowWorkOrderDispatch.dispatchId,
        )
        .join(
            MegaFlowWorkOrderDispatch,
            MegaFlowWorkOrderDispatch.work_order_id == MegaFlowWorkOrder.id,
        )
        .where(
            MegaFlowWorkOrder.status.in_(tuple(SYNCABLE_ORDER_STATUSES)),
            MegaFlowWorkOrderDispatch.status.notin_(tuple(TERMINAL_DISPATCH_STATUSES)),
        )
        .order_by(MegaFlowWorkOrder.id.desc(), MegaFlowWorkOrderDispatch.id.desc())
    ).all()

    order_to_dispatch: dict[int, str] = {}
    for order_id, dispatch_id in rows:
        key = int(order_id)
        if key not in order_to_dispatch:
            order_to_dispatch[key] = str(dispatch_id)

    if not order_to_dispatch:
        return {"skipped": False, "total": 0, "applied": 0}

    dispatch_to_order = {dispatch_id: order_id for order_id, dispatch_id in order_to_dispatch.items()}
    dispatch_ids = list(dispatch_to_order.keys())
    applied = 0
    not_found = 0
    failed = 0

    for offset in range(0, len(dispatch_ids), _QUERY_BATCH_SIZE):
        batch_ids = dispatch_ids[offset : offset + _QUERY_BATCH_SIZE]
        try:
            statuses = query_order_statuses(batch_ids)
        except LabillionError:
            logger.exception("labillion batch query failed: dispatchIds=%s", batch_ids)
            failed += len(batch_ids)
            continue

        for dispatch_id in batch_ids:
            order_id = dispatch_to_order[dispatch_id]
            entry = statuses.get(dispatch_id)
            if not entry:
                not_found += 1
                continue
            order = db.scalar(
                select(MegaFlowWorkOrder).where(MegaFlowWorkOrder.id == order_id).with_for_update()
            )
            dispatch = _get_syncable_dispatch(db, order_id, for_update=True)
            if not order or not dispatch or dispatch.dispatchId != dispatch_id:
                failed += 1
                continue
            try:
                changed = _apply_query_entry(order, dispatch, entry)
                if changed:
                    db.commit()
                    applied += 1
                else:
                    db.rollback()
            except Exception:
                db.rollback()
                logger.exception("labillion status sync failed: order_id=%s", order_id)
                failed += 1

    summary = {
        "skipped": False,
        "total": len(order_to_dispatch),
        "applied": applied,
    }
    if not_found:
        summary["not_found"] = not_found
    if failed:
        summary["failed"] = failed
    return summary
