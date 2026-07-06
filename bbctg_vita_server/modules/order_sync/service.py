from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
import re
from typing import Any

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from core.config import get_settings
from models.order_sync import OrderSync


class OrderSyncError(Exception):
    def __init__(self, code: int, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


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


def receive_sync(db: Session, trace_id: str, order_json: UploadFile) -> dict[str, Any]:
    normalized_trace_id = (trace_id or "").strip()
    if not normalized_trace_id:
        raise OrderSyncError(400, "trace_id 不能为空")

    raw_bytes = order_json.file.read()
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

    order_nos, project_infos = _extract_summary(raw_data)

    exists = db.scalar(select(OrderSync.id).where(OrderSync.trace_id == normalized_trace_id))
    if exists:
        raise OrderSyncError(422, f"trace_id 已存在：{normalized_trace_id}")

    now = datetime.now()
    date_part = now.strftime("%Y%m%d")
    time_part = now.strftime("%H%M%S%f")
    file_name = f"{_safe_filename_part(normalized_trace_id)}_{time_part}.json"
    relative_path = f"/order_sync/{date_part}/{file_name}"
    file_path = _sync_root() / date_part / file_name
    file_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        file_path.write_text(raw_text, encoding="utf-8")
        record = OrderSync(
            trace_id=normalized_trace_id,
            file_path=relative_path,
            order_count=len(order_nos),
            order_nos=order_nos,
            project_count=len(project_infos),
            project_infos=project_infos,
            status="pending",
        )
        db.add(record)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        if file_path.exists():
            file_path.unlink()
        raise OrderSyncError(422, f"trace_id 已存在：{normalized_trace_id}") from exc
    except Exception:
        db.rollback()
        if file_path.exists():
            file_path.unlink()
        raise

    return {
        "total_orders": len(order_nos),
        "success_orders": order_nos,
        "failed_orders": [],
    }
