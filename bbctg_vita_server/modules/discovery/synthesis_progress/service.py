from __future__ import annotations

from datetime import datetime
from io import BytesIO
import logging
import secrets
import string
from typing import Any

from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.orm import Session

from models.discovery import DiscoverySynthesisOrder
from models.target import Target
from modules.discovery.synthesis_progress.constants import (
    ACTIVE_STATUSES,
    AFFINITY_RESULT_NORMAL,
    AFFINITY_RESULT_OPTIONS,
    DRIFT_COMPARE_FIELDS,
    ENG_METHOD_OPTIONS,
    ENG_TYPE_OPTIONS,
    MOUSE_STRAIN_OPTIONS,
    ORDER_KIND_ENGINEERING,
    ORDER_KIND_NORMAL,
    ORDER_KIND_OPTIONS,
    SELECTION_METHOD_OPTIONS,
    STATUS_ASSAYING,
    STATUS_CANCELLED,
    STATUS_COMPLETED,
    STATUS_OPTIONS,
    STATUS_SYNTHESIZING,
    STATUS_WAIT_ASSAY,
    STATUS_WAIT_ORDER,
    SUPPLY_MODE_ARRIVAL,
    SUPPLY_MODE_OPTIONS,
    SYNTHETIC_CORP_OPTIONS,
    TARGET_TYPE_OPTIONS,
    UNCLAIMED_OWNER,
)
from modules.discovery.synthesis_progress.one_sync import (
    check_remote_for_local_rows,
    compute_drift_fields,
    derive_status_for_row,
)
from utils.excel import build_list_workbook
from utils.filter_values import (
    catalog_names_for_pairs,
    clean_field_text,
    combine_any,
    match_any,
    recorded_target_clause,
    split_code_tokens,
    target_select_options,
)
from utils.target_structure import parse_target_structure
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

logger = logging.getLogger(__name__)

MISSING_ROW = "合成与验证记录不存在"
SYNTHESIS_ID_PREFIX = "SYN"
SYNTHESIS_ID_RANDOM_LEN = 6
SYNTHESIS_ID_MAX_ATTEMPTS = 25
SYNTHESIS_ID_ALPHABET = string.ascii_uppercase + string.digits

STRING_FIELDS: dict[str, int] = {
    "target_name": 128,
    "target_type": 64,
    "synthesis_code": 64,
    "order_no": 64,
    "synthetic_corp": 64,
    "owner": 64,
    "batch_label": 255,
    "project_code": 64,
    "experiment_id": 64,
    "study_type": 64,
    "pm": 64,
    "assay_note": 500,
    "remark": 1000,
    "eng_parent_seq": 500,
    "eng_requirement": 1000,
    "eng_result": 500,
}

CSV_JOINED_FIELDS: dict[str, tuple[tuple[str, ...], int, str]] = {
    "mouse_strain": (MOUSE_STRAIN_OPTIONS, 128, "小鼠品系"),
    "selection_method": (SELECTION_METHOD_OPTIONS, 128, "挑选方式"),
    "eng_type": (ENG_TYPE_OPTIONS, 128, "改造类型"),
    "eng_method": (ENG_METHOD_OPTIONS, 128, "改造方式"),
}

INT_COUNT_FIELDS: dict[str, str] = {
    "synthetic_count": "合成个数",
    "arrival_count": "到货个数",
    "flow_count": "流式个数",
    "affinity_count": "亲和力个数",
}

DATE_FIELDS: tuple[str, ...] = (
    "synthetic_date",
    "arrival_date",
    "flow_date",
    "affinity_date",
)

WRITABLE_FIELDS = (
    *STRING_FIELDS,
    *CSV_JOINED_FIELDS,
    *INT_COUNT_FIELDS,
    *DATE_FIELDS,
    "status",
    "priority",
    "sort_order",
    "order_kind",
    "supply_mode",
    "affinity_result",
    "target_codes",
)

PM_EDIT_FIELDS = frozenset(
    {
        "priority",
        "sort_order",
        "order_kind",
        "owner",
        "pm",
        "project_code",
        "experiment_id",
        "study_type",
        "target_name",
        "target_codes",
        "target_type",
        "mouse_strain",
        "selection_method",
        "eng_type",
        "eng_method",
        "eng_parent_seq",
        "eng_requirement",
        "remark",
    }
)


def clean_actor_person_name(name: str | None) -> str | None:
    text = str(name or "").strip()
    if not text:
        return None
    first = text.split()[0].strip()
    return first[:64] if first else None


def generate_synthesis_order_id(now: datetime | None = None) -> str:
    stamp = (now or datetime.now()).strftime("%y%m%d")
    suffix = "".join(
        secrets.choice(SYNTHESIS_ID_ALPHABET) for _ in range(SYNTHESIS_ID_RANDOM_LEN)
    )
    return f"{SYNTHESIS_ID_PREFIX}-{stamp}-{suffix}"


def next_synthesis_order_id(db: Session) -> str:
    for _ in range(SYNTHESIS_ID_MAX_ATTEMPTS):
        candidate = generate_synthesis_order_id()
        exists = db.scalar(
            select(DiscoverySynthesisOrder.id).where(
                DiscoverySynthesisOrder.synthesis_order_id == candidate
            )
        )
        if not exists:
            return candidate
    raise ValueError("无法分配合成与验证单号")


def serialize_order(row: DiscoverySynthesisOrder) -> dict[str, Any]:
    data = row.to_dict()
    drifts = compute_drift_fields(row)
    data["drift_fields"] = drifts
    data["has_drift"] = bool(drifts)
    return data


BREAK_FIELDS = frozenset({
    "assay_note",
    "remark",
    "eng_parent_seq",
    "eng_requirement",
    "eng_result",
})


def _normalize_text(value: Any, max_len: int, *, keep_breaks: bool = False) -> str | None:
    if value is None:
        return None
    text = clean_field_text(value, keep_breaks=keep_breaks)
    if not text:
        return None
    if len(text) > max_len:
        raise ValueError(f"字段长度不能超过 {max_len}")
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


def _normalize_target_codes(value: Any) -> list[str]:
    if value is None or value == "":
        return []
    if isinstance(value, str):
        return [
            part.strip().upper()
            for part in value.replace("，", ",").replace("、", ",").split(",")
            if part.strip()
        ]
    if not isinstance(value, list):
        raise ValueError("靶点编号必须是数组")
    return [str(item).strip().upper() for item in value if str(item).strip()]


def _normalize_csv_joined(
    value: Any,
    options: tuple[str, ...],
    max_len: int,
    label: str,
) -> str | None:
    if value is None or value == "":
        return None
    if isinstance(value, (list, tuple)):
        raw_items = [str(item).strip() for item in value if str(item).strip()]
    else:
        text = str(value).strip()
        if not text:
            return None
        raw_items = [
            p.strip()
            for p in text.replace("，", ",").replace("、", ",").replace("+", ",").split(",")
            if p.strip()
        ]
    tokens: list[str] = []
    seen: set[str] = set()
    for tok in raw_items:
        if tok and tok not in seen:
            seen.add(tok)
            tokens.append(tok)
    if not tokens:
        return None
    known = set(options)
    ordered = [opt for opt in options if opt in tokens]
    extras = [tok for tok in tokens if tok not in known]
    joined = "、".join([*ordered, *extras])
    if len(joined) > max_len:
        raise ValueError(f"{label}长度不能超过 {max_len}")
    return joined


def _normalize_priority(value: Any) -> str:
    text = canonicalize_priority(value)
    if text not in PRIORITY_ORDER:
        raise ValueError("优先级不在允许的选项中")
    return text


def _normalize_sort_order(value: Any) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("排序必须是正整数") from exc
    if number <= 0:
        raise ValueError("排序必须是正整数")
    return number


def _normalize_status(value: Any) -> str:
    text = str(value or "").strip() or STATUS_WAIT_ORDER
    if text not in STATUS_OPTIONS:
        raise ValueError("状态不在允许的选项中")
    return text


def _normalize_order_kind(value: Any) -> str:
    text = str(value or "").strip() or ORDER_KIND_NORMAL
    if text not in ORDER_KIND_OPTIONS:
        raise ValueError("订单性质不在允许的选项中")
    return text


def _normalize_supply_mode(value: Any) -> str:
    text = str(value or "").strip() or SUPPLY_MODE_ARRIVAL
    if text not in SUPPLY_MODE_OPTIONS:
        raise ValueError("供应方式不在允许的选项中")
    return text


def _normalize_affinity_result(value: Any) -> str | None:
    text = str(value or "").strip()
    if not text:
        return None
    if text not in AFFINITY_RESULT_OPTIONS:
        raise ValueError("亲和力结果不在允许的选项中")
    return text


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


def _parse_row_id(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        row_id = int(value)
    except (TypeError, ValueError):
        return None
    return row_id if row_id > 0 else None


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


def _code_search_clause(column, value: Any):
    tokens = split_code_tokens(value)
    if not tokens:
        return None
    if len(tokens) == 1:
        return column.like(f"%{tokens[0]}%")
    return column.in_(tokens)


def _contains_filter(column, value: Any):
    return combine_any(value, lambda text: column.like(f"%{text}%"))


def _csv_token_filter(column, value: str, separators: tuple[str, ...] = (",", "、", "+")):
    clauses = [column == value]
    for sep in separators:
        clauses.extend(
            (
                column.like(f"{value}{sep}%"),
                column.like(f"%{sep}{value}"),
                column.like(f"%{sep}{value}{sep}%"),
            )
        )
    return or_(*clauses)


def _unassigned_clause():
    return and_(
        DiscoverySynthesisOrder.status != STATUS_CANCELLED,
        DiscoverySynthesisOrder.owner == UNCLAIMED_OWNER,
    )


def _has_issue_clause():
    return and_(
        DiscoverySynthesisOrder.assay_note.is_not(None),
        DiscoverySynthesisOrder.assay_note != "",
    )


def _apply_list_filters(
    stmt,
    data: dict[str, Any],
    *,
    apply_view: bool = True,
    apply_quick: bool = True,
    db: Session | None = None,
):
    filters = []
    keyword = str(data.get("keyword") or "").strip()
    if keyword:
        like = f"%{keyword}%"
        filters.append(
            or_(
                DiscoverySynthesisOrder.synthesis_order_id.like(like),
                DiscoverySynthesisOrder.order_no.like(like),
                DiscoverySynthesisOrder.synthesis_code.like(like),
                DiscoverySynthesisOrder.batch_label.like(like),
                DiscoverySynthesisOrder.target_name.like(like),
                DiscoverySynthesisOrder.project_code.like(like),
                DiscoverySynthesisOrder.experiment_id.like(like),
                DiscoverySynthesisOrder.owner.like(like),
                DiscoverySynthesisOrder.pm.like(like),
                DiscoverySynthesisOrder.assay_note.like(like),
                DiscoverySynthesisOrder.remark.like(like),
            )
        )

    target_clause = recorded_target_clause(
        db,
        DiscoverySynthesisOrder.target_name,
        DiscoverySynthesisOrder.target_codes,
        data.get("target_name"),
        select(DiscoverySynthesisOrder.target_name, DiscoverySynthesisOrder.target_codes),
    )
    if target_clause is not None:
        filters.append(target_clause)

    order_no_clause = _code_search_clause(DiscoverySynthesisOrder.order_no, data.get("order_no"))
    if order_no_clause is not None:
        filters.append(order_no_clause)

    syn_code_clause = _code_search_clause(
        DiscoverySynthesisOrder.synthesis_code, data.get("synthesis_code")
    )
    if syn_code_clause is not None:
        filters.append(syn_code_clause)

    batch_label_clause = _code_search_clause(
        DiscoverySynthesisOrder.batch_label, data.get("batch_label")
    )
    if batch_label_clause is not None:
        filters.append(batch_label_clause)

    status_clause = combine_any(
        data.get("status"),
        lambda val: DiscoverySynthesisOrder.status == _normalize_status(val),
    )
    if status_clause is not None:
        filters.append(status_clause)

    priority_clause = combine_any(
        data.get("priority"),
        lambda val: DiscoverySynthesisOrder.priority == _normalize_priority(val),
    )
    if priority_clause is not None:
        filters.append(priority_clause)

    kind_clause = combine_any(
        data.get("order_kind"),
        lambda val: DiscoverySynthesisOrder.order_kind == _normalize_order_kind(val),
    )
    if kind_clause is not None:
        filters.append(kind_clause)

    supply_clause = combine_any(
        data.get("supply_mode"),
        lambda val: DiscoverySynthesisOrder.supply_mode == _normalize_supply_mode(val),
    )
    if supply_clause is not None:
        filters.append(supply_clause)

    target_type_clause = combine_any(
        data.get("target_type"),
        lambda val: (
            and_(
                DiscoverySynthesisOrder.target_type.is_not(None),
                DiscoverySynthesisOrder.target_type != "",
                ~DiscoverySynthesisOrder.target_type.like("%分泌%"),
            )
            if str(val).strip() == "非分泌型"
            else DiscoverySynthesisOrder.target_type == str(val).strip()
        ),
    )
    if target_type_clause is not None:
        filters.append(target_type_clause)

    corp_clause = match_any(DiscoverySynthesisOrder.synthetic_corp, data.get("synthetic_corp"))
    if corp_clause is not None:
        filters.append(corp_clause)

    owner_clause = match_any(DiscoverySynthesisOrder.owner, data.get("owner"))
    if owner_clause is not None:
        filters.append(owner_clause)

    pm_clause = match_any(DiscoverySynthesisOrder.pm, data.get("pm"))
    if pm_clause is not None:
        filters.append(pm_clause)

    study_clause = match_any(DiscoverySynthesisOrder.study_type, data.get("study_type"))
    if study_clause is not None:
        filters.append(study_clause)

    aff_res_clause = combine_any(
        data.get("affinity_result"),
        lambda val: DiscoverySynthesisOrder.affinity_result == _normalize_affinity_result(val),
    )
    if aff_res_clause is not None:
        filters.append(aff_res_clause)

    for csv_key in ("mouse_strain", "selection_method", "eng_type", "eng_method"):
        tokens = split_code_tokens(data.get(csv_key))
        if tokens:
            col = getattr(DiscoverySynthesisOrder, csv_key)
            filters.append(or_(*[_csv_token_filter(col, item) for item in tokens]))

    p_tokens = split_code_tokens(data.get("project_code"))
    if len(p_tokens) == 1:
        like_p = f"%{p_tokens[0]}%"
        filters.append(
            or_(
                DiscoverySynthesisOrder.project_code.like(like_p),
                DiscoverySynthesisOrder.experiment_id.like(like_p),
            )
        )
    elif len(p_tokens) > 1:
        filters.append(
            or_(
                DiscoverySynthesisOrder.project_code.in_(p_tokens),
                DiscoverySynthesisOrder.experiment_id.in_(p_tokens),
            )
        )

    for text_field in (
        "assay_note",
        "remark",
    ):
        clause = _contains_filter(getattr(DiscoverySynthesisOrder, text_field), data.get(text_field))
        if clause is not None:
            filters.append(clause)

    for date_col, start_key, end_key in (
        (DiscoverySynthesisOrder.synthetic_date, "synthetic_date_start", "synthetic_date_end"),
        (DiscoverySynthesisOrder.arrival_date, "arrival_date_start", "arrival_date_end"),
        (DiscoverySynthesisOrder.flow_date, "flow_date_start", "flow_date_end"),
        (DiscoverySynthesisOrder.affinity_date, "affinity_date_start", "affinity_date_end"),
    ):
        s_raw = data.get(start_key)
        e_raw = data.get(end_key)
        if s_raw not in (None, ""):
            filters.append(date_col >= _normalize_date(s_raw))
        if e_raw not in (None, ""):
            filters.append(date_col <= _normalize_date(e_raw))

    if apply_view:
        view_group = str(data.get("view_group") or "").strip()
        if view_group == "wait_order":
            filters.append(DiscoverySynthesisOrder.status == STATUS_WAIT_ORDER)
        elif view_group == "synthesizing":
            filters.append(DiscoverySynthesisOrder.status == STATUS_SYNTHESIZING)
        elif view_group == "assay":
            filters.append(
                DiscoverySynthesisOrder.status.in_((STATUS_WAIT_ASSAY, STATUS_ASSAYING))
            )
        elif view_group == "completed":
            filters.append(DiscoverySynthesisOrder.status == STATUS_COMPLETED)
        elif view_group == "engineering":
            filters.append(DiscoverySynthesisOrder.order_kind == ORDER_KIND_ENGINEERING)
        elif view_group == "cancelled":
            filters.append(DiscoverySynthesisOrder.status == STATUS_CANCELLED)

    if apply_quick:
        quick_filter = str(data.get("quick_filter") or "").strip()
        if quick_filter == "unassigned":
            filters.append(_unassigned_clause())
        elif quick_filter == "has_issue":
            filters.append(_has_issue_clause())

    if filters:
        return stmt.where(*filters)
    return stmt


_SORT_COLUMNS = {
    "synthetic_date": DiscoverySynthesisOrder.synthetic_date,
    "arrival_date": DiscoverySynthesisOrder.arrival_date,
    "flow_date": DiscoverySynthesisOrder.flow_date,
    "affinity_date": DiscoverySynthesisOrder.affinity_date,
    "order_no": DiscoverySynthesisOrder.order_no,
    "synthesis_code": DiscoverySynthesisOrder.synthesis_code,
    "target_name": DiscoverySynthesisOrder.target_name,
}


def _list_order(data: dict[str, Any] | None = None):
    payload = data or {}
    field = str(payload.get("sort_field") or "").strip()
    direction = str(payload.get("sort_dir") or "desc").strip().lower()
    column = _SORT_COLUMNS.get(field)
    if column is not None and direction in {"asc", "desc"}:
        blank = or_(column.is_(None), column == "")
        ordered = column.asc() if direction == "asc" else column.desc()
        return (
            case((blank, 1), else_=0),
            ordered,
            DiscoverySynthesisOrder.id.desc(),
        )
    return list_order_clauses(
        field,
        DiscoverySynthesisOrder.sort_order,
        DiscoverySynthesisOrder.id,
    )


def _is_terminal(status: str | None) -> bool:
    return str(status or "").strip() in {STATUS_COMPLETED, STATUS_CANCELLED}


def _queue_rows(db: Session) -> list[DiscoverySynthesisOrder]:
    status_col = func.coalesce(DiscoverySynthesisOrder.status, STATUS_WAIT_ORDER)
    return list(
        db.scalars(
            select(DiscoverySynthesisOrder)
            .where(status_col.notin_((STATUS_COMPLETED, STATUS_CANCELLED)))
            .order_by(DiscoverySynthesisOrder.sort_order.asc(), DiscoverySynthesisOrder.id.asc())
        ).all()
    )


def _lock_queue(db: Session) -> None:
    db.scalars(
        select(DiscoverySynthesisOrder.id)
        .order_by(DiscoverySynthesisOrder.id.asc())
        .with_for_update()
    ).all()


def _place_row(
    db: Session,
    row: DiscoverySynthesisOrder,
    *,
    mode: str,
    target_sort: int | None = None,
) -> None:
    if not getattr(row, "id", None):
        db.flush()
    others = [item for item in _queue_rows(db) if int(item.id) != int(row.id)]
    place_row_among(others, row, mode=mode, target_sort=target_sort)


def _apply_queue(
    db: Session,
    row: DiscoverySynthesisOrder,
    *,
    previous_sort: int | None,
    previous_priority: Any,
    payload: dict[str, Any],
    is_new: bool,
) -> None:
    if _is_terminal(row.status):
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
        place=lambda mode, target_sort=None: _place_row(
            db, row, mode=mode, target_sort=target_sort
        ),
    )


def _list_stats(db: Session, payload: dict[str, Any]) -> dict[str, int]:
    stmt = _apply_list_filters(
        select(
            func.count(),
            func.coalesce(
                func.sum(
                    case((DiscoverySynthesisOrder.status == STATUS_WAIT_ORDER, 1), else_=0)
                ),
                0,
            ),
            func.coalesce(
                func.sum(
                    case((DiscoverySynthesisOrder.status == STATUS_SYNTHESIZING, 1), else_=0)
                ),
                0,
            ),
            func.coalesce(
                func.sum(
                    case(
                        (
                            DiscoverySynthesisOrder.status.in_(
                                (STATUS_WAIT_ASSAY, STATUS_ASSAYING)
                            ),
                            1,
                        ),
                        else_=0,
                    )
                ),
                0,
            ),
            func.coalesce(
                func.sum(
                    case((DiscoverySynthesisOrder.status == STATUS_COMPLETED, 1), else_=0)
                ),
                0,
            ),
            func.coalesce(
                func.sum(
                    case(
                        (DiscoverySynthesisOrder.order_kind == ORDER_KIND_ENGINEERING, 1),
                        else_=0,
                    )
                ),
                0,
            ),
            func.coalesce(
                func.sum(
                    case((DiscoverySynthesisOrder.status == STATUS_CANCELLED, 1), else_=0)
                ),
                0,
            ),
            func.coalesce(func.sum(case((_unassigned_clause(), 1), else_=0)), 0),
            func.coalesce(func.sum(case((_has_issue_clause(), 1), else_=0)), 0),
        ).select_from(DiscoverySynthesisOrder),
        payload,
        apply_view=False,
        apply_quick=False,
        db=db,
    )
    row = db.execute(stmt).one()
    return {
        "all": int(row[0] or 0),
        "wait_order": int(row[1] or 0),
        "synthesizing": int(row[2] or 0),
        "assay": int(row[3] or 0),
        "completed": int(row[4] or 0),
        "engineering": int(row[5] or 0),
        "cancelled": int(row[6] or 0),
        "unassigned": int(row[7] or 0),
        "has_issue": int(row[8] or 0),
    }


def get_list(db: Session, data: dict[str, Any]) -> dict[str, Any]:
    payload = data or {}
    page, limit = _page_limit(payload)
    stmt = _apply_list_filters(select(DiscoverySynthesisOrder), payload, db=db)
    total = (
        db.scalar(
            _apply_list_filters(
                select(func.count()).select_from(DiscoverySynthesisOrder),
                payload,
                db=db,
            )
        )
        or 0
    )
    rows = db.scalars(
        stmt.order_by(*_list_order(payload))
        .offset((page - 1) * limit)
        .limit(limit)
    ).all()
    return {
        "items": [serialize_order(row) for row in rows],
        "total": total,
        "page": page,
        "limit": limit,
        "stats": _list_stats(db, payload),
    }


def get_options(db: Session) -> dict[str, Any]:
    def distinct_values(column, presets: tuple[str, ...] = ()) -> list[str]:
        found: set[str] = set()
        for val in db.scalars(select(column).where(column.is_not(None)).distinct()).all():
            text = str(val or "").strip()
            if text:
                found.add(text)
        ordered = list(presets)
        extras = sorted(item for item in found if item not in set(presets))
        return [*ordered, *extras]

    def distinct_csv_tokens(column, presets: tuple[str, ...] = ()) -> list[str]:
        found: set[str] = set()
        for val in db.scalars(select(column).where(column.is_not(None)).distinct()).all():
            for part in str(val or "").replace("，", ",").replace("、", ",").replace("+", ",").split(","):
                tok = part.strip()
                if tok:
                    found.add(tok)
        ordered = list(presets)
        extras = sorted(item for item in found if item not in set(presets))
        return [*ordered, *extras]

    pairs = db.execute(
        select(DiscoverySynthesisOrder.target_name, DiscoverySynthesisOrder.target_codes)
    ).all()
    return {
        "statuses": list(STATUS_OPTIONS),
        "priorities": list(PRIORITY_ORDER),
        "order_kinds": list(ORDER_KIND_OPTIONS),
        "supply_modes": list(SUPPLY_MODE_OPTIONS),
        "affinity_results": list(AFFINITY_RESULT_OPTIONS),
        "target_types": distinct_values(
            DiscoverySynthesisOrder.target_type, TARGET_TYPE_OPTIONS
        ),
        "mouse_strains": list(MOUSE_STRAIN_OPTIONS),
        "selection_methods": distinct_csv_tokens(
            DiscoverySynthesisOrder.selection_method, SELECTION_METHOD_OPTIONS
        ),
        "synthetic_corps": distinct_values(
            DiscoverySynthesisOrder.synthetic_corp, SYNTHETIC_CORP_OPTIONS
        ),
        "eng_types": distinct_csv_tokens(DiscoverySynthesisOrder.eng_type, ENG_TYPE_OPTIONS),
        "eng_methods": distinct_csv_tokens(DiscoverySynthesisOrder.eng_method, ENG_METHOD_OPTIONS),
        "targets": target_select_options(pairs, catalog_names_for_pairs(db, pairs)),
        "owners": distinct_values(DiscoverySynthesisOrder.owner, (UNCLAIMED_OWNER,)),
        "pms": distinct_values(DiscoverySynthesisOrder.pm),
    }


def _infer_target_type(db: Session, target_codes: Any) -> str | None:
    codes = _normalize_target_codes(target_codes)
    if not codes:
        return None
    row = db.execute(
        select(Target.structural_properties, Target.structure_feature).where(
            Target.snum == codes[0]
        )
    ).first()
    return parse_target_structure(row[0], row[1])["label"] if row else None


def _apply_fields(
    row: DiscoverySynthesisOrder,
    data: dict[str, Any],
) -> None:
    prev_order_no = row.order_no
    prev_codes = (row.synthesis_code, row.batch_label)
    for field in WRITABLE_FIELDS:
        if field not in data:
            continue
        raw = data.get(field)
        if field == "status":
            value: Any = _normalize_status(raw)
        elif field == "priority":
            value = _normalize_priority(raw)
        elif field == "sort_order":
            if raw in (None, "", "-"):
                continue
            value = _normalize_sort_order(raw)
        elif field == "order_kind":
            value = _normalize_order_kind(raw)
        elif field == "supply_mode":
            value = _normalize_supply_mode(raw)
        elif field == "affinity_result":
            value = _normalize_affinity_result(raw)
        elif field == "target_codes":
            value = _normalize_target_codes(raw)
        elif field in CSV_JOINED_FIELDS:
            opts, max_len, label = CSV_JOINED_FIELDS[field]
            value = _normalize_csv_joined(raw, opts, max_len, label)
        elif field in INT_COUNT_FIELDS:
            value = _normalize_nonneg_int(raw, INT_COUNT_FIELDS[field])
        elif field in DATE_FIELDS:
            value = _normalize_date(raw)
        else:
            value = _normalize_text(
                raw,
                STRING_FIELDS[field],
                keep_breaks=field in BREAK_FIELDS,
            )
        setattr(row, field, value)

    if "affinity_date" in data:
        if row.affinity_date:
            if not row.affinity_result:
                row.affinity_result = AFFINITY_RESULT_NORMAL
            if not row.owner:
                row.owner = UNCLAIMED_OWNER
        else:
            if "affinity_result" not in data:
                row.affinity_result = None
            if "owner" not in data and row.owner == UNCLAIMED_OWNER:
                row.owner = None

    if row.source_one_id is not None:
        old_snap = row.source_snapshot if isinstance(row.source_snapshot, dict) else {}
        order_changed = "order_no" in data and row.order_no != prev_order_no
        code_changed = ("batch_label" in data or "synthesis_code" in data) and (
            row.synthesis_code,
            row.batch_label,
        ) != prev_codes
        if order_changed or (
            code_changed
            and "order_no" not in data
            and row.order_no == old_snap.get("order_no")
        ):
            if not order_changed:
                row.order_no = None
            row.source_one_type = None
            row.source_one_id = None
            if not any((row.order_no, row.synthesis_code, row.batch_label)):
                row.source_snapshot = None

    if "status" not in data:
        row.status = derive_status_for_row(row, preserve_terminal=True)


def save(
    db: Session,
    data: dict[str, Any],
    created_by: str | None = None,
    *,
    commit: bool = True,
    lock_queue: bool = True,
    scopes: frozenset[str] = frozenset({"full"}),
) -> dict[str, Any]:
    payload = dict(data or {})
    payload.pop("synthesis_order_id", None)
    row_id = _parse_row_id(payload.get("id"))
    if payload.get("id") not in (None, "") and row_id is None:
        raise ValueError("合成与验证记录 ID 不正确")

    if "full" not in scopes:
        if "pm" not in scopes:
            raise PermissionError("没有权限编辑合成与验证工单")
        disallowed = [
            key
            for key in payload
            if key != "id" and key in WRITABLE_FIELDS and key not in PM_EDIT_FIELDS
        ]
        if disallowed:
            raise PermissionError("当前权限仅可编辑项目、认领及改造需求相关字段")

    actor_person = clean_actor_person_name(created_by)
    is_new = row_id is None
    if lock_queue and (
        is_new
        or "sort_order" in payload
        or "priority" in payload
        or "status" in payload
    ):
        _lock_queue(db)

    if is_new:
        row = DiscoverySynthesisOrder(
            synthesis_order_id=next_synthesis_order_id(db),
            status=STATUS_WAIT_ORDER,
            priority=DEFAULT_PRIORITY,
            sort_order=None,
            order_kind=ORDER_KIND_NORMAL,
            supply_mode=SUPPLY_MODE_ARRIVAL,
            created_by=(created_by or "").strip() or None,
        )
        db.add(row)
        previous_sort = None
        previous_priority = DEFAULT_PRIORITY
    else:
        row = db.get(DiscoverySynthesisOrder, row_id)
        if not row:
            raise ValueError(MISSING_ROW)
        previous_sort = queued_sort(row.sort_order)
        previous_priority = row.priority or DEFAULT_PRIORITY

    _apply_fields(row, payload)
    if "target_codes" in payload and "target_type" not in payload:
        row.target_type = _infer_target_type(db, row.target_codes)

    if actor_person and (
        (is_new and (row.order_kind == ORDER_KIND_ENGINEERING or "full" not in scopes))
        or (payload.get("order_kind") == ORDER_KIND_ENGINEERING)
    ):
        if not row.owner or row.owner == UNCLAIMED_OWNER:
            row.owner = actor_person
        if not row.pm:
            row.pm = actor_person

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
    return serialize_order(row)


def save_batch(
    db: Session,
    data: dict[str, Any],
    created_by: str | None = None,
    *,
    scopes: frozenset[str] = frozenset({"full"}),
) -> dict[str, Any]:
    raw_items = data.get("items") or []
    if not isinstance(raw_items, list) or not raw_items:
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
            raise ValueError("合成与验证记录 ID 不正确")
        if row_id is not None:
            row_ids.append(row_id)
        if row_id is None or "sort_order" in item or "priority" in item or "status" in item:
            needs_lock = True
    if len(row_ids) != len(set(row_ids)):
        raise ValueError("批量保存包含重复的记录")
    if needs_lock:
        _lock_queue(db)

    saved_ids = [
        int(
            save(
                db,
                item,
                created_by=created_by,
                commit=False,
                lock_queue=False,
                scopes=scopes,
            )["id"]
        )
        for item in items
    ]
    db.commit()
    saved = []
    for row_id in saved_ids:
        row = db.get(DiscoverySynthesisOrder, row_id)
        if row:
            saved.append(serialize_order(row))
    return {"items": saved}


def claim_order(
    db: Session,
    row_id: int,
    actor_name: str | None,
) -> dict[str, Any]:
    row = db.get(DiscoverySynthesisOrder, int(row_id))
    if not row:
        raise ValueError(MISSING_ROW)
    person = clean_actor_person_name(actor_name)
    if not person:
        raise ValueError("无法识别当前认领人姓名")
    row.owner = person
    db.commit()
    db.refresh(row)
    return serialize_order(row)


def delete(
    db: Session,
    row_id: int,
    *,
    scopes: frozenset[str] = frozenset({"full"}),
) -> None:
    _lock_queue(db)
    row = db.get(DiscoverySynthesisOrder, int(row_id))
    if not row:
        raise ValueError(MISSING_ROW)
    if "full" not in scopes:
        if row.status != STATUS_WAIT_ORDER:
            raise PermissionError("PM 权限只能删除待下单状态的工单")
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
    moved = db.get(DiscoverySynthesisOrder, parsed_moved_id)
    target = db.get(DiscoverySynthesisOrder, parsed_target_id)
    if not moved or not target:
        raise ValueError(MISSING_ROW)
    if parsed_moved_id == parsed_target_id:
        return {"items": [serialize_order(moved)]}
    for row in (moved, target):
        if _is_terminal(row.status) or queued_sort(row.sort_order) is None:
            raise ValueError("终态记录不参与排序")
    _place_row(db, moved, mode="snap", target_sort=queued_sort(target.sort_order))
    db.commit()
    return {"items": [serialize_order(moved), serialize_order(target)]}


def adopt_source(
    db: Session,
    row_id: int,
    fields: list[str] | None = None,
) -> dict[str, Any]:
    row = db.get(DiscoverySynthesisOrder, int(row_id))
    if not row:
        raise ValueError(MISSING_ROW)
    snapshot = row.source_snapshot if isinstance(row.source_snapshot, dict) else {}
    if not snapshot:
        raise ValueError("该记录没有可用的外部来源快照")

    target_fields = (
        [f for f in fields if f in DRIFT_COMPARE_FIELDS]
        if fields
        else list(DRIFT_COMPARE_FIELDS)
    )
    if not target_fields:
        raise ValueError("未指定可采用的来源字段")

    for field in target_fields:
        remote_val = snapshot.get(field)
        if remote_val in (None, ""):
            continue
        setattr(row, field, remote_val)

    row.status = derive_status_for_row(row, preserve_terminal=True)
    db.commit()
    db.refresh(row)
    return serialize_order(row)


def sync_from_one(
    db: Session,
    created_by: str | None = "system",
) -> dict[str, Any]:
    """Matches and updates existing active local synthesis rows against One DB without creating new rows."""
    _ = created_by
    candidate_rows = list(
        db.scalars(
            select(DiscoverySynthesisOrder).where(
                DiscoverySynthesisOrder.status.in_(tuple(ACTIVE_STATUSES)),
                or_(
                    DiscoverySynthesisOrder.source_one_id.is_not(None),
                    DiscoverySynthesisOrder.supply_mode == SUPPLY_MODE_ARRIVAL,
                ),
            )
        ).all()
    )
    if not candidate_rows:
        return {"linked": 0, "updated": 0, "unchanged": 0, "total": 0}

    res = check_remote_for_local_rows(
        db,
        rows=candidate_rows,
        connect_timeout=3,
        read_timeout=15,
        serialize_changed=False,
    )
    if not res.get("remote_available"):
        return {"skipped": True, "message": "未配置或无法连接 ONE_DB_URL，已跳过外部同步"}

    total_linked = int(res.get("linked") or 0)
    total_updated = int(res.get("updated") or 0)

    if total_linked or total_updated:
        for r in db.scalars(
            select(DiscoverySynthesisOrder).where(
                DiscoverySynthesisOrder.status.in_((STATUS_COMPLETED, STATUS_CANCELLED)),
                DiscoverySynthesisOrder.sort_order.is_not(None),
            )
        ).all():
            r.sort_order = None
        renumber_queue(_queue_rows(db))
        db.commit()

    total_checked = len(candidate_rows)
    return {
        "linked": total_linked,
        "updated": total_updated,
        "unchanged": max(0, total_checked - total_linked - total_updated),
        "total": total_checked,
    }


EXPORT_COLUMNS = (
    ("排序", "sort_order"),
    ("优先级", "priority"),
    ("系统单号", "synthesis_order_id"),
    ("状态", "status"),
    ("靶点名称", "target_name"),
    ("靶点类型", "target_type"),
    ("小鼠品系", "mouse_strain"),
    ("挑选方式", "selection_method"),
    ("送测转码", "synthesis_code"),
    ("订单号", "order_no"),
    ("合成公司", "synthetic_corp"),
    ("合成个数", "synthetic_count"),
    ("合成日期", "synthetic_date"),
    ("到货个数", "arrival_count"),
    ("到货日期", "arrival_date"),
    ("流式个数", "flow_count"),
    ("流式日期", "flow_date"),
    ("亲和力个数", "affinity_count"),
    ("亲和力日期", "affinity_date"),
    ("亲和力结果", "affinity_result"),
    ("负责人", "owner"),
    ("订单性质", "order_kind"),
    ("供应方式", "supply_mode"),
    ("工单批次", "batch_label"),
    ("检测与异常说明", "assay_note"),
    ("备注", "remark"),
    ("改造类型", "eng_type"),
    ("改造方式", "eng_method"),
    ("改造序列或母本", "eng_parent_seq"),
    ("改造要求", "eng_requirement"),
    ("改造结果", "eng_result"),
    ("靶点编号", "target_codes"),
    ("项目编号", "project_code"),
    ("课题类型", "study_type"),
    ("PM", "pm"),
)


def export_list_workbook(db: Session, data: dict[str, Any]) -> tuple[BytesIO, str]:
    payload = data or {}
    stmt = _apply_list_filters(select(DiscoverySynthesisOrder), payload, db=db)
    rows = db.scalars(stmt.order_by(*_list_order(payload))).all()
    headers = [header for header, _ in EXPORT_COLUMNS]
    body = [
        [getattr(row, field) for _, field in EXPORT_COLUMNS]
        for row in rows
    ]
    return build_list_workbook(
        sheet_title="合成与验证",
        filename_prefix="合成与验证",
        headers=headers,
        rows=body,
    )


__all__ = [
    "MISSING_ROW",
    "PM_EDIT_FIELDS",
    "adopt_source",
    "check_remote_for_local_rows",
    "claim_order",
    "delete",
    "export_list_workbook",
    "get_list",
    "get_options",
    "reorder",
    "save",
    "save_batch",
    "serialize_order",
    "sync_from_one",
]
