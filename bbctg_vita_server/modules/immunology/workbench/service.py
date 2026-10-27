import hashlib
import json
import secrets
import string
from copy import deepcopy
from datetime import datetime
from io import BytesIO
from typing import Any

from sqlalchemy import and_, case, exists, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from utils.filter_values import (
    catalog_names_for_pairs,
    clean_field_text,
    recorded_target_clause,
    restrict,
    split_code_tokens,
    target_select_options,
)

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
    join_strain_parts as _join_strain_parts,
    rename_experiment_related_records,
    update_project_identifiers,
    validate_scheme_graph as _validate_scheme_graph,
)
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

PLAN_STATUS_DRAFT = "草稿"
PLAN_STATUS_PREP = "筹备中"
PLAN_STATUS_STARTED = "已开展"
PLAN_STATUS_CANCELLED = "已取消"
CLOSED_PLAN_STATUSES = frozenset({PLAN_STATUS_CANCELLED, "小鼠KO致死"})
EDITABLE_PLAN_STATUSES = frozenset({PLAN_STATUS_DRAFT, PLAN_STATUS_PREP, *CLOSED_PLAN_STATUSES})
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
MOUSE_REGION_OPTIONS = ("北京", "海门", "客户")
REQUIRED_YES_NO_DEFAULTS = {"antigen_ready": "否", "can_start": "否"}
SPECIES_CROSS_OPTIONS = ("人", "猴", "鼠", "狗", "猫", "空白")
IMMUNO_METHOD_OPTIONS = ("蛋白", "DNA", "LNP", "细胞", "混合")
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
        "mouse_group_count",
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


_priority_value = canonicalize_priority


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


def _normalize_species_cross(value: Any) -> str | None:
    return _normalize_csv_options(value, SPECIES_CROSS_OPTIONS, "种属交叉包含不允许的选项")


def _normalize_immuno_method(value: Any) -> str | None:
    return _normalize_csv_options(value, IMMUNO_METHOD_OPTIONS, "免疫方式包含不允许的选项")


def _list_order(data: dict[str, Any] | None = None):
    return list_order_clauses(
        (data or {}).get("sort_field"),
        SerumImmWorkbench.sort_order,
        SerumImmWorkbench.id,
    )


def _row_is_terminal(row: SerumImmWorkbench, project: SerumImmProject | None = None) -> bool:
    if _is_closed_plan(row.plan_status):
        return True
    if _is_started(row) and project is not None:
        return str(project.project_status or "").strip() in TERMINAL_PROJECT_STATUSES
    return False


def _terminal_sql():
    plan_status = func.coalesce(SerumImmWorkbench.plan_status, PLAN_STATUS_DRAFT)
    project_status = func.coalesce(SerumImmProject.project_status, "")
    return or_(
        plan_status.in_(CLOSED_PLAN_STATUSES),
        and_(
            plan_status == PLAN_STATUS_STARTED,
            project_status.in_(TERMINAL_PROJECT_STATUSES),
        ),
    )


def _queue_rows(db: Session) -> list[SerumImmWorkbench]:
    return db.scalars(
        select(SerumImmWorkbench)
        .outerjoin(
            SerumImmProject,
            SerumImmWorkbench.experiment_id == SerumImmProject.experiment_id,
        )
        .where(~_terminal_sql())
        .order_by(SerumImmWorkbench.sort_order.asc(), SerumImmWorkbench.id.asc())
    ).unique().all()


def _projects_for_rows(
    db: Session,
    rows: list[SerumImmWorkbench],
) -> dict[str, SerumImmProject]:
    experiment_ids = [
        str(row.experiment_id or "").strip()
        for row in rows
        if row.experiment_id
    ]
    if not experiment_ids:
        return {}
    return {
        str(item.experiment_id or "").strip(): item
        for item in db.scalars(
            select(SerumImmProject).where(
                SerumImmProject.experiment_id.in_(experiment_ids)
            )
        ).all()
    }


def _lock_queue(db: Session) -> None:
    """Serialize queue mutations so concurrent writers cannot allocate the same slot."""
    db.scalars(
        select(SerumImmWorkbench.id)
        .order_by(SerumImmWorkbench.id.asc())
        .with_for_update()
    ).all()


def sync_project_queue_status(
    db: Session,
    experiment_id: str,
    *,
    is_terminal: bool,
) -> None:
    """Apply one project's terminal transition without rebuilding the full queue."""
    _lock_queue(db)
    row = db.scalar(
        select(SerumImmWorkbench)
        .where(SerumImmWorkbench.experiment_id == experiment_id)
        .with_for_update()
    )
    if row is None or not _is_started(row):
        return
    if is_terminal:
        if queued_sort(row.sort_order) is None:
            return
        row.sort_order = None
        renumber_queue(
            [
                item
                for item in _queue_rows(db)
                if int(item.id) != int(row.id)
            ]
        )
    elif queued_sort(row.sort_order) is None:
        _place_row(db, row, mode="last")


def _place_row(db: Session, row: SerumImmWorkbench, *, mode: str, target_sort: int | None = None) -> None:
    if not getattr(row, "id", None):
        db.flush()
    others = [item for item in _queue_rows(db) if int(item.id) != int(row.id)]
    place_row_among(others, row, mode=mode, target_sort=target_sort)


def _apply_queue(
    db: Session,
    row: SerumImmWorkbench,
    *,
    previous_sort: int | None,
    previous_priority: Any,
    payload: dict[str, Any],
    is_new: bool,
    project: SerumImmProject | None = None,
) -> None:
    if _row_is_terminal(row, project):
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


def _strain_groups_by_experiment(
    db: Session,
    experiment_ids: list[str],
) -> dict[str, list[dict[str, Any]]]:
    ids = [item for item in dict.fromkeys(experiment_ids) if item]
    if not ids:
        return {}
    grouped: dict[str, list[dict[str, Any]]] = {}
    rows = db.execute(
        select(
            SerumImmMouse.experiment_id,
            SerumImmMouse.mouse_strain,
            SerumImmMouse.mouse_strain_category,
        )
        .where(SerumImmMouse.experiment_id.in_(ids))
        .order_by(SerumImmMouse.id.asc())
    ).all()
    for experiment_id, mouse_strain, mouse_strain_category in rows:
        eid = str(experiment_id or "").strip()
        if not eid:
            continue
        grouped.setdefault(eid, []).append(
            {
                "mouse_strain": mouse_strain,
                "mouse_strain_category": mouse_strain_category,
            }
        )
    return grouped


def _show_scheme_strains(
    items: list[dict[str, Any]],
    grouped: dict[str, list[dict[str, Any]]],
) -> None:
    """有方案分组时，列表展示分组本身，用顿号拼接。不读项目上用加号存的字段。"""
    for item in items:
        experiment_id = str(item.get("experiment_id") or "").strip()
        groups = grouped.get(experiment_id) or []
        item["mouse_group_count"] = len(groups)
        if not groups:
            continue
        item["mouse_strain"] = _join_strain_parts(groups, "mouse_strain")
        item["mouse_strain_category"] = _join_strain_parts(groups, "mouse_strain_category")


def _write_strain_to_single_group(db: Session, row: SerumImmWorkbench) -> None:
    """没有分组时写入 G1；只有一组时改这一组。两组及以上不在这里改。"""
    experiment_id = str(row.experiment_id or "").strip()
    if not experiment_id:
        return
    groups = list(
        db.scalars(
            select(SerumImmMouse)
            .where(SerumImmMouse.experiment_id == experiment_id)
            .order_by(SerumImmMouse.id.asc())
        ).all()
    )
    if len(groups) >= 2:
        return
    strain = row.mouse_strain or None
    category = row.mouse_strain_category or None
    if len(groups) == 1:
        groups[0].mouse_strain = strain
        groups[0].mouse_strain_category = category
        return
    if not strain and not category:
        return
    db.add(
        SerumImmMouse(
            experiment_id=experiment_id,
            group_id="G1",
            mouse_strain=strain,
            mouse_strain_category=category,
        )
    )


def _with_mouse_group_flag(db: Session, data: dict[str, Any]) -> dict[str, Any]:
    grouped = _strain_groups_by_experiment(
        db,
        [str(data.get("experiment_id") or "").strip()],
    )
    _show_scheme_strains([data], grouped)
    return data


def _unique_project_name_strains(values: Any) -> list[str]:
    strains: list[str] = []
    seen: set[str] = set()
    for value in values:
        strain = str(value or "")
        if not strain.strip() or strain in seen:
            continue
        seen.add(strain)
        strains.append(strain)
    return strains


def _project_name_strains(db: Session, row: SerumImmWorkbench) -> list[str]:
    """品系优先取方案分组；还没有分组时用工作台行上的规划品系。"""
    experiment_id = str(row.experiment_id or "").strip()
    if experiment_id:
        group_strains = db.scalars(
            select(SerumImmMouse.mouse_strain)
            .where(SerumImmMouse.experiment_id == experiment_id)
            .order_by(SerumImmMouse.id.asc())
        ).all()
        if group_strains:
            return _unique_project_name_strains(group_strains)
    header = str(row.mouse_strain or "").strip()
    return [header] if header else []


def _auto_project_name(target_name: Any, strains: list[str]) -> str:
    # 与方案页、正式编辑页的 updateProjectName 同一句。
    return f"{str(target_name or '')}基于{','.join(strains)}的抗体发现"[:255]


def serialize_row(
    row: SerumImmWorkbench,
    project: SerumImmProject | None = None,
) -> dict[str, Any]:
    data = _overlay_identity(row.to_dict(), project)
    data["species_cross"] = _normalize_species_cross(data.get("species_cross")) or ""
    try:
        data["immuno_method"] = _normalize_immuno_method(data.get("immuno_method")) or ""
    except ValueError:
        data["immuno_method"] = str(data.get("immuno_method") or "").strip()
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
    if field == "immuno_method":
        try:
            return _normalize_immuno_method(value)
        except ValueError:
            return None
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
                continue
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
        elif field == "immuno_method":
            value = _normalize_immuno_method(value)
        elif field == "project_code":
            value = _compact_identifier(value) or None
        elif field in WORKBENCH_REMARK_FIELDS:
            value = clean_field_text(value, keep_breaks=True) or None
            if value and len(value) > 255:
                raise ValueError("备注不能超过 255 个字符")
        elif isinstance(value, str):
            value = clean_field_text(value, keep_breaks=field == "project_purpose") or None
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
        for item in db.scalars(select(model).where(model.experiment_id == exp_id)).all():
            db.delete(item)


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


def _scheme_strain_filter(field_name: str, value: str):
    group_column = getattr(SerumImmMouse, field_name)
    header_column = getattr(SerumImmWorkbench, field_name)
    in_scheme = exists(
        select(1).where(
            SerumImmMouse.experiment_id == SerumImmWorkbench.experiment_id,
            group_column == value,
        )
    ).correlate(SerumImmWorkbench)
    no_scheme = ~exists(
        select(1).where(SerumImmMouse.experiment_id == SerumImmWorkbench.experiment_id)
    ).correlate(SerumImmWorkbench)
    return or_(in_scheme, and_(no_scheme, header_column == value))


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
    )


def _keyword_rank_expr(keyword: str):
    like = f"%{keyword}%"
    return case(
        *((field.like(like), rank) for rank, field in enumerate(_keyword_field_exprs())),
        else_=len(_keyword_field_exprs()),
    )


def _csv_token_filter(column, value: str):
    return or_(
        column == value,
        column.like(f"{value},%"),
        column.like(f"%,{value}"),
        column.like(f"%,{value},%"),
    )


def _species_cross_filter(value: str):
    return _csv_token_filter(SerumImmWorkbench.species_cross, value)


def _immuno_method_filter(value: str):
    return _csv_token_filter(SerumImmWorkbench.immuno_method, value)


def _has_scheme_data_expr():
    return or_(*(
        exists(
            select(1).where(model.experiment_id == SerumImmWorkbench.experiment_id)
        ).correlate(SerumImmWorkbench)
        for model, _ in COPY_CHILD_MODELS
    ))


def _target_pair_stmt():
    name_expr = _aligned_value_expr(SerumImmWorkbench.target_name, SerumImmProject.target_name)
    codes_expr = _aligned_value_expr(SerumImmWorkbench.target_codes, SerumImmProject.target_codes)
    return (
        select(name_expr, codes_expr)
        .select_from(SerumImmWorkbench)
        .outerjoin(
            SerumImmProject,
            SerumImmWorkbench.experiment_id == SerumImmProject.experiment_id,
        )
    ), name_expr, codes_expr


def _apply_list_filters(stmt, data: dict[str, Any], *, skip_status: bool = False, db: Session | None = None):
    kw_tokens = split_code_tokens(data.get("keyword"))
    view_group = str(data.get("view_group") or "").strip()

    if len(kw_tokens) == 1:
        like = f"%{kw_tokens[0]}%"
        stmt = stmt.where(or_(*(field.like(like) for field in _keyword_field_exprs())))
    elif len(kw_tokens) > 1:
        stmt = stmt.where(or_(*(field.in_(kw_tokens) for field in _keyword_field_exprs())))
    pair_stmt, name_expr, codes_expr = _target_pair_stmt()
    target_clause = recorded_target_clause(db, name_expr, codes_expr, data.get("target_name"), pair_stmt)
    if target_clause is not None:
        stmt = stmt.where(target_clause)
    if not skip_status:
        view_filter = _view_group_expr(view_group)
        if view_filter is not None:
            stmt = stmt.where(view_filter)
        stmt = restrict(stmt, data.get("can_start"), lambda value: SerumImmWorkbench.can_start == value)
    stmt = restrict(stmt, data.get("has_scheme_data"), _has_scheme_data_clause)
    stmt = restrict(
        stmt,
        data.get("study_type"),
        lambda value: _aligned_value_expr(
            SerumImmWorkbench.study_type,
            SerumImmProject.study_type,
        ) == value,
    )
    stmt = restrict(
        stmt,
        data.get("mouse_strain_category"),
        lambda value: _scheme_strain_filter("mouse_strain_category", value),
    )
    stmt = restrict(stmt, data.get("species_cross"), _species_cross_filter)
    stmt = restrict(stmt, data.get("mouse_status"), lambda value: SerumImmWorkbench.mouse_status == value)
    stmt = restrict(stmt, data.get("antigen_ready"), lambda value: SerumImmWorkbench.antigen_ready == value)
    stmt = restrict(
        stmt,
        data.get("pm"),
        lambda value: _aligned_value_expr(SerumImmWorkbench.pm, SerumImmProject.pm) == value,
    )
    stmt = restrict(stmt, data.get("priority"), lambda value: SerumImmWorkbench.priority == value)
    stmt = restrict(
        stmt,
        data.get("owner"),
        lambda value: _aligned_value_expr(SerumImmWorkbench.owner, SerumImmProject.owner) == value,
    )
    stmt = restrict(stmt, data.get("reviewer"), lambda value: SerumImmWorkbench.reviewer == value)
    stmt = restrict(stmt, data.get("review_status"), lambda value: SerumImmWorkbench.review_status == value)
    stmt = restrict(stmt, data.get("display_status"), lambda value: _display_status_expr() == value)
    stmt = restrict(stmt, data.get("immuno_method"), _immuno_method_filter)
    stmt = restrict(
        stmt,
        data.get("mouse_strain"),
        lambda value: _scheme_strain_filter("mouse_strain", value),
    )
    stmt = restrict(stmt, data.get("mouse_zygosity"), lambda value: SerumImmWorkbench.mouse_zygosity == value)
    stmt = restrict(stmt, data.get("mouse_region"), lambda value: SerumImmWorkbench.mouse_region == value)
    stmt = restrict(
        stmt,
        data.get("mouse_expand_requested"),
        lambda value: SerumImmWorkbench.mouse_expand_requested == value,
    )
    stmt = restrict(stmt, data.get("antigen_source"), lambda value: SerumImmWorkbench.antigen_source == value)
    stmt = restrict(stmt, data.get("lnp_ordered"), lambda value: SerumImmWorkbench.lnp_ordered == value)
    stmt = restrict(
        stmt,
        data.get("cell_prep_status"),
        lambda value: SerumImmWorkbench.cell_prep_status == value,
    )
    return stmt


def _has_scheme_data_clause(value: str):
    if value == "是":
        return _has_scheme_data_expr()
    if value == "否":
        return ~_has_scheme_data_expr()
    return None


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
        db=db,
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
    limit = min(max(int(data.get("limit", 20) or 20), 1), 500)
    payload = data or {}
    stmt = _apply_list_filters(_base_stmt(), payload, db=db)
    total = db.scalar(_apply_list_filters(_count_stmt(), payload, db=db)) or 0
    order_by = [*_list_order(payload)]
    kw_tokens = split_code_tokens(payload.get("keyword"))
    if len(kw_tokens) == 1:
        order_by.insert(0, _keyword_rank_expr(kw_tokens[0]))
    rows = db.scalars(
        stmt.order_by(*order_by)
        .offset((page - 1) * limit)
        .limit(limit)
    ).unique().all()
    experiment_ids = [str(row.experiment_id or "").strip() for row in rows if row.experiment_id]
    strain_groups = _strain_groups_by_experiment(db, experiment_ids)
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
    _show_scheme_strains(items, strain_groups)
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
    stmt = _apply_list_filters(_base_stmt(), payload, db=db)
    order_by = [*_list_order(payload)]
    kw_tokens = split_code_tokens(payload.get("keyword"))
    if len(kw_tokens) == 1:
        order_by.insert(0, _keyword_rank_expr(kw_tokens[0]))
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
    _show_scheme_strains(items, _strain_groups_by_experiment(db, experiment_ids))
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


def get_options(db: Session) -> dict[str, Any]:
    def values(*columns) -> list[str]:
        result: set[str] = set()
        for column in columns:
            for value in db.scalars(select(column).where(column.is_not(None)).distinct()).all():
                text = str(value or "").strip()
                if text:
                    result.add(text)
        return sorted(result)

    def token_values(*columns) -> list[str]:
        result: set[str] = set()
        for column in columns:
            for value in db.scalars(select(column).where(column.is_not(None)).distinct()).all():
                for part in str(value).split("、"):
                    if part.strip():
                        result.add(part.strip())
        return sorted(result)

    owners = values(SerumImmProject.owner, SerumImmWorkbench.owner)
    pms = values(SerumImmProject.pm, SerumImmWorkbench.pm)
    pair_stmt, _name_expr, _codes_expr = _target_pair_stmt()
    return {
        "targets": target_select_options(
            (pairs := db.execute(pair_stmt).all()),
            catalog_names_for_pairs(db, pairs),
        ),
        "owners": owners,
        "pms": pms,
        "reviewers": values(SerumImmWorkbench.reviewer),
        "study_types": values(SerumImmWorkbench.study_type, SerumImmProject.study_type),
        "mouse_strains": token_values(
            SerumImmMouse.mouse_strain,
            SerumImmWorkbench.mouse_strain,
        ),
        "mouse_strain_categories": token_values(
            SerumImmMouse.mouse_strain_category,
            SerumImmWorkbench.mouse_strain_category,
        ),
        "statuses": values(
            SerumImmWorkbench.plan_status,
            SerumImmProject.project_status,
        ),
        "immuno_methods": sorted({
            part.strip()
            for value in values(SerumImmWorkbench.immuno_method)
            for part in str(value).replace("，", ",").split(",")
            if part.strip()
        }),
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
    if raw_id is None or "sort_order" in payload or "priority" in payload or "plan_status" in payload:
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
            sort_order=None,
            created_by=created_by,
        )
        db.add(row)

    _validate_row_edit_scope(
        row,
        payload,
        is_new=is_new,
        edit_scopes=edit_scopes,
    )
    previous_sort = queued_sort(row.sort_order)
    previous_priority = row.priority
    _validate_expected_fields(row, expected)
    refresh_project_name = (
        not _is_started(row)
        and "project_name" not in payload
        and ("target_name" in payload or "mouse_strain" in payload)
    )
    previous_auto_name = (
        _auto_project_name(row.target_name, _project_name_strains(db, row))
        if refresh_project_name
        else ""
    )

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
        wrote_strain = any(field in payload for field in STRAIN_FIELDS)
        if wrote_strain:
            experiment_id = str(row.experiment_id or "").strip()
            if len(_strain_groups_by_experiment(db, [experiment_id]).get(experiment_id) or []) >= 2:
                raise ValueError("方案已有两组及以上小鼠，请在方案中修改小鼠品系和归类鼠型")
        incoming_category = str(payload.get("mouse_strain_category") or "").strip()
        if incoming_category and incoming_category not in MOUSE_STRAIN_CATEGORY_OPTIONS:
            raise ValueError("归类鼠型不在允许的选项中")
        incoming_region = str(payload.get("mouse_region") or "").strip()
        if incoming_region and incoming_region not in MOUSE_REGION_OPTIONS:
            raise ValueError("提供地区不在允许的选项中")
        _apply_fields(row, payload, ALIGNED_FIELDS + PREP_FIELDS)
        _assign_temp_experiment_id(db, row)
        if wrote_strain:
            _write_strain_to_single_group(db, row)
            db.flush()
        if refresh_project_name:
            current_name = str(row.project_name or "").strip()
            if not current_name or current_name == previous_auto_name:
                row.project_name = _auto_project_name(
                    row.target_name,
                    _project_name_strains(db, row),
                )
    project = _project_by_experiment(db, row.experiment_id) if _is_started(row) else None
    _apply_queue(
        db,
        row,
        previous_sort=previous_sort,
        previous_priority=previous_priority,
        payload=payload,
        is_new=is_new,
        project=project,
    )
    if commit:
        db.commit()
        db.refresh(row)
    project = _project_by_experiment(db, row.experiment_id) if _is_started(row) else None
    return _with_mouse_group_flag(db, serialize_row(row, project))


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
        if row_id is None or "sort_order" in item or "priority" in item or "plan_status" in item:
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
    _show_scheme_strains(
        saved,
        _strain_groups_by_experiment(
            db,
            [str(item.get("experiment_id") or "").strip() for item in saved],
        ),
    )
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
    renumber_queue(_queue_rows(db))
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
                if mouse_group_data:
                    project.mouse_strain = _join_strain_parts(mouse_group_data, "mouse_strain")
                    project.mouse_strain_category = _join_strain_parts(
                        mouse_group_data,
                        "mouse_strain_category",
                    )
                else:
                    project.mouse_strain = row.mouse_strain or None
                    project.mouse_strain_category = row.mouse_strain_category or None
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
    return _with_mouse_group_flag(db, serialize_row(row, project))


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
    return _with_mouse_group_flag(db, serialize_row(row))


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
    _assign_temp_experiment_id(db, clone)
    _apply_queue(
        db,
        clone,
        previous_sort=None,
        previous_priority=DEFAULT_PRIORITY,
        payload={},
        is_new=True,
    )
    _clone_children(db, source.experiment_id, clone.experiment_id)
    db.commit()
    db.refresh(clone)
    return _with_mouse_group_flag(db, serialize_row(clone))


def reorder(
    db: Session,
    moved_id: Any,
    target_id: Any,
    *,
    edit_scopes: set[str] | frozenset[str] | None = None,
) -> dict[str, Any]:
    _lock_queue(db)
    if "full" not in _edit_scope_set(edit_scopes):
        raise PermissionError("没有权限调整工作台队列排序")
    parsed_moved_id = _parse_row_id(moved_id)
    parsed_target_id = _parse_row_id(target_id)
    if parsed_moved_id is None or parsed_target_id is None:
        raise ValueError("排序记录 ID 不正确")
    moved = db.get(SerumImmWorkbench, parsed_moved_id)
    target = db.get(SerumImmWorkbench, parsed_target_id)
    if not moved or not target:
        raise ValueError("工作台记录不存在")
    if parsed_moved_id == parsed_target_id:
        return {
            "items": [
                serialize_row(moved, _project_by_experiment(db, moved.experiment_id) if _is_started(moved) else None),
            ]
        }
    projects = _projects_for_rows(db, [moved, target])
    for row in (moved, target):
        if _row_is_terminal(row, projects.get(str(row.experiment_id or "").strip())) or queued_sort(row.sort_order) is None:
            raise ValueError("终态记录不参与排序")
    _place_row(db, moved, mode="snap", target_sort=queued_sort(target.sort_order))
    db.commit()
    return {
        "items": [
            serialize_row(row, _project_by_experiment(db, row.experiment_id) if _is_started(row) else None)
            for row in (moved, target)
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
    scheme_groups = sanitized_children["mouse_groups"]
    if len(scheme_groups) == 1:
        row.mouse_strain = str(scheme_groups[0].get("mouse_strain") or "").strip() or None
        row.mouse_strain_category = str(scheme_groups[0].get("mouse_strain_category") or "").strip() or None
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
