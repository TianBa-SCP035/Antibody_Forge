"""抗体发现留存细胞冻存：挂在发现安排上，记录入库管数和位置。"""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.errors import NotFoundError
from models.discovery import DiscoveryCellBank, DiscoveryWorkbench
from utils.clock import today_local
from utils.normalize import normalize_date

_TEXT_LIMITS = {
    "cell_kind": 32,
    "mouse_nos": 1000,
    "cell_count": 64,
    "volume": 64,
    "box_location": 128,
    "operator": 64,
    "checked_out_by": 64,
    "remark": 500,
}


def _text(value: Any, key: str, *, required: bool = False) -> str | None:
    text = "" if value is None else str(value).strip()
    if required and not text:
        raise ValueError("请填写细胞类型")
    limit = _TEXT_LIMITS[key]
    if len(text) > limit:
        raise ValueError(f"内容超过 {limit} 个字符")
    return text or None


def _tube_count(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        number = int(value)
    except (TypeError, ValueError):
        raise ValueError("管数必须是整数") from None
    if number < 0 or number > 9999:
        raise ValueError("管数需在 0 到 9999 之间")
    return number


def _workbench(db: Session, workbench_id: int) -> DiscoveryWorkbench:
    row = db.get(DiscoveryWorkbench, workbench_id)
    if not row:
        raise NotFoundError("发现安排不存在")
    return row


def list_records(db: Session, workbench_id: int) -> dict[str, Any]:
    _workbench(db, workbench_id)
    rows = db.scalars(
        select(DiscoveryCellBank)
        .where(DiscoveryCellBank.workbench_id == workbench_id)
        .order_by(DiscoveryCellBank.id.desc())
    ).all()
    return {"items": [row.to_dict() for row in rows]}


def save_record(db: Session, data: dict[str, Any], created_by: str | None = None) -> dict[str, Any]:
    workbench_id = int(data.get("workbench_id") or 0)
    workbench = _workbench(db, workbench_id)
    record_id = data.get("id")
    if record_id:
        row = db.get(DiscoveryCellBank, int(record_id))
        if not row or row.workbench_id != workbench.id:
            raise NotFoundError("冻存记录不存在")
    else:
        row = DiscoveryCellBank(workbench_id=workbench.id, cell_kind="脾细胞")
        row.created_by = (created_by or "").strip() or None
        db.add(row)
    row.discovery_id = workbench.discovery_id
    row.cell_kind = _text(data.get("cell_kind"), "cell_kind", required=True) or "脾细胞"
    row.mouse_nos = _text(data.get("mouse_nos"), "mouse_nos")
    row.tube_count = _tube_count(data.get("tube_count"))
    row.cell_count = _text(data.get("cell_count"), "cell_count")
    row.volume = _text(data.get("volume"), "volume")
    row.box_location = _text(data.get("box_location"), "box_location")
    row.frozen_on = normalize_date(data.get("frozen_on"))
    row.operator = _text(data.get("operator"), "operator")
    row.remark = _text(data.get("remark"), "remark")
    db.commit()
    db.refresh(row)
    return row.to_dict()


def checkout_record(db: Session, record_id: int, checked_out_by: Any) -> dict[str, Any]:
    row = db.get(DiscoveryCellBank, record_id)
    if not row:
        raise NotFoundError("冻存记录不存在")
    name = _text(checked_out_by, "checked_out_by")
    if not name:
        raise ValueError("请填写出库人")
    row.checked_out_by = name
    row.checked_out_on = today_local().isoformat()
    db.commit()
    db.refresh(row)
    return row.to_dict()


def delete_record(db: Session, record_id: int) -> None:
    row = db.get(DiscoveryCellBank, record_id)
    if not row:
        raise NotFoundError("冻存记录不存在")
    db.delete(row)
    db.commit()
