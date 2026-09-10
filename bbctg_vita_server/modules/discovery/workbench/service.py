from datetime import date, datetime
from typing import Any

from sqlalchemy import String, and_, case, cast, func, or_, select, update
from sqlalchemy.orm import Session

from models.discovery import DiscoveryWorkbench
from utils.workbench_queue import (
    DEFAULT_PRIORITY,
    PRIORITY_ORDER,
    apply_priority_constraints,
    canonicalize_priority,
    list_order_clauses,
    place_row_among,
    queued_sort,
    renumber_queue,
)

SCREENING_METHOD_OPTIONS = ("达普", "噬菌体", "Beacon")
PLAN_STATUS_PLANNING = "规划中"
PLAN_STATUS_WAIT_BOOST = "待冲击"
PLAN_STATUS_WAIT_HARVEST = "待剖鼠"
PLAN_STATUS_WAIT_LIBRARY = "待建库"
PLAN_STATUS_WAIT_PHAGE = "待噬菌体"
PLAN_STATUS_WAIT_SEQ = "待测序"
PLAN_STATUS_DONE = "已完成"
PLAN_STATUS_CANCELLED = "已取消"
PLAN_STATUS_OPTIONS = (
    PLAN_STATUS_PLANNING,
    PLAN_STATUS_WAIT_BOOST,
    PLAN_STATUS_WAIT_HARVEST,
    PLAN_STATUS_WAIT_LIBRARY,
    PLAN_STATUS_WAIT_PHAGE,
    PLAN_STATUS_WAIT_SEQ,
    PLAN_STATUS_DONE,
    PLAN_STATUS_CANCELLED,
)
TERMINAL_STATUSES = frozenset({PLAN_STATUS_DONE, PLAN_STATUS_CANCELLED})
HARVEST_VIEW_STATUSES = frozenset({PLAN_STATUS_PLANNING, PLAN_STATUS_WAIT_BOOST, PLAN_STATUS_WAIT_HARVEST})
LIBRARY_VIEW_STATUSES = frozenset({PLAN_STATUS_WAIT_LIBRARY, PLAN_STATUS_WAIT_PHAGE})
VIEW_GROUP_STATUSES = {
    "harvest": HARVEST_VIEW_STATUSES,
    "library": LIBRARY_VIEW_STATUSES,
    "sequencing": frozenset({PLAN_STATUS_WAIT_SEQ}),
    "cancelled": frozenset({PLAN_STATUS_CANCELLED}),
}
COPY_CLEAR_FIELDS = ("harvest_date", "boost_date", "boost_antigen")
MISSING_ROW = "发现工作台记录不存在"
STRING_FIELDS = {
    "project_code": 64,
    "experiment_id": 64,
    "target_name": 128,
    "study_type": 64,
    "pm": 64,
    "owner": 64,
    "mouse_strain_category": 128,
    "mouse_strain": 128,
    "cage_position": 64,
    "mouse_nos": 512,
    "serum_titer": 255,
    "immune_antigen": 255,
    "screening_antigen": 255,
    "positive_cell_count": 64,
    "plate_nos": 512,
    "boost_antigen": 255,
    "remark": 500,
}
DATE_FIELDS = ("harvest_date", "boost_date")
WRITABLE_FIELDS = (
    *STRING_FIELDS,
    "target_codes",
    "screening_methods",
    "mouse_count",
    *DATE_FIELDS,
    "status",
    "priority",
    "sort_order",
)


def _today_text() -> str:
    return date.today().isoformat()


def _normalize_csv_options(value: Any, options: tuple[str, ...], error: str) -> str | None:
    if value is None:
        return None
    if isinstance(value, (list, tuple)):
        tokens = [str(item).strip() for item in value if str(item).strip()]
    else:
        text = str(value).strip()
        if not text:
            return None
        tokens = [part.strip() for part in text.replace("，", ",").split(",") if part.strip()]
    allowed = set(options)
    if any(token not in allowed for token in tokens):
        raise ValueError(error)
    ordered = [option for option in options if option in tokens]
    return ",".join(ordered) or None


def _normalize_screening_methods(value: Any) -> str | None:
    return _normalize_csv_options(value, SCREENING_METHOD_OPTIONS, "筛选方式包含不允许的选项")


def _normalize_target_codes(value: Any) -> list[str]:
    if value is None or value == "":
        return []
    if isinstance(value, str):
        return [part.strip() for part in value.replace("，", ",").split(",") if part.strip()]
    if not isinstance(value, list):
        raise ValueError("靶点编号必须是数组")
    return [str(item).strip() for item in value if str(item).strip()]


def _normalize_date(value: Any) -> str | None:
    if value in (None, ""):
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        datetime.strptime(text, "%Y-%m-%d")
    except ValueError as exc:
        raise ValueError("日期必须是 YYYY-MM-DD") from exc
    return text


def _normalize_nonneg_int(value: Any, label: str) -> int | None:
    if value in (None, ""):
        return None
    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label}必须是整数") from exc
    if number < 0:
        raise ValueError(f"{label}不能为负数")
    return number


def _normalize_mouse_count(value: Any) -> int | None:
    return _normalize_nonneg_int(value, "小鼠只数")


def _normalize_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _normalize_text(value: Any, max_len: int) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if len(text) > max_len:
        raise ValueError(f"字段长度不能超过 {max_len}")
    return text


def _normalize_status(value: Any) -> str:
    text = str(value or "").strip() or PLAN_STATUS_PLANNING
    if text not in PLAN_STATUS_OPTIONS:
        raise ValueError("状态不在允许的选项中")
    return text


def _normalize_priority(value: Any) -> str:
    text = canonicalize_priority(value)
    if text not in PRIORITY_ORDER:
        raise ValueError("优先级不在允许的选项中")
    return text


def _normalize_sort_order(value: Any) -> int:
    number = _normalize_int(value)
    if number is None or number <= 0:
        raise ValueError("排序必须是正整数")
    return number


def _current_status(row: DiscoveryWorkbench) -> str:
    return str(row.status or "").strip() or PLAN_STATUS_PLANNING


def _is_terminal(status: str) -> bool:
    return status in TERMINAL_STATUSES


def _has_date_value(value: Any) -> bool:
    return bool(str(value or "").strip())


def _boost_active(boost_date: Any, today: str | None = None) -> bool:
    text = str(boost_date or "").strip()
    if not text:
        return False
    return text >= (today or _today_text())


def _boost_expired(boost_date: Any, today: str | None = None) -> bool:
    text = str(boost_date or "").strip()
    if not text:
        return False
    return text < (today or _today_text())


def _csv_token_filter(column, value: str):
    return or_(
        column == value,
        column.like(f"{value},%"),
        column.like(f"%,{value}"),
        column.like(f"%,{value},%"),
    )


def _split_filter_tokens(value: Any) -> list[str]:
    if value is None or value == "":
        return []
    if isinstance(value, (list, tuple)):
        return [str(item).strip() for item in value if str(item).strip()]
    return [part.strip() for part in str(value).replace("，", ",").split(",") if part.strip()]


def _parse_row_id(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        row_id = int(value)
    except (TypeError, ValueError):
        return None
    if row_id <= 0:
        return None
    return row_id


def _page_limit(data: dict[str, Any]) -> tuple[int, int]:
    try:
        page = int(data.get("page", 1) or 1)
    except (TypeError, ValueError):
        page = 1
    try:
        limit = int(data.get("limit", 20) or 20)
    except (TypeError, ValueError):
        limit = 20
    return max(page, 1), min(max(limit, 1), 200)


def _apply_fields(row: DiscoveryWorkbench, data: dict[str, Any]) -> None:
    for field in WRITABLE_FIELDS:
        if field not in data:
            continue
        value = data.get(field)
        if field == "target_codes":
            value = _normalize_target_codes(value)
        elif field == "screening_methods":
            value = _normalize_screening_methods(value)
        elif field == "mouse_count":
            value = _normalize_mouse_count(value)
        elif field == "sort_order":
            if value in (None, "", "-"):
                continue
            value = _normalize_sort_order(value)
        elif field == "status":
            value = _normalize_status(value)
        elif field == "priority":
            value = _normalize_priority(value)
        elif field in DATE_FIELDS:
            value = _normalize_date(value)
        else:
            value = _normalize_text(value, STRING_FIELDS[field])
        setattr(row, field, value)


def _apply_status_from_dates(row: DiscoveryWorkbench, payload: dict[str, Any]) -> None:
    status = _current_status(row)
    if _is_terminal(status):
        return
    today = _today_text()
    if "boost_date" in payload and "status" not in payload:
        if _has_date_value(row.boost_date):
            if status in {PLAN_STATUS_PLANNING, PLAN_STATUS_WAIT_HARVEST, PLAN_STATUS_WAIT_BOOST}:
                row.status = PLAN_STATUS_WAIT_HARVEST if _boost_expired(row.boost_date, today) else PLAN_STATUS_WAIT_BOOST
        elif status == PLAN_STATUS_WAIT_BOOST:
            row.status = PLAN_STATUS_PLANNING
    if _current_status(row) == PLAN_STATUS_WAIT_BOOST and _boost_expired(row.boost_date, today):
        row.status = PLAN_STATUS_WAIT_HARVEST


def _advance_expired_boosts(db: Session) -> None:
    result = db.execute(
        update(DiscoveryWorkbench)
        .where(
            DiscoveryWorkbench.status == PLAN_STATUS_WAIT_BOOST,
            DiscoveryWorkbench.boost_date.is_not(None),
            DiscoveryWorkbench.boost_date != "",
            DiscoveryWorkbench.boost_date < _today_text(),
        )
        .values(status=PLAN_STATUS_WAIT_HARVEST)
    )
    if result.rowcount:
        db.commit()


def _view_group_for_status(status: str) -> str | None:
    text = str(status or "").strip() or PLAN_STATUS_PLANNING
    if text in HARVEST_VIEW_STATUSES:
        return "harvest"
    if text in LIBRARY_VIEW_STATUSES:
        return "library"
    if text == PLAN_STATUS_WAIT_SEQ:
        return "sequencing"
    if text == PLAN_STATUS_CANCELLED:
        return "cancelled"
    return None


def _contains_filter(column, value: Any):
    text = str(value or "").strip()
    if not text:
        return None
    return column.like(f"%{text}%")


def _apply_date_range(filters: list, column, data: dict[str, Any], start_key: str, end_key: str) -> None:
    start_raw = data.get(start_key)
    end_raw = data.get(end_key)
    if start_raw not in (None, ""):
        filters.append(column >= _normalize_date(start_raw))
    if end_raw not in (None, ""):
        filters.append(column <= _normalize_date(end_raw))


def _status_column():
    return func.coalesce(DiscoveryWorkbench.status, PLAN_STATUS_PLANNING)


def _view_group_filter(view_group: str):
    statuses = VIEW_GROUP_STATUSES.get(view_group)
    if not statuses:
        return None
    return _status_column().in_(tuple(statuses))


def _boosting_filter():
    today = _today_text()
    return and_(
        DiscoveryWorkbench.boost_date.is_not(None),
        DiscoveryWorkbench.boost_date != "",
        DiscoveryWorkbench.boost_date >= today,
    )


def _need_boost_filter():
    return and_(
        DiscoveryWorkbench.harvest_date.is_not(None),
        DiscoveryWorkbench.harvest_date != "",
        or_(DiscoveryWorkbench.boost_date.is_(None), DiscoveryWorkbench.boost_date == ""),
        ~_status_column().in_(tuple(TERMINAL_STATUSES)),
    )


def _apply_list_filters(stmt, data: dict[str, Any], *, apply_view: bool = True, apply_boost: bool = True):
    filters = []
    keyword = str(data.get("keyword") or "").strip()
    if keyword:
        like = f"%{keyword}%"
        filters.append(
            or_(
                DiscoveryWorkbench.project_code.like(like),
                DiscoveryWorkbench.experiment_id.like(like),
                DiscoveryWorkbench.target_name.like(like),
                DiscoveryWorkbench.pm.like(like),
                DiscoveryWorkbench.owner.like(like),
                DiscoveryWorkbench.remark.like(like),
                cast(DiscoveryWorkbench.target_codes, String).like(like),
            )
        )
    methods = _split_filter_tokens(data.get("screening_methods"))
    if methods:
        if any(token not in SCREENING_METHOD_OPTIONS for token in methods):
            raise ValueError("筛选方式包含不允许的选项")
        filters.append(
            or_(*[_csv_token_filter(DiscoveryWorkbench.screening_methods, method) for method in methods])
        )
    pm = str(data.get("pm") or "").strip()
    if pm:
        filters.append(DiscoveryWorkbench.pm == pm)
    owner = str(data.get("owner") or "").strip()
    if owner:
        filters.append(DiscoveryWorkbench.owner == owner)
    study_type = str(data.get("study_type") or "").strip()
    if study_type:
        filters.append(DiscoveryWorkbench.study_type == study_type)
    status = str(data.get("status") or "").strip()
    if status:
        if status not in PLAN_STATUS_OPTIONS:
            raise ValueError("状态不在允许的选项中")
        filters.append(_status_column() == status)
    priority = str(data.get("priority") or "").strip()
    if priority:
        filters.append(DiscoveryWorkbench.priority == _normalize_priority(priority))
    for field in (
        "cage_position",
        "mouse_strain",
        "mouse_strain_category",
        "mouse_nos",
        "immune_antigen",
        "screening_antigen",
        "plate_nos",
        "boost_antigen",
    ):
        contains = _contains_filter(getattr(DiscoveryWorkbench, field), data.get(field))
        if contains is not None:
            filters.append(contains)
    _apply_date_range(
        filters,
        DiscoveryWorkbench.harvest_date,
        data,
        "harvest_date_start",
        "harvest_date_end",
    )
    _apply_date_range(
        filters,
        DiscoveryWorkbench.boost_date,
        data,
        "boost_date_start",
        "boost_date_end",
    )
    if apply_view:
        view_filter = _view_group_filter(str(data.get("view_group") or "").strip())
        if view_filter is not None:
            filters.append(view_filter)
    if apply_boost:
        boost_filter = str(data.get("boost_filter") or "").strip()
        if boost_filter == "boosting":
            filters.append(_boosting_filter())
        elif boost_filter == "need_boost":
            filters.append(_need_boost_filter())
        elif boost_filter:
            raise ValueError("冲击免筛选不正确")
    if filters:
        return stmt.where(*filters)
    return stmt


def _list_order(data: dict[str, Any] | None = None):
    return list_order_clauses(
        (data or {}).get("sort_field"),
        DiscoveryWorkbench.sort_order,
        DiscoveryWorkbench.id,
    )


def _queue_rows(db: Session) -> list[DiscoveryWorkbench]:
    status = func.coalesce(DiscoveryWorkbench.status, PLAN_STATUS_PLANNING)
    return list(
        db.scalars(
            select(DiscoveryWorkbench)
            .where(status.notin_(TERMINAL_STATUSES))
            .order_by(DiscoveryWorkbench.sort_order.asc(), DiscoveryWorkbench.id.asc())
        ).all()
    )


def _lock_queue(db: Session) -> None:
    db.scalars(
        select(DiscoveryWorkbench.id)
        .order_by(DiscoveryWorkbench.id.asc())
        .with_for_update()
    ).all()


def _place_row(db: Session, row: DiscoveryWorkbench, *, mode: str, target_sort: int | None = None) -> None:
    if not getattr(row, "id", None):
        db.flush()
    others = [item for item in _queue_rows(db) if int(item.id) != int(row.id)]
    place_row_among(others, row, mode=mode, target_sort=target_sort)


def _apply_queue(
    db: Session,
    row: DiscoveryWorkbench,
    *,
    previous_sort: int | None,
    previous_priority: Any,
    payload: dict[str, Any],
    is_new: bool,
) -> None:
    if _is_terminal(_current_status(row)):
        leaving = queued_sort(previous_sort) is not None or queued_sort(row.sort_order) is not None
        row.sort_order = None
        if leaving:
            renumber_queue(_queue_rows(db))
        return
    if is_new or queued_sort(previous_sort) is None:
        target = queued_sort(payload.get("sort_order"))
        _place_row(db, row, mode="snap" if target else "last", target_sort=target)
        return
    apply_priority_constraints(
        row,
        previous_sort=previous_sort,
        previous_priority=previous_priority,
        place=lambda mode, target_sort=None: _place_row(db, row, mode=mode, target_sort=target_sort),
    )


def _list_stats(db: Session, payload: dict[str, Any]) -> dict[str, int]:
    status_col = _status_column()
    stmt = _apply_list_filters(
        select(
            status_col,
            func.count(),
            func.coalesce(func.sum(case((_boosting_filter(), 1), else_=0)), 0),
            func.coalesce(func.sum(case((_need_boost_filter(), 1), else_=0)), 0),
        )
        .select_from(DiscoveryWorkbench)
        .group_by(status_col),
        payload,
        apply_view=False,
        apply_boost=False,
    )
    stats = {
        "all": 0,
        "harvest": 0,
        "library": 0,
        "sequencing": 0,
        "cancelled": 0,
        "boosting": 0,
        "need_boost": 0,
    }
    for status, count, boosting, need_boost in db.execute(stmt).all():
        n = int(count or 0)
        stats["all"] += n
        group = _view_group_for_status(status)
        if group:
            stats[group] += n
        stats["boosting"] += int(boosting or 0)
        stats["need_boost"] += int(need_boost or 0)
    return stats


def get_list(db: Session, data: dict[str, Any]) -> dict[str, Any]:
    _advance_expired_boosts(db)
    payload = data or {}
    page, limit = _page_limit(payload)
    stmt = _apply_list_filters(select(DiscoveryWorkbench), payload)
    total = db.scalar(_apply_list_filters(select(func.count()).select_from(DiscoveryWorkbench), payload)) or 0
    rows = db.scalars(
        stmt.order_by(*_list_order(payload))
        .offset((page - 1) * limit)
        .limit(limit)
    ).all()
    return {
        "items": [row.to_dict() for row in rows],
        "total": total,
        "page": page,
        "limit": limit,
        "stats": _list_stats(db, payload),
    }


def get_options(db: Session) -> dict[str, list[str]]:
    def values(*columns) -> list[str]:
        result: set[str] = set()
        for column in columns:
            for value in db.scalars(select(column).where(column.is_not(None)).distinct()).all():
                text = str(value or "").strip()
                if text:
                    result.add(text)
        return sorted(result)

    return {
        "screening_methods": list(SCREENING_METHOD_OPTIONS),
        "statuses": list(PLAN_STATUS_OPTIONS),
        "priorities": list(PRIORITY_ORDER),
        "pms": values(DiscoveryWorkbench.pm),
        "owners": values(DiscoveryWorkbench.owner),
        "immune_antigens": values(DiscoveryWorkbench.immune_antigen),
        "screening_antigens": values(DiscoveryWorkbench.screening_antigen),
        "boost_antigens": values(DiscoveryWorkbench.boost_antigen),
    }


def save(
    db: Session,
    data: dict[str, Any],
    created_by: str | None = None,
    *,
    commit: bool = True,
) -> dict[str, Any]:
    payload = dict(data or {})
    row_id = _parse_row_id(payload.get("id"))
    if payload.get("id") not in (None, "") and row_id is None:
        raise ValueError("工作台记录 ID 不正确")
    if row_id is None or "sort_order" in payload or "priority" in payload or "status" in payload:
        _lock_queue(db)
    if row_id is None:
        row = DiscoveryWorkbench(
            created_by=(created_by or "").strip() or None,
            status=PLAN_STATUS_PLANNING,
            priority=DEFAULT_PRIORITY,
            sort_order=None,
        )
        db.add(row)
        db.flush()
        is_new = True
        previous_sort = None
        previous_priority = DEFAULT_PRIORITY
    else:
        row = db.get(DiscoveryWorkbench, row_id)
        if not row:
            raise ValueError(MISSING_ROW)
        is_new = False
        previous_sort = queued_sort(row.sort_order)
        previous_priority = row.priority
    _apply_fields(row, payload)
    _apply_status_from_dates(row, payload)
    _apply_queue(
        db,
        row,
        previous_sort=previous_sort,
        previous_priority=previous_priority,
        payload=payload,
        is_new=is_new,
    )
    if commit:
        db.commit()
        db.refresh(row)
    else:
        db.flush()
    return row.to_dict()


def save_batch(
    db: Session,
    data: dict[str, Any],
    created_by: str | None = None,
) -> dict[str, Any]:
    raw_items = data.get("items") or []
    if not isinstance(raw_items, list):
        raise ValueError("批量保存数据格式不正确")
    if any(not isinstance(item, dict) for item in raw_items):
        raise ValueError("批量保存行数据格式不正确")
    items = [dict(item) for item in raw_items]
    row_ids: list[int] = []
    needs_lock = False
    for item in items:
        supplied_id = item.get("id")
        row_id = _parse_row_id(supplied_id)
        if supplied_id not in (None, "") and row_id is None:
            raise ValueError("工作台记录 ID 不正确")
        if row_id is not None:
            row_ids.append(row_id)
        if row_id is None or "sort_order" in item or "priority" in item or "status" in item:
            needs_lock = True
    if len(row_ids) != len(set(row_ids)):
        raise ValueError("批量保存包含重复的工作台记录")
    if needs_lock:
        _lock_queue(db)
    saved_ids = [
        int(save(db, item, created_by, commit=False)["id"])
        for item in items
    ]
    db.commit()
    saved = []
    for row_id in saved_ids:
        row = db.get(DiscoveryWorkbench, row_id)
        if row:
            saved.append(row.to_dict())
    return {"items": saved}


def copy_row(db: Session, row_id: int, created_by: str | None = None) -> dict[str, Any]:
    source = db.get(DiscoveryWorkbench, int(row_id))
    if not source:
        raise ValueError(MISSING_ROW)
    payload = {
        field: getattr(source, field)
        for field in WRITABLE_FIELDS
        if field not in COPY_CLEAR_FIELDS and field != "sort_order"
    }
    if isinstance(payload.get("target_codes"), list):
        payload["target_codes"] = list(payload["target_codes"])
    payload["status"] = PLAN_STATUS_PLANNING
    payload["priority"] = DEFAULT_PRIORITY
    _lock_queue(db)
    row = DiscoveryWorkbench(
        created_by=(created_by or "").strip() or None,
        status=PLAN_STATUS_PLANNING,
        priority=DEFAULT_PRIORITY,
        sort_order=None,
    )
    db.add(row)
    db.flush()
    _apply_fields(row, payload)
    _apply_queue(
        db,
        row,
        previous_sort=None,
        previous_priority=DEFAULT_PRIORITY,
        payload={},
        is_new=True,
    )
    db.commit()
    db.refresh(row)
    return row.to_dict()


def delete(db: Session, row_id: int) -> None:
    _lock_queue(db)
    row = db.get(DiscoveryWorkbench, int(row_id))
    if not row:
        raise ValueError(MISSING_ROW)
    db.delete(row)
    db.flush()
    renumber_queue(_queue_rows(db))
    db.commit()


def reorder(db: Session, moved_id: Any, target_id: Any) -> dict[str, Any]:
    _lock_queue(db)
    parsed_moved_id = _parse_row_id(moved_id)
    parsed_target_id = _parse_row_id(target_id)
    if parsed_moved_id is None or parsed_target_id is None:
        raise ValueError("排序记录 ID 不正确")
    moved = db.get(DiscoveryWorkbench, parsed_moved_id)
    target = db.get(DiscoveryWorkbench, parsed_target_id)
    if not moved or not target:
        raise ValueError(MISSING_ROW)
    if parsed_moved_id == parsed_target_id:
        return {"items": [moved.to_dict()]}
    for row in (moved, target):
        if _is_terminal(_current_status(row)) or queued_sort(row.sort_order) is None:
            raise ValueError("终态记录不参与排序")
    _place_row(db, moved, mode="snap", target_sort=queued_sort(target.sort_order))
    db.commit()
    return {"items": [moved.to_dict(), target.to_dict()]}


EXPORT_COLUMNS = (
    ("排序", "sort_order"),
    ("优先级", "priority"),
    ("状态", "status"),
    ("项目编号", "project_code"),
    ("实验号", "experiment_id"),
    ("靶点名称", "target_name"),
    ("靶点编号", "target_codes"),
    ("课题类型", "study_type"),
    ("PM", "pm"),
    ("负责人", "owner"),
    ("归类鼠型", "mouse_strain_category"),
    ("小鼠品系", "mouse_strain"),
    ("笼位", "cage_position"),
    ("只数", "mouse_count"),
    ("鼠号", "mouse_nos"),
    ("血清效价", "serum_titer"),
    ("免疫用抗原", "immune_antigen"),
    ("筛选方式", "screening_methods"),
    ("筛选抗原", "screening_antigen"),
    ("阳性细胞数", "positive_cell_count"),
    ("板号", "plate_nos"),
    ("剖鼠日期", "harvest_date"),
    ("冲击日期", "boost_date"),
    ("冲击免抗原", "boost_antigen"),
    ("备注", "remark"),
    ("创建人", "created_by"),
)


def export_list_workbook(db: Session, data: dict[str, Any]):
    from utils.excel import build_list_workbook, cell_text

    _advance_expired_boosts(db)
    payload = data or {}
    rows = db.scalars(
        _apply_list_filters(select(DiscoveryWorkbench), payload).order_by(*_list_order(payload))
    ).all()
    items = [row.to_dict() for row in rows]
    table_rows = [
        [cell_text(item.get(key)) for _, key in EXPORT_COLUMNS]
        for item in items
    ]
    return build_list_workbook(
        sheet_title="发现工作台",
        filename_prefix="发现工作台",
        headers=[label for label, _ in EXPORT_COLUMNS],
        rows=table_rows,
    )
