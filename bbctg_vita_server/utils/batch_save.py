from collections.abc import Collection, Iterable, Mapping
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.errors import ConflictError, NotFoundError
from utils.model_fields import SORT_FIELD
from utils.normalize import parse_row_id

CONFLICT_MESSAGE = "记录已被其他用户修改，请按最新内容重新填写"


def parse_batch_items(
    raw_items: Any,
    *,
    invalid_id_message: str,
    duplicate_message: str,
    require_id: bool = False,
    allow_empty: bool = True,
    empty_message: str = "批量保存数据格式不正确",
    max_items: int | None = None,
    too_many_message: str | None = None,
) -> tuple[list[dict[str, Any]], list[int]]:
    if not isinstance(raw_items, list):
        raise ValueError("批量保存数据格式不正确")
    if not allow_empty and not raw_items:
        raise ValueError(empty_message)
    if max_items is not None and len(raw_items) > max_items:
        raise ValueError(too_many_message or f"单次最多保存 {max_items} 条记录")
    if any(not isinstance(item, dict) for item in raw_items):
        raise ValueError("批量保存行数据格式不正确")

    items = [dict(item) for item in raw_items]
    row_ids: list[int] = []
    seen_ids: set[int] = set()
    for item in items:
        supplied_id = item.get("id")
        row_id = parse_row_id(supplied_id)
        if require_id:
            if row_id is None:
                raise ValueError(invalid_id_message)
        elif supplied_id not in (None, "") and row_id is None:
            raise ValueError(invalid_id_message)
        if row_id is not None:
            if row_id in seen_ids:
                raise ValueError(duplicate_message)
            seen_ids.add(row_id)
            row_ids.append(row_id)
    return items, row_ids


def lock_rows_by_id(
    db: Session,
    model: Any,
    row_ids: Iterable[int],
    *,
    missing_message: str,
) -> dict[int, Any]:
    unique_ids = sorted({int(row_id) for row_id in row_ids})
    if not unique_ids:
        return {}
    rows = db.scalars(
        select(model)
        .where(model.id.in_(unique_ids))
        .order_by(model.id.asc())
        .with_for_update()
    ).all()
    rows_by_id = {int(row.id): row for row in rows}
    if len(rows_by_id) != len(unique_ids):
        raise NotFoundError(missing_message)
    return rows_by_id


def normalize_comparable(value: Any) -> Any:
    """去掉格式差异：None、空串、空列表相同；字符串去首尾空白；数字按文字比（5 与 5.0 相同）；列表去重保序。"""
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, (int, float, Decimal)):
        return format(Decimal(str(value)).normalize(), "f")
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, (list, tuple)):
        items: list[Any] = []
        for item in (normalize_comparable(item) for item in value):
            if item is not None and item not in items:
                items.append(item)
        return items or None
    if isinstance(value, str):
        return value.strip() or None
    return value


def check_expected(
    current: Mapping[str, Any],
    expected: Any,
    *,
    fields: Collection[str],
) -> None:
    """current 是该行按列表接口序列化的当前值，expected 是前端拿到的旧值；只比可写字段。

    排序值不比：别人调整队列会顺带改动其他行的排序值，这不算冲突。
    """
    if not isinstance(expected, Mapping) or not expected:
        return
    for field, expected_value in expected.items():
        if field not in fields or field == SORT_FIELD:
            continue
        if normalize_comparable(current.get(field)) != normalize_comparable(expected_value):
            raise ConflictError(CONFLICT_MESSAGE)
