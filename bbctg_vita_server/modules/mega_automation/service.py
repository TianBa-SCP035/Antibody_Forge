from __future__ import annotations

from datetime import datetime
import json
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, defer

from models.mega_automation import MegaFlowWorkOrder, MegaFlowWorkOrderDispatch

from modules.mega_automation.content import (
    build_content_body,
    build_content_hash,
    clean_text,
    collect_validation_issues,
    compute_hash_from_payload,
    default_cell_columns,
    default_sample_wells,
    extract_search_arrays,
    get_order_content,
    safe_dict,
)
from modules.mega_automation.dispatch import (
    TERMINAL_DISPATCH_STATUSES,
    acknowledge_pause_current_dispatch,
    acknowledge_resume_current_dispatch,
    batch_current_dispatches,
    complete_current_dispatch,
    confirm_current_dispatch,
    create_dispatch_record,
    fail_current_dispatch,
    get_current_dispatch,
    has_dispatches,
    normalize_pause_state,
    request_pause_current_dispatch,
    request_resume_current_dispatch,
    void_open_dispatches,
)


WORK_ORDER_STATUSES = [
    {"value": "draft", "label": "草稿"},
    {"value": "validated", "label": "已校验"},
    {"value": "sent", "label": "已发送"},
    {"value": "running", "label": "执行中"},
    {"value": "paused", "label": "已暂停"},
    {"value": "execution_failed", "label": "执行失败"},
    {"value": "completed", "label": "已完成"},
    {"value": "failed", "label": "校验失败"},
    {"value": "cancelled", "label": "已作废"},
]
ORDER_STATUS_LABELS = {item["value"]: item["label"] for item in WORK_ORDER_STATUSES}
DATA_TYPES = [
    {"value": "TITER", "label": "效价"},
    {"value": "PLAS", "label": "质粒"},
    {"value": "PCR", "label": "PCR"},
]
DATA_TYPE_VALUES = {item["value"] for item in DATA_TYPES}
PRIORITIES = [
    {"value": "high", "label": "高"},
    {"value": "normal", "label": "普通"},
    {"value": "low", "label": "低"},
]
PRIORITY_VALUES = {item["value"] for item in PRIORITIES}

EDITABLE_STATUSES = frozenset({"draft", "validated", "failed", "execution_failed"})
ACTIVE_EXECUTION_STATUSES = frozenset({"sent", "running"})
PAUSED_CHANGE_CONFIRM_MESSAGE = (
    "工单内容已变更。确认后将使此前有效的下发记录失效，且无法再通过「继续」恢复为原发送状态。"
)

def _operator_name(user: Any) -> str:
    return clean_text(getattr(user, "display_name", None) or getattr(user, "username", None) or "unknown")


def _get_order_or_raise(
    db: Session,
    order_id: int,
    *,
    for_update: bool = False,
) -> MegaFlowWorkOrder:
    stmt = select(MegaFlowWorkOrder).where(MegaFlowWorkOrder.id == int(order_id))
    if for_update:
        stmt = stmt.with_for_update()
    order = db.scalar(stmt)
    if not order:
        raise ValueError("流式工单不存在")
    return order


def _ensure_not_cancelled(order: MegaFlowWorkOrder) -> None:
    if order.status == "cancelled":
        raise ValueError("工单已作废，不可操作")
    if order.status == "completed":
        raise ValueError("工单已完成，不可再操作")


def _get_confirmed_paused_dispatch(
    db: Session,
    order: MegaFlowWorkOrder,
    *,
    error_message: str,
    missing_message: str | None = None,
) -> MegaFlowWorkOrderDispatch:
    current = get_current_dispatch(db, order.id)
    if not current:
        raise ValueError(missing_message or error_message)
    if normalize_pause_state(current.pause_state) != "paused":
        raise ValueError(error_message)
    return current


def _ensure_editable(order: MegaFlowWorkOrder) -> None:
    _ensure_not_cancelled(order)
    if order.status in ACTIVE_EXECUTION_STATUSES:
        raise ValueError("已发送工单请先停止后再修改")
    if order.status == "paused":
        raise ValueError("已暂停工单请使用校验确认修改，不能直接保存")
    if order.status not in EDITABLE_STATUSES:
        raise ValueError(f"当前状态（{order.status}）不可编辑")


def _apply_order_columns(order: MegaFlowWorkOrder, data: dict[str, Any]) -> None:
    base_info = safe_dict(data.get("base_info"))
    order.order_name = clean_text(data.get("order_name") or base_info.get("order_name"))
    order.order_no = clean_text(data.get("order_no"))
    if not order.order_no:
        raise ValueError("订单编号不能为空")
    order.remark = clean_text(data.get("remark") or base_info.get("remark"))
    data_type = clean_text(data.get("data_type") or order.data_type or "TITER")
    if data_type not in DATA_TYPE_VALUES:
        raise ValueError(f"不支持的检测类型：{data_type}")
    order.data_type = data_type
    priority = clean_text(data.get("priority") or order.priority or "normal")
    if priority not in PRIORITY_VALUES:
        raise ValueError(f"不支持的优先级：{priority}")
    order.priority = priority
    if "source_id" in data:
        incoming = clean_text(data.get("source_id"))
        if not order.source_id:
            order.source_id = incoming or None
        elif incoming and incoming != (order.source_id or ""):
            raise ValueError("来源业务单不可修改")


def _check_expected_content_hash(order: MegaFlowWorkOrder, data: dict[str, Any]) -> None:
    if "expected_content_hash" not in data:
        raise ValueError("缺少 expected_content_hash，无法确认编辑版本")
    if clean_text(data.get("expected_content_hash")) != (order.content_hash or ""):
        raise ValueError("工单内容已被其他用户修改，请刷新后重试")


def _apply_content(order: MegaFlowWorkOrder, data: dict[str, Any]) -> str:
    content = build_content_body(data)
    order.content = content
    search_arrays = extract_search_arrays(content)
    order.project_nos = search_arrays["project_nos"]
    order.targets = search_arrays["targets"]
    order.sample_plate_barcodes = search_arrays["sample_plate_barcodes"]
    order.cell_plate_barcodes = search_arrays["cell_plate_barcodes"]
    new_hash = build_content_hash(order, content)
    order.content_hash = new_hash
    return new_hash


def _apply_order_data(order: MegaFlowWorkOrder, data: dict[str, Any]) -> str:
    """写入工单列字段与 content（及派生检索字段、content_hash）。"""
    _apply_order_columns(order, data)
    return _apply_content(order, data)


def _resolve_order_display(status: str, pause_state: str | None) -> dict[str, str]:
    pause = normalize_pause_state(pause_state)
    if status == "paused":
        if pause == "pausing":
            return {"display_status": "pausing", "display_status_label": "暂停中"}
        if pause == "resuming":
            return {"display_status": "resuming", "display_status_label": "恢复中"}
        return {"display_status": "paused", "display_status_label": "已暂停"}
    label = ORDER_STATUS_LABELS.get(status, status or "-")
    return {"display_status": status, "display_status_label": label}


def _apply_order_display(
    item: dict[str, Any],
    *,
    status: str,
    pause_state: str | None = None,
) -> dict[str, Any]:
    normalized = normalize_pause_state(pause_state)
    item["pause_state"] = normalized
    item.update(_resolve_order_display(status, normalized))
    return item


def _enrich_detail(data: dict[str, Any], order: MegaFlowWorkOrder) -> dict[str, Any]:
    """详情补充：是否有下发历史、以及当前未终止下发的 pause 显示态。"""
    dispatches = data.get("dispatches") or []
    data["has_dispatches"] = bool(dispatches)
    # dispatches 已按 id desc；与 get_current_dispatch 相同，无需再查库
    current = next(
        (item for item in dispatches if item.get("status") not in TERMINAL_DISPATCH_STATUSES),
        None,
    )
    return _apply_order_display(
        data,
        status=order.status,
        pause_state=current.get("pause_state") if current else None,
    )


def get_meta() -> dict[str, Any]:
    return {
        "statuses": WORK_ORDER_STATUSES,
        "data_types": DATA_TYPES,
        "priorities": PRIORITIES,
        "default_sample_wells": default_sample_wells(),
        "default_cell_columns": default_cell_columns(),
    }


def save_work_order(db: Session, data: dict[str, Any], user: Any) -> dict[str, Any]:
    order_id = data.get("id")
    if order_id:
        order = _get_order_or_raise(db, int(order_id), for_update=True)
        _check_expected_content_hash(order, data)
        _ensure_editable(order)

        preview_hash = compute_hash_from_payload(data, order)
        if preview_hash == (order.content_hash or ""):
            detail = get_work_order_detail(db, order.id)
            detail["unchanged"] = True
            return detail

        previous_hash = order.content_hash
        _apply_order_data(order, data)

        if order.status in {"validated", "execution_failed"} and previous_hash != order.content_hash:
            order.status = "draft"

        order.error_message = None
        db.commit()
        return get_work_order_detail(db, order.id)

    order = MegaFlowWorkOrder(status="draft", created_by=_operator_name(user))
    _apply_order_data(order, data)
    db.add(order)
    order.error_message = None
    db.commit()
    return get_work_order_detail(db, order.id)


def _load_dispatches(db: Session, order_id: int) -> list[dict[str, Any]]:
    rows = db.scalars(
        select(MegaFlowWorkOrderDispatch)
        .options(defer(MegaFlowWorkOrderDispatch.payload))
        .where(MegaFlowWorkOrderDispatch.work_order_id == order_id)
        .order_by(MegaFlowWorkOrderDispatch.id.desc())
    ).all()
    return [row.to_dict(include_payload=False) for row in rows]


def get_work_order_detail(db: Session, order_id: int) -> dict[str, Any]:
    order = _get_order_or_raise(db, order_id)
    data = order.to_dict(include_detail=True)
    data["dispatches"] = _load_dispatches(db, order.id)
    return _enrich_detail(data, order)


def get_active_dispatch_payload(db: Session, order_id: int) -> dict[str, Any]:
    order = _get_order_or_raise(db, int(order_id))
    current = get_current_dispatch(db, order.id, include_payload=True)
    if not current:
        return {"dispatch": None, "payload": None}
    return {
        "dispatch": current.to_dict(include_payload=False),
        "payload": current.payload,
    }


def _json_overlaps(column, value: str):
    return func.json_overlaps(column, json.dumps([value]))


def get_work_order_list(db: Session, data: dict[str, Any]) -> dict[str, Any]:
    page = max(int(data.get("page", 1) or 1), 1)
    limit = min(max(int(data.get("limit", 20) or 20), 1), 200)
    stmt = select(MegaFlowWorkOrder)

    keyword = clean_text(data.get("keyword"))
    if keyword:
        pattern = f"%{keyword}%"
        stmt = stmt.where(
            or_(
                MegaFlowWorkOrder.order_no.like(pattern),
                MegaFlowWorkOrder.order_name.like(pattern),
            )
        )
    status = clean_text(data.get("status"))
    if status:
        stmt = stmt.where(MegaFlowWorkOrder.status == status)
    data_type = clean_text(data.get("data_type"))
    if data_type:
        stmt = stmt.where(MegaFlowWorkOrder.data_type == data_type)
    project_no = clean_text(data.get("project_no"))
    if project_no:
        stmt = stmt.where(_json_overlaps(MegaFlowWorkOrder.project_nos, project_no))
    target = clean_text(data.get("target"))
    if target:
        stmt = stmt.where(_json_overlaps(MegaFlowWorkOrder.targets, target))
    sample_plate_barcode = clean_text(data.get("sample_plate_barcode"))
    if sample_plate_barcode:
        stmt = stmt.where(_json_overlaps(MegaFlowWorkOrder.sample_plate_barcodes, sample_plate_barcode))
    cell_plate_barcode = clean_text(data.get("cell_plate_barcode"))
    if cell_plate_barcode:
        stmt = stmt.where(_json_overlaps(MegaFlowWorkOrder.cell_plate_barcodes, cell_plate_barcode))

    total = db.scalar(
        stmt.with_only_columns(func.count(), maintain_column_froms=True).order_by(None)
    ) or 0
    rows = db.scalars(
        stmt.options(defer(MegaFlowWorkOrder.content))
        .order_by(MegaFlowWorkOrder.updated_at.desc(), MegaFlowWorkOrder.id.desc())
        .offset((page - 1) * limit)
        .limit(limit)
    ).all()
    current_dispatches = batch_current_dispatches(db, [row.id for row in rows])
    items = []
    for row in rows:
        item = row.to_dict(include_detail=False)
        current = current_dispatches.get(row.id)
        _apply_order_display(
            item,
            status=row.status,
            pause_state=current.pause_state if current else None,
        )
        items.append(item)
    return {
        "items": items,
        "total": total,
        "stats": get_work_order_stats(db),
    }


def get_work_orders_by_source(db: Session, data: dict[str, Any]) -> dict[str, Any]:
    data_type = clean_text(data.get("data_type"))
    source_id = clean_text(data.get("source_id"))
    if not data_type or not source_id:
        raise ValueError("data_type 与 source_id 不能为空")
    if data_type not in DATA_TYPE_VALUES:
        raise ValueError(f"不支持的检测类型：{data_type}")

    stmt = select(MegaFlowWorkOrder).where(
        MegaFlowWorkOrder.data_type == data_type,
        MegaFlowWorkOrder.source_id == source_id,
    )
    if data.get("exclude_cancelled"):
        stmt = stmt.where(MegaFlowWorkOrder.status != "cancelled")

    rows = db.scalars(
        stmt.options(defer(MegaFlowWorkOrder.content)).order_by(MegaFlowWorkOrder.id.desc())
    ).all()
    current_dispatches = batch_current_dispatches(db, [row.id for row in rows])
    items = []
    for row in rows:
        item = row.to_dict(include_detail=False)
        current = current_dispatches.get(row.id)
        _apply_order_display(
            item,
            status=row.status,
            pause_state=current.pause_state if current else None,
        )
        items.append(item)
    return {"items": items}


def get_work_order_stats(db: Session) -> dict[str, int]:
    rows = db.execute(
        select(MegaFlowWorkOrder.status, func.count(MegaFlowWorkOrder.id)).group_by(MegaFlowWorkOrder.status)
    ).all()
    stats = {status["value"]: 0 for status in WORK_ORDER_STATUSES}
    for status, count in rows:
        stats[str(status or "draft")] = int(count or 0)
    stats["total"] = sum(value for key, value in stats.items() if key != "total")
    return stats


def _validate_from_db(order: MegaFlowWorkOrder) -> dict[str, Any]:
    content = get_order_content(order)
    issues = collect_validation_issues(order=order, content=content)
    errors = [item["message"] for item in issues]

    if errors:
        order.status = "failed"
        order.error_message = "；".join(errors)
    else:
        order.status = "validated"
        order.error_message = None

    return {"valid": not errors, "errors": errors, "issues": issues}


def _paused_validation_result(
    *,
    valid: bool,
    errors: list[str] | None = None,
    issues: list[dict[str, str]] | None = None,
    needs_confirm: bool = False,
    content_changed: bool = False,
    can_resume: bool = False,
    saved: bool = False,
    message: str = "",
    item: dict[str, Any] | None = None,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "valid": valid,
        "errors": errors or [],
        "issues": issues or [],
        "needs_confirm": needs_confirm,
        "content_changed": content_changed,
        "can_resume": can_resume,
        "saved": saved,
        "message": message,
    }
    if item is not None:
        result["item"] = item
    return result


def _validate_paused(
    db: Session,
    order: MegaFlowWorkOrder,
    data: dict[str, Any],
) -> dict[str, Any]:
    current = _get_confirmed_paused_dispatch(
        db,
        order,
        error_message="设备尚未完成暂停，暂不可编辑或校验",
    )
    payload = safe_dict(data.get("payload"))
    if not payload:
        raise ValueError("暂停校验需要提交当前编辑内容")

    confirm_revoke = bool(data.get("confirm_revoke"))
    _check_expected_content_hash(order, data)
    issues = collect_validation_issues(payload, order)
    errors = [item["message"] for item in issues]
    if errors:
        return _paused_validation_result(valid=False, errors=errors, issues=issues)

    local_hash = compute_hash_from_payload(payload, order)
    baseline_hash = current.content_hash_at_send

    if local_hash == baseline_hash:
        return _paused_validation_result(
            valid=True,
            can_resume=True,
            item=get_work_order_detail(db, order.id),
        )

    if not confirm_revoke:
        return _paused_validation_result(
            valid=True,
            needs_confirm=True,
            content_changed=True,
            message=PAUSED_CHANGE_CONFIRM_MESSAGE,
        )

    _apply_order_data(order, payload)
    void_open_dispatches(db, order.id)
    order.status = "validated"
    order.error_message = None
    db.commit()
    return _paused_validation_result(
        valid=True,
        content_changed=True,
        saved=True,
        item=get_work_order_detail(db, order.id),
    )


def validate_work_order(db: Session, order_id: int, data: dict[str, Any] | None = None) -> dict[str, Any]:
    data = data or {}
    order = _get_order_or_raise(db, int(order_id), for_update=True)
    _ensure_not_cancelled(order)

    if order.status == "paused":
        return _validate_paused(db, order, data)

    _check_expected_content_hash(order, data)
    if order.status in ACTIVE_EXECUTION_STATUSES:
        raise ValueError("已发送工单请先停止后再校验")
    if order.status not in EDITABLE_STATUSES:
        raise ValueError(f"当前状态（{order.status}）不可校验")

    result = _validate_from_db(order)
    db.commit()
    result["needs_confirm"] = False
    result["content_changed"] = False
    result["can_resume"] = False
    result["saved"] = False
    result["message"] = ""
    result["item"] = get_work_order_detail(db, order.id)
    return result


def dispatch_work_order(db: Session, order_id: int, user: Any) -> dict[str, Any]:
    order = _get_order_or_raise(db, int(order_id), for_update=True)
    _ensure_not_cancelled(order)
    if order.status != "validated":
        raise ValueError("请先校验通过后再发送")

    create_dispatch_record(db, order, operator_name=_operator_name(user))
    order.status = "sent"
    order.sent_at = datetime.now()
    order.error_message = None
    db.commit()
    return get_work_order_detail(db, order.id)


def pause_work_order(db: Session, order_id: int) -> dict[str, Any]:
    order = _get_order_or_raise(db, int(order_id), for_update=True)
    _ensure_not_cancelled(order)
    if order.status not in ACTIVE_EXECUTION_STATUSES:
        raise ValueError("仅已发送或执行中的工单可以停止")
    request_pause_current_dispatch(db, order.id)
    order.status = "paused"
    order.error_message = None
    db.commit()
    return get_work_order_detail(db, order.id)


def acknowledge_pause_work_order(db: Session, order_id: int) -> dict[str, Any]:
    order = _get_order_or_raise(db, int(order_id), for_update=True)
    _ensure_not_cancelled(order)
    if order.status != "paused":
        raise ValueError("仅已暂停工单可以确认设备暂停")
    acknowledge_pause_current_dispatch(db, order.id)
    db.commit()
    return get_work_order_detail(db, order.id)


def resume_work_order(db: Session, order_id: int) -> dict[str, Any]:
    order = _get_order_or_raise(db, int(order_id), for_update=True)
    _ensure_not_cancelled(order)
    if order.status != "paused":
        raise ValueError("仅已暂停工单可以继续")

    current = _get_confirmed_paused_dispatch(
        db,
        order,
        error_message="设备尚未完成暂停，暂不可继续",
        missing_message="没有可继续的下发记录",
    )

    if (order.content_hash or "") != current.content_hash_at_send:
        raise ValueError("工单内容已变更，无法继续，请使用校验确认修改")

    request_resume_current_dispatch(db, order.id)
    db.commit()
    return get_work_order_detail(db, order.id)


def acknowledge_resume_work_order(db: Session, order_id: int) -> dict[str, Any]:
    order = _get_order_or_raise(db, int(order_id), for_update=True)
    _ensure_not_cancelled(order)
    if order.status != "paused":
        raise ValueError("仅已暂停工单可以确认设备恢复")
    dispatch = acknowledge_resume_current_dispatch(db, order.id)
    order.status = "running" if dispatch.status == "running" else "sent"
    order.error_message = None
    db.commit()
    return get_work_order_detail(db, order.id)


def confirm_dispatch_execution(db: Session, order_id: int) -> dict[str, Any]:
    order = _get_order_or_raise(db, int(order_id), for_update=True)
    _ensure_not_cancelled(order)
    if order.status != "sent":
        raise ValueError("仅已发送工单可以确认执行")
    confirm_current_dispatch(db, order.id)
    order.status = "running"
    order.error_message = None
    db.commit()
    return get_work_order_detail(db, order.id)


def complete_work_order(db: Session, order_id: int) -> dict[str, Any]:
    order = _get_order_or_raise(db, int(order_id), for_update=True)
    _ensure_not_cancelled(order)
    if order.status != "running":
        raise ValueError("仅执行中的工单可以完成")
    complete_current_dispatch(db, order.id)
    order.status = "completed"
    order.error_message = None
    db.commit()
    return get_work_order_detail(db, order.id)


def fail_work_order(
    db: Session,
    order_id: int,
    error_message: str = "",
) -> dict[str, Any]:
    order = _get_order_or_raise(db, int(order_id), for_update=True)
    _ensure_not_cancelled(order)
    if order.status not in {"sent", "running", "paused"}:
        raise ValueError("仅已发送、执行中或已暂停的工单可以标记执行失败")
    error = clean_text(error_message)
    fail_current_dispatch(db, order.id)
    order.status = "execution_failed"
    order.error_message = error or "设备执行失败"
    db.commit()
    return get_work_order_detail(db, order.id)


def delete_work_order(db: Session, order_id: int) -> dict[str, Any]:
    order = _get_order_or_raise(db, int(order_id), for_update=True)
    if order.status == "cancelled":
        raise ValueError("工单已作废")
    if has_dispatches(db, order.id):
        raise ValueError("已发送过的工单不能删除，请使用作废")

    deleted_id = order.id
    db.delete(order)
    db.commit()
    return {"deleted": True, "id": deleted_id}


def cancel_work_order(db: Session, order_id: int) -> dict[str, Any]:
    order = _get_order_or_raise(db, int(order_id), for_update=True)
    if order.status == "cancelled":
        raise ValueError("工单已作废")
    if order.status == "completed":
        raise ValueError("已完成工单不可作废")
    if order.status in ACTIVE_EXECUTION_STATUSES:
        raise ValueError("已发送或执行中的工单请先停止后再作废")
    if not has_dispatches(db, order.id):
        raise ValueError("未发送的工单请使用删除")
    if order.status == "paused":
        _get_confirmed_paused_dispatch(
            db,
            order,
            error_message="设备尚未完成暂停，暂不可作废",
        )

    void_open_dispatches(db, order.id)
    order.status = "cancelled"
    order.error_message = None
    db.commit()
    return get_work_order_detail(db, order.id)
