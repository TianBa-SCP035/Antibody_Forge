from datetime import date, datetime, timedelta
import secrets
import string
from typing import Any

from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.orm import Session

from utils.filter_values import (
    DEFAULT_RECORDED_TARGET_LIMIT,
    combine_any,
    like_contains,
    match_any,
    recorded_target_clause,
    recorded_target_search,
    split_code_tokens,
)
from models.types import date_blank, date_present
from utils.normalize import (
    join_known_options,
    join_tokens,
    normalize_choice,
    normalize_date,
    normalize_nonneg_int,
    normalize_positive_int,
    normalize_priority,
    normalize_target_codes,
    normalize_text,
)
from utils.header_filters import (
    HeaderColumn,
    column_values,
    csv_column,
    csv_token_clause,
    header_filter_clauses,
    header_sort_clauses,
    target_column,
)

from models.discovery import DiscoveryWorkbench
from modules.discovery.workbench.constants import (
    HARVEST_VIEW_STATUSES,
    LIBRARY_VIEW_STATUSES,
    MOUSE_STRAIN_CATEGORY_OPTIONS,
    MOUSE_STRAIN_OPTIONS,
    PLAN_STATUS_CANCELLED,
    PLAN_STATUS_OPTIONS,
    PLAN_STATUS_PLANNING,
    PLAN_STATUS_WAIT_BOOST,
    PLAN_STATUS_WAIT_HARVEST,
    PLAN_STATUS_WAIT_SEQ,
    SCREENING_METHOD_OPTIONS,
    TERMINAL_STATUSES,
    VIEW_GROUP_STATUSES,
)
from utils.workbench_queue import (
    DEFAULT_PRIORITY,
    PRIORITY_OPTIONS,
    PRIORITY_ORDER,
    apply_priority_constraints,
    list_order_clauses,
    lock_queue,
    place_row_among,
    queued_sort,
    renumber_queue,
)
from utils.clock import now_local, today_local
MISSING_ROW = "发现工作台记录不存在"
DISCOVERY_ID_PREFIX = "DSC"
DISCOVERY_ID_RANDOM_LEN = 6
DISCOVERY_ID_MAX_ATTEMPTS = 20
DISCOVERY_ID_ALPHABET = string.ascii_uppercase + string.digits
STRING_FIELDS = {
    "project_code": 64,
    "experiment_id": 64,
    "target_name": 128,
    "study_type": 64,
    "pm": 64,
    "owner": 64,
    "immune_owner": 64,
    "cell_collector": 64,
    "mouse_strain_category": 128,
    "mouse_strain": 128,
    "cage_position": 64,
    "mouse_nos": 1000,
    "serum_titer": 1000,
    "immune_antigen": 1000,
    "screening_antigen": 1000,
    "positive_cell_count": 64,
    "plate_nos": 1000,
    "boost_antigen": 1000,
    "boost_cells": 1000,
    "remark": 1000,
}
BREAK_FIELDS = frozenset({
    "mouse_nos",
    "plate_nos",
    "serum_titer",
    "positive_cell_count",
    "immune_antigen",
    "screening_antigen",
    "boost_antigen",
    "boost_cells",
    "remark",
})
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
    return today_local().isoformat()


def generate_discovery_id(now: datetime | None = None) -> str:
    stamp = (now or now_local()).strftime("%y%m%d")
    suffix = "".join(secrets.choice(DISCOVERY_ID_ALPHABET) for _ in range(DISCOVERY_ID_RANDOM_LEN))
    return f"{DISCOVERY_ID_PREFIX}-{stamp}-{suffix}"


def _next_discovery_id(db: Session) -> str:
    for _ in range(DISCOVERY_ID_MAX_ATTEMPTS):
        candidate = generate_discovery_id()
        exists = db.scalar(
            select(DiscoveryWorkbench.id).where(DiscoveryWorkbench.discovery_id == candidate)
        )
        if not exists:
            return candidate
    raise ValueError("无法分配发现安排号")


def _assign_discovery_id(db: Session, row: DiscoveryWorkbench) -> None:
    row.discovery_id = _next_discovery_id(db)


def _normalize_screening_methods(value: Any) -> str | None:
    return join_known_options(value, SCREENING_METHOD_OPTIONS, "筛选方式包含不允许的选项")


def _normalize_mouse_strain_category(value: Any) -> str | None:
    return join_tokens(value, MOUSE_STRAIN_CATEGORY_OPTIONS)


def _normalize_mouse_strain(value: Any) -> str | None:
    return join_tokens(value, MOUSE_STRAIN_OPTIONS)


def _shift_date(value: str | None, days: int) -> str | None:
    if not value:
        return None
    return (date.fromisoformat(value) + timedelta(days=days)).isoformat()


def _normalize_status(value: Any) -> str:
    return normalize_choice(value, PLAN_STATUS_OPTIONS, "状态", default=PLAN_STATUS_PLANNING)


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
    return max(page, 1), min(max(limit, 1), 500)


def _apply_fields(row: DiscoveryWorkbench, data: dict[str, Any]) -> bool:
    previous_harvest = row.harvest_date or None
    for field in WRITABLE_FIELDS:
        if field not in data:
            continue
        value = data.get(field)
        if field == "target_codes":
            value = normalize_target_codes(value)
        elif field == "screening_methods":
            value = _normalize_screening_methods(value)
        elif field == "mouse_strain_category":
            value = _normalize_mouse_strain_category(value)
        elif field == "mouse_strain":
            value = _normalize_mouse_strain(value)
        elif field == "mouse_count":
            value = normalize_nonneg_int(value, "小鼠只数")
        elif field == "sort_order":
            if value in (None, "", "-"):
                continue
            value = normalize_positive_int(value, "排序必须是正整数")
        elif field == "status":
            value = _normalize_status(value)
        elif field == "priority":
            value = normalize_priority(value)
        elif field in DATE_FIELDS:
            value = normalize_date(value)
        else:
            value = normalize_text(
                value,
                STRING_FIELDS[field],
                keep_breaks=field in BREAK_FIELDS,
            )
        setattr(row, field, value)
    harvest_changed = "harvest_date" in data and (row.harvest_date or None) != previous_harvest
    if harvest_changed:
        row.boost_date = _shift_date(row.harvest_date, -5)
    return harvest_changed


def _apply_status_from_dates(
    row: DiscoveryWorkbench,
    payload: dict[str, Any],
    harvest_changed: bool = False,
) -> None:
    status = _current_status(row)
    if _is_terminal(status):
        return
    today = _today_text()
    if ("boost_date" in payload or harvest_changed) and "status" not in payload:
        if _has_date_value(row.boost_date):
            if status in {PLAN_STATUS_PLANNING, PLAN_STATUS_WAIT_HARVEST, PLAN_STATUS_WAIT_BOOST}:
                row.status = PLAN_STATUS_WAIT_HARVEST if _boost_expired(row.boost_date, today) else PLAN_STATUS_WAIT_BOOST
        elif status == PLAN_STATUS_WAIT_BOOST:
            row.status = PLAN_STATUS_PLANNING
    if _current_status(row) == PLAN_STATUS_WAIT_BOOST and _boost_expired(row.boost_date, today):
        row.status = PLAN_STATUS_WAIT_HARVEST


def advance_expired_boosts(db: Session) -> int:
    rows = db.scalars(
        select(DiscoveryWorkbench).where(
            DiscoveryWorkbench.status == PLAN_STATUS_WAIT_BOOST,
            date_present(DiscoveryWorkbench.boost_date),
            DiscoveryWorkbench.boost_date < _today_text(),
        ).with_for_update()
    ).all()
    for row in rows:
        row.status = PLAN_STATUS_WAIT_HARVEST
    return len(rows)


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
    return combine_any(value, lambda text: like_contains(column, text))


def _apply_date_range(filters: list, column, data: dict[str, Any], start_key: str, end_key: str) -> None:
    start_raw = data.get(start_key)
    end_raw = data.get(end_key)
    if start_raw not in (None, ""):
        filters.append(column >= normalize_date(start_raw))
    if end_raw not in (None, ""):
        filters.append(column <= normalize_date(end_raw))


def _status_column():
    return func.coalesce(DiscoveryWorkbench.status, PLAN_STATUS_PLANNING)


def _status_filter_clause(status: str):
    if status not in PLAN_STATUS_OPTIONS:
        raise ValueError("状态不在允许的选项中")
    return _status_column() == status


def _view_group_filter(view_group: str):
    statuses = VIEW_GROUP_STATUSES.get(view_group)
    if not statuses:
        return None
    return _status_column().in_(tuple(statuses))


def _boosting_filter():
    today = _today_text()
    return and_(
        date_present(DiscoveryWorkbench.boost_date),
        DiscoveryWorkbench.boost_date >= today,
    )


def _missing_date_filter():
    return and_(
        or_(
            date_blank(DiscoveryWorkbench.harvest_date),
            date_blank(DiscoveryWorkbench.boost_date),
        ),
        ~_status_column().in_(tuple(TERMINAL_STATUSES)),
    )


_W = DiscoveryWorkbench
HEADER_COLUMNS: dict[str, HeaderColumn] = {
    "priority": HeaderColumn(_W.priority, "enum", order=tuple(PRIORITY_ORDER)),
    "status": HeaderColumn(_status_column(), "enum", order=tuple(PLAN_STATUS_OPTIONS)),
    "pm": HeaderColumn(_W.pm, "enum"),
    "project_code": HeaderColumn(_W.project_code),
    "experiment_id": HeaderColumn(_W.experiment_id),
    "target_name": target_column(_W.target_name, _W.target_codes),
    "study_type": HeaderColumn(_W.study_type, "enum"),
    "mouse_strain_category": csv_column(_W.mouse_strain_category, tuple(MOUSE_STRAIN_CATEGORY_OPTIONS)),
    "mouse_strain": csv_column(_W.mouse_strain, tuple(MOUSE_STRAIN_OPTIONS)),
    "screening_methods": csv_column(_W.screening_methods, tuple(SCREENING_METHOD_OPTIONS)),
    "mouse_count": HeaderColumn(_W.mouse_count, "number"),
    "harvest_date": HeaderColumn(_W.harvest_date, "date"),
    "boost_date": HeaderColumn(_W.boost_date, "date"),
    "owner": HeaderColumn(_W.owner, "enum"),
    "immune_owner": HeaderColumn(_W.immune_owner, "enum"),
    "cell_collector": HeaderColumn(_W.cell_collector, "enum"),
    "cage_position": HeaderColumn(_W.cage_position),
    "mouse_nos": HeaderColumn(_W.mouse_nos),
    "serum_titer": HeaderColumn(_W.serum_titer),
    "immune_antigen": HeaderColumn(_W.immune_antigen),
    "screening_antigen": HeaderColumn(_W.screening_antigen),
    "positive_cell_count": HeaderColumn(_W.positive_cell_count),
    "plate_nos": HeaderColumn(_W.plate_nos),
    "boost_antigen": HeaderColumn(_W.boost_antigen),
    "boost_cells": HeaderColumn(_W.boost_cells),
    "remark": HeaderColumn(_W.remark),
}


def _csv_filter(column, value: Any):
    tokens = _split_filter_tokens(value)
    if not tokens:
        return None
    return or_(*[csv_token_clause(column, token) for token in tokens])


def _apply_list_filters(
    stmt,
    data: dict[str, Any],
    *,
    apply_view: bool = True,
    apply_boost: bool = True,
    db: Session | None = None,
    header_except: str | None = None,
):
    filters = []
    kw_tokens = split_code_tokens(data.get("keyword"))
    if len(kw_tokens) == 1:
        like = f"%{kw_tokens[0]}%"
        filters.append(
            or_(
                DiscoveryWorkbench.discovery_id.like(like),
                DiscoveryWorkbench.project_code.like(like),
                DiscoveryWorkbench.experiment_id.like(like),
            )
        )
    elif len(kw_tokens) > 1:
        filters.append(
            or_(
                DiscoveryWorkbench.discovery_id.in_(kw_tokens),
                DiscoveryWorkbench.project_code.in_(kw_tokens),
                DiscoveryWorkbench.experiment_id.in_(kw_tokens),
            )
        )
    target_clause = recorded_target_clause(
        db,
        DiscoveryWorkbench.target_name,
        DiscoveryWorkbench.target_codes,
        data.get("target_name"),
        select(DiscoveryWorkbench.target_name, DiscoveryWorkbench.target_codes),
    )
    if target_clause is not None:
        filters.append(target_clause)
    remark = _contains_filter(DiscoveryWorkbench.remark, data.get("remark"))
    if remark is not None:
        filters.append(remark)
    for field in ("screening_methods", "mouse_strain_category", "mouse_strain"):
        csv_filter = _csv_filter(getattr(DiscoveryWorkbench, field), data.get(field))
        if csv_filter is not None:
            filters.append(csv_filter)
    pm = match_any(DiscoveryWorkbench.pm, data.get("pm"))
    if pm is not None:
        filters.append(pm)
    owner = match_any(DiscoveryWorkbench.owner, data.get("owner"))
    if owner is not None:
        filters.append(owner)
    immune_owner = match_any(DiscoveryWorkbench.immune_owner, data.get("immune_owner"))
    if immune_owner is not None:
        filters.append(immune_owner)
    cell_collector = match_any(DiscoveryWorkbench.cell_collector, data.get("cell_collector"))
    if cell_collector is not None:
        filters.append(cell_collector)
    study_type = match_any(DiscoveryWorkbench.study_type, data.get("study_type"))
    if study_type is not None:
        filters.append(study_type)
    status = combine_any(data.get("status"), _status_filter_clause)
    if status is not None:
        filters.append(status)
    priority = combine_any(
        data.get("priority"),
        lambda value: DiscoveryWorkbench.priority == normalize_priority(value),
    )
    if priority is not None:
        filters.append(priority)
    for field in (
        "cage_position",
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
    filters.extend(
        header_filter_clauses(db, HEADER_COLUMNS, data.get("field_filters"), except_field=header_except)
    )
    if apply_view:
        view_filter = _view_group_filter(str(data.get("view_group") or "").strip())
        if view_filter is not None:
            filters.append(view_filter)
    if apply_boost:
        boost_filter = str(data.get("boost_filter") or "").strip()
        if boost_filter == "boosting":
            filters.append(_boosting_filter())
        elif boost_filter == "missing_date":
            filters.append(_missing_date_filter())
        elif boost_filter:
            raise ValueError("日期快捷筛选不正确")
    if filters:
        return stmt.where(*filters)
    return stmt


def _list_order(data: dict[str, Any] | None = None):
    payload = data or {}
    field = str(payload.get("sort_field") or "").strip()
    spec = HEADER_COLUMNS.get(field)
    direction = str(payload.get("sort_dir") or "").strip()
    if spec is not None and direction in {"asc", "desc"}:
        return header_sort_clauses(spec, direction, DiscoveryWorkbench.id)
    return list_order_clauses(
        field,
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
    lock_queue(db, DiscoveryWorkbench)


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
            renumber_queue([item for item in _queue_rows(db) if int(item.id) != int(row.id or 0)])
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
            func.coalesce(func.sum(case((_missing_date_filter(), 1), else_=0)), 0),
        )
        .select_from(DiscoveryWorkbench)
        .group_by(status_col),
        payload,
        apply_view=False,
        apply_boost=False,
        db=db,
    )
    stats = {
        "all": 0,
        "harvest": 0,
        "library": 0,
        "sequencing": 0,
        "cancelled": 0,
        "boosting": 0,
        "missing_date": 0,
    }
    for status, count, boosting, missing_date in db.execute(stmt).all():
        n = int(count or 0)
        stats["all"] += n
        group = _view_group_for_status(status)
        if group:
            stats[group] += n
        stats["boosting"] += int(boosting or 0)
        stats["missing_date"] += int(missing_date or 0)
    return stats


def get_list(db: Session, data: dict[str, Any]) -> dict[str, Any]:
    payload = data or {}
    page, limit = _page_limit(payload)
    stmt = _apply_list_filters(select(DiscoveryWorkbench), payload, db=db)
    total = db.scalar(
        _apply_list_filters(select(func.count()).select_from(DiscoveryWorkbench), payload, db=db)
    ) or 0
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


def get_column_values(db: Session, data: dict[str, Any]) -> dict[str, Any]:
    """表头筛选的取值列表：套用除本列表头条件以外的全部筛选。顶部筛选里的本列条件由前端去掉。"""
    payload = data or {}
    field = str(payload.get("field") or "").strip()
    spec = HEADER_COLUMNS.get(field)
    if spec is None:
        raise ValueError(f"不支持按「{field}」表头筛选")
    return column_values(
        db,
        spec,
        lambda stmt: _apply_list_filters(stmt, payload, db=db, header_except=field),
        id_column=DiscoveryWorkbench.id,
        keyword=str(payload.get("value_keyword") or ""),
        limit=payload.get("value_limit"),
        order=str(payload.get("value_order") or "value"),
    )


# 抗原建议只取最近录入的行，开销固定；更早的冷门写法用户可直接手填
ANTIGEN_SUGGESTION_SCAN_ROWS = 5000


def _distinct_lines(db: Session, column) -> list[str]:
    result: set[str] = set()
    stmt = (
        select(column)
        .where(column.is_not(None), column != "")
        .order_by(DiscoveryWorkbench.id.desc())
        .limit(ANTIGEN_SUGGESTION_SCAN_ROWS)
    )
    for value in db.scalars(stmt).all():
        for part in str(value or "").splitlines():
            text = part.strip()
            if text:
                result.add(text)
    return sorted(result)


def search_recorded_targets(db: Session, keyword: str = "", limit: int = DEFAULT_RECORDED_TARGET_LIMIT) -> list[dict]:
    return recorded_target_search(
        db,
        select(DiscoveryWorkbench.target_name, DiscoveryWorkbench.target_codes),
        keyword,
        limit,
    )


def get_options(db: Session) -> dict[str, Any]:
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
        "priorities": list(PRIORITY_OPTIONS),
        "mouse_strain_categories": list(MOUSE_STRAIN_CATEGORY_OPTIONS),
        "mouse_strains": list(MOUSE_STRAIN_OPTIONS),
        "pms": values(DiscoveryWorkbench.pm),
        "owners": values(DiscoveryWorkbench.owner),
        "immune_owners": values(DiscoveryWorkbench.immune_owner),
        "cell_collectors": values(DiscoveryWorkbench.cell_collector),
        "immune_antigens": _distinct_lines(db, DiscoveryWorkbench.immune_antigen),
        "screening_antigens": _distinct_lines(db, DiscoveryWorkbench.screening_antigen),
        "boost_antigens": _distinct_lines(db, DiscoveryWorkbench.boost_antigen),
    }


def save(
    db: Session,
    data: dict[str, Any],
    created_by: str | None = None,
    *,
    commit: bool = True,
) -> dict[str, Any]:
    payload = dict(data or {})
    payload.pop("discovery_id", None)
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
        _assign_discovery_id(db, row)
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
    harvest_changed = _apply_fields(row, payload)
    _apply_status_from_dates(row, payload, harvest_changed)
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


def delete(db: Session, row_id: int) -> None:
    _lock_queue(db)
    row = db.get(DiscoveryWorkbench, int(row_id))
    if not row:
        raise ValueError(MISSING_ROW)
    from modules.molecular_cell.library_orders.service import has_orders_for_discovery

    if has_orders_for_discovery(db, row.discovery_id):
        raise ValueError("该安排已有建库工单，不能删除")
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
    ("免疫负责人", "immune_owner"),
    ("细胞收集人", "cell_collector"),
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
    ("冲击免细胞", "boost_cells"),
    ("备注", "remark"),
    ("创建人", "created_by"),
)


def export_list_workbook(db: Session, data: dict[str, Any]):
    from utils.excel import build_list_workbook, cell_text

    payload = data or {}
    rows = db.scalars(
        _apply_list_filters(select(DiscoveryWorkbench), payload, db=db).order_by(*_list_order(payload))
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
