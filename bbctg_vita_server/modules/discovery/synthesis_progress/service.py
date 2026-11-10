from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import replace
from datetime import datetime, timedelta
from functools import partial
from io import BytesIO
import logging
import re
import secrets
import string
from typing import Any

from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.orm import Session

from models.discovery import DiscoverySynthesisOrder
from models.target import Target
from modules.discovery.synthesis_progress.constants import (
    ACTIVE_STATUSES,
    AFFINITY_STATUS_ASSAYING,
    AFFINITY_STATUS_COMPLETED,
    AFFINITY_STATUS_OPTIONS,
    AFFINITY_STATUS_WAIT,
    AFFINITY_RESULT_OPTIONS,
    CLAIM_RETURN_DAYS,
    DRIFT_COMPARE_FIELDS,
    ENG_METHOD_OPTIONS,
    ENG_TYPE_OPTIONS,
    FLOW_STATUS_NOT_REQUIRED,
    FLOW_STATUS_OPTIONS,
    FLOW_STATUS_WAIT,
    INTERNAL_CORP,
    MOUSE_STRAIN_OPTIONS,
    ONE_AUTO_CREATE_SINCE,
    ONE_AUTO_CREATED_BY,
    ORDER_KIND_ENGINEERING,
    ORDER_KIND_NORMAL,
    ORDER_KIND_OPTIONS,
    RECHOOSE_OPTIONS,
    RECHOOSE_TOKEN,
    SELECTION_METHOD_OPTIONS,
    STATUS_ASSAYING,
    STATUS_CANCELLED,
    STATUS_COMPLETED,
    STATUS_OPTIONS,
    STATUS_SYNTHESIZING,
    STATUS_WAIT_ASSAY,
    STATUS_WAIT_ORDER,
    SUPPLY_MODE_ARRIVAL,
    SUPPLY_MODE_INTERNAL,
    SUPPLY_MODE_ISOTYPE,
    SUPPLY_MODE_OPTIONS,
    SYNTHETIC_CORP_OPTIONS,
    TARGET_COLOR_OPTIONS,
    TARGET_TYPE_OPTIONS,
    UNCLAIMED_OWNER,
)
from modules.discovery.synthesis_progress.one_sync import (
    SNAPSHOT_STORED_FIELDS,
    apply_remote_snapshot_to_row,
    check_remote_for_local_rows,
    collect_new_remote_orders,
    compute_drift_fields,
    parse_one_target,
    sync_derived_statuses,
)
from utils.excel import build_list_workbook
from utils.header_filters import (
    HeaderColumn,
    header_column_values,
    csv_column,
    csv_token_clause,
    header_filter_clauses,
    header_sort_clauses,
    json_array_column,
    target_column,
    without_header_fields,
)
from utils.normalize import (
    join_tokens,
    normalize_choice,
    normalize_date,
    normalize_nonneg_int,
    normalize_positive_int,
    normalize_priority,
    normalize_target_codes,
    normalize_text,
    split_tokens,
)
from utils.filter_values import (
    DEFAULT_RECORDED_TARGET_LIMIT,
    combine_any,
    filter_terms,
    like_contains,
    match_any,
    recorded_target_clause,
    recorded_target_search,
    split_code_tokens,
)
from utils.target_structure import parse_target_structure
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
from utils.clock import now_local

logger = logging.getLogger(__name__)

MISSING_ROW = "合成与验证记录不存在"
SYNTHESIS_ID_PREFIX = "SYN"
SYNTHESIS_ID_RANDOM_LEN = 6
SYNTHESIS_ID_MAX_ATTEMPTS = 25
SYNTHESIS_ID_ALPHABET = string.ascii_uppercase + string.digits

AUTO_STATUS_FIELDS = frozenset(
    {
        "order_no",
        "supply_mode",
        "arrival_date",
        "affinity_owner",
        "affinity_date",
        "report_reason",
        "flow_date",
        "target_type",
        "target_codes",
        "affinity_status",
        "flow_status",
    }
)

QUEUE_LOCK_FIELDS = frozenset({"sort_order", "priority", "status", *AUTO_STATUS_FIELDS})

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
    "flow_note": 500,
    "report_reason": 500,
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
    "affinity_owner": ((), 64, "亲和力人员"),
}

INT_COUNT_FIELDS: dict[str, str] = {
    "synthetic_count": "合成个数",
    "arrival_count": "到货个数",
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
    "affinity_status",
    "flow_status",
    "target_codes",
    "target_color",
    "is_rechoose",
)

PM_EDIT_FIELDS = frozenset(
    {
        "priority",
        "sort_order",
        "order_kind",
        "supply_mode",
        "owner",
        "project_code",
        "study_type",
        "target_name",
        "target_codes",
        "mouse_strain",
        "eng_type",
        "eng_method",
        "eng_parent_seq",
        "eng_requirement",
        "remark",
    }
)

AFFINITY_EDIT_FIELDS = frozenset(
    {
        "affinity_owner",
        "affinity_result",
        "affinity_status",
        "affinity_date",
        "report_reason",
    }
)

FLOW_EDIT_FIELDS = frozenset({"flow_status", "flow_date", "flow_note"})

ASSAY_EDIT_FIELDS = AFFINITY_EDIT_FIELDS | FLOW_EDIT_FIELDS
# 改造实验员只能改改造 / 内部转染 / 改亚型的工单，字段上除检测、负责人和靶点底色外都能改
ENG_EDIT_FIELDS = frozenset(WRITABLE_FIELDS) - ASSAY_EDIT_FIELDS - {"owner", "target_color"}
ENG_SUPPLY_MODES = frozenset({SUPPLY_MODE_INTERNAL, SUPPLY_MODE_ISOTYPE})
ENG_ROW_MESSAGE = "改造实验员只能操作改造、内部转染或改亚型的工单"
SCOPE_EDIT_FIELDS = {
    "pm": PM_EDIT_FIELDS,
    "eng": ENG_EDIT_FIELDS,
    "affinity": AFFINITY_EDIT_FIELDS,
    "flow": FLOW_EDIT_FIELDS,
}
# 同时有亲和力和流式权限的实验员：可把已完成的工单打回待检测
ASSAY_SCOPES = frozenset({"affinity", "flow"})
ASSAY_MAIN_STATUS_MESSAGE = "实验员只能把已完成的工单打回待检测"
COMPLETED_ASSAY_MESSAGE = "工单已完成，不能再改实验状态；需要重新检测请先打回待检测"
CLAIM_RETURN_EXPIRED_MESSAGE = f"认领已超过 {CLAIM_RETURN_DAYS} 天，不能退回「无人问津」"
CREATE_REQUIRED_FIELDS = (
    ("order_kind", "订单性质"),
    ("supply_mode", "供应方式"),
    ("mouse_strain", "小鼠品系"),
    ("pm", "PM"),
)
ENGINEERING_REQUIRED_FIELDS = (
    ("eng_type", "改造类型"),
    ("eng_method", "改造方式"),
    ("eng_parent_seq", "母本序列"),
    ("eng_requirement", "改造要求"),
)
CORP_MASK = "***"


class CompletionConfirmRequired(Exception):
    """保存会让工单整单变为已完成，需用户确认后带 confirm_complete 重提。"""


def _completion_confirm_message(row: DiscoverySynthesisOrder, scopes: frozenset[str]) -> str:
    label = " · ".join(
        part for part in (row.target_name, row.order_no or row.synthesis_code or row.batch_label) if part
    )
    subject = f"工单「{label}」" if label else "该工单"
    can_reopen = "full" in scopes or ASSAY_SCOPES <= scopes or _eng_covers(row, scopes)
    tail = "" if can_reopen else "完成后你将不能再改回，"
    return f"保存后{subject}将整单标记为「已完成」并移出排队，{tail}确认保存吗？"


def clean_actor_person_name(name: str | None) -> str | None:
    text = str(name or "").strip()
    if not text:
        return None
    first = text.split()[0].strip()
    return first[:64] if first else None


def _claimed_owner(row: DiscoverySynthesisOrder) -> str:
    owner = str(row.owner or "").strip()
    return "" if owner == UNCLAIMED_OWNER else owner


def pm_owns_row(row: DiscoverySynthesisOrder, actor_person: str | None) -> bool:
    """已认领的工单归负责人；没有负责人或「无人问津」时归 PM。"""
    if not actor_person:
        return False
    return actor_person == (_claimed_owner(row) or str(row.pm or "").strip())


def pm_ownership_message(row: DiscoverySynthesisOrder) -> str:
    owner = _claimed_owner(row)
    if owner:
        return f"该工单由 {owner} 负责，只有负责人可以操作"
    return "该工单还没有负责人，只有本人是 PM 时可以操作"


def _is_engineering_kind(order_kind: Any, supply_mode: Any) -> bool:
    return order_kind == ORDER_KIND_ENGINEERING or supply_mode in ENG_SUPPLY_MODES


def is_engineering_row(row: DiscoverySynthesisOrder) -> bool:
    """改造实验员负责的工单：订单性质为改造，或供应方式为内部转染 / 改亚型。"""
    return _is_engineering_kind(row.order_kind, row.supply_mode)


def _eng_covers(row: DiscoverySynthesisOrder, scopes: frozenset[str]) -> bool:
    return "eng" in scopes and is_engineering_row(row)


def _row_manage_error(
    row: DiscoverySynthesisOrder, scopes: frozenset[str], actor_person: str | None
) -> str | None:
    """删除、排序：全部编辑不限；改造实验员管改造类工单；PM 管归属本人的工单。"""
    if "full" in scopes or _eng_covers(row, scopes):
        return None
    if "pm" in scopes:
        return None if pm_owns_row(row, actor_person) else pm_ownership_message(row)
    return ENG_ROW_MESSAGE


def _touch_owner_claim(row: DiscoverySynthesisOrder, previous_owner: str | None) -> None:
    owner = str(row.owner or "").strip()
    if owner != str(previous_owner or "").strip():
        row.owner_claimed_at = now_local() if owner and owner != UNCLAIMED_OWNER else None


def _can_return_claim(row: DiscoverySynthesisOrder) -> bool:
    claimed_at = row.owner_claimed_at
    return claimed_at is not None and now_local() - claimed_at <= timedelta(days=CLAIM_RETURN_DAYS)


def _check_pm_owner_change(
    row: DiscoverySynthesisOrder,
    cur_owner: str,
    next_owner: str,
    actor_person: str | None,
) -> None:
    """PM 只能认领「无人问津」，或在认领 7 天内把本人负责的批次退回「无人问津」。"""
    if actor_person and cur_owner == UNCLAIMED_OWNER and next_owner == actor_person:
        return
    if actor_person and cur_owner == actor_person and next_owner == UNCLAIMED_OWNER:
        if _can_return_claim(row):
            return
        raise PermissionError(CLAIM_RETURN_EXPIRED_MESSAGE)
    raise PermissionError("负责人只能认领「无人问津」，或把本人负责的批次退回「无人问津」")


def _missing_create_fields(row: DiscoverySynthesisOrder, payload: dict[str, Any]) -> list[str]:
    def blank(value: Any) -> bool:
        return not str(value or "").strip()

    missing = []
    for key, label in CREATE_REQUIRED_FIELDS:
        # 订单性质、供应方式建行时有默认值，必须在本次提交里明确传入
        value = payload.get(key) if key in {"order_kind", "supply_mode"} else getattr(row, key)
        if blank(value):
            missing.append(label)
    if blank(row.target_name) and not row.target_codes:
        missing.append("靶点")
    if row.order_kind == ORDER_KIND_ENGINEERING:
        missing.extend(label for key, label in ENGINEERING_REQUIRED_FIELDS if blank(getattr(row, key)))
    return missing


def generate_synthesis_order_id(now: datetime | None = None) -> str:
    stamp = (now or now_local()).strftime("%y%m%d")
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


def mask_synthetic_corp(value: Any, *, keep_engineering_rows: bool = False) -> Any:
    """没有全部编辑权限时，行数据、来源快照、差异提示和 One 候选里的合成公司都换成 ***；
    改造实验员（keep_engineering_rows）保留改造类工单整行原值。"""
    if isinstance(value, list):
        return [mask_synthetic_corp(item, keep_engineering_rows=keep_engineering_rows) for item in value]
    if not isinstance(value, dict):
        return value
    if (
        keep_engineering_rows
        and "order_kind" in value
        and _is_engineering_kind(value.get("order_kind"), value.get("supply_mode"))
    ):
        return value
    masked = {
        key: CORP_MASK
        if key == "synthetic_corp" and item not in (None, "")
        else mask_synthetic_corp(item, keep_engineering_rows=keep_engineering_rows)
        for key, item in value.items()
    }
    if masked.get("field") == "synthetic_corp":
        for key in ("current", "remote"):
            if masked.get(key) not in (None, ""):
                masked[key] = CORP_MASK
    return masked


def without_corp_query(data: dict[str, Any] | None) -> dict[str, Any]:
    """看不到合成公司的人也不能按它筛选或排序，避免从结果反推。"""
    payload = without_header_fields(data or {}, {"synthetic_corp"})
    payload.pop("synthetic_corp", None)
    if payload.get("sort_field") == "synthetic_corp":
        payload.pop("sort_field")
    return payload


BREAK_FIELDS = frozenset({
    "flow_note",
    "report_reason",
    "remark",
    "eng_parent_seq",
    "eng_requirement",
    "eng_result",
})


def _normalize_csv_joined(
    value: Any,
    options: tuple[str, ...],
    max_len: int,
    label: str,
) -> str | None:
    joined = join_tokens(value, options)
    if joined and len(joined) > max_len:
        raise ValueError(f"{label}长度不能超过 {max_len}")
    return joined


def _normalize_status(value: Any) -> str:
    return normalize_choice(value, STATUS_OPTIONS, "状态", default=STATUS_WAIT_ORDER)


def _normalize_affinity_status(value: Any) -> str:
    return normalize_choice(value, AFFINITY_STATUS_OPTIONS, "亲和力状态")


def _normalize_flow_status(value: Any) -> str:
    return normalize_choice(value, FLOW_STATUS_OPTIONS, "流式状态")


def _validate_assay_status_edits(
    row: DiscoverySynthesisOrder,
    payload: dict[str, Any],
    *,
    can_close_with_reason: bool = False,
) -> None:
    reason = payload["report_reason"] if "report_reason" in payload else row.report_reason
    target_type = payload["target_type"] if "target_type" in payload else row.target_type
    if "affinity_status" in payload:
        next_status = _normalize_affinity_status(payload["affinity_status"])
        closing = can_close_with_reason and next_status == AFFINITY_STATUS_COMPLETED
        if next_status != AFFINITY_STATUS_WAIT and str(reason or "").strip() and not closing:
            raise ValueError("请先清除未出报告原因，再修改亲和力状态")

    if "flow_status" in payload:
        _normalize_flow_status(payload["flow_status"])
        if str(target_type or "").strip() == "分泌型":
            raise ValueError("分泌型靶点不需要流式实验")


def _normalize_order_kind(value: Any) -> str:
    return normalize_choice(value, ORDER_KIND_OPTIONS, "订单性质", default=ORDER_KIND_NORMAL)


def _normalize_supply_mode(value: Any) -> str:
    return normalize_choice(value, SUPPLY_MODE_OPTIONS, "供应方式", default=SUPPLY_MODE_ARRIVAL)


def _normalize_affinity_result(value: Any) -> str | None:
    return normalize_choice(value, AFFINITY_RESULT_OPTIONS, "亲和力结果", nullable=True)


def _normalize_target_color(value: Any) -> str | None:
    text = str(value or "").strip().lower()
    if not text or text == "none":
        return None
    if text not in TARGET_COLOR_OPTIONS:
        raise ValueError("靶点颜色标记不在允许的选项中")
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
        return like_contains(column, tokens[0])
    return column.in_(tokens)


def _status_filter_clause(data: dict[str, Any]):
    raw_terms = [
        *filter_terms(data.get("status")),
        *filter_terms(data.get("affinity_status")),
        *filter_terms(data.get("flow_status")),
    ]
    if not raw_terms:
        return None
    return _status_terms_clause(raw_terms)


def _assay_combo_term(affinity: Any, flow: Any) -> str:
    return f"{affinity}且{flow}"


ASSAY_COMBO_TERMS = {
    _assay_combo_term(affinity, flow): (affinity, flow)
    for affinity in AFFINITY_STATUS_OPTIONS
    for flow in FLOW_STATUS_OPTIONS
}


def _status_terms_clause(raw_terms: list[str]):
    """主状态之间取或；检测子状态只看待检测/检测中的行，亲和力与流式同时选时两者都要满足。

    「亲和力X且流式Y」是组合项，各组合之间、组合与其他项之间取或。
    """
    main_vals: list[str] = []
    aff_vals: list[str] = []
    flow_vals: list[str] = []
    combos: list[tuple[str, str]] = []
    for val in raw_terms:
        if val in STATUS_OPTIONS:
            main_vals.append(val)
        elif val in AFFINITY_STATUS_OPTIONS:
            aff_vals.append(val)
        elif val in FLOW_STATUS_OPTIONS:
            flow_vals.append(val)
        elif val in ASSAY_COMBO_TERMS:
            combos.append(ASSAY_COMBO_TERMS[val])
        else:
            raise ValueError("状态不在允许的选项中")

    branches = []
    if main_vals:
        branches.append(DiscoverySynthesisOrder.status.in_(tuple(main_vals)))
    in_assay = DiscoverySynthesisOrder.status.in_((STATUS_WAIT_ASSAY, STATUS_ASSAYING))
    for affinity, flow in combos:
        branches.append(and_(
            in_assay,
            DiscoverySynthesisOrder.affinity_status == affinity,
            DiscoverySynthesisOrder.flow_status == flow,
        ))
    if aff_vals or flow_vals:
        assay_parts = [in_assay]
        if aff_vals:
            assay_parts.append(
                DiscoverySynthesisOrder.affinity_status.in_(tuple(aff_vals))
            )
        if flow_vals:
            assay_parts.append(DiscoverySynthesisOrder.flow_status.in_(tuple(flow_vals)))
        branches.append(and_(*assay_parts))
    return branches[0] if len(branches) == 1 else or_(*branches)


def _contains_filter(column, value: Any):
    return combine_any(value, lambda text: like_contains(column, text))


def _unassigned_clause():
    return and_(
        DiscoverySynthesisOrder.status != STATUS_CANCELLED,
        DiscoverySynthesisOrder.owner == UNCLAIMED_OWNER,
    )


def _has_issue_clause():
    return or_(
        and_(
            DiscoverySynthesisOrder.flow_note.is_not(None),
            DiscoverySynthesisOrder.flow_note != "",
        ),
        and_(
            DiscoverySynthesisOrder.report_reason.is_not(None),
            DiscoverySynthesisOrder.report_reason != "",
        ),
    )


def _target_color_clause(tokens: list[str]):
    clauses = []
    valid = [c for c in tokens if c in TARGET_COLOR_OPTIONS]
    if valid:
        clauses.append(DiscoverySynthesisOrder.target_color.in_(valid))
    if "none" in tokens:
        clauses.append(
            or_(
                DiscoverySynthesisOrder.target_color.is_(None),
                DiscoverySynthesisOrder.target_color == "",
            )
        )
    if not clauses:
        return None
    return clauses[0] if len(clauses) == 1 else or_(*clauses)


def _target_clause(db: Session | None, names: Any):
    return recorded_target_clause(
        db,
        DiscoverySynthesisOrder.target_name,
        DiscoverySynthesisOrder.target_codes,
        names,
        select(DiscoverySynthesisOrder.target_name, DiscoverySynthesisOrder.target_codes),
    )


def _status_values(db: Session, scoped, keyword: str, *, combos: bool) -> list[dict[str, Any]]:
    """主状态之后列出检测中/待检测行的亲和力、流式子状态，计数口径与筛选一致；combos 再列亲和力×流式组合。"""
    columns = (
        DiscoverySynthesisOrder.status,
        DiscoverySynthesisOrder.affinity_status,
        DiscoverySynthesisOrder.flow_status,
    )
    counts: Counter[str] = Counter()
    for status, affinity, flow, count in db.execute(scoped(select(*columns, func.count()).group_by(*columns))).all():
        counts[status] += count
        if status in (STATUS_WAIT_ASSAY, STATUS_ASSAYING):
            counts[affinity] += count
            counts[flow] += count
            counts[_assay_combo_term(affinity, flow)] += count
    values = (*STATUS_OPTIONS, *AFFINITY_STATUS_OPTIONS, *FLOW_STATUS_OPTIONS, *(ASSAY_COMBO_TERMS if combos else ()))
    text = keyword.lower()
    return [
        {"value": value, "count": counts[value]}
        for value in values
        if counts.get(value) and (not text or text in value.lower())
    ]


_O = DiscoverySynthesisOrder
HEADER_COLUMNS: dict[str, HeaderColumn] = {
    "priority": HeaderColumn(_O.priority, "enum", order=tuple(PRIORITY_ORDER)),
    "status": HeaderColumn(
        _O.status,
        "multi",
        order=tuple(STATUS_OPTIONS),
        match=lambda _db, terms: _status_terms_clause(terms),
        values=partial(_status_values, combos=False),
    ),
    "target_name": target_column(_O.target_name, _O.target_codes, colors=_target_color_clause),
    "target_codes": json_array_column(_O.target_codes),
    "target_type": HeaderColumn(_O.target_type, "enum", order=tuple(TARGET_TYPE_OPTIONS)),
    "mouse_strain": csv_column(_O.mouse_strain, tuple(MOUSE_STRAIN_OPTIONS)),
    "selection_method": csv_column(_O.selection_method, tuple(SELECTION_METHOD_OPTIONS)),
    "is_rechoose": HeaderColumn(_O.is_rechoose, "enum", order=RECHOOSE_OPTIONS),
    "synthesis_code": HeaderColumn(_O.synthesis_code),
    "order_no": HeaderColumn(_O.order_no),
    "batch_label": HeaderColumn(_O.batch_label),
    "synthetic_count": HeaderColumn(_O.synthetic_count, "number"),
    "synthetic_date": HeaderColumn(_O.synthetic_date, "date"),
    "order_sender": HeaderColumn(_O.order_sender, "enum"),
    "arrival_count": HeaderColumn(_O.arrival_count, "number"),
    "arrival_date": HeaderColumn(_O.arrival_date, "date"),
    "affinity_date": HeaderColumn(_O.affinity_date, "date"),
    "flow_date": HeaderColumn(_O.flow_date, "date"),
    "affinity_owner": csv_column(_O.affinity_owner),
    "affinity_result": HeaderColumn(_O.affinity_result, "enum", order=tuple(AFFINITY_RESULT_OPTIONS)),
    "owner": HeaderColumn(_O.owner, "enum", order=(UNCLAIMED_OWNER,)),
    "remark": HeaderColumn(_O.remark),
    "report_reason": HeaderColumn(_O.report_reason),
    "flow_note": HeaderColumn(_O.flow_note),
    "synthetic_corp": HeaderColumn(_O.synthetic_corp, "enum", order=tuple(SYNTHETIC_CORP_OPTIONS)),
    "order_kind": HeaderColumn(_O.order_kind, "enum", order=tuple(ORDER_KIND_OPTIONS)),
    "supply_mode": HeaderColumn(_O.supply_mode, "enum", order=tuple(SUPPLY_MODE_OPTIONS)),
    "project_code": HeaderColumn(_O.project_code),
    "pm": HeaderColumn(_O.pm, "enum"),
    "study_type": HeaderColumn(_O.study_type, "enum"),
    "eng_type": csv_column(_O.eng_type, tuple(ENG_TYPE_OPTIONS)),
    "eng_method": csv_column(_O.eng_method, tuple(ENG_METHOD_OPTIONS)),
    "eng_parent_seq": HeaderColumn(_O.eng_parent_seq),
    "eng_requirement": HeaderColumn(_O.eng_requirement),
    "eng_result": HeaderColumn(_O.eng_result),
}
# 待测视图子弹窗的计数：在状态列取值之外再按亲和力×流式组合计数，只供取值，不参与表头筛选和排序
STATUS_BREAKDOWN_FIELD = "status_breakdown"
VALUE_COLUMNS: dict[str, HeaderColumn] = {
    **HEADER_COLUMNS,
    STATUS_BREAKDOWN_FIELD: replace(HEADER_COLUMNS["status"], values=partial(_status_values, combos=True)),
}


def _apply_list_filters(
    stmt,
    data: dict[str, Any],
    *,
    apply_view: bool = True,
    apply_quick: bool = True,
    db: Session | None = None,
    header_except: str | None = None,
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
                DiscoverySynthesisOrder.flow_note.like(like),
                DiscoverySynthesisOrder.report_reason.like(like),
                DiscoverySynthesisOrder.remark.like(like),
            )
        )

    target_clause = _target_clause(db, data.get("target_name"))
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

    status_clause = _status_filter_clause(data)
    if status_clause is not None:
        filters.append(status_clause)

    priority_clause = combine_any(
        data.get("priority"),
        lambda val: DiscoverySynthesisOrder.priority == normalize_priority(val),
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

    sender_clause = match_any(DiscoverySynthesisOrder.order_sender, data.get("order_sender"))
    if sender_clause is not None:
        filters.append(sender_clause)

    aff_owner_terms = filter_terms(data.get("affinity_owner"))
    if aff_owner_terms:
        filters.append(or_(*[csv_token_clause(DiscoverySynthesisOrder.affinity_owner, t) for t in aff_owner_terms]))

    rechoose_clause = match_any(DiscoverySynthesisOrder.is_rechoose, data.get("is_rechoose"))
    if rechoose_clause is not None:
        filters.append(rechoose_clause)

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
            filters.append(or_(*[csv_token_clause(col, item) for item in tokens]))

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
        "flow_note",
        "report_reason",
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
            filters.append(date_col >= normalize_date(s_raw))
        if e_raw not in (None, ""):
            filters.append(date_col <= normalize_date(e_raw))

    filters.extend(
        header_filter_clauses(
            db,
            HEADER_COLUMNS,
            data.get("field_filters"),
            except_field=header_except,
        )
    )

    if apply_view:
        view_group = str(data.get("view_group") or "").strip()
        if view_group == "wait_order":
            filters.append(DiscoverySynthesisOrder.status == STATUS_WAIT_ORDER)
        elif view_group == "synthesizing":
            filters.append(DiscoverySynthesisOrder.status == STATUS_SYNTHESIZING)
        elif view_group == "assay":
            filters.append(
                DiscoverySynthesisOrder.status.in_(
                    (STATUS_WAIT_ASSAY, STATUS_ASSAYING)
                )
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


def _list_order(data: dict[str, Any] | None = None):
    payload = data or {}
    field = str(payload.get("sort_field") or "").strip()
    direction = str(payload.get("sort_dir") or "desc").strip().lower()
    spec = HEADER_COLUMNS.get(field)
    if spec is not None and direction in {"asc", "desc"}:
        return header_sort_clauses(spec, direction, DiscoverySynthesisOrder.id)
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
    lock_queue(db, DiscoverySynthesisOrder)


def settle_queue_after_sync(db: Session) -> None:
    """外部同步可能把行改成终态：在队列锁内让终态出队并重编，与同步改动同一次提交。"""
    _lock_queue(db)
    db.flush()
    for row in db.scalars(
        select(DiscoverySynthesisOrder).where(
            DiscoverySynthesisOrder.status.in_((STATUS_COMPLETED, STATUS_CANCELLED)),
            DiscoverySynthesisOrder.sort_order.is_not(None),
        )
    ).all():
        row.sort_order = None
    renumber_queue(_queue_rows(db))


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
            renumber_queue(
                [item for item in _queue_rows(db) if int(item.id) != int(row.id or 0)]
            )
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


def get_column_values(db: Session, data: dict[str, Any]) -> dict[str, Any]:
    return header_column_values(
        db,
        VALUE_COLUMNS,
        data,
        lambda stmt, payload, field: _apply_list_filters(
            stmt, payload, db=db, header_except="status" if field == STATUS_BREAKDOWN_FIELD else field
        ),
        id_column=DiscoverySynthesisOrder.id,
    )


def search_recorded_targets(db: Session, keyword: str = "", limit: int = DEFAULT_RECORDED_TARGET_LIMIT) -> list[dict]:
    return recorded_target_search(
        db,
        select(DiscoverySynthesisOrder.target_name, DiscoverySynthesisOrder.target_codes),
        keyword,
        limit,
    )


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
            found.update(split_tokens(val))
        ordered = list(presets)
        extras = sorted(item for item in found if item not in set(presets))
        return [*ordered, *extras]

    def used_names(column, presets: tuple[str, ...] = ()) -> list[str]:
        counts: Counter[str] = Counter()
        rows = db.execute(select(column, func.count()).where(func.coalesce(column, "") != "").group_by(column))
        for raw, count in rows.all():
            for name in split_tokens(raw):
                counts[name] += count
        ordered = sorted(counts, key=lambda name: (-counts[name], name))
        return [*presets, *(name for name in ordered if name not in presets)]

    return {
        "statuses": list(STATUS_OPTIONS),
        "affinity_statuses": list(AFFINITY_STATUS_OPTIONS),
        "flow_statuses": list(FLOW_STATUS_OPTIONS),
        "priorities": list(PRIORITY_OPTIONS),
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
        "owners": used_names(DiscoverySynthesisOrder.owner, (UNCLAIMED_OWNER,)),
        "pms": used_names(DiscoverySynthesisOrder.pm),
        "order_senders": used_names(DiscoverySynthesisOrder.order_sender),
        "affinity_owners": used_names(DiscoverySynthesisOrder.affinity_owner),
    }


def _infer_target_type(db: Session, target_codes: Any) -> str | None:
    codes = normalize_target_codes(target_codes, upper=True)
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
    for field in WRITABLE_FIELDS:
        if field not in data:
            continue
        raw = data.get(field)
        if field == "status":
            value: Any = _normalize_status(raw)
        elif field == "affinity_status":
            value = _normalize_affinity_status(raw)
        elif field == "flow_status":
            value = _normalize_flow_status(raw)
        elif field == "priority":
            value = normalize_priority(raw)
        elif field == "sort_order":
            if raw in (None, "", "-"):
                continue
            value = normalize_positive_int(raw, "排序必须是正整数")
        elif field == "order_kind":
            value = _normalize_order_kind(raw)
        elif field == "supply_mode":
            value = _normalize_supply_mode(raw)
        elif field == "affinity_result":
            value = _normalize_affinity_result(raw)
        elif field == "target_color":
            value = _normalize_target_color(raw)
        elif field == "is_rechoose":
            value = normalize_choice(raw, RECHOOSE_OPTIONS, "是否补挑", nullable=True)
        elif field == "target_codes":
            value = normalize_target_codes(raw, upper=True)
        elif field in CSV_JOINED_FIELDS:
            opts, max_len, label = CSV_JOINED_FIELDS[field]
            value = _normalize_csv_joined(raw, opts, max_len, label)
        elif field in INT_COUNT_FIELDS:
            value = normalize_nonneg_int(raw, INT_COUNT_FIELDS[field])
        elif field in DATE_FIELDS:
            value = normalize_date(raw)
        else:
            value = normalize_text(
                raw,
                STRING_FIELDS[field],
                keep_breaks=field in BREAK_FIELDS,
            )
        setattr(row, field, value)

    if "affinity_date" in data and not row.affinity_date and "affinity_result" not in data:
        row.affinity_result = None

    methods = split_tokens(row.selection_method)
    if "selection_method" in data and RECHOOSE_TOKEN in methods:
        row.selection_method = join_tokens([m for m in methods if m != RECHOOSE_TOKEN], SELECTION_METHOD_OPTIONS)
        if "is_rechoose" not in data:
            row.is_rechoose = "是"

    # 订单号决定关联哪笔 One 订单；工单批次、送测转码允许与 One 不一致，改了不解除关联。
    if row.source_one_id is not None and "order_no" in data and row.order_no != prev_order_no:
        row.source_one_type = None
        row.source_one_id = None
        row.order_sender = None
        if not any((row.order_no, row.synthesis_code, row.batch_label)):
            row.source_snapshot = None


def save(
    db: Session,
    data: dict[str, Any],
    created_by: str | None = None,
    *,
    commit: bool = True,
    lock_queue: bool = True,
    scopes: frozenset[str] = frozenset({"full"}),
    require_fields: bool = False,
    confirm_complete: bool = True,
) -> dict[str, Any]:
    payload = dict(data or {})
    payload.pop("synthesis_order_id", None)
    row_id = _parse_row_id(payload.get("id"))
    if payload.get("id") not in (None, "") and row_id is None:
        raise ValueError("合成与验证记录 ID 不正确")

    actor_person = clean_actor_person_name(created_by)
    is_new = row_id is None
    writable_keys = {key for key in payload if key != "id" and key in WRITABLE_FIELDS}
    eng_keys: set[str] = set()
    if "full" not in scopes:
        if is_new and not scopes.intersection({"pm", "eng"}):
            raise PermissionError("当前权限不能新建合成与验证工单")
        allowed_fields: set[str] = set()
        for scope, fields in SCOPE_EDIT_FIELDS.items():
            if scope in scopes:
                allowed_fields.update(fields)
        if ASSAY_SCOPES <= scopes and not is_new:
            allowed_fields.add("status")
        if not allowed_fields:
            raise PermissionError("没有权限编辑合成与验证工单")
        if writable_keys - allowed_fields:
            raise PermissionError("当前权限不可修改该字段")
        if is_new and normalize_text(payload.get("owner"), STRING_FIELDS["owner"]):
            raise PermissionError("负责人需通过认领设置")

    if lock_queue and (is_new or QUEUE_LOCK_FIELDS.intersection(payload)):
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
        if "full" not in scopes:
            pm_fields: frozenset[str] = frozenset()
            if "pm" in scopes:
                pm_fields = PM_EDIT_FIELDS if pm_owns_row(row, actor_person) else frozenset({"owner"})
            pm_keys = writable_keys & pm_fields
            if _eng_covers(row, scopes):
                eng_keys = (writable_keys - pm_keys) & ENG_EDIT_FIELDS
            assay_keys = set()
            if "affinity" in scopes:
                assay_keys |= AFFINITY_EDIT_FIELDS
            if "flow" in scopes:
                assay_keys |= FLOW_EDIT_FIELDS
            if ASSAY_SCOPES <= scopes and "status" in writable_keys - eng_keys:
                if (row.status or "").strip() != STATUS_COMPLETED or _normalize_status(
                    payload["status"]
                ) != STATUS_WAIT_ASSAY:
                    raise PermissionError(ASSAY_MAIN_STATUS_MESSAGE)
                assay_keys.add("status")
            denied = writable_keys - pm_keys - eng_keys - assay_keys
            if denied:
                pm_denied = "pm" in scopes and denied <= PM_EDIT_FIELDS
                raise PermissionError(pm_ownership_message(row) if pm_denied else ENG_ROW_MESSAGE)
            if "owner" in payload:
                cur_owner = str(row.owner or "").strip()
                next_owner = normalize_text(payload.get("owner"), STRING_FIELDS["owner"]) or ""
                if next_owner != cur_owner:
                    _check_pm_owner_change(row, cur_owner, next_owner, actor_person)
        previous_sort = queued_sort(row.sort_order)
        previous_priority = row.priority or DEFAULT_PRIORITY

    if "affinity_status" in payload or "flow_status" in payload:
        if is_new:
            raise ValueError("请先创建工单，再修改实验状态")
        if (row.status or "").strip() == STATUS_CANCELLED:
            raise ValueError("已取消工单不可修改实验状态")
        if (row.status or "").strip() == STATUS_COMPLETED and "status" not in payload:
            raise ValueError(COMPLETED_ASSAY_MESSAGE)
        _validate_assay_status_edits(
            row, payload, can_close_with_reason="full" in scopes or ASSAY_SCOPES <= scopes
        )

    previous_target_type = (row.target_type or "").strip()
    previous_owner = row.owner
    previous_status = (row.status or "").strip()
    had_reason = bool(str(row.report_reason or "").strip())
    _apply_fields(row, payload)
    _touch_owner_claim(row, previous_owner)
    # 只替亲和力实验员补空的亲和力人员，管理员改状态不会把自己加进去
    if (
        actor_person
        and "affinity" in scopes
        and "full" not in scopes
        and "affinity_owner" not in payload
        and not row.affinity_owner
        and (
            ("affinity_date" in payload and row.affinity_date)
            or ("affinity_status" in payload and row.affinity_status == AFFINITY_STATUS_ASSAYING)
        )
    ):
        row.affinity_owner = actor_person
    if "target_codes" in payload and "target_type" not in payload:
        row.target_type = _infer_target_type(db, row.target_codes)
    secreted = (row.target_type or "").strip() == "分泌型"
    if "status" in payload and row.status in {STATUS_WAIT_ASSAY, STATUS_ASSAYING}:
        # 手动进入检测阶段时两项实验从待测开始，之后改订单号、One 回填等不会退回合成阶段；
        # 从已完成打回即重做，两项一并回到待测（流式不做的保留），日期和人员留作记录
        reopen = previous_status == STATUS_COMPLETED
        if reopen or not row.affinity_status:
            row.affinity_status = AFFINITY_STATUS_WAIT
        if not row.flow_status or (reopen and row.flow_status != FLOW_STATUS_NOT_REQUIRED):
            row.flow_status = FLOW_STATUS_NOT_REQUIRED if secreted else FLOW_STATUS_WAIT
    if "status" not in payload and (is_new or AUTO_STATUS_FIELDS.intersection(payload)):
        changed = set(payload) - {"target_type"}
        if secreted != (previous_target_type == "分泌型"):
            # 只有要不要做流式变了才算靶点类型变化
            changed.add("target_type")
        reason_added = not had_reason and bool(str(row.report_reason or "").strip())
        sync_derived_statuses(row, changed_fields=changed, reason_added=reason_added)
    if "full" not in scopes and not is_engineering_row(row) and (
        eng_keys or (is_new and ("pm" not in scopes or (writable_keys & ENG_EDIT_FIELDS) - PM_EDIT_FIELDS))
    ):
        raise PermissionError(ENG_ROW_MESSAGE)

    eng_create = is_new and "full" not in scopes and _eng_covers(row, scopes)
    if eng_create:
        row.order_sender = (created_by or "").strip()[:128] or None
    if is_new and is_engineering_row(row) and not row.synthetic_corp:
        row.synthetic_corp = INTERNAL_CORP
    if actor_person and is_new and "full" not in scopes and not (eng_create and row.pm):
        row.pm = actor_person
    elif actor_person and not row.pm and (
        (is_new and row.order_kind == ORDER_KIND_ENGINEERING)
        or payload.get("order_kind") == ORDER_KIND_ENGINEERING
    ):
        row.pm = actor_person
    if is_new and require_fields:
        missing = _missing_create_fields(row, payload)
        if missing:
            raise ValueError(f"请先填写必填项：{'、'.join(missing)}")
    if (
        not (confirm_complete or is_new or "status" in payload)
        and previous_status != STATUS_COMPLETED
        and row.status == STATUS_COMPLETED
    ):
        raise CompletionConfirmRequired(_completion_confirm_message(row, scopes))

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
    require_fields: bool = False,
    confirm_complete: bool = True,
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
        if row_id is None or QUEUE_LOCK_FIELDS.intersection(item):
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
                require_fields=require_fields,
                confirm_complete=confirm_complete,
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
    *,
    scopes: frozenset[str] = frozenset({"full"}),
) -> dict[str, Any]:
    """全部编辑权限在空白与「无人问津」间切换（开放/撤回认领）；PM 认领「无人问津」或在 7 天内退回本人批次。"""
    row = db.get(DiscoverySynthesisOrder, int(row_id), with_for_update=True)
    if not row:
        raise ValueError(MISSING_ROW)
    cur_owner = str(row.owner or "").strip()
    if "full" in scopes:
        if cur_owner not in {"", UNCLAIMED_OWNER}:
            raise ValueError(f"该批次已由 {cur_owner} 负责，如需调整请直接修改负责人")
        row.owner = None if cur_owner else UNCLAIMED_OWNER
    else:
        person = clean_actor_person_name(actor_name)
        if not person:
            raise ValueError("无法识别当前认领人姓名")
        if cur_owner == UNCLAIMED_OWNER:
            row.owner = person
        elif cur_owner == person:
            if not _can_return_claim(row):
                raise ValueError(CLAIM_RETURN_EXPIRED_MESSAGE)
            row.owner = UNCLAIMED_OWNER
        elif not cur_owner:
            raise ValueError("该批次尚未开放认领，标记为「无人问津」后才能认领")
        else:
            raise ValueError(f"该批次已被 {cur_owner} 认领，不可重复认领")
    _touch_owner_claim(row, cur_owner)
    db.commit()
    db.refresh(row)
    return serialize_order(row)


def delete(
    db: Session,
    row_id: int,
    *,
    scopes: frozenset[str] = frozenset({"full"}),
    actor_name: str | None = None,
) -> None:
    _lock_queue(db)
    row = db.get(DiscoverySynthesisOrder, int(row_id))
    if not row:
        raise ValueError(MISSING_ROW)
    if row.source_one_id is not None:
        raise ValueError("该工单已关联 One 订单，不能删除；不再需要时请把状态改为「已取消」")
    error = _row_manage_error(row, scopes, clean_actor_person_name(actor_name))
    if error:
        raise PermissionError(error)
    if "full" not in scopes and not _eng_covers(row, scopes) and row.status != STATUS_WAIT_ORDER:
        raise PermissionError("PM 权限只能删除待下单状态的工单")
    db.delete(row)
    db.flush()
    renumber_queue(_queue_rows(db))
    db.commit()


def reorder(
    db: Session,
    moved_id: Any,
    target_id: Any,
    *,
    scopes: frozenset[str] = frozenset({"full"}),
    actor_name: str | None = None,
) -> dict[str, Any]:
    _lock_queue(db)
    parsed_moved_id = _parse_row_id(moved_id)
    parsed_target_id = _parse_row_id(target_id)
    if parsed_moved_id is None or parsed_target_id is None:
        raise ValueError("排序记录 ID 不正确")
    moved = db.get(DiscoverySynthesisOrder, parsed_moved_id)
    target = db.get(DiscoverySynthesisOrder, parsed_target_id)
    if not moved or not target:
        raise ValueError(MISSING_ROW)
    error = _row_manage_error(moved, scopes, clean_actor_person_name(actor_name))
    if error:
        raise PermissionError(error)
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
    target_fields = (
        [f for f in fields if f in DRIFT_COMPARE_FIELDS]
        if fields
        else list(DRIFT_COMPARE_FIELDS)
    )
    if not target_fields:
        raise ValueError("未指定可采用的来源字段")
    rederive = bool({"order_no", "arrival_date"}.intersection(target_fields))
    if rederive:
        _lock_queue(db)
    row = db.get(DiscoverySynthesisOrder, int(row_id))
    if not row:
        raise ValueError(MISSING_ROW)
    snapshot = row.source_snapshot if isinstance(row.source_snapshot, dict) else {}
    if not snapshot:
        raise ValueError("该记录没有可用的外部来源快照")

    for field in target_fields:
        remote_val = snapshot.get(field)
        if remote_val in (None, ""):
            continue
        setattr(row, field, remote_val)

    if rederive:
        previous_sort = queued_sort(row.sort_order)
        sync_derived_statuses(row)
        _apply_queue(
            db,
            row,
            previous_sort=previous_sort,
            previous_priority=row.priority,
            payload={},
            is_new=False,
        )
    db.commit()
    db.refresh(row)
    return serialize_order(row)


_SIBLING_COPY_FIELDS = ("priority", "pm", "project_code", "experiment_id", "study_type", "mouse_strain")
_STRAIN_KEY_TAIL_RE = re.compile(r"(?:[SAPCDM]\d+|\d+)$")


def _strain_key(synthesis_code: Any) -> str:
    """送测转码去掉靶点段与批次后缀后的品系标记，如 20R430_RM_C_W_S1 -> RMCW。"""
    parts = str(synthesis_code or "").split("_", 1)
    if len(parts) < 2:
        return ""
    return _STRAIN_KEY_TAIL_RE.sub("", re.sub(r"[^A-Z0-9]", "", parts[1].upper()))


def _mouse_strain_guesser(db: Session):
    counts: dict[str, Counter] = defaultdict(Counter)
    rows = db.execute(
        select(DiscoverySynthesisOrder.synthesis_code, DiscoverySynthesisOrder.mouse_strain).where(
            DiscoverySynthesisOrder.synthesis_code.is_not(None),
            DiscoverySynthesisOrder.mouse_strain.is_not(None),
        )
    ).all()
    for code, strain in rows:
        key = _strain_key(code)
        if key and strain in MOUSE_STRAIN_OPTIONS:
            counts[key][strain] += 1

    def guess(synthesis_code: Any) -> str | None:
        hits = counts.get(_strain_key(synthesis_code))
        return hits.most_common(1)[0][0] if hits else None

    return guess


def _payload_from_snapshot(db: Session, snap: dict[str, Any], guess_strain) -> dict[str, Any]:
    """One 新订单建行时的字段：执行信息取 One，项目信息沿用同批次已有行，靶点优先取 One。"""
    payload = {f: snap[f] for f in SNAPSHOT_STORED_FIELDS if snap.get(f) not in (None, "")}
    clauses = [
        column == value
        for column, value in (
            (DiscoverySynthesisOrder.batch_label, snap.get("batch_label")),
            (DiscoverySynthesisOrder.synthesis_code, snap.get("synthesis_code")),
        )
        if value
    ]
    sibling = (
        db.scalars(
            select(DiscoverySynthesisOrder)
            .where(or_(*clauses))
            .order_by(DiscoverySynthesisOrder.id.desc())
            .limit(1)
        ).first()
        if clauses
        else None
    )
    if sibling is not None:
        for field in _SIBLING_COPY_FIELDS:
            value = getattr(sibling, field)
            if value not in (None, ""):
                payload[field] = value

    codes, name = parse_one_target(snap.get("task_target"), snap.get("task_projectcode"), snap.get("synthesis_code"))
    if codes:
        known = db.scalar(select(Target.name).where(Target.snum == codes[0])) if len(codes) == 1 else None
        payload["target_codes"] = codes
        if known or name:
            payload["target_name"] = (known or name)[: STRING_FIELDS["target_name"]]
    elif sibling is not None and sibling.target_name:
        payload["target_name"] = sibling.target_name
        payload["target_codes"] = sibling.target_codes
        if sibling.target_type:
            payload["target_type"] = sibling.target_type
    elif name:
        payload["target_name"] = name[: STRING_FIELDS["target_name"]]

    if not payload.get("mouse_strain"):
        strain = guess_strain(snap.get("synthesis_code"))
        if strain:
            payload["mouse_strain"] = strain
    return payload


def _apply_new_remote_orders(
    db: Session,
    creates: list[dict[str, Any]],
    relinks: list[tuple[DiscoverySynthesisOrder, dict[str, Any]]],
) -> int:
    for row, snap in relinks:
        previous = dict(row.source_snapshot) if isinstance(row.source_snapshot, dict) else None
        row.source_one_type = snap["source_one_type"]
        row.source_one_id = snap["source_one_id"]
        apply_remote_snapshot_to_row(row, snap, replace_from_snapshot=previous)

    created = 0
    if creates:
        _lock_queue(db)
        guess_strain = _mouse_strain_guesser(db)
        for snap in creates:
            try:
                with db.begin_nested():
                    saved = save(
                        db,
                        _payload_from_snapshot(db, snap, guess_strain),
                        created_by=ONE_AUTO_CREATED_BY,
                        commit=False,
                        lock_queue=False,
                    )
                    row = db.get(DiscoverySynthesisOrder, saved["id"])
                    row.source_one_type = snap["source_one_type"]
                    row.source_one_id = snap["source_one_id"]
                    apply_remote_snapshot_to_row(row, snap)
                    db.flush()
                created += 1
            except ValueError:
                logger.warning(
                    "skip auto-create from One %s:%s",
                    snap.get("source_one_type"),
                    snap.get("source_one_id"),
                    exc_info=True,
                )
    db.commit()
    return created


def sync_from_one(db: Session) -> dict[str, Any]:
    """核对并回填本地未完结工单，再把 One 新出现、本地还没有的订单建成新行。"""
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
    skipped = {"skipped": True, "message": "未配置或无法连接 ONE_DB_URL，已跳过外部同步"}
    total_linked = total_updated = 0
    if candidate_rows:
        res = check_remote_for_local_rows(
            db,
            rows=candidate_rows,
            connect_timeout=3,
            read_timeout=15,
            serialize_changed=False,
        )
        if not res.get("remote_available"):
            return skipped
        total_linked = int(res.get("linked") or 0)
        total_updated = int(res.get("updated") or 0)

    pending = collect_new_remote_orders(db, ONE_AUTO_CREATE_SINCE)
    if pending is None and not candidate_rows:
        return skipped
    creates, relinks = pending or ([], [])
    created = _apply_new_remote_orders(db, creates, relinks) if creates or relinks else 0

    total_checked = len(candidate_rows)
    return {
        "linked": total_linked + len(relinks),
        "created": created,
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
    ("是否补挑", "is_rechoose"),
    ("送测转码", "synthesis_code"),
    ("订单号", "order_no"),
    ("工单批次", "batch_label"),
    ("合成个数", "synthetic_count"),
    ("合成日期", "synthetic_date"),
    ("到货个数", "arrival_count"),
    ("到货日期", "arrival_date"),
    ("检测备注", "remark"),
    ("亲和力状态", "affinity_status"),
    ("亲和力人员", "affinity_owner"),
    ("亲和力日期", "affinity_date"),
    ("亲和力结果", "affinity_result"),
    ("未出原因", "report_reason"),
    ("流式状态", "flow_status"),
    ("流式日期", "flow_date"),
    ("流式说明", "flow_note"),
    ("负责人", "owner"),
    ("合成公司", "synthetic_corp"),
    ("下单人", "order_sender"),
    ("订单性质", "order_kind"),
    ("供应方式", "supply_mode"),
    ("靶点编号", "target_codes"),
    ("项目编号", "project_code"),
    ("PM", "pm"),
    ("课题类型", "study_type"),
    ("改造类型", "eng_type"),
    ("改造方式", "eng_method"),
    ("改造序列或母本", "eng_parent_seq"),
    ("改造要求", "eng_requirement"),
    ("改造结果", "eng_result"),
)


def export_list_workbook(
    db: Session,
    data: dict[str, Any],
    *,
    hide_corp: bool = False,
    keep_engineering_rows: bool = False,
) -> tuple[BytesIO, str]:
    payload = data or {}
    stmt = _apply_list_filters(select(DiscoverySynthesisOrder), payload, db=db)
    rows = db.scalars(stmt.order_by(*_list_order(payload))).all()
    headers = [header for header, _ in EXPORT_COLUMNS]

    def cell(row: DiscoverySynthesisOrder, field: str) -> Any:
        value = getattr(row, field)
        masked = hide_corp and not (keep_engineering_rows and is_engineering_row(row))
        return CORP_MASK if masked and field == "synthetic_corp" and value else value

    body = [[cell(row, field) for _, field in EXPORT_COLUMNS] for row in rows]
    return build_list_workbook(
        sheet_title="合成与验证",
        filename_prefix="合成与验证",
        headers=headers,
        rows=body,
    )


__all__ = [
    "AFFINITY_EDIT_FIELDS",
    "CompletionConfirmRequired",
    "FLOW_EDIT_FIELDS",
    "MISSING_ROW",
    "PM_EDIT_FIELDS",
    "adopt_source",
    "check_remote_for_local_rows",
    "claim_order",
    "delete",
    "export_list_workbook",
    "get_list",
    "get_options",
    "mask_synthetic_corp",
    "reorder",
    "save",
    "save_batch",
    "serialize_order",
    "sync_from_one",
    "without_corp_query",
]
