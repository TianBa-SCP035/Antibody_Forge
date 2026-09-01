import hashlib
import json
import secrets
import string
from copy import deepcopy
from datetime import datetime
from io import BytesIO
from typing import Any

from sqlalchemy import String, and_, case, cast, exists, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from models.immunology import (
    SerumElisaPlate,
    SerumFacsPlate,
    SerumImmAntigen,
    SerumImmMouse,
    SerumImmProject,
    SerumImmStep,
    SerumImmWorkbench,
    SerumTiterOrder,
    SerumTiterPc,
    SerumTiterTarget,
)
from modules.immunology.serum.service import (
    EXPERIMENT_RELATED_MODELS,
    TERMINAL_PROJECT_STATUSES,
    generate_next_id,
    rename_experiment_related_records,
    update_project_identifiers,
)

PLAN_STATUS_DRAFT = "草稿"
PLAN_STATUS_PREP = "筹备中"
PLAN_STATUS_STARTED = "已开展"
PLAN_STATUS_CANCELLED = "已取消"
CLOSED_PLAN_STATUSES = frozenset({PLAN_STATUS_CANCELLED, "小鼠KO致死"})
EDITABLE_PLAN_STATUSES = frozenset({PLAN_STATUS_DRAFT, PLAN_STATUS_PREP, *CLOSED_PLAN_STATUSES})
DEFAULT_PRIORITY = "正常"
PRIORITY_ORDER = ("吉吉国王", "非常紧急", "加急", "正常")
DEFAULT_REVIEW_STATUS = "未审"
REVIEW_STATUS_OPTIONS = ("未审", "已通过", "驳回")
DEFAULT_MOUSE_STATUS = "未定"
MOUSE_STATUS_OPTIONS = ("未定", "扩繁中", "可运", "在途", "已到")
MOUSE_STRAIN_CATEGORY_OPTIONS = (
    "RL-KO",
    "RN-KO",
    "RM-KO",
    "RL",
    "RN",
    "RM",
    "RN-VM",
    "RN-VR",
    "RN-VM-KO",
)
MOUSE_REGION_OPTIONS = ("北京", "海门", "苏州", "客户")
REQUIRED_YES_NO_DEFAULTS = {"antigen_ready": "否", "can_start": "否"}
SPECIES_CROSS_OPTIONS = ("人", "猴", "鼠", "狗", "猫", "空白")
DEFAULT_PROJECT_STATUS = "规划中"
TEMP_ID_RANDOM_LEN = 4
TEMP_ID_MAX_ATTEMPTS = 8
TEMP_ID_ALPHABET = string.ascii_uppercase + string.digits

ALIGNED_FIELDS = [
    "experiment_id",
    "project_code",
    "project_name",
    "project_purpose",
    "start_date",
    "immunization_interval",
    "target_codes",
    "target_name",
    "target_type",
    "target_size",
    "owner",
    "pm",
    "study_type",
    "assay_method",
    "facs_plate_count",
    "elisa_plate_count",
    "remark",
    "mouse_strain",
    "mouse_strain_category",
]
STRAIN_FIELDS = ("mouse_strain", "mouse_strain_category")
SCHEME_HEADER_FIELDS = [
    field
    for field in ALIGNED_FIELDS
    if field != "experiment_id" and field not in STRAIN_FIELDS
]

PREP_FIELDS = [
    "sort_order",
    "priority",
    "plan_status",
    "project_set_code",
    "species_cross",
    "immuno_method",
    "reviewer",
    "review_status",
    "mouse_scheme_no",
    "mouse_count",
    "mouse_zygosity",
    "mouse_birth_date",
    "mouse_age_weeks",
    "mouse_expand_requested",
    "mouse_region",
    "mouse_room",
    "mouse_status",
    "mouse_arrive_date",
    "mouse_remark",
    "antigen_source",
    "antigen_ready",
    "antigen_eta",
    "lnp_ordered",
    "cell_prep_status",
    "antigen_remark",
    "can_start",
]

WORKBENCH_MUTABLE_FIELDS = frozenset(ALIGNED_FIELDS + PREP_FIELDS)
DRAFT_PROTECTED_FIELDS = frozenset(
    {"plan_status", "reviewer", "review_status", "can_start"}
)
SUPPORT_EDIT_FIELDS = frozenset(
    {
        "mouse_scheme_no",
        "mouse_count",
        "mouse_zygosity",
        "mouse_birth_date",
        "mouse_age_weeks",
        "mouse_expand_requested",
        "mouse_region",
        "mouse_room",
        "mouse_status",
        "mouse_arrive_date",
        "mouse_remark",
        "antigen_source",
        "antigen_ready",
        "antigen_eta",
        "lnp_ordered",
        "cell_prep_status",
        "antigen_remark",
    }
)
WORKBENCH_REMARK_FIELDS = frozenset({"remark", "mouse_remark", "antigen_remark"})

YES_NO_FIELDS = frozenset(
    {"can_start", "antigen_ready", "lnp_ordered", "mouse_expand_requested"}
)
INT_FIELDS = frozenset({"sort_order", "facs_plate_count", "elisa_plate_count"})
READONLY_RESPONSE_KEYS = frozenset(
    {
        "experiment_id",
        "created_by",
        "created_at",
        "updated_at",
        "display_status",
        "serum_project_id",
        "aligned_locked",
        "mouse_groups",
        "antigens",
        "steps",
        "titer_targets",
        "titer_pcs",
        "scheme_revision",
    }
)
COPY_CHILD_MODELS = [
    (SerumImmMouse, "id"),
    (SerumImmAntigen, "id"),
    (SerumImmStep, "step_id"),
    (SerumTiterTarget, "id"),
    (SerumTiterPc, "id"),
]
COPY_HEADER_FIELDS = [
    "project_name",
    "project_purpose",
    "immunization_interval",
    "target_codes",
    "target_name",
    "target_type",
    "target_size",
    "pm",
    "study_type",
    "assay_method",
    "facs_plate_count",
    "elisa_plate_count",
    "remark",
    "mouse_strain",
    "mouse_strain_category",
    "species_cross",
    "immuno_method",
    "mouse_zygosity",
]
COPY_CHILD_CLEAR_FIELDS = {
    SerumImmMouse: ("mouse_no_list", "mouse_registry", "cage_position"),
    SerumImmStep: ("date_actual",),
}


def _compact_identifier(raw: Any) -> str:
    return "".join(str(raw or "").split())


def _normalize_yes_no(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    return text


def _normalize_target_codes(value: Any) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError("靶点编号必须是数组")
    return [str(item).strip() for item in value if str(item).strip()]


def _normalize_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _new_temp_experiment_id() -> str:
    now = datetime.now()
    rand = "".join(secrets.choice(TEMP_ID_ALPHABET) for _ in range(TEMP_ID_RANDOM_LEN))
    return f"SCP-{now:%Y%m%d}-{now:%H%M%S}-{rand}"


def _assign_temp_experiment_id(db: Session, row: SerumImmWorkbench) -> None:
    if str(row.experiment_id or "").strip():
        return
    last_error: Exception | None = None
    for _ in range(TEMP_ID_MAX_ATTEMPTS):
        try:
            with db.begin_nested():
                row.experiment_id = _new_temp_experiment_id()
                db.flush()
            return
        except IntegrityError as exc:
            last_error = exc
            row.experiment_id = None
    raise ValueError("无法分配临时实验号") from last_error


def _is_started(row: SerumImmWorkbench) -> bool:
    return (row.plan_status or "") == PLAN_STATUS_STARTED


def _is_closed_plan(status: str | None) -> bool:
    return str(status or "").strip() in CLOSED_PLAN_STATUSES


def _priority_value(value: Any) -> str:
    return str(value or "").strip() or DEFAULT_PRIORITY


def _priority_rank(value: Any) -> int:
    canon = _priority_value(value)
    try:
        return PRIORITY_ORDER.index(canon)
    except ValueError:
        return len(PRIORITY_ORDER)


def _normalize_species_cross(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, (list, tuple)):
        tokens = [str(item).strip() for item in value if str(item).strip()]
    else:
        text = str(value).strip()
        if not text:
            return None
        tokens = [part.strip() for part in text.split(",") if part.strip()]
    allowed = set(SPECIES_CROSS_OPTIONS)
    if any(token not in allowed for token in tokens):
        raise ValueError("种属交叉包含不允许的选项")
    ordered = [option for option in SPECIES_CROSS_OPTIONS if option in tokens]
    return ",".join(ordered) or None


def _band_index_range(others: list[Any], priority: Any) -> tuple[int, int]:
    """Insert indices in ``others`` for priority P: first of band .. after last peer."""
    rank = _priority_rank(priority)
    first_insert = 0
    last_peer_index = None
    for index, item in enumerate(others or []):
        item_rank = _priority_rank(getattr(item, "priority", None))
        if item_rank < rank:
            first_insert = index + 1
        elif item_rank == rank:
            last_peer_index = index
    last_insert = last_peer_index + 1 if last_peer_index is not None else first_insert
    return first_insert, last_insert


def _insert_index_for_target(others: list[Any], priority: Any, target_sort: int) -> int:
    first_insert, last_insert = _band_index_range(others, priority)
    desired = max(0, int(target_sort) - 1)
    return min(max(desired, first_insert), last_insert)


def _renumber_queue(rows: list[Any]) -> None:
    for index, row in enumerate(rows, start=1):
        row.sort_order = index


def _queue_rows(db: Session) -> list[SerumImmWorkbench]:
    return list(db.scalars(select(SerumImmWorkbench).order_by(*_list_order())).all())


def _lock_queue(db: Session) -> None:
    """Serialize queue mutations so concurrent writers cannot allocate the same slot."""
    db.scalars(
        select(SerumImmWorkbench.id)
        .order_by(SerumImmWorkbench.id.asc())
        .with_for_update()
    ).all()


def _place_row(db: Session, row: SerumImmWorkbench, *, mode: str, target_sort: int | None = None) -> None:
    if not getattr(row, "id", None):
        db.flush()
    others = [item for item in _queue_rows(db) if int(item.id) != int(row.id)]
    first_insert, last_insert = _band_index_range(others, row.priority)
    if mode == "first":
        index = first_insert
    elif mode == "last":
        index = last_insert
    else:
        index = _insert_index_for_target(others, row.priority, int(target_sort if target_sort is not None else row.sort_order or 0))
    others.insert(index, row)
    _renumber_queue(others)


def _apply_queue_constraints(
    db: Session,
    row: SerumImmWorkbench,
    *,
    previous_sort: int,
    previous_priority: Any,
    payload: dict[str, Any],
    is_new: bool,
) -> None:
    if not getattr(row, "id", None):
        db.flush()
    current_sort = int(row.sort_order or 0)
    sort_changed = current_sort != int(previous_sort or 0)
    priority_changed = _priority_value(row.priority) != _priority_value(previous_priority)
    explicit_sort = "sort_order" in payload and _normalize_int(payload.get("sort_order")) not in (None, 0)
    if not sort_changed and not priority_changed and not (is_new and explicit_sort):
        return
    if priority_changed and not sort_changed:
        demote = _priority_rank(row.priority) > _priority_rank(previous_priority)
        _place_row(db, row, mode="first" if demote else "last")
        return
    _place_row(db, row, mode="snap", target_sort=current_sort)


def _compact_all_sorts(db: Session) -> None:
    _renumber_queue(_queue_rows(db))


def _list_order():
    return (
        SerumImmWorkbench.sort_order.asc(),
        SerumImmWorkbench.id.asc(),
    )


def _next_sort_order(db: Session, exclude_id: int | None = None) -> int:
    stmt = select(func.coalesce(func.max(SerumImmWorkbench.sort_order), 0))
    if exclude_id:
        stmt = stmt.where(SerumImmWorkbench.id != int(exclude_id))
    current = int(db.scalar(stmt) or 0)
    for obj in list(db.new) + list(db.dirty):
        if not isinstance(obj, SerumImmWorkbench):
            continue
        if exclude_id and obj.id == exclude_id:
            continue
        current = max(current, int(obj.sort_order or 0))
    return current + 1


def _assign_queue_sort(db: Session, row: SerumImmWorkbench, *, is_new: bool, payload: dict[str, Any]) -> None:
    if not is_new:
        return
    explicit = "sort_order" in payload and _normalize_int(payload.get("sort_order")) not in (None, 0)
    if not explicit:
        row.sort_order = _next_sort_order(db, exclude_id=row.id)


def _project_by_experiment(
    db: Session,
    experiment_id: str | None,
    *,
    for_update: bool = False,
) -> SerumImmProject | None:
    eid = str(experiment_id or "").strip()
    if not eid:
        return None
    stmt = select(SerumImmProject).where(SerumImmProject.experiment_id == eid)
    if for_update:
        stmt = stmt.with_for_update()
    return db.scalar(stmt)


def _overlay_identity(data: dict[str, Any], project: SerumImmProject | None) -> dict[str, Any]:
    started = (data.get("plan_status") or "") == PLAN_STATUS_STARTED
    if started and project:
        for field in ALIGNED_FIELDS:
            data[field] = getattr(project, field)
        if isinstance(data.get("target_codes"), list) is False:
            data["target_codes"] = project.target_codes if isinstance(project.target_codes, list) else []
        data["serum_project_id"] = project.id
        data["display_status"] = project.project_status or PLAN_STATUS_STARTED
    else:
        data["serum_project_id"] = None
        data["display_status"] = data.get("plan_status") or PLAN_STATUS_DRAFT
    data["aligned_locked"] = started
    return data


def _join_strain_parts(groups: list[dict[str, Any]], key: str) -> str:
    values = {str(item.get(key) or "").strip() for item in groups}
    return "+".join(sorted(value for value in values if value))


def serialize_row(
    row: SerumImmWorkbench,
    project: SerumImmProject | None = None,
) -> dict[str, Any]:
    data = _overlay_identity(row.to_dict(), project)
    data["species_cross"] = _normalize_species_cross(data.get("species_cross")) or ""
    return data


def _scheme_revision(db: Session, row: SerumImmWorkbench) -> str:
    header = row.to_dict()
    snapshot = {
        "header": {field: header.get(field) for field in SCHEME_HEADER_FIELDS},
        "children": _load_children(db, row.experiment_id),
    }
    encoded = json.dumps(snapshot, ensure_ascii=False, sort_keys=True, default=str, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _comparison_value(field: str, value: Any) -> Any:
    if field == "target_codes":
        return _normalize_target_codes(value)
    if field == "species_cross":
        return _normalize_species_cross(value)
    if field == "priority":
        return _priority_value(value)
    if field in YES_NO_FIELDS:
        return _normalize_yes_no(value)
    if field in INT_FIELDS:
        return _normalize_int(value)
    if field == "plan_status":
        return str(value or "").strip() or PLAN_STATUS_DRAFT
    if isinstance(value, str):
        return value.strip() or None
    return value


def _validate_expected_fields(row: SerumImmWorkbench, expected: Any) -> None:
    if not isinstance(expected, dict) or not expected:
        return
    current = row.to_dict()
    allowed = set(ALIGNED_FIELDS + PREP_FIELDS)
    for field, expected_value in expected.items():
        if field not in allowed:
            continue
        if _comparison_value(field, current.get(field)) != _comparison_value(field, expected_value):
            raise ValueError("工作台记录已被其他用户修改，请刷新后重试")


def _apply_fields(row: SerumImmWorkbench, data: dict[str, Any], fields: list[str]) -> None:
    for field in fields:
        if field == "experiment_id" or field not in data:
            continue
        value = data.get(field)
        if field == "target_codes":
            value = _normalize_target_codes(value)
        elif field in YES_NO_FIELDS:
            value = _normalize_yes_no(value)
            if value is None and field in REQUIRED_YES_NO_DEFAULTS:
                value = REQUIRED_YES_NO_DEFAULTS[field]
            if value not in (None, "是", "否"):
                raise ValueError(f"{field} 只能填写“是”或“否”")
        elif field in INT_FIELDS:
            value = _normalize_int(value)
            if field == "sort_order" and (value is None or value <= 0):
                raise ValueError("排序必须是大于 0 的整数")
        elif field == "plan_status":
            text = str(value or "").strip()
            if text == PLAN_STATUS_STARTED:
                raise ValueError("请使用开展接口将计划状态改为已开展")
            if text and text not in EDITABLE_PLAN_STATUSES:
                raise ValueError("工作台状态不在允许的选项中")
            value = text or PLAN_STATUS_DRAFT
        elif field == "priority":
            value = _priority_value(value)
            if value not in PRIORITY_ORDER:
                raise ValueError("优先级不在允许的选项中")
        elif field == "review_status":
            value = str(value or "").strip() or DEFAULT_REVIEW_STATUS
            if value not in REVIEW_STATUS_OPTIONS:
                raise ValueError("审核结果不在允许的选项中")
        elif field == "mouse_status":
            value = str(value or "").strip() or DEFAULT_MOUSE_STATUS
            if value not in MOUSE_STATUS_OPTIONS:
                raise ValueError("运输状态不在允许的选项中")
        elif field == "species_cross":
            value = _normalize_species_cross(value)
        elif field == "project_code":
            value = _compact_identifier(value) or None
        elif field in WORKBENCH_REMARK_FIELDS:
            value = str(value or "").strip() or None
            if value and len(value) > 255:
                raise ValueError("备注不能超过 255 个字符")
        elif isinstance(value, str):
            value = value.strip() or None
        setattr(row, field, value)


def _load_children(db: Session, experiment_id: str | None) -> dict[str, list[dict]]:
    exp_id = str(experiment_id or "").strip()
    if not exp_id:
        return {
            "mouse_groups": [],
            "antigens": [],
            "steps": [],
            "titer_targets": [],
            "titer_pcs": [],
        }
    return {
        "mouse_groups": [
            item.to_dict()
            for item in db.scalars(
                select(SerumImmMouse)
                .where(SerumImmMouse.experiment_id == exp_id)
                .order_by(SerumImmMouse.id.asc())
            ).all()
        ],
        "antigens": [
            item.to_dict()
            for item in db.scalars(
                select(SerumImmAntigen)
                .where(SerumImmAntigen.experiment_id == exp_id)
                .order_by(SerumImmAntigen.id.asc())
            ).all()
        ],
        "steps": [
            item.to_dict()
            for item in db.scalars(
                select(SerumImmStep)
                .where(SerumImmStep.experiment_id == exp_id)
                .order_by(SerumImmStep.group_id.asc(), SerumImmStep.sort_order.asc(), SerumImmStep.step_id.asc())
            ).all()
        ],
        "titer_targets": [
            item.to_dict()
            for item in db.scalars(
                select(SerumTiterTarget)
                .where(SerumTiterTarget.experiment_id == exp_id)
                .order_by(SerumTiterTarget.id.asc())
            ).all()
        ],
        "titer_pcs": [
            item.to_dict()
            for item in db.scalars(
                select(SerumTiterPc)
                .where(SerumTiterPc.experiment_id == exp_id)
                .order_by(SerumTiterPc.id.asc())
            ).all()
        ],
    }


def _delete_children(db: Session, experiment_id: str | None) -> None:
    exp_id = str(experiment_id or "").strip()
    if not exp_id:
        return
    for model in EXPERIMENT_RELATED_MODELS:
        db.query(model).filter(model.experiment_id == exp_id).delete(synchronize_session=False)


def _resolve_view_group(plan_status: Any, project_status: Any) -> str:
    plan = str(plan_status or "").strip() or PLAN_STATUS_DRAFT
    project = str(project_status or "").strip()
    if plan in CLOSED_PLAN_STATUSES:
        return "cancelled"
    if plan != PLAN_STATUS_STARTED:
        return "planned"
    if project in TERMINAL_PROJECT_STATUSES:
        return "completed"
    return "ongoing"


def _view_group_expr(view_group: str):
    plan_status = func.coalesce(SerumImmWorkbench.plan_status, PLAN_STATUS_DRAFT)
    is_started = plan_status == PLAN_STATUS_STARTED
    is_cancelled = plan_status.in_(CLOSED_PLAN_STATUSES)
    is_completed = and_(
        is_started,
        SerumImmProject.project_status.in_(TERMINAL_PROJECT_STATUSES),
    )
    if view_group == "planned":
        return and_(~is_cancelled, plan_status != PLAN_STATUS_STARTED)
    if view_group == "ongoing":
        return and_(
            is_started,
            or_(
                SerumImmProject.project_status.is_(None),
                SerumImmProject.project_status.notin_(TERMINAL_PROJECT_STATUSES),
            ),
        )
    if view_group == "completed":
        return is_completed
    if view_group == "cancelled":
        return is_cancelled
    return None


def _aligned_value_expr(workbench_column, project_column):
    return case(
        (
            and_(
                SerumImmWorkbench.plan_status == PLAN_STATUS_STARTED,
                SerumImmProject.id.is_not(None),
            ),
            project_column,
        ),
        else_=workbench_column,
    )


def _composed_value_filter(workbench_column, project_column, value: str):
    field = _aligned_value_expr(workbench_column, project_column)
    return or_(
        field == value,
        field.like(f"{value}+%"),
        field.like(f"%+{value}"),
        field.like(f"%+{value}+%"),
    )


def _display_status_expr():
    return case(
        (
            and_(
                SerumImmWorkbench.plan_status == PLAN_STATUS_STARTED,
                SerumImmProject.id.is_not(None),
            ),
            func.coalesce(SerumImmProject.project_status, PLAN_STATUS_STARTED),
        ),
        else_=func.coalesce(SerumImmWorkbench.plan_status, PLAN_STATUS_DRAFT),
    )


def _keyword_field_exprs():
    return (
        _aligned_value_expr(
            SerumImmWorkbench.target_name,
            SerumImmProject.target_name,
        ),
        cast(
            _aligned_value_expr(
                SerumImmWorkbench.target_codes,
                SerumImmProject.target_codes,
            ),
            String,
        ),
        _aligned_value_expr(
            SerumImmWorkbench.project_name,
            SerumImmProject.project_name,
        ),
        _aligned_value_expr(
            SerumImmWorkbench.project_code,
            SerumImmProject.project_code,
        ),
        SerumImmWorkbench.project_set_code,
        _aligned_value_expr(
            SerumImmWorkbench.experiment_id,
            SerumImmProject.experiment_id,
        ),
        _aligned_value_expr(SerumImmWorkbench.pm, SerumImmProject.pm),
        _aligned_value_expr(SerumImmWorkbench.owner, SerumImmProject.owner),
    )


def _keyword_rank_expr(keyword: str):
    like = f"%{keyword}%"
    return case(
        *((field.like(like), rank) for rank, field in enumerate(_keyword_field_exprs())),
        else_=len(_keyword_field_exprs()),
    )


def _species_cross_filter(value: str):
    return or_(
        SerumImmWorkbench.species_cross == value,
        SerumImmWorkbench.species_cross.like(f"{value},%"),
        SerumImmWorkbench.species_cross.like(f"%,{value}"),
        SerumImmWorkbench.species_cross.like(f"%,{value},%"),
    )


def _has_scheme_data_expr():
    return or_(*(
        exists(
            select(1).where(model.experiment_id == SerumImmWorkbench.experiment_id)
        ).correlate(SerumImmWorkbench)
        for model, _ in COPY_CHILD_MODELS
    ))


def _apply_list_filters(stmt, data: dict[str, Any], *, skip_status: bool = False):
    keyword = str(data.get("keyword") or "").strip()
    view_group = str(data.get("view_group") or "").strip()
    can_start = _normalize_yes_no(data.get("can_start"))
    has_scheme_data = _normalize_yes_no(data.get("has_scheme_data"))
    study_type = str(data.get("study_type") or "").strip()
    mouse_strain_category = str(data.get("mouse_strain_category") or "").strip()
    species_cross = str(data.get("species_cross") or "").strip()
    mouse_status = str(data.get("mouse_status") or "").strip()
    antigen_ready = _normalize_yes_no(data.get("antigen_ready"))
    pm = str(data.get("pm") or "").strip()
    priority = str(data.get("priority") or "").strip()
    owner = str(data.get("owner") or "").strip()
    reviewer = str(data.get("reviewer") or "").strip()
    review_status = str(data.get("review_status") or "").strip()
    display_status = str(data.get("display_status") or "").strip()
    immuno_method = str(data.get("immuno_method") or "").strip()
    mouse_strain = str(data.get("mouse_strain") or "").strip()
    mouse_zygosity = str(data.get("mouse_zygosity") or "").strip()
    mouse_region = str(data.get("mouse_region") or "").strip()
    mouse_expand_requested = _normalize_yes_no(data.get("mouse_expand_requested"))
    antigen_source = str(data.get("antigen_source") or "").strip()
    lnp_ordered = _normalize_yes_no(data.get("lnp_ordered"))
    cell_prep_status = str(data.get("cell_prep_status") or "").strip()

    if keyword:
        like = f"%{keyword}%"
        stmt = stmt.where(or_(*(field.like(like) for field in _keyword_field_exprs())))
    if not skip_status:
        view_filter = _view_group_expr(view_group)
        if view_filter is not None:
            stmt = stmt.where(view_filter)
        if can_start:
            stmt = stmt.where(SerumImmWorkbench.can_start == can_start)
    if has_scheme_data in {"是", "否"}:
        condition = _has_scheme_data_expr()
        stmt = stmt.where(condition if has_scheme_data == "是" else ~condition)
    if study_type:
        stmt = stmt.where(
            _aligned_value_expr(
                SerumImmWorkbench.study_type,
                SerumImmProject.study_type,
            )
            == study_type
        )
    if mouse_strain_category:
        stmt = stmt.where(
            _composed_value_filter(
                SerumImmWorkbench.mouse_strain_category,
                SerumImmProject.mouse_strain_category,
                mouse_strain_category,
            )
        )
    if species_cross:
        stmt = stmt.where(_species_cross_filter(species_cross))
    if mouse_status:
        stmt = stmt.where(SerumImmWorkbench.mouse_status == mouse_status)
    if antigen_ready:
        stmt = stmt.where(SerumImmWorkbench.antigen_ready == antigen_ready)
    if pm:
        stmt = stmt.where(
            _aligned_value_expr(SerumImmWorkbench.pm, SerumImmProject.pm) == pm
        )
    if priority:
        stmt = stmt.where(SerumImmWorkbench.priority == priority)
    if owner:
        stmt = stmt.where(
            _aligned_value_expr(SerumImmWorkbench.owner, SerumImmProject.owner) == owner
        )
    if reviewer:
        stmt = stmt.where(SerumImmWorkbench.reviewer == reviewer)
    if review_status:
        stmt = stmt.where(SerumImmWorkbench.review_status == review_status)
    if display_status:
        stmt = stmt.where(_display_status_expr() == display_status)
    if immuno_method:
        stmt = stmt.where(SerumImmWorkbench.immuno_method == immuno_method)
    if mouse_strain:
        stmt = stmt.where(
            _composed_value_filter(
                SerumImmWorkbench.mouse_strain,
                SerumImmProject.mouse_strain,
                mouse_strain,
            )
        )
    if mouse_zygosity:
        stmt = stmt.where(SerumImmWorkbench.mouse_zygosity == mouse_zygosity)
    if mouse_region:
        stmt = stmt.where(SerumImmWorkbench.mouse_region == mouse_region)
    if mouse_expand_requested:
        stmt = stmt.where(
            SerumImmWorkbench.mouse_expand_requested == mouse_expand_requested
        )
    if antigen_source:
        stmt = stmt.where(SerumImmWorkbench.antigen_source == antigen_source)
    if lnp_ordered:
        stmt = stmt.where(SerumImmWorkbench.lnp_ordered == lnp_ordered)
    if cell_prep_status:
        stmt = stmt.where(SerumImmWorkbench.cell_prep_status == cell_prep_status)
    return stmt


def _base_stmt():
    return select(SerumImmWorkbench).outerjoin(
        SerumImmProject,
        SerumImmWorkbench.experiment_id == SerumImmProject.experiment_id,
    )


def _count_stmt():
    return (
        select(func.count(SerumImmWorkbench.id))
        .select_from(SerumImmWorkbench)
        .outerjoin(
            SerumImmProject,
            SerumImmWorkbench.experiment_id == SerumImmProject.experiment_id,
        )
    )


def _list_stats(db: Session, data: dict[str, Any]) -> dict[str, int]:
    stmt = _apply_list_filters(
        select(
            SerumImmWorkbench.plan_status,
            SerumImmProject.project_status,
            SerumImmWorkbench.can_start,
            func.count(SerumImmWorkbench.id),
        )
        .select_from(SerumImmWorkbench)
        .outerjoin(
            SerumImmProject,
            SerumImmWorkbench.experiment_id == SerumImmProject.experiment_id,
        )
        .group_by(
            SerumImmWorkbench.plan_status,
            SerumImmProject.project_status,
            SerumImmWorkbench.can_start,
        ),
        data or {},
        skip_status=True,
    )
    stats = {
        "all": 0,
        "planned": 0,
        "ongoing": 0,
        "completed": 0,
        "cancelled": 0,
        "can_start": 0,
    }
    for status, project_status, ready, count in db.execute(stmt).all():
        n = int(count or 0)
        stats["all"] += n
        group = _resolve_view_group(status, project_status)
        stats[group] += n
        if (
            _normalize_yes_no(ready) == "是"
            and group == "planned"
        ):
            stats["can_start"] += n
    return stats


def get_list(db: Session, data: dict[str, Any]) -> dict[str, Any]:
    page = max(int(data.get("page", 1) or 1), 1)
    limit = min(max(int(data.get("limit", 50) or 50), 1), 200)
    payload = data or {}
    stmt = _apply_list_filters(_base_stmt(), payload)
    total = db.scalar(_apply_list_filters(_count_stmt(), payload)) or 0
    keyword = str(payload.get("keyword") or "").strip()
    order_by = [*_list_order()]
    if keyword:
        order_by.insert(0, _keyword_rank_expr(keyword))
    rows = db.scalars(
        stmt.order_by(*order_by)
        .offset((page - 1) * limit)
        .limit(limit)
    ).unique().all()
    experiment_ids = [str(row.experiment_id or "").strip() for row in rows if row.experiment_id]
    projects = {}
    if experiment_ids:
        projects = {
            str(item.experiment_id or "").strip(): item
            for item in db.scalars(
                select(SerumImmProject).where(SerumImmProject.experiment_id.in_(experiment_ids))
            ).all()
        }
    items = [
        serialize_row(
            row,
            projects.get(str(row.experiment_id or "").strip()),
        )
        for row in rows
    ]
    return {
        "items": items,
        "total": total,
        "page": page,
        "limit": limit,
        "stats": _list_stats(db, payload),
    }


def export_list_workbook(
    db: Session,
    data: dict[str, Any],
) -> tuple[BytesIO, str]:
    from utils.excel import build_list_workbook

    payload = data or {}
    stmt = _apply_list_filters(_base_stmt(), payload)
    order_by = [*_list_order()]
    keyword = str(payload.get("keyword") or "").strip()
    if keyword:
        order_by.insert(0, _keyword_rank_expr(keyword))
    workbench_rows = db.scalars(stmt.order_by(*order_by)).unique().all()

    experiment_ids = [
        str(row.experiment_id or "").strip()
        for row in workbench_rows
        if row.experiment_id
    ]
    projects = {
        str(project.experiment_id or "").strip(): project
        for project in db.scalars(
            select(SerumImmProject).where(
                SerumImmProject.experiment_id.in_(experiment_ids)
            )
        ).all()
    } if experiment_ids else {}
    items = [
        serialize_row(
            row,
            projects.get(str(row.experiment_id or "").strip()),
        )
        for row in workbench_rows
    ]
    columns = (
        ("编号", "id"),
        ("排序", "sort_order"),
        ("优先级", "priority"),
        ("状态", "display_status"),
        ("是否可开展", "can_start"),
        ("项目编号", "project_code"),
        ("项目集编号", "project_set_code"),
        ("实验ID", "experiment_id"),
        ("项目名称", "project_name"),
        ("项目目的", "project_purpose"),
        ("课题类型", "study_type"),
        ("PM", "pm"),
        ("开展人", "owner"),
        ("审核人", "reviewer"),
        ("审核结果", "review_status"),
        ("靶点", "target_name"),
        ("靶点编号", "target_codes"),
        ("靶点类型", "target_type"),
        ("靶点大小", "target_size"),
        ("免疫方式", "immuno_method"),
        ("种属交叉", "species_cross"),
        ("归类鼠型", "mouse_strain_category"),
        ("小鼠品系", "mouse_strain"),
        ("开始日期", "start_date"),
        ("免疫间隔", "immunization_interval"),
        ("检测方法", "assay_method"),
        ("FACS板数", "facs_plate_count"),
        ("ELISA板数", "elisa_plate_count"),
        ("备注", "remark"),
        ("小鼠方案号", "mouse_scheme_no"),
        ("小鼠数量", "mouse_count"),
        ("纯合/杂合", "mouse_zygosity"),
        ("出生日期", "mouse_birth_date"),
        ("周龄", "mouse_age_weeks"),
        ("代下扩繁", "mouse_expand_requested"),
        ("提供地区", "mouse_region"),
        ("鼠房", "mouse_room"),
        ("小鼠状态", "mouse_status"),
        ("到货日期", "mouse_arrive_date"),
        ("小鼠备注", "mouse_remark"),
        ("抗原来源", "antigen_source"),
        ("抗原就绪", "antigen_ready"),
        ("抗原ETA", "antigen_eta"),
        ("LNP下单", "lnp_ordered"),
        ("冲击细胞", "cell_prep_status"),
        ("抗原备注", "antigen_remark"),
        ("创建人", "created_by"),
        ("创建时间", "created_at"),
        ("更新时间", "updated_at"),
    )
    return build_list_workbook(
        sheet_title="免疫工作台",
        filename_prefix="免疫工作台列表",
        headers=[label for label, _ in columns],
        rows=[[item.get(key) for _, key in columns] for item in items],
    )


def get_options(db: Session) -> dict[str, list[str]]:
    def values(*columns) -> list[str]:
        result: set[str] = set()
        for column in columns:
            for value in db.scalars(select(column).where(column.is_not(None)).distinct()).all():
                text = str(value or "").strip()
                if text:
                    result.add(text)
        return sorted(result)

    def composed_values(workbench_column, project_column) -> list[str]:
        result: set[str] = set()
        statements = (
            select(workbench_column)
            .where(
                SerumImmWorkbench.plan_status != PLAN_STATUS_STARTED,
                workbench_column.is_not(None),
            )
            .distinct(),
            select(project_column).where(project_column.is_not(None)).distinct(),
        )
        for statement in statements:
            for value in db.scalars(statement).all():
                result.update(part.strip() for part in str(value).split("+") if part.strip())
        return sorted(result)

    owners = values(SerumImmProject.owner, SerumImmWorkbench.owner)
    pms = values(SerumImmProject.pm, SerumImmWorkbench.pm)
    return {
        "owners": owners,
        "pms": pms,
        "reviewers": values(SerumImmWorkbench.reviewer),
        "study_types": values(SerumImmWorkbench.study_type, SerumImmProject.study_type),
        "mouse_strains": composed_values(
            SerumImmWorkbench.mouse_strain,
            SerumImmProject.mouse_strain,
        ),
        "mouse_strain_categories": composed_values(
            SerumImmWorkbench.mouse_strain_category,
            SerumImmProject.mouse_strain_category,
        ),
        "statuses": values(
            SerumImmWorkbench.plan_status,
            SerumImmProject.project_status,
        ),
        "immuno_methods": values(SerumImmWorkbench.immuno_method),
    }


def get_detail(db: Session, workbench_id: int) -> dict[str, Any] | None:
    row = db.get(SerumImmWorkbench, int(workbench_id))
    if not row:
        return None
    project = _project_by_experiment(db, row.experiment_id)
    data = serialize_row(row, project)
    data.update(_load_children(db, row.experiment_id))
    if not _is_started(row):
        data["scheme_revision"] = _scheme_revision(db, row)
    return data


def _parse_row_id(raw: Any) -> int | None:
    if raw in (None, ""):
        return None
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return None
    return value if value > 0 else None


def _edit_scope_set(edit_scopes: set[str] | frozenset[str] | None) -> set[str]:
    return set(edit_scopes) if edit_scopes is not None else {"full"}


def _validate_row_edit_scope(
    row: SerumImmWorkbench,
    payload: dict[str, Any],
    *,
    is_new: bool,
    edit_scopes: set[str] | frozenset[str] | None,
) -> None:
    scopes = _edit_scope_set(edit_scopes)
    if "full" in scopes:
        return

    allowed_fields: set[str] = set()
    is_draft = str(row.plan_status or PLAN_STATUS_DRAFT).strip() == PLAN_STATUS_DRAFT
    if "draft" in scopes and (is_new or is_draft):
        allowed_fields.update(WORKBENCH_MUTABLE_FIELDS - DRAFT_PROTECTED_FIELDS)
    if "support" in scopes and not is_new:
        allowed_fields.update(SUPPORT_EDIT_FIELDS)
    if not allowed_fields:
        raise PermissionError("没有权限编辑该工作台记录")

    denied_fields = (set(payload) & WORKBENCH_MUTABLE_FIELDS) - allowed_fields
    if denied_fields:
        raise PermissionError("没有权限修改该工作台字段")


def save(
    db: Session,
    data: dict[str, Any],
    created_by: str | None = None,
    *,
    commit: bool = True,
    edit_scopes: set[str] | frozenset[str] | None = None,
) -> dict[str, Any]:
    payload = dict(data or {})
    supplied_id = payload.get("id")
    raw_id = _parse_row_id(payload.get("id"))
    if supplied_id not in (None, "") and raw_id is None:
        raise ValueError("工作台记录 ID 不正确")
    for key in READONLY_RESPONSE_KEYS:
        payload.pop(key, None)
    payload.pop("id", None)
    expected = payload.pop("_expected", None)
    if raw_id is None or "sort_order" in payload or "priority" in payload:
        _lock_queue(db)

    row = None
    if raw_id is not None:
        row = db.scalar(
            select(SerumImmWorkbench)
            .where(SerumImmWorkbench.id == raw_id)
            .with_for_update()
        )
    if raw_id is not None and row is None:
        raise ValueError("工作台记录不存在")
    is_new = raw_id is None
    if row is None:
        row = SerumImmWorkbench(
            plan_status=PLAN_STATUS_DRAFT,
            priority=DEFAULT_PRIORITY,
            review_status=DEFAULT_REVIEW_STATUS,
            mouse_status=DEFAULT_MOUSE_STATUS,
            antigen_ready=REQUIRED_YES_NO_DEFAULTS["antigen_ready"],
            can_start=REQUIRED_YES_NO_DEFAULTS["can_start"],
            sort_order=0,
            created_by=created_by,
        )
        db.add(row)

    _validate_row_edit_scope(
        row,
        payload,
        is_new=is_new,
        edit_scopes=edit_scopes,
    )
    previous_sort = int(row.sort_order or 0)
    previous_priority = row.priority
    _validate_expected_fields(row, expected)

    if _is_started(row):
        incoming_status = str(payload.get("plan_status") or "").strip()
        if incoming_status and incoming_status != PLAN_STATUS_STARTED:
            raise ValueError("已开展记录不能改回其他计划状态")
        payload.pop("plan_status", None)
        if "project_code" in payload:
            project = _project_by_experiment(db, row.experiment_id, for_update=True)
            if not project:
                raise ValueError("未找到对应免疫实验，无法修改项目编号")
            update_project_identifiers(
                db,
                project,
                payload.pop("project_code"),
            )
        _apply_fields(row, payload, PREP_FIELDS)
    else:
        incoming_status = str(payload.get("plan_status") or "").strip()
        if incoming_status == PLAN_STATUS_STARTED:
            raise ValueError("请使用开展接口将计划状态改为已开展")
        incoming_category = str(payload.get("mouse_strain_category") or "").strip()
        if incoming_category and incoming_category not in MOUSE_STRAIN_CATEGORY_OPTIONS:
            raise ValueError("归类鼠型不在允许的选项中")
        incoming_region = str(payload.get("mouse_region") or "").strip()
        if incoming_region and incoming_region not in MOUSE_REGION_OPTIONS:
            raise ValueError("提供地区不在允许的选项中")
        _apply_fields(row, payload, ALIGNED_FIELDS + PREP_FIELDS)
        _assign_temp_experiment_id(db, row)
    _assign_queue_sort(db, row, is_new=is_new, payload=payload)
    _apply_queue_constraints(
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
    project = _project_by_experiment(db, row.experiment_id) if _is_started(row) else None
    return serialize_row(row, project)


def save_batch(
    db: Session,
    data: dict[str, Any],
    created_by: str | None = None,
    *,
    edit_scopes: set[str] | frozenset[str] | None = None,
) -> dict[str, Any]:
    raw_items = data.get("items") or []
    if not isinstance(raw_items, list):
        raise ValueError("批量保存数据格式不正确")
    if any(not isinstance(item, dict) for item in raw_items):
        raise ValueError("批量保存行数据格式不正确")
    items = [dict(item) for item in raw_items]
    row_ids: list[int] = []
    queue_mutation = False
    for item in items:
        supplied_id = item.get("id")
        row_id = _parse_row_id(supplied_id)
        if supplied_id not in (None, "") and row_id is None:
            raise ValueError("工作台记录 ID 不正确")
        if row_id is not None:
            row_ids.append(row_id)
        if row_id is None or "sort_order" in item or "priority" in item:
            queue_mutation = True
    if len(row_ids) != len(set(row_ids)):
        raise ValueError("批量保存包含重复的工作台记录")

    if queue_mutation:
        _lock_queue(db)
    existing_rows = (
        db.scalars(
            select(SerumImmWorkbench)
            .where(SerumImmWorkbench.id.in_(row_ids))
            .order_by(SerumImmWorkbench.id.asc())
            .with_for_update()
        ).all()
        if row_ids
        else []
    )
    rows_by_id = {int(row.id): row for row in existing_rows}
    if len(rows_by_id) != len(row_ids):
        raise ValueError("工作台记录不存在")

    for item in items:
        row_id = _parse_row_id(item.get("id"))
        if row_id is not None:
            _validate_expected_fields(rows_by_id[row_id], item.get("_expected"))
        item.pop("_expected", None)

    saved_ids = [
        int(
            save(
                db,
                item,
                created_by,
                commit=False,
                edit_scopes=edit_scopes,
            )["id"]
        )
        for item in items
    ]
    db.commit()
    saved = []
    for row_id in saved_ids:
        row = db.get(SerumImmWorkbench, row_id)
        project = _project_by_experiment(db, row.experiment_id) if row and _is_started(row) else None
        if row:
            saved.append(serialize_row(row, project))
    return {"items": saved}


def delete(
    db: Session,
    workbench_id: int,
    *,
    edit_scopes: set[str] | frozenset[str] | None = None,
) -> None:
    _lock_queue(db)
    row = db.get(SerumImmWorkbench, int(workbench_id))
    if not row:
        raise ValueError("工作台记录不存在")
    scopes = _edit_scope_set(edit_scopes)
    is_draft = str(row.plan_status or PLAN_STATUS_DRAFT).strip() == PLAN_STATUS_DRAFT
    if "full" not in scopes and not ("draft" in scopes and is_draft):
        raise PermissionError("只能删除草稿状态的工作台记录")
    if _is_started(row):
        raise ValueError("已开展的工作台记录不能删除")
    if _project_by_experiment(db, row.experiment_id):
        raise ValueError("已关联免疫实验，不能删除工作台记录")
    if row.experiment_id:
        _delete_children(db, row.experiment_id)
    db.delete(row)
    db.flush()
    _compact_all_sorts(db)
    db.commit()


def start(db: Session, workbench_id: int) -> dict[str, Any]:
    row = db.scalar(
        select(SerumImmWorkbench)
        .where(SerumImmWorkbench.id == int(workbench_id))
        .with_for_update()
    )
    if not row:
        raise ValueError("工作台记录不存在")
    if _is_started(row):
        raise ValueError("该记录已开展")
    if _is_closed_plan(row.plan_status):
        raise ValueError("该状态不能开展")
    project_code = _compact_identifier(row.project_code)
    if not project_code:
        raise ValueError("开展前必须填写项目编号")
    if not str(row.owner or "").strip():
        raise ValueError("开展前必须选择负责人")
    row.project_code = project_code
    old_eid = row.experiment_id
    last_error: Exception | None = None
    project: SerumImmProject | None = None

    for _ in range(TEMP_ID_MAX_ATTEMPTS):
        new_eid = generate_next_id(db, project_code)
        if not new_eid:
            raise ValueError("无法生成实验号")
        try:
            with db.begin_nested():
                mouse_groups = db.scalars(
                    select(SerumImmMouse).where(
                        SerumImmMouse.experiment_id == old_eid
                    )
                ).all()
                mouse_group_data = [item.to_dict() for item in mouse_groups]
                project = SerumImmProject()
                for field in ALIGNED_FIELDS:
                    if field == "experiment_id" or field in STRAIN_FIELDS:
                        continue
                    setattr(project, field, getattr(row, field))
                project.mouse_strain = _join_strain_parts(
                    mouse_group_data,
                    "mouse_strain",
                ) or None
                project.mouse_strain_category = _join_strain_parts(
                    mouse_group_data,
                    "mouse_strain_category",
                ) or None
                project.experiment_id = new_eid
                project.project_status = DEFAULT_PROJECT_STATUS
                db.add(project)
                db.flush()

                row.experiment_id = new_eid
                row.plan_status = PLAN_STATUS_STARTED
                db.flush()

                rename_experiment_related_records(db, old_eid, new_eid)
                db.flush()
            break
        except IntegrityError as exc:
            last_error = exc
            if project is not None:
                try:
                    db.expunge(project)
                except Exception:
                    pass
            db.expire(row)
            row.project_code = project_code
            project = None
    else:
        raise ValueError("无法生成实验号") from last_error

    db.commit()
    db.refresh(row)
    if project is not None:
        db.refresh(project)
    else:
        project = _project_by_experiment(db, row.experiment_id)
    return serialize_row(row, project)


def _count_by_experiment(db: Session, model, experiment_id: str) -> int:
    return int(
        db.scalar(select(func.count()).select_from(model).where(model.experiment_id == experiment_id)) or 0
    )


def effect_data_block_reason(db: Session, experiment_id: str) -> str | None:
    if _count_by_experiment(db, SerumTiterOrder, experiment_id):
        return "已有效价工单"
    if _count_by_experiment(db, SerumFacsPlate, experiment_id):
        return "已有 FACS 板数据"
    if _count_by_experiment(db, SerumElisaPlate, experiment_id):
        return "已有 ELISA 板数据"
    return None


def _clone_children(db: Session, old_eid: str | None, new_eid: str | None) -> None:
    source_id = str(old_eid or "").strip()
    target_id = str(new_eid or "").strip()
    if not source_id or not target_id or source_id == target_id:
        return
    for model, pk_field in COPY_CHILD_MODELS:
        for item in db.scalars(select(model).where(model.experiment_id == source_id)).all():
            payload = {}
            for column in model.__mapper__.columns:
                key = column.key
                if key == pk_field:
                    continue
                if key == "experiment_id":
                    payload[key] = target_id
                    continue
                payload[key] = deepcopy(getattr(item, key))
            for key in COPY_CHILD_CLEAR_FIELDS.get(model, ()):
                payload[key] = None
            db.add(model(**payload))


def unlist(
    db: Session,
    workbench_id: int,
    *,
    require_planning: bool = True,
) -> dict[str, Any]:
    row = db.scalar(
        select(SerumImmWorkbench)
        .where(SerumImmWorkbench.id == int(workbench_id))
        .with_for_update()
    )
    if not row:
        raise ValueError("工作台记录不存在")
    if not _is_started(row):
        raise ValueError("未开展的记录无需下架")
    project = _project_by_experiment(db, row.experiment_id, for_update=True)
    if not project:
        raise ValueError("未找到对应免疫实验，无法下架")
    status = str(project.project_status or "").strip()
    if require_planning and status != DEFAULT_PROJECT_STATUS:
        raise ValueError(f"仅「{DEFAULT_PROJECT_STATUS}」的实验可下架，当前为「{status or '空'}」")
    old_eid = str(row.experiment_id or "").strip()
    blocked = effect_data_block_reason(db, old_eid)
    if blocked:
        raise ValueError(f"{blocked}，不能下架")

    for field in ALIGNED_FIELDS:
        if field == "experiment_id" or field in STRAIN_FIELDS:
            continue
        setattr(row, field, getattr(project, field))

    last_error: Exception | None = None
    for _ in range(TEMP_ID_MAX_ATTEMPTS):
        new_eid = _new_temp_experiment_id()
        try:
            with db.begin_nested():
                rename_experiment_related_records(db, old_eid, new_eid)
                db.delete(project)
                row.experiment_id = new_eid
                row.plan_status = PLAN_STATUS_DRAFT
                db.flush()
            break
        except IntegrityError as exc:
            last_error = exc
            db.expire(row)
            db.expire(project)
    else:
        raise ValueError("无法生成临时实验号") from last_error

    db.commit()
    db.refresh(row)
    return serialize_row(row)


def copy_row(
    db: Session,
    workbench_id: int,
    created_by: str | None = None,
    *,
    edit_scopes: set[str] | frozenset[str] | None = None,
) -> dict[str, Any]:
    if not (_edit_scope_set(edit_scopes) & {"full", "draft"}):
        raise PermissionError("没有权限复制工作台记录")
    _lock_queue(db)
    source = db.get(SerumImmWorkbench, int(workbench_id))
    if not source:
        raise ValueError("工作台记录不存在")
    project = _project_by_experiment(db, source.experiment_id) if _is_started(source) else None
    overlay = serialize_row(source, project)
    clone = SerumImmWorkbench(
        plan_status=PLAN_STATUS_DRAFT,
        priority=DEFAULT_PRIORITY,
        review_status=DEFAULT_REVIEW_STATUS,
        mouse_status=DEFAULT_MOUSE_STATUS,
        antigen_ready=REQUIRED_YES_NO_DEFAULTS["antigen_ready"],
        can_start=REQUIRED_YES_NO_DEFAULTS["can_start"],
        created_by=created_by,
    )
    db.add(clone)
    copy_payload = {field: overlay.get(field) for field in COPY_HEADER_FIELDS}
    _apply_fields(clone, copy_payload, COPY_HEADER_FIELDS)
    clone.plan_status = PLAN_STATUS_DRAFT
    if clone.project_name:
        clone.project_name = f"{clone.project_name}（副本）"
    clone.sort_order = _next_sort_order(db)
    _assign_temp_experiment_id(db, clone)
    _clone_children(db, source.experiment_id, clone.experiment_id)
    db.commit()
    db.refresh(clone)
    return serialize_row(clone)


def reorder(
    db: Session,
    ordered_ids: list[Any],
    moved_id: Any,
    expected_rows: list[dict[str, Any]],
    *,
    edit_scopes: set[str] | frozenset[str] | None = None,
) -> dict[str, Any]:
    _lock_queue(db)
    ids = [_parse_row_id(raw) for raw in ordered_ids]
    if any(value is None for value in ids) or len(ids) != len(set(ids)):
        raise ValueError("排序记录 ID 不正确或重复")
    ids = [int(value) for value in ids if value is not None]
    if len(ids) < 2:
        raise ValueError("请至少选择两条记录排序")
    parsed_moved_id = _parse_row_id(moved_id)
    if parsed_moved_id not in ids:
        raise ValueError("被拖动的记录不在排序列表中")
    rows = db.scalars(select(SerumImmWorkbench).where(SerumImmWorkbench.id.in_(ids))).all()
    by_id = {int(row.id): row for row in rows}
    missing = [item for item in ids if item not in by_id]
    if missing:
        raise ValueError("排序记录不存在")
    scopes = _edit_scope_set(edit_scopes)
    moved_row = by_id[parsed_moved_id]
    if "full" not in scopes:
        raise PermissionError("没有权限调整工作台队列排序")
    expected_by_id = {
        _parse_row_id(item.get("id")): item
        for item in expected_rows
        if isinstance(item, dict) and _parse_row_id(item.get("id")) is not None
    }
    if set(expected_by_id) != set(ids):
        raise ValueError("排序快照不完整，请刷新后重试")
    for row_id, expected in expected_by_id.items():
        row = by_id[row_id]
        if (
            int(row.sort_order or 0) != int(expected.get("sort_order") or 0)
            or _priority_value(row.priority) != _priority_value(expected.get("priority"))
        ):
            raise ValueError("工作台队列已变化，请刷新后重试")
    ordered_rows = [by_id[item] for item in ids]
    orders = sorted(int(row.sort_order or 0) for row in ordered_rows)
    if len(set(orders)) != len(orders) or any(value <= 0 for value in orders):
        raise ValueError("工作台队列序号异常，请刷新后重试")
    for row, order in zip(ordered_rows, orders):
        row.sort_order = order
    _place_row(db, moved_row, mode="snap", target_sort=int(moved_row.sort_order or 0))
    db.commit()
    return {
        "items": [
            serialize_row(
                row,
                _project_by_experiment(db, row.experiment_id) if _is_started(row) else None,
            )
            for row in ordered_rows
        ]
    }


def _sanitize_child_items(model_class, items: list[dict], id_field: str = "id") -> list[dict]:
    allowed = {column.key for column in model_class.__mapper__.columns}
    cleaned: list[dict] = []
    for item in items or []:
        if not isinstance(item, dict):
            raise ValueError("方案子表数据格式不正确")
        row = {key: value for key, value in item.items() if key in allowed or key == id_field}
        row.pop("experiment_id", None)
        supplied_id = row.get(id_field)
        parsed_id = _parse_row_id(supplied_id)
        if supplied_id not in (None, "") and parsed_id is None:
            raise ValueError("方案子表记录 ID 不正确")
        if parsed_id is None:
            row.pop(id_field, None)
        else:
            row[id_field] = parsed_id
        cleaned.append(row)
    return cleaned


def _replace_owned_children(
    db: Session,
    model_class,
    items: list[dict],
    experiment_id: str,
    *,
    id_field: str = "id",
) -> list[Any]:
    supplied_ids = [
        int(item[id_field])
        for item in items
        if item.get(id_field) is not None
    ]
    if len(supplied_ids) != len(set(supplied_ids)):
        raise ValueError("方案子表记录 ID 重复")
    existing = list(
        db.scalars(select(model_class).where(model_class.experiment_id == experiment_id)).all()
    )
    existing_by_id = {int(getattr(item, id_field)): item for item in existing}
    submitted_ids: set[int] = set()
    inserted: list[Any] = []

    for item in items:
        values = dict(item)
        item_id = _parse_row_id(values.pop(id_field, None))
        if item_id is not None:
            obj = existing_by_id.get(item_id)
            if obj is None:
                raise ValueError("方案子表记录不属于当前工作台")
            submitted_ids.add(item_id)
            for key, value in values.items():
                if key != "experiment_id" and hasattr(obj, key):
                    setattr(obj, key, value)
            continue

        values.pop("experiment_id", None)
        obj = model_class(**values, experiment_id=experiment_id)
        db.add(obj)
        inserted.append(obj)

    for item_id, obj in existing_by_id.items():
        if item_id not in submitted_ids:
            db.delete(obj)
    db.flush()
    return inserted


def _validate_scheme_graph(payload: dict[str, Any]) -> None:
    mouse_groups = payload["mouse_groups"]
    antigens = payload["antigens"]
    steps = payload["steps"]
    group_ids = [str(item.get("group_id") or "").strip() for item in mouse_groups]
    antigen_ids = [str(item.get("antigen_id") or "").strip() for item in antigens]

    if any(not item for item in group_ids):
        raise ValueError("小鼠分组的组别不能为空")
    if len(group_ids) != len(set(group_ids)):
        raise ValueError("小鼠分组的组别不能重复")
    if any(not item for item in antigen_ids):
        raise ValueError("抗原 ID 不能为空")
    if len(antigen_ids) != len(set(antigen_ids)):
        raise ValueError("抗原 ID 不能重复")

    group_set = set(group_ids)
    antigen_set = set(antigen_ids)
    for step in steps:
        group_id = str(step.get("group_id") or "").strip()
        if not group_id or group_id not in group_set:
            raise ValueError("免疫步骤引用了不存在的小鼠分组")
        raw_antigens = step.get("antigen_id")
        if isinstance(raw_antigens, list):
            refs = [str(item).strip() for item in raw_antigens if str(item).strip()]
        else:
            refs = [
                item.strip()
                for item in str(raw_antigens or "").replace("，", ",").split(",")
                if item.strip()
            ]
        if any(item != "N/A" and item not in antigen_set for item in refs):
            raise ValueError("免疫步骤引用了不存在的抗原")


def save_scheme(
    db: Session,
    data: dict[str, Any],
    created_by: str | None = None,
    *,
    edit_scopes: set[str] | frozenset[str] | None = None,
) -> dict[str, Any]:
    workbench_id = _parse_row_id(data.get("id"))
    if workbench_id is None:
        raise ValueError("缺少工作台记录")
    row = db.scalar(
        select(SerumImmWorkbench)
        .where(SerumImmWorkbench.id == int(workbench_id))
        .with_for_update()
    )
    if not row:
        raise ValueError("工作台记录不存在")
    scopes = _edit_scope_set(edit_scopes)
    is_draft = str(row.plan_status or PLAN_STATUS_DRAFT).strip() == PLAN_STATUS_DRAFT
    if "full" not in scopes and not ("draft" in scopes and is_draft):
        raise PermissionError("只能编辑草稿状态的方案")
    if _is_started(row):
        raise ValueError("已开展记录请到免疫实验编辑页保存")
    expected_revision = str(data.get("scheme_revision") or "").strip()
    if not expected_revision:
        raise ValueError("方案版本缺失，请刷新后重试")
    if expected_revision != _scheme_revision(db, row):
        raise ValueError("方案已被其他用户修改，请刷新后重试")

    payload = dict(data or {})
    payload.pop("plan_status", None)
    payload.pop("experiment_id", None)
    payload.pop("id", None)
    payload.pop("scheme_revision", None)
    child_specs = (
        ("mouse_groups", SerumImmMouse, "id"),
        ("antigens", SerumImmAntigen, "id"),
        ("steps", SerumImmStep, "step_id"),
        ("titer_targets", SerumTiterTarget, "id"),
        ("titer_pcs", SerumTiterPc, "id"),
    )
    for key, _, _ in child_specs:
        if key not in payload or not isinstance(payload[key], list):
            raise ValueError(f"方案数据不完整：缺少 {key}")
    _validate_scheme_graph(payload)
    sanitized_children = {
        key: _sanitize_child_items(model, payload[key], id_field)
        for key, model, id_field in child_specs
    }

    _apply_fields(row, payload, SCHEME_HEADER_FIELDS)
    _assign_temp_experiment_id(db, row)
    if created_by and not row.created_by:
        row.created_by = created_by

    experiment_id = row.experiment_id
    new_mice = _replace_owned_children(
        db, SerumImmMouse, sanitized_children["mouse_groups"], experiment_id
    )
    new_antigens = _replace_owned_children(
        db, SerumImmAntigen, sanitized_children["antigens"], experiment_id
    )
    new_steps = _replace_owned_children(
        db,
        SerumImmStep,
        sanitized_children["steps"],
        experiment_id,
        id_field="step_id",
    )
    new_targets = _replace_owned_children(
        db,
        SerumTiterTarget,
        sanitized_children["titer_targets"],
        experiment_id,
    )
    new_pcs = _replace_owned_children(
        db, SerumTiterPc, sanitized_children["titer_pcs"], experiment_id
    )
    db.flush()
    scheme_revision = _scheme_revision(db, row)
    db.commit()
    db.refresh(row)

    response = serialize_row(row)
    response["scheme_revision"] = scheme_revision
    if new_mice:
        response["new_mouse_records"] = [item.to_dict() for item in new_mice]
    if new_antigens:
        response["new_antigen_records"] = [item.to_dict() for item in new_antigens]
    if new_steps:
        response["new_step_records"] = [item.to_dict() for item in new_steps]
    if new_targets:
        response["new_target_records"] = [item.to_dict() for item in new_targets]
    if new_pcs:
        response["new_pc_records"] = [item.to_dict() for item in new_pcs]
    return response
