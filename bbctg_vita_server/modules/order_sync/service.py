from __future__ import annotations

from dataclasses import dataclass, field
import json
import logging
from pathlib import Path
import re
from typing import Any

from fastapi import UploadFile
from sqlalchemy import String, cast, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from core.config import get_settings
from core.errors import NotFoundError
from models.order_sync import OrderSync, OrderSyncBoard
from modules.order_sync import titer_import, verify
from modules.order_sync.verify import BoardResult, OrderResult, TiterPlan
from utils.clock import now_local
from utils.filter_values import like_contains
from utils.pagination import parse_page_limit
from utils.uploads import contained_path, read_limited

logger = logging.getLogger(__name__)

STATUS_PROCESSING = "processing"
STATUS_PASSED = "passed"
STATUS_PARTIAL = "partial"
STATUS_REJECTED = "rejected"
STATUS_INVALID = "invalid"
STATUS_ERROR = "error"
STATUS_LABELS = {
    "pending": "旧数据未核对",
    STATUS_PROCESSING: "处理中",
    STATUS_PASSED: "全部通过",
    STATUS_PARTIAL: "部分通过",
    STATUS_REJECTED: "全部未通过",
    STATUS_INVALID: "格式错误",
    STATUS_ERROR: "处理异常",
}
LIST_STATUSES = (STATUS_PASSED, STATUS_PARTIAL, STATUS_REJECTED, STATUS_INVALID, STATUS_ERROR)


class OrderSyncError(Exception):
    def __init__(self, code: int, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


@dataclass
class SyncReply:
    http_status: int
    body: dict[str, Any]
    plans: list[TiterPlan] = field(default_factory=list)
    sync_id: int | None = None


def device_body(code: int, message: str, trace_id: str, data: Any = None) -> dict[str, Any]:
    return {"code": code, "message": message, "trace_id": trace_id, "data": data}


def _safe_filename_part(value: str) -> str:
    safe = re.sub(r"[^0-9A-Za-z._-]+", "_", value).strip("._-")
    return safe or "trace"


def _sync_root() -> Path:
    root = Path(get_settings().repository_root) / "order_sync"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _extract_summary(raw: dict[str, Any]) -> tuple[list[str], list[dict[str, str]]]:
    order_infos = raw.get("order_infos")
    if not isinstance(order_infos, list) or not order_infos:
        raise OrderSyncError(400, "order_json 文件格式错误：order_infos 不能为空")

    order_nos: list[str] = []
    project_infos: list[dict[str, str]] = []
    for index, item in enumerate(order_infos, start=1):
        if not isinstance(item, dict):
            raise OrderSyncError(400, f"order_json 文件格式错误：order_infos[{index}] 必须是对象")
        order_no = _clean_text(item.get("order_no"))
        if not order_no:
            raise OrderSyncError(400, f"order_json 文件格式错误：order_infos[{index}].order_no 不能为空")
        order_nos.append(order_no)

        projects = item.get("project_infos")
        if not isinstance(projects, list):
            continue
        for project in projects:
            if not isinstance(project, dict):
                continue
            project_infos.append(
                {
                    "order_no": order_no,
                    "project_no": _clean_text(project.get("project_no")),
                    "data_type": _clean_text(project.get("data_type")),
                    "experiment_date": _clean_text(project.get("experiment_date")),
                    "target": _clean_text(project.get("target")),
                }
            )
    return order_nos, project_infos


def _parse_raw(raw_bytes: bytes) -> dict[str, Any]:
    if not raw_bytes:
        raise OrderSyncError(400, "order_json 文件不能为空")
    try:
        raw_text = raw_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise OrderSyncError(400, "order_json 文件必须是 UTF-8 编码") from exc
    try:
        raw_data = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise OrderSyncError(400, f"order_json 文件格式错误：{exc.msg}") from exc
    if not isinstance(raw_data, dict):
        raise OrderSyncError(400, "order_json 文件格式错误：根节点必须是对象")
    return raw_data


def _replay(record: OrderSync) -> SyncReply:
    if record.response_body is not None:
        return SyncReply(record.http_status or 200, record.response_body)
    if record.status == STATUS_PROCESSING:
        raise OrderSyncError(409, f"trace_id 正在处理：{record.trace_id}")
    raise OrderSyncError(422, f"trace_id 已存在：{record.trace_id}")


def _store_raw(db: Session, trace_id: str, raw_bytes: bytes) -> OrderSync | None:
    """原文落盘并登记，先提交；trace_id 撞上并发写入时返回 None。"""
    now = now_local()
    date_part = now.strftime("%Y%m%d")
    file_name = f"{_safe_filename_part(trace_id)}_{now.strftime('%H%M%S%f')}.json"
    file_path = _sync_root() / date_part / file_name
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_bytes(raw_bytes)
    record = OrderSync(
        trace_id=trace_id,
        file_path=f"/order_sync/{date_part}/{file_name}",
        status=STATUS_PROCESSING,
    )
    try:
        db.add(record)
        db.commit()
    except IntegrityError:
        db.rollback()
        file_path.unlink(missing_ok=True)
        return None
    except Exception:
        db.rollback()
        file_path.unlink(missing_ok=True)
        raise
    return record


def _raw_path(record: OrderSync) -> Path:
    return contained_path(Path(get_settings().repository_root), record.file_path)


def _order_payload(order: OrderResult) -> dict[str, Any]:
    return {
        "order_no": order.order_no,
        "status": order.status,
        "message": order.message,
        "boards": [
            {
                "barcode": board.detect_barcode,
                "sample_code": board.sample_barcode,
                "cell_name": board.cell_name,
                "status": board.status,
                "message": board.message,
            }
            for board in order.boards
        ],
    }


def _sync_status(orders: list[OrderResult]) -> str:
    statuses = {order.status for order in orders}
    if statuses == {verify.ORDER_ACCEPTED}:
        return STATUS_PASSED
    if statuses == {verify.ORDER_REJECTED}:
        return STATUS_REJECTED
    return STATUS_PARTIAL


def _board_row(board: BoardResult, sync_id: int, row: OrderSyncBoard | None) -> OrderSyncBoard:
    if row is None:
        row = OrderSyncBoard(sync_id=sync_id, seq=board.seq)
    elif (row.work_order_id, row.sample_barcode, row.cell_name) != (
        board.work_order_id,
        board.sample_barcode or None,
        board.cell_name or None,
    ):
        row.facs_plate_id = None
        row.image_file_id = None
        row.excel_file_id = None
    row.order_no = board.order_no
    row.data_type = board.data_type or None
    row.work_order_id = board.work_order_id
    row.dispatch_id = board.dispatch_id or None
    row.detect_barcode = board.detect_barcode or None
    row.sample_barcode = board.sample_barcode or None
    row.cell_name = board.cell_name or None
    row.experiment_date = board.experiment_date or None
    row.image_path = board.image_path or None
    row.csv_path = board.csv_path or None
    row.verify_status = board.status
    row.verify_message = board.message or None
    row.experiment_id = board.experiment_id or None
    row.import_status = titer_import.IMPORT_PENDING if board.plan else titer_import.IMPORT_NONE
    row.import_message = None
    return row


def _verify_and_record(db: Session, record: OrderSync, raw: dict[str, Any]) -> tuple[dict[str, Any], list[TiterPlan]]:
    """核对整份回传并写检测板记录，不提交；返回回复 data 和待导入的板。"""
    order_nos, project_infos = _extract_summary(raw)
    record.order_count = len(order_nos)
    record.order_nos = order_nos
    record.project_count = len(project_infos)
    record.project_infos = project_infos

    orders: list[OrderResult] = []
    seq = 1
    for order_info in raw["order_infos"]:
        order = verify.verify_order(db, order_info, seq)
        seq += len(order.boards)
        orders.append(order)

    existing = {
        row.seq: row
        for row in db.scalars(select(OrderSyncBoard).where(OrderSyncBoard.sync_id == record.id)).all()
    }
    plans: list[TiterPlan] = []
    boards = [board for order in orders for board in order.boards]
    for board in boards:
        row = _board_row(board, record.id, existing.pop(board.seq, None))
        db.add(row)
        db.flush()
        if board.plan is not None:
            board.plan.board_id = row.id
            plans.append(board.plan)
    for stale in existing.values():
        db.delete(stale)

    status = _sync_status(orders)
    data = {
        "status": status,
        "total_orders": len(orders),
        "success_orders": [order.order_no for order in orders if order.status == verify.ORDER_ACCEPTED],
        "partial_orders": [order.order_no for order in orders if order.status == verify.ORDER_PARTIAL],
        "failed_orders": [order.order_no for order in orders if order.status == verify.ORDER_REJECTED],
        "results": [_order_payload(order) for order in orders],
    }
    record.status = status
    record.error_message = None
    record.import_status = titer_import.IMPORT_PENDING if plans else titer_import.IMPORT_NONE
    record.processed_at = now_local()
    return data, plans


def _finish(db: Session, record: OrderSync, reply: SyncReply) -> SyncReply:
    record.http_status = reply.http_status
    record.response_body = reply.body
    record.processed_at = now_local()
    db.commit()
    reply.sync_id = record.id
    return reply


def receive_sync(db: Session, trace_id: str, order_json: UploadFile | None) -> SyncReply:
    """先留存原文再核对；留存之后的结果（含格式错误）连同回复一起存进记录，trace_id 重推原样返回。"""
    normalized_trace_id = (trace_id or "").strip()
    if not normalized_trace_id:
        raise OrderSyncError(400, "trace_id 不能为空")
    if order_json is None:
        raise OrderSyncError(400, "缺少 order_json 文件")
    try:
        raw_bytes = read_limited(order_json, get_settings().order_sync_max_mb * 1024 * 1024, "order_json 文件")
    except ValueError as exc:
        raise OrderSyncError(413, str(exc)) from exc

    existing = db.scalar(select(OrderSync).where(OrderSync.trace_id == normalized_trace_id))
    if existing is not None:
        return _replay(existing)
    record = _store_raw(db, normalized_trace_id, raw_bytes)
    if record is None:
        existing = db.scalar(select(OrderSync).where(OrderSync.trace_id == normalized_trace_id))
        if existing is None:
            raise OrderSyncError(500, "服务端异常")
        return _replay(existing)

    try:
        raw = _parse_raw(raw_bytes)
        data, plans = _verify_and_record(db, record, raw)
    except OrderSyncError as exc:
        db.rollback()
        record.status = STATUS_INVALID
        record.error_message = exc.message
        record.import_status = titer_import.IMPORT_NONE
        return _finish(db, record, SyncReply(exc.code, device_body(exc.code, exc.message, normalized_trace_id)))
    except Exception as exc:
        db.rollback()
        logger.exception("order sync verify failed: trace_id=%s", normalized_trace_id)
        record.status = STATUS_ERROR
        record.error_message = str(exc)[:2000] or "服务端异常"
        record.import_status = titer_import.IMPORT_NONE
        return _finish(db, record, SyncReply(500, device_body(500, "服务端异常", normalized_trace_id)))

    reply = SyncReply(200, device_body(0, "success", normalized_trace_id, data), plans)
    return _finish(db, record, reply)


def reprocess_sync(db: Session, sync_id: int) -> tuple[dict[str, Any], list[TiterPlan]]:
    """用存档原文按当前数据重新核对、重新导入；当初回给镁伽的回复不改。

    服务中断会留下没回复的「处理中」记录，镁伽重推只能拿到 409；这种记录重新处理时把回复补存上，重推即可拿到。
    """
    record = db.get(OrderSync, sync_id)
    if record is None:
        raise NotFoundError("回传记录不存在")
    if titer_import.is_running(sync_id):
        raise ValueError("这条回传正在导入，请稍后再试")
    path = _raw_path(record)
    if not path.exists():
        raise NotFoundError("回传原文文件不存在")
    unanswered = record.status == STATUS_PROCESSING and record.response_body is None
    try:
        raw = _parse_raw(path.read_bytes())
        data, plans = _verify_and_record(db, record, raw)
    except OrderSyncError as exc:
        db.rollback()
        record.status = STATUS_INVALID
        record.error_message = exc.message
        record.import_status = titer_import.IMPORT_NONE
        if unanswered:
            _finish(db, record, SyncReply(exc.code, device_body(exc.code, exc.message, record.trace_id)))
        else:
            record.processed_at = now_local()
            db.commit()
        raise ValueError(exc.message) from exc
    if unanswered:
        _finish(db, record, SyncReply(200, device_body(0, "success", record.trace_id, data)))
    else:
        db.commit()
    return get_sync_detail(db, sync_id), plans


def _record_item(record: OrderSync) -> dict[str, Any]:
    item = record.to_dict()
    item["status_label"] = STATUS_LABELS.get(record.status, record.status)
    return item


def get_sync_list(db: Session, data: dict[str, Any]) -> dict[str, Any]:
    page, limit = parse_page_limit(data)
    conditions = []
    keyword = _clean_text(data.get("keyword"))
    if keyword:
        conditions.append(
            or_(like_contains(OrderSync.trace_id, keyword), like_contains(cast(OrderSync.order_nos, String), keyword))
        )
    import_status = _clean_text(data.get("import_status"))
    if import_status:
        conditions.append(OrderSync.import_status == import_status)

    stats_rows = db.execute(
        select(OrderSync.status, func.count()).where(*conditions).group_by(OrderSync.status)
    ).all()
    stats = {status: 0 for status in LIST_STATUSES}
    for status, count in stats_rows:
        stats[status] = int(count)

    status = _clean_text(data.get("status"))
    if status:
        conditions.append(OrderSync.status == status)
    total = db.scalar(select(func.count()).select_from(OrderSync).where(*conditions)) or 0
    rows = db.scalars(
        select(OrderSync)
        .where(*conditions)
        .order_by(OrderSync.id.desc())
        .offset((page - 1) * limit)
        .limit(limit)
    ).all()
    return {"items": [_record_item(row) for row in rows], "total": total, "page": page, "stats": stats}


def get_sync_detail(db: Session, sync_id: int) -> dict[str, Any]:
    record = db.get(OrderSync, sync_id)
    if record is None:
        raise NotFoundError("回传记录不存在")
    boards = db.scalars(
        select(OrderSyncBoard).where(OrderSyncBoard.sync_id == sync_id).order_by(OrderSyncBoard.seq)
    ).all()
    item = _record_item(record)
    item["response_body"] = record.response_body
    item["boards"] = [board.to_dict() for board in boards]
    return item


def get_raw_file(db: Session, sync_id: int) -> tuple[Path, str]:
    record = db.get(OrderSync, sync_id)
    if record is None:
        raise NotFoundError("回传记录不存在")
    path = _raw_path(record)
    if not path.exists():
        raise NotFoundError("回传原文文件不存在")
    return path, f"{_safe_filename_part(record.trace_id)}.json"


def get_work_order_boards(db: Session, work_order_id: int) -> list[dict[str, Any]]:
    rows = db.execute(
        select(OrderSyncBoard, OrderSync.trace_id, OrderSync.received_at)
        .join(OrderSync, OrderSync.id == OrderSyncBoard.sync_id)
        .where(OrderSyncBoard.work_order_id == work_order_id)
        .order_by(OrderSyncBoard.sync_id.desc(), OrderSyncBoard.seq)
    ).all()
    items = []
    for board, trace_id, received_at in rows:
        item = board.to_dict()
        item["trace_id"] = trace_id
        item["received_at"] = received_at.strftime("%Y-%m-%d %H:%M:%S") if received_at else None
        items.append(item)
    return items
