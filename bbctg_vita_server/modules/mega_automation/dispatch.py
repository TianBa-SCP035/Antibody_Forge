from __future__ import annotations

from datetime import datetime
import random

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, defer

from models.mega_automation import MegaFlowWorkOrder, MegaFlowWorkOrderDispatch

from modules.mega_automation.content import hash_dict
from modules.mega_automation.payload import build_dispatch_payload

PAUSABLE_STATUSES = frozenset({"pending", "running"})
TERMINAL_DISPATCH_STATUSES = frozenset({"voided", "completed", "failed"})
DISPATCH_ID_PREFIX = "DSP"
DISPATCH_ID_RANDOM_DIGITS = 6
DISPATCH_ID_RETRY_LIMIT = 30
# 列表/状态查询不需要完整下发 JSON，默认跳过加载。
_DISPATCH_META_DEFER = (defer(MegaFlowWorkOrderDispatch.payload),)


def normalize_pause_state(pause_state: str | None) -> str:
    return str(pause_state or "").strip()


def is_pause_state_idle(pause_state: str | None) -> bool:
    return normalize_pause_state(pause_state) == ""


def get_current_dispatch(
    db: Session,
    work_order_id: int,
    *,
    include_payload: bool = False,
) -> MegaFlowWorkOrderDispatch | None:
    stmt = (
        select(MegaFlowWorkOrderDispatch)
        .where(
            MegaFlowWorkOrderDispatch.work_order_id == work_order_id,
            MegaFlowWorkOrderDispatch.status.notin_(TERMINAL_DISPATCH_STATUSES),
        )
        .order_by(MegaFlowWorkOrderDispatch.id.desc())
    )
    if not include_payload:
        stmt = stmt.options(*_DISPATCH_META_DEFER)
    return db.scalars(stmt).first()


def batch_current_dispatches(db: Session, work_order_ids: list[int]) -> dict[int, MegaFlowWorkOrderDispatch]:
    if not work_order_ids:
        return {}
    rows = db.scalars(
        select(MegaFlowWorkOrderDispatch)
        .options(*_DISPATCH_META_DEFER)
        .where(
            MegaFlowWorkOrderDispatch.work_order_id.in_(work_order_ids),
            MegaFlowWorkOrderDispatch.status.notin_(TERMINAL_DISPATCH_STATUSES),
        )
        .order_by(MegaFlowWorkOrderDispatch.work_order_id, MegaFlowWorkOrderDispatch.id.desc())
    ).all()
    result: dict[int, MegaFlowWorkOrderDispatch] = {}
    for row in rows:
        if row.work_order_id not in result:
            result[row.work_order_id] = row
    return result


def generate_dispatch_id(now: datetime | None = None) -> str:
    """生成下发编号：DSP + yyMMdd + 6 位随机数，例如 DSP260710482913。"""
    stamp = (now or datetime.now()).strftime("%y%m%d")
    suffix = f"{random.randint(0, 10**DISPATCH_ID_RANDOM_DIGITS - 1):0{DISPATCH_ID_RANDOM_DIGITS}d}"
    return f"{DISPATCH_ID_PREFIX}{stamp}{suffix}"


def has_dispatches(db: Session, work_order_id: int) -> bool:
    row = db.scalar(
        select(MegaFlowWorkOrderDispatch.id)
        .where(MegaFlowWorkOrderDispatch.work_order_id == work_order_id)
        .limit(1)
    )
    return row is not None


def void_open_dispatches(db: Session, work_order_id: int) -> None:
    rows = db.scalars(
        select(MegaFlowWorkOrderDispatch)
        .options(*_DISPATCH_META_DEFER)
        .where(
            MegaFlowWorkOrderDispatch.work_order_id == work_order_id,
            MegaFlowWorkOrderDispatch.status.notin_(TERMINAL_DISPATCH_STATUSES),
        )
    ).all()
    for row in rows:
        row.status = "voided"
        row.pause_state = None


def request_pause_current_dispatch(db: Session, work_order_id: int) -> MegaFlowWorkOrderDispatch:
    current = get_current_dispatch(db, work_order_id)
    if not current:
        raise ValueError("没有可停止的下发记录")

    if current.status not in PAUSABLE_STATUSES:
        raise ValueError("仅待确认或执行中的下发记录可以暂停")

    pause_state = normalize_pause_state(current.pause_state)
    if pause_state == "pausing":
        raise ValueError("设备暂停确认中，请稍候")
    if pause_state == "paused":
        return current
    if pause_state == "resuming":
        raise ValueError("设备恢复确认中，请稍候")

    current.pause_state = "pausing"
    return current


def acknowledge_pause_current_dispatch(db: Session, work_order_id: int) -> MegaFlowWorkOrderDispatch:
    current = get_current_dispatch(db, work_order_id)
    if not current:
        raise ValueError("没有可确认的下发记录")
    if normalize_pause_state(current.pause_state) != "pausing":
        raise ValueError("当前下发记录不在暂停确认中")
    current.pause_state = "paused"
    return current


def request_resume_current_dispatch(db: Session, work_order_id: int) -> MegaFlowWorkOrderDispatch:
    current = get_current_dispatch(db, work_order_id)
    if not current:
        raise ValueError("没有可继续的下发记录")
    if normalize_pause_state(current.pause_state) != "paused":
        raise ValueError("仅设备已暂停的下发记录可以继续")

    current.pause_state = "resuming"
    return current


def acknowledge_resume_current_dispatch(db: Session, work_order_id: int) -> MegaFlowWorkOrderDispatch:
    current = get_current_dispatch(db, work_order_id)
    if not current:
        raise ValueError("没有可确认的下发记录")
    if normalize_pause_state(current.pause_state) != "resuming":
        raise ValueError("当前下发记录不在恢复确认中")
    current.pause_state = None
    return current


def create_dispatch_record(
    db: Session,
    order: MegaFlowWorkOrder,
    *,
    operator_name: str,
) -> MegaFlowWorkOrderDispatch:
    if get_current_dispatch(db, order.id):
        raise ValueError("上一条下发记录尚未结束，不能重复发送")
    for _ in range(DISPATCH_ID_RETRY_LIMIT):
        dispatchId = generate_dispatch_id()
        payload = build_dispatch_payload(order, dispatchId)
        record = MegaFlowWorkOrderDispatch(
            dispatchId=dispatchId,
            work_order_id=order.id,
            payload=payload,
            payload_hash=hash_dict(payload),
            content_hash_at_send=order.content_hash or "",
            status="pending",
            pause_state=None,
            sent_at=datetime.now(),
            created_by=operator_name,
        )
        try:
            with db.begin_nested():
                db.add(record)
                db.flush()
            return record
        except IntegrityError:
            continue
    raise ValueError("无法生成唯一下发编号，请稍后重试")


def confirm_current_dispatch(db: Session, work_order_id: int) -> MegaFlowWorkOrderDispatch:
    current = get_current_dispatch(db, work_order_id)
    if not current:
        raise ValueError("没有可确认的下发记录")
    if current.status != "pending":
        raise ValueError("仅待确认的下发记录可以确认执行")
    if not is_pause_state_idle(current.pause_state):
        raise ValueError("暂停流程进行中，暂不可确认执行")
    current.status = "running"
    return current


def complete_current_dispatch(db: Session, work_order_id: int) -> MegaFlowWorkOrderDispatch:
    current = get_current_dispatch(db, work_order_id)
    if not current:
        raise ValueError("没有可完成的下发记录")
    if current.status != "running":
        raise ValueError("仅执行中的下发记录可以完成")
    if not is_pause_state_idle(current.pause_state):
        raise ValueError("暂停流程进行中，暂不可完成")
    current.status = "completed"
    return current


def fail_current_dispatch(
    db: Session,
    work_order_id: int,
) -> MegaFlowWorkOrderDispatch:
    current = get_current_dispatch(db, work_order_id)
    if not current:
        raise ValueError("没有可标记失败的下发记录")
    if current.status not in PAUSABLE_STATUSES:
        raise ValueError("当前下发记录不可标记失败")
    current.status = "failed"
    current.pause_state = None
    return current
