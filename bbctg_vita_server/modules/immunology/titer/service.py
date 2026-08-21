from datetime import datetime, time, timedelta
from io import BytesIO
from pathlib import Path
import json
import random
from typing import Any

from fastapi import UploadFile
from PIL import Image
from sqlalchemy import JSON, String, and_, bindparam, case, cast, func, or_, select, text
from sqlalchemy.orm import Session

from core.config import get_settings
from integrations import drm_service
from models.immunology import (
    SerumElisaPlate,
    SerumFacsPlate,
    SerumFile,
    SerumImmMouse,
    SerumImmProject,
    SerumImmStep,
    SerumTiterOrder,
    SerumTiterPc,
    SerumTiterTarget,
)
from models.mega_automation import MegaFlowWorkOrder
from modules.mega_automation.service import ORDER_STATUS_LABELS


def _upload_root() -> Path:
    root = Path(get_settings().repository_root) / "uploads" / "titer_files"
    root.mkdir(parents=True, exist_ok=True)
    return root


def get_full_path(relative_path: str) -> Path:
    path_parts = relative_path.lstrip("/")
    settings = get_settings()
    return Path(settings.repository_root) / "uploads" / path_parts


def get_file_list(db: Session, experiment_id: str) -> list[dict]:
    if not experiment_id:
        return []
    return [item.to_dict() for item in db.scalars(select(SerumFile).where(SerumFile.experiment_id == experiment_id)).all()]


def _save_upload_content(db: Session, file_obj: UploadFile, file_path: Path) -> None:
    with file_path.open("wb") as target:
        target.write(file_obj.file.read())
    drm_service.decrypt_upload_file_if_available(db, file_path)


def save_file(db: Session, file_obj: UploadFile, experiment_id: str, user_name: str = "unknown") -> dict:
    if not file_obj.filename or not experiment_id:
        raise ValueError("缺少文件或实验 ID")

    exp_dir = _upload_root() / experiment_id
    exp_dir.mkdir(parents=True, exist_ok=True)
    save_name = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{Path(file_obj.filename).name}"
    file_path = exp_dir / save_name

    _save_upload_content(db, file_obj, file_path)

    record = SerumFile(
        experiment_id=experiment_id,
        upload_user=user_name,
        file_name=file_obj.filename,
        file_path=f"/titer_files/{experiment_id}/{save_name}",
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record.to_dict()


def delete_file(db: Session, file_id: int) -> None:
    record = db.get(SerumFile, file_id)
    if not record:
        raise ValueError("文件不存在")
    full_path = get_full_path(record.file_path)
    if full_path.exists():
        full_path.unlink()
    db.delete(record)
    db.commit()


def rename_file(db: Session, file_id: int, new_name: str) -> None:
    record = db.get(SerumFile, file_id)
    if not record:
        raise ValueError("文件不存在")
    record.file_name = new_name
    db.commit()


def replace_file(db: Session, file_id: int, file_obj: UploadFile, user_name: str = "unknown") -> dict:
    record = db.get(SerumFile, file_id)
    if not record:
        raise ValueError("文件不存在")

    old_path = get_full_path(record.file_path)
    exp_dir = old_path.parent
    exp_dir.mkdir(parents=True, exist_ok=True)
    save_name = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{Path(file_obj.filename or '').name}"
    new_path = exp_dir / save_name

    _save_upload_content(db, file_obj, new_path)
    if old_path != new_path and old_path.exists():
        old_path.unlink()

    record.file_name = file_obj.filename or save_name
    record.file_path = f"/titer_files/{record.experiment_id}/{save_name}"
    record.upload_user = user_name
    db.commit()
    db.refresh(record)
    return record.to_dict()


def get_download_record(db: Session, file_id: int) -> tuple[SerumFile, Path]:
    record = db.get(SerumFile, file_id)
    if not record:
        raise ValueError("文件不存在")
    full_path = get_full_path(record.file_path)
    if not full_path.exists():
        raise ValueError("磁盘上找不到文件")
    return record, full_path


def create_thumbnail(file_path: Path, width: int, height: int) -> tuple[BytesIO, str] | None:
    suffix = file_path.suffix.lower()
    if suffix not in {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"}:
        return None
    image = Image.open(file_path)
    image.thumbnail((width, height), Image.Resampling.LANCZOS)
    output = BytesIO()
    image_format = image.format or "JPEG"
    image.save(output, format=image_format, quality=85)
    output.seek(0)
    return output, f"image/{image_format.lower()}"


def _normalize_owner_names(value: Any) -> list[str]:
    if not value:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item or "").strip()]
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    return []


ASSAY_FILTER_FACS = "__facs__"
ASSAY_FILTER_ELISA = "__elisa__"
ASSAY_FILTER_FACS_ELISA = "__facs_elisa__"


def _assay_method_expr():
    return func.coalesce(SerumTiterOrder.assay_method, SerumImmProject.assay_method)


def _assay_plate_expr(method: str):
    order_col = SerumTiterOrder.facs_plate_count if method == "FACS" else SerumTiterOrder.elisa_plate_count
    project_col = SerumImmProject.facs_plate_count if method == "FACS" else SerumImmProject.elisa_plate_count
    return func.coalesce(order_col, project_col)


def _has_positive_plate_count(column):
    return and_(column.is_not(None), column > 0)


def _only_zero_plate_count(column):
    return or_(column.is_(None), column <= 0)


def _parse_optional_plate_count(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _mouse_count_expr():
    return func.coalesce(SerumTiterOrder.mouse_count, 0)


def _apply_numeric_column_filters(stmt, data: dict[str, Any]):
    specs = (
        ("mouse_count", _mouse_count_expr),
        ("facs_plate", lambda: _assay_plate_expr("FACS")),
        ("elisa_plate", lambda: _assay_plate_expr("ELISA")),
    )
    for prefix, expr_fn in specs:
        zero_mode = str(data.get(f"{prefix}_zero") or "").strip()
        min_val = _parse_optional_plate_count(data.get(f"{prefix}_min"))
        max_val = _parse_optional_plate_count(data.get(f"{prefix}_max"))
        if not zero_mode and min_val is None and max_val is None:
            continue
        expr = expr_fn()
        parts = []
        if zero_mode == "hide":
            parts.append(_has_positive_plate_count(expr))
        elif zero_mode == "only":
            parts.append(_only_zero_plate_count(expr))
        if min_val is not None:
            parts.append(expr >= min_val)
        if max_val is not None:
            parts.append(expr <= max_val)
        stmt = stmt.where(and_(*parts))
    return stmt


def _apply_assay_method_filter(stmt, assay_method: str):
    """检测方法筛选：按检测方法文案列匹配。"""
    expr = _assay_method_expr()
    if assay_method == ASSAY_FILTER_FACS:
        return stmt.where(expr.like("%FACS%"))
    if assay_method == ASSAY_FILTER_ELISA:
        return stmt.where(expr.like("%ELISA%"))
    if assay_method == ASSAY_FILTER_FACS_ELISA:
        return stmt.where(expr.like("%FACS%"), expr.like("%ELISA%"))
    target = str(assay_method or "").strip()
    if not target:
        return stmt
    return stmt.where(expr == target)


def _normalize_test_dates(value: Any) -> list[str]:
    if not value:
        return []
    items = value if isinstance(value, list) else str(value).replace("、", ",").split(",")
    dates: list[str] = []
    for item in items:
        text_value = str(item or "").strip()[:10]
        if len(text_value) == 10:
            dates.append(text_value)
    return sorted(set(dates))


def _test_dates_in_range_clause(range_start: str, range_end: str):
    """工单 test_dates（JSON 日期数组）中任意一天落在 [range_start, range_end] 内即命中。"""
    start_d = datetime.strptime(range_start, "%Y-%m-%d").date()
    end_d = datetime.strptime(range_end, "%Y-%m-%d").date()
    if start_d > end_d:
        start_d, end_d = end_d, start_d
    span = (end_d - start_d).days + 1

    if span <= 400:
        range_dates = [(start_d + timedelta(days=i)).isoformat() for i in range(span)]
        range_json = json.dumps(range_dates)
        return func.json_overlaps(
            func.coalesce(SerumTiterOrder.test_dates, text("JSON_ARRAY()")),
            cast(bindparam("test_dates_range_json", value=range_json), JSON),
        )

    parts = []
    if range_start != "0000-01-01":
        parts.append("LEFT(td.d, 10) >= :test_dates_range_start")
    if range_end != "9999-12-31":
        parts.append("LEFT(td.d, 10) <= :test_dates_range_end")
    where_clause = " AND ".join(parts) if parts else "1=1"
    return text(
        "EXISTS (SELECT 1 FROM JSON_TABLE("
        "COALESCE(CAST(serum_titer_order.test_dates AS JSON), JSON_ARRAY()), '$[*]' "
        "COLUMNS (d VARCHAR(32) PATH '$')) td "
        f"WHERE {where_clause})"
    ).bindparams(
        test_dates_range_start=range_start,
        test_dates_range_end=range_end,
    )


def _parse_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    raw = str(value).strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            continue
    raise ValueError("检测日期格式不正确")


def _filter_date_bounds(data: dict[str, Any], start_key: str, end_key: str) -> tuple[str | None, str | None]:
    range_start = None
    range_end = None
    if data.get(start_key):
        try:
            start_time = _parse_datetime(data[start_key])
            if start_time:
                range_start = start_time.date().isoformat()
        except ValueError:
            pass
    if data.get(end_key):
        try:
            end_time = _parse_datetime(data[end_key])
            if end_time:
                if str(data[end_key]).strip().count(":") == 0:
                    end_time = datetime.combine(end_time.date(), time.max)
                range_end = end_time.date().isoformat()
        except ValueError:
            pass
    return range_start, range_end


def _project_code_part(project_code: str | None, experiment_id: str) -> str:
    value = (project_code or experiment_id or "NO_PROJECT").strip()
    return value.replace(" ", "")


def generate_titer_order_id(db: Session, project_code: str | None, experiment_id: str) -> str:
    prefix = datetime.now().strftime("%Y%m%d%H%M%S")
    project_part = _project_code_part(project_code, experiment_id)
    for _ in range(20):
        candidate = f"{prefix}-{project_part}-{random.randint(0, 9999):04d}"
        exists = db.scalar(select(SerumTiterOrder.id).where(SerumTiterOrder.titer_order_id == candidate))
        if not exists:
            return candidate
    raise ValueError("效价工单 ID 生成失败")


def _sum_mouse_count(mice: list[SerumImmMouse]) -> int | None:
    total = 0
    has_value = False
    for mouse in mice:
        try:
            total += int(str(mouse.mouse_count or "").strip())
            has_value = True
        except ValueError:
            continue
    return total if has_value else None


def _unique_cages(mice: list[SerumImmMouse]) -> list[str]:
    cages = {str(mouse.cage_position or "").strip() for mouse in mice}
    return sorted(cage for cage in cages if cage)


def _groups_for_blood_date(steps: list[SerumImmStep], blood_date: str) -> set[str]:
    date = _normalize_blood_collection_date(blood_date) or ""
    if not date:
        return set()
    groups: set[str] = set()
    for step in steps:
        if str(step.stage_name or "").strip() != BLOOD_COLLECTION_STAGE_NAME:
            continue
        if (_normalize_blood_collection_date(step.date_actual) or "") != date:
            continue
        group_id = str(step.group_id or "").strip()
        if group_id:
            groups.add(group_id)
    return groups


def _derived_cage_position(
    mice: list[SerumImmMouse],
    steps: list[SerumImmStep],
    blood_date: str,
) -> str:
    """能对上采血日则只用当天组；对不上则用全项目。笼位去重去空后拼接。"""
    groups = _groups_for_blood_date(steps, blood_date)
    if groups:
        mice = [mouse for mouse in mice if str(mouse.group_id or "").strip() in groups]
    return "、".join(_unique_cages(mice))


BLOOD_COLLECTION_STAGE_NAME = "采血"
PENDING_BLOOD_COLLECTION_STATUS = "待采血"
PENDING_BLOOD_COLLECTION_BOOST_STATUS = "待采血-加免"
TITER_ORDER_PRIORITY_DEFAULT = "正常"
TITER_ORDER_PRIORITIES = ("正常", "加急", "非常紧急", "吉吉国王")
TITER_SERUM_STATUS_ORDER = ("待采血", "待采血-加免", "已采血", "已检测", "已交接", "已销毁")
TITER_SERUM_STATUS_POST_TEST = ("已检测", "已交接", "已销毁")
TITER_FLOW_ORDER_TYPE = "TITER"

# NULL=跟随免疫方案；非 NULL=用户覆盖（字段互相独立）
FOLLOWABLE_BATCH_KEYS = (
    "cage_position",
    "blood_collection_date",
    "mouse_count",
    "assay_method",
    "facs_plate_count",
    "elisa_plate_count",
)


def _normalize_blood_collection_date(raw: Any) -> str | None:
    value = str(raw or "").strip()[:10]
    return value if len(value) == 10 else None


def _all_blood_collection_dates(steps: list[SerumImmStep]) -> list[str]:
    """方案全部采血日：去重升序。"""
    dates: list[str] = []
    seen: set[str] = set()
    for step in steps:
        if str(step.stage_name or "").strip() != BLOOD_COLLECTION_STAGE_NAME:
            continue
        blood_date = _normalize_blood_collection_date(step.date_actual)
        if not blood_date or blood_date in seen:
            continue
        seen.add(blood_date)
        dates.append(blood_date)
    return sorted(dates)


def _blood_collection_seq_for_date(blood_dates: list[str], blood_date: str) -> int | None:
    try:
        return blood_dates.index(blood_date) + 1
    except ValueError:
        return None


def _scheme_date_for_seq(blood_dates: list[str], seq: int | None) -> str | None:
    if not blood_dates or not isinstance(seq, int) or seq < 1:
        return None
    idx = seq - 1
    return blood_dates[idx] if idx < len(blood_dates) else blood_dates[-1]


def _known_blood_collection_seqs(db: Session, experiment_id: str) -> set[int]:
    rows = db.scalars(
        select(SerumTiterOrder.blood_collection_seq).where(
            SerumTiterOrder.experiment_id == experiment_id,
            SerumTiterOrder.blood_collection_seq.is_not(None),
        )
    ).all()
    return {int(seq) for seq in rows if seq is not None}


def _default_blood_collection_seq(
    db: Session,
    experiment_id: str,
    steps: list[SerumImmStep],
) -> int | None:
    """新建默认：最小未占用的采血次数。"""
    blood_dates = _all_blood_collection_dates(steps)
    if not blood_dates:
        return None
    known_seqs = _known_blood_collection_seqs(db, experiment_id)
    for seq in range(1, len(blood_dates) + 1):
        if seq not in known_seqs:
            return seq
    return None


def _immune_batch_fields(
    project: SerumImmProject,
    mice: list[SerumImmMouse],
    steps: list[SerumImmStep] | None = None,
    blood_date: str | None = None,
) -> dict[str, Any]:
    """方案侧可跟随字段（采血日由 seq 推导，不在此返回）。"""
    return {
        "cage_position": _derived_cage_position(mice, steps or [], blood_date or "") or None,
        "mouse_count": _sum_mouse_count(mice),
        "assay_method": project.assay_method,
        "facs_plate_count": project.facs_plate_count,
        "elisa_plate_count": project.elisa_plate_count,
    }


def _immune_batch_for_experiment(
    db: Session,
    experiment_id: str,
    *,
    project: SerumImmProject | None = None,
) -> tuple[SerumImmProject, dict[str, Any], list[SerumImmStep]]:
    if project is None:
        experiment_id = str(experiment_id or "").strip()
        if not experiment_id:
            raise ValueError("请选择免疫实验")
        project = db.scalar(select(SerumImmProject).where(SerumImmProject.experiment_id == experiment_id))
        if not project:
            raise ValueError("免疫实验不存在")
    else:
        experiment_id = project.experiment_id
        if not experiment_id:
            raise ValueError("免疫实验不存在")
    mice = list(db.scalars(select(SerumImmMouse).where(SerumImmMouse.experiment_id == experiment_id)).all())
    steps = list(db.scalars(select(SerumImmStep).where(SerumImmStep.experiment_id == experiment_id)).all())
    return project, _immune_batch_fields(project, mice, steps), steps


def _apply_batch_fields_to_order(order: SerumTiterOrder, batch: dict[str, Any]) -> None:
    order.cage_position = batch.get("cage_position")
    order.blood_collection_date = batch.get("blood_collection_date")
    order.mouse_count = batch.get("mouse_count")
    order.assay_method = batch.get("assay_method")
    order.facs_plate_count = batch.get("facs_plate_count")
    order.elisa_plate_count = batch.get("elisa_plate_count")


def _batch_fields_to_preview(batch: dict[str, Any]) -> dict[str, Any]:
    return {
        "cage_position": batch.get("cage_position") or "",
        "mouse_count": batch.get("mouse_count"),
        "assay_method": batch.get("assay_method") or "",
        "facs_plate_count": batch.get("facs_plate_count"),
        "elisa_plate_count": batch.get("elisa_plate_count"),
    }


def _coalesce_follow_str(stored: str | None, derived: str | None) -> str:
    if stored is not None:
        return stored or ""
    return derived or ""


def _coalesce_follow_int(stored: int | None, derived: int | None) -> int | None:
    if stored is not None:
        return stored
    return derived


def _effective_blood_collection_date(order: SerumTiterOrder, blood_dates: list[str]) -> str:
    if order.blood_collection_date is not None:
        return _normalize_blood_collection_date(order.blood_collection_date) or ""
    return _scheme_date_for_seq(blood_dates, order.blood_collection_seq) or ""


def _build_derive_contexts(db: Session, experiment_ids: list[str]) -> dict[str, dict[str, Any]]:
    ids = [str(eid).strip() for eid in experiment_ids if str(eid or "").strip()]
    if not ids:
        return {}

    mice_by_exp: dict[str, list[SerumImmMouse]] = {eid: [] for eid in ids}
    for mouse in db.scalars(select(SerumImmMouse).where(SerumImmMouse.experiment_id.in_(ids))).all():
        mice_by_exp.setdefault(mouse.experiment_id, []).append(mouse)

    steps_by_exp: dict[str, list[SerumImmStep]] = {eid: [] for eid in ids}
    for step in db.scalars(select(SerumImmStep).where(SerumImmStep.experiment_id.in_(ids))).all():
        steps_by_exp.setdefault(step.experiment_id, []).append(step)

    return {
        eid: {
            "mice": mice_by_exp.get(eid, []),
            "steps": steps_by_exp.get(eid, []),
            "blood_dates": _all_blood_collection_dates(steps_by_exp.get(eid, [])),
        }
        for eid in ids
    }


def _resolve_followable_fields(
    order: SerumTiterOrder,
    project: SerumImmProject,
    ctx: dict[str, Any] | None,
) -> dict[str, Any]:
    mice = list(ctx.get("mice") or []) if ctx else []
    steps = list(ctx.get("steps") or []) if ctx else []
    blood_dates = list(ctx.get("blood_dates") or []) if ctx else []
    blood_date = _effective_blood_collection_date(order, blood_dates)
    scheme = _immune_batch_fields(project, mice, steps, blood_date)
    return {
        "cage_position": _coalesce_follow_str(order.cage_position, scheme.get("cage_position")),
        "blood_collection_date": blood_date,
        "blood_collection_seq": order.blood_collection_seq,
        "mouse_count": _coalesce_follow_int(order.mouse_count, scheme.get("mouse_count")),
        "assay_method": _coalesce_follow_str(order.assay_method, scheme.get("assay_method")),
        "facs_plate_count": _coalesce_follow_int(order.facs_plate_count, scheme.get("facs_plate_count")),
        "elisa_plate_count": _coalesce_follow_int(order.elisa_plate_count, scheme.get("elisa_plate_count")),
    }


def _normalize_batch_fields_payload(data: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    if "cage_position" in data:
        result["cage_position"] = str(data.get("cage_position") or "").strip() or None
    if "blood_collection_date" in data:
        value = str(data.get("blood_collection_date") or "").strip()[:10]
        result["blood_collection_date"] = value if len(value) == 10 else None
    if "mouse_count" in data:
        raw = data.get("mouse_count")
        if raw is None or raw == "":
            result["mouse_count"] = None
        else:
            try:
                result["mouse_count"] = int(raw)
            except (TypeError, ValueError) as exc:
                raise ValueError("只数须为整数") from exc
    if "assay_method" in data:
        value = str(data.get("assay_method") or "").strip()
        result["assay_method"] = value or None
    if "facs_plate_count" in data:
        result["facs_plate_count"] = _normalize_plate_count(data.get("facs_plate_count"))
    if "elisa_plate_count" in data:
        result["elisa_plate_count"] = _normalize_plate_count(data.get("elisa_plate_count"))
    return result


def _normalize_plate_count(raw: Any) -> int | None:
    if raw is None or raw == "":
        return None
    try:
        value = int(raw)
    except (TypeError, ValueError) as exc:
        raise ValueError("板数须为整数") from exc
    if value < 0:
        raise ValueError("板数须为非负整数")
    return value


def _apply_batch_overrides(order: SerumTiterOrder, overrides: dict[str, Any]) -> None:
    for key in FOLLOWABLE_BATCH_KEYS:
        if key in overrides:
            setattr(order, key, overrides[key])


def _blood_collections_payload(blood_dates: list[str]) -> list[dict[str, Any]]:
    return [{"seq": idx + 1, "date": blood_date} for idx, blood_date in enumerate(blood_dates)]


def _scheme_follow_baseline(
    order: SerumTiterOrder,
    project: SerumImmProject,
    ctx: dict[str, Any] | None,
) -> dict[str, Any]:
    """编辑保存时对比用：方案推导值（采血日按当前 seq）。"""
    mice = list(ctx.get("mice") or []) if ctx else []
    steps = list(ctx.get("steps") or []) if ctx else []
    blood_dates = list(ctx.get("blood_dates") or []) if ctx else []
    blood_date = _scheme_date_for_seq(blood_dates, order.blood_collection_seq)
    scheme = _immune_batch_fields(project, mice, steps, blood_date)
    return {
        **scheme,
        "blood_collection_date": blood_date,
    }


def _follow_values_equal(key: str, submitted: Any, baseline: Any) -> bool:
    if key in ("mouse_count", "facs_plate_count", "elisa_plate_count"):
        return submitted == baseline
    if key == "blood_collection_date":
        return (_normalize_blood_collection_date(submitted) or "") == (
            _normalize_blood_collection_date(baseline) or ""
        )
    return (str(submitted or "").strip()) == (str(baseline or "").strip())


def _apply_batch_overrides_on_edit(
    order: SerumTiterOrder,
    overrides: dict[str, Any],
    baseline: dict[str, Any],
) -> None:
    """表内已是 NULL 且提交值仍等于方案推导 → 保持跟随，避免误写成覆盖。"""
    for key, value in overrides.items():
        if key not in FOLLOWABLE_BATCH_KEYS:
            continue
        if getattr(order, key) is None and _follow_values_equal(key, value, baseline.get(key)):
            continue
        setattr(order, key, value)


def _parse_blood_collection_seq(raw: Any) -> int | None:
    if raw is None or raw == "":
        return None
    try:
        seq = int(raw)
    except (TypeError, ValueError) as exc:
        raise ValueError("采血次数须为整数") from exc
    if seq < 1:
        raise ValueError("采血次数须为正整数")
    return seq


def _normalize_titer_order_priority(raw: Any) -> str:
    value = str(raw or "").strip() or TITER_ORDER_PRIORITY_DEFAULT
    if value not in TITER_ORDER_PRIORITIES:
        raise ValueError("检测优先级须为：正常、加急、非常紧急、吉吉国王")
    return value


def get_titer_order_batch_preview(db: Session, experiment_id: str) -> dict[str, Any]:
    project, batch, steps = _immune_batch_for_experiment(db, experiment_id)
    blood_dates = _all_blood_collection_dates(steps)
    preview = _batch_fields_to_preview(batch)
    # 采血日默认空：由次数跟随方案；仅用户填自定义日期时才写入
    preview["blood_collection_date"] = ""
    preview["blood_collection_seq"] = _default_blood_collection_seq(db, project.experiment_id, steps)
    return {
        "experiment_id": project.experiment_id,
        "project_code": project.project_code or "",
        "target_name": project.target_name or "",
        "blood_collections": _blood_collections_payload(blood_dates),
        **preview,
    }


def _order_to_list_item(
    order: SerumTiterOrder,
    project: SerumImmProject,
    ctx: dict[str, Any] | None = None,
) -> dict:
    item = order.to_dict()
    item.update(_resolve_followable_fields(order, project, ctx))
    blood_dates = list(ctx.get("blood_dates") or []) if ctx else []
    item.update(
        {
            "project_id": project.id,
            "project_code": project.project_code or "",
            "target_name": project.target_name or "",
            "immune_owner": project.owner or "",
            "immune_status": project.project_status or "",
            "blood_collections": _blood_collections_payload(blood_dates),
            "following": {
                "cage_position": order.cage_position is None,
                "blood_collection_date": order.blood_collection_date is None,
                "mouse_count": order.mouse_count is None,
                "assay_method": order.assay_method is None,
                "facs_plate_count": order.facs_plate_count is None,
                "elisa_plate_count": order.elisa_plate_count is None,
            },
        }
    )
    return item


def _latest_titer_flow_id_subquery(*, source_ids: list[str] | None = None):
    stmt = (
        select(
            MegaFlowWorkOrder.source_id.label("source_id"),
            func.max(MegaFlowWorkOrder.id).label("max_id"),
        )
        .where(
            MegaFlowWorkOrder.orderType == TITER_FLOW_ORDER_TYPE,
            MegaFlowWorkOrder.source_id.is_not(None),
            MegaFlowWorkOrder.source_id != "",
        )
        .group_by(MegaFlowWorkOrder.source_id)
    )
    if source_ids is not None:
        stmt = stmt.where(MegaFlowWorkOrder.source_id.in_(source_ids))
    return stmt.subquery()


def _latest_titer_flow_status_subquery():
    latest_id = _latest_titer_flow_id_subquery()
    return (
        select(
            MegaFlowWorkOrder.source_id.label("source_id"),
            MegaFlowWorkOrder.status.label("status"),
        )
        .join(latest_id, MegaFlowWorkOrder.id == latest_id.c.max_id)
        .subquery()
    )


def _latest_flow_status_by_titer_ids(db: Session, titer_order_ids: list[str]) -> dict[str, str]:
    ids = [str(value).strip() for value in titer_order_ids if str(value or "").strip()]
    if not ids:
        return {}
    latest_id = _latest_titer_flow_id_subquery(source_ids=ids)
    rows = db.execute(
        select(MegaFlowWorkOrder.source_id, MegaFlowWorkOrder.status).join(
            latest_id, MegaFlowWorkOrder.id == latest_id.c.max_id
        )
    ).all()
    return {str(source_id): str(status or "") for source_id, status in rows if source_id}


def _apply_flow_status_to_items(db: Session, items: list[dict]) -> list[dict]:
    status_map = _latest_flow_status_by_titer_ids(db, [item.get("titer_order_id") or "" for item in items])
    for item in items:
        status = status_map.get(str(item.get("titer_order_id") or "").strip(), "")
        item["order_status"] = status
        item["order_status_label"] = ORDER_STATUS_LABELS.get(status, status) if status else ""
    return items


def _enrich_order_rows(
    db: Session,
    rows: list[tuple[SerumTiterOrder, SerumImmProject]],
) -> list[dict]:
    exp_ids = [project.experiment_id for _order, project in rows if project.experiment_id]
    contexts = _build_derive_contexts(db, exp_ids)
    items = [
        _order_to_list_item(order, project, contexts.get(order.experiment_id))
        for order, project in rows
    ]
    return _apply_flow_status_to_items(db, items)


def _blood_date_in_range(value: str, start: str | None, end: str | None) -> bool:
    date_value = _normalize_blood_collection_date(value) or ""
    if not date_value:
        return False
    if start and date_value < start:
        return False
    if end and date_value > end:
        return False
    return True


def _titer_order_query():
    return (
        select(SerumTiterOrder, SerumImmProject)
        .join(SerumImmProject, SerumImmProject.experiment_id == SerumTiterOrder.experiment_id)
        .where(or_(SerumImmProject.project_status.is_(None), SerumImmProject.project_status != "deleted"))
    )


TITER_SERUM_STATUS_RANK = {status: index for index, status in enumerate(TITER_SERUM_STATUS_ORDER)}
TITER_PRIORITY_RANK = {name: index for index, name in enumerate(TITER_ORDER_PRIORITIES)}
TITER_ORDER_SQL_SORT_COLUMNS = {
    "project_code": SerumImmProject.project_code,
    "serum_status": case(
        TITER_SERUM_STATUS_RANK,
        value=SerumTiterOrder.serum_status,
        else_=len(TITER_SERUM_STATUS_ORDER),
    ),
    "priority": case(
        TITER_PRIORITY_RANK,
        value=func.coalesce(func.nullif(SerumTiterOrder.priority, ""), TITER_ORDER_PRIORITY_DEFAULT),
        else_=len(TITER_ORDER_PRIORITIES),
    ),
}
TITER_ORDER_ITEM_SORT_FIELDS = {
    "blood_collection_date",
    "project_code",
    "serum_status",
    "priority",
    "test_dates_display",
}


def _titer_order_sql_order_by(data: dict[str, Any]) -> list:
    column = TITER_ORDER_SQL_SORT_COLUMNS.get(str(data.get("sort_field") or ""))
    if column is None:
        return [SerumTiterOrder.id.desc()]
    direction = str(data.get("sort_order") or "").lower()
    ordered_column = column.asc() if direction == "asc" else column.desc()
    return [ordered_column, SerumTiterOrder.id.desc()]


def _titer_order_needs_full_scan(data: dict[str, Any], blood_start: str | None, blood_end: str | None) -> bool:
    if blood_start or blood_end:
        return True
    return str(data.get("sort_field") or "") in {"blood_collection_date", "test_dates_display"}


def _item_sort_key(item: dict, field: str):
    if field == "serum_status":
        return TITER_SERUM_STATUS_RANK.get(str(item.get("serum_status") or "").strip(), len(TITER_SERUM_STATUS_ORDER))
    if field == "priority":
        value = str(item.get("priority") or "").strip() or TITER_ORDER_PRIORITY_DEFAULT
        return TITER_PRIORITY_RANK.get(value, len(TITER_ORDER_PRIORITIES))
    return str(item.get(field) or "")


def _sort_titer_order_items(items: list[dict], data: dict[str, Any]) -> list[dict]:
    field = str(data.get("sort_field") or "")
    if field not in TITER_ORDER_ITEM_SORT_FIELDS:
        return items
    reverse = str(data.get("sort_order") or "").lower() == "desc"
    items.sort(key=lambda item: int(item.get("id") or 0), reverse=True)
    items.sort(key=lambda item: _item_sort_key(item, field), reverse=reverse)
    return items


def _empty_titer_owners_condition():
    return or_(
        SerumTiterOrder.titer_owners.is_(None),
        cast(SerumTiterOrder.titer_owners, String).in_(("[]", "null")),
    )


def _empty_test_dates_condition():
    return func.json_length(func.coalesce(SerumTiterOrder.test_dates, text("JSON_ARRAY()"))) == 0


def _serum_status_pre_tested_condition():
    return or_(
        SerumTiterOrder.serum_status.is_(None),
        SerumTiterOrder.serum_status == "",
        SerumTiterOrder.serum_status.notin_(TITER_SERUM_STATUS_POST_TEST),
    )


def _apply_titer_order_list_filters(stmt, data: dict[str, Any]):
    project_code = str(data.get("project_code") or "").strip()
    project_codes = data.get("project_codes")
    target_name = str(data.get("target_name") or "").strip()
    owner = str(data.get("titer_owner") or "").strip()
    immune_owner = str(data.get("immune_owner") or "").strip()
    immune_status = str(data.get("immune_status") or "").strip()
    serum_status = str(data.get("serum_status") or "").strip()
    if project_codes:
        codes = [str(code).strip() for code in project_codes if str(code or "").strip()]
        if codes:
            stmt = stmt.where(SerumImmProject.project_code.in_(codes))
    elif project_code:
        stmt = stmt.where(SerumImmProject.project_code.like(f"%{project_code}%"))
    if target_name:
        stmt = stmt.where(SerumImmProject.target_name == target_name)
    if data.get("titer_owner_unassigned"):
        stmt = stmt.where(_empty_titer_owners_condition())
    elif owner:
        stmt = stmt.where(cast(SerumTiterOrder.titer_owners, String).like(f"%{owner}%"))
    if immune_owner:
        stmt = stmt.where(SerumImmProject.owner == immune_owner)
    if immune_status:
        stmt = stmt.where(SerumImmProject.project_status == immune_status)
    if serum_status:
        stmt = stmt.where(SerumTiterOrder.serum_status == serum_status)
    priority = str(data.get("priority") or "").strip()
    if priority:
        if priority == TITER_ORDER_PRIORITY_DEFAULT:
            stmt = stmt.where(
                or_(
                    SerumTiterOrder.priority == priority,
                    SerumTiterOrder.priority.is_(None),
                    SerumTiterOrder.priority == "",
                )
            )
        else:
            stmt = stmt.where(SerumTiterOrder.priority == priority)
    order_status = str(data.get("order_status") or "").strip()
    if order_status:
        latest_flow = _latest_titer_flow_status_subquery()
        stmt = stmt.where(
            SerumTiterOrder.titer_order_id.in_(
                select(latest_flow.c.source_id).where(latest_flow.c.status == order_status)
            )
        )
    assay_method = str(data.get("assay_method") or "").strip()
    if assay_method:
        stmt = _apply_assay_method_filter(stmt, assay_method)
    stmt = _apply_numeric_column_filters(stmt, data)
    if data.get("summary_empty"):
        stmt = stmt.where(or_(SerumTiterOrder.summary.is_(None), SerumTiterOrder.summary == ""))
    if data.get("summary_filled"):
        stmt = stmt.where(SerumTiterOrder.summary.is_not(None), SerumTiterOrder.summary != "")
    if data.get("test_dates_empty"):
        stmt = stmt.where(_empty_test_dates_condition())
    elif data.get("tested_unsubmitted"):
        stmt = stmt.where(~_empty_test_dates_condition(), _serum_status_pre_tested_condition())
    else:
        test_start, test_end = _filter_date_bounds(data, "test_dates_start", "test_dates_end")
        if test_start or test_end:
            stmt = stmt.where(
                _test_dates_in_range_clause(
                    test_start or "0000-01-01",
                    test_end or "9999-12-31",
                )
            )
    return stmt


def _titer_order_list_items(db: Session, data: dict[str, Any]) -> list[dict]:
    stmt = _apply_titer_order_list_filters(_titer_order_query(), data)
    blood_start, blood_end = _filter_date_bounds(data, "blood_collection_start", "blood_collection_end")
    rows = db.execute(stmt.order_by(*_titer_order_sql_order_by(data))).all()
    items = _enrich_order_rows(db, rows)
    if blood_start or blood_end:
        items = [
            item
            for item in items
            if _blood_date_in_range(item.get("blood_collection_date") or "", blood_start, blood_end)
        ]
    return _sort_titer_order_items(items, data)


def get_titer_order_list(db: Session, data: dict[str, Any]) -> dict:
    page = int(data.get("page", 1) or 1)
    limit = int(data.get("limit", 20) or 20)
    stmt = _apply_titer_order_list_filters(_titer_order_query(), data)

    blood_start, blood_end = _filter_date_bounds(data, "blood_collection_start", "blood_collection_end")

    if _titer_order_needs_full_scan(data, blood_start, blood_end):
        items = _titer_order_list_items(db, data)
        total = len(items)
        start = max(page - 1, 0) * limit
        return {"items": items[start : start + limit], "total": total}

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.execute(
        stmt.order_by(*_titer_order_sql_order_by(data)).offset((page - 1) * limit).limit(limit)
    ).all()
    return {"items": _enrich_order_rows(db, rows), "total": total}


def create_titer_order_for_blood_collection_if_absent(
    db: Session,
    project: SerumImmProject,
    blood_collection_date: str,
) -> bool:
    """
    仅为当前这次采血建一张空单：写入 blood_collection_seq，批次字段保持 NULL。
    已有相同 seq 则跳过；不补齐更早次数。不 commit。
    """
    experiment_id = str(project.experiment_id or "").strip()
    blood_date = _normalize_blood_collection_date(blood_collection_date)
    if not experiment_id or not blood_date:
        return False

    steps = list(db.scalars(select(SerumImmStep).where(SerumImmStep.experiment_id == experiment_id)).all())
    blood_dates = _all_blood_collection_dates(steps)
    seq = _blood_collection_seq_for_date(blood_dates, blood_date)
    if not seq:
        return False

    exists = db.scalar(
        select(SerumTiterOrder.id).where(
            SerumTiterOrder.experiment_id == experiment_id,
            SerumTiterOrder.blood_collection_seq == seq,
        ).limit(1)
    )
    if exists:
        return False

    db.add(
        SerumTiterOrder(
            experiment_id=experiment_id,
            titer_order_id=generate_titer_order_id(db, project.project_code, experiment_id),
            titer_owners=[],
            test_dates=[],
            serum_status=(
                PENDING_BLOOD_COLLECTION_STATUS
                if seq < 2
                else PENDING_BLOOD_COLLECTION_BOOST_STATUS
            ),
            priority=TITER_ORDER_PRIORITY_DEFAULT,
            blood_collection_seq=seq,
            cage_position=None,
            blood_collection_date=None,
            mouse_count=None,
            assay_method=None,
            facs_plate_count=None,
            elisa_plate_count=None,
        )
    )
    return True


def _sync_blood_collection_seq(db: Session, order: SerumTiterOrder) -> None:
    """按工单采血日回填第 N 次；无日期或方案对不上则保持现有 seq。"""
    blood_date = _normalize_blood_collection_date(order.blood_collection_date)
    if not blood_date or not order.experiment_id:
        return
    steps = list(
        db.scalars(select(SerumImmStep).where(SerumImmStep.experiment_id == order.experiment_id)).all()
    )
    seq = _blood_collection_seq_for_date(_all_blood_collection_dates(steps), blood_date)
    if seq:
        order.blood_collection_seq = seq


def save_titer_order(db: Session, data: dict[str, Any]) -> dict:
    order_id = data.get("id")
    project: SerumImmProject | None = None
    is_create = not order_id
    if order_id:
        order = db.get(SerumTiterOrder, int(order_id))
        if not order:
            raise ValueError("效价工单不存在")
        project = db.scalar(
            select(SerumImmProject).where(SerumImmProject.experiment_id == order.experiment_id)
        )
    else:
        experiment_id = str(data.get("experiment_id") or "").strip()
        if not experiment_id:
            raise ValueError("请选择免疫实验")
        project, immune_batch, steps = _immune_batch_for_experiment(db, experiment_id)
        # 手动创建：预填方法/笼位等；采血日默认 NULL，由 seq 跟随方案
        immune_batch = dict(immune_batch)
        immune_batch["blood_collection_date"] = None
        order = SerumTiterOrder(
            experiment_id=experiment_id,
            titer_order_id=generate_titer_order_id(db, project.project_code, experiment_id),
            titer_owners=[],
            test_dates=[],
            priority=TITER_ORDER_PRIORITY_DEFAULT,
            blood_collection_seq=_default_blood_collection_seq(db, experiment_id, steps),
        )
        _apply_batch_fields_to_order(order, immune_batch)
        db.add(order)

    if "blood_collection_seq" in data:
        order.blood_collection_seq = _parse_blood_collection_seq(data.get("blood_collection_seq"))

    overrides = _normalize_batch_fields_payload(data)
    if overrides:
        if is_create:
            _apply_batch_overrides(order, overrides)
        else:
            contexts = _build_derive_contexts(db, [order.experiment_id])
            baseline = _scheme_follow_baseline(
                order, project, contexts.get(order.experiment_id)
            ) if project else {}
            _apply_batch_overrides_on_edit(order, overrides, baseline)

    if "titer_owners" in data:
        order.titer_owners = _normalize_owner_names(data.get("titer_owners"))
    if "test_dates" in data:
        order.test_dates = _normalize_test_dates(data.get("test_dates"))
    if "serum_status" in data:
        order.serum_status = str(data.get("serum_status") or "").strip() or None
    if "summary" in data:
        summary = str(data.get("summary") or "").strip()
        if len(summary) > 500:
            raise ValueError("效价小结不能超过 500 字")
        order.summary = summary or None
    if "remark" in data:
        order.remark = str(data.get("remark") or "").strip() or None
    if "priority" in data:
        order.priority = _normalize_titer_order_priority(data.get("priority"))

    _sync_blood_collection_seq(db, order)

    db.commit()
    db.refresh(order)
    if project is None:
        return order.to_dict()
    contexts = _build_derive_contexts(db, [order.experiment_id])
    item = _order_to_list_item(order, project, contexts.get(order.experiment_id))
    return _apply_flow_status_to_items(db, [item])[0]


def delete_titer_order(db: Session, order_id: int) -> None:
    order = db.get(SerumTiterOrder, int(order_id))
    if not order:
        raise ValueError("效价工单不存在")
    db.delete(order)
    db.commit()


def _current_week_range() -> tuple[datetime, datetime]:
    now = datetime.now()
    start = datetime.combine((now - timedelta(days=now.weekday())).date(), time.min)
    end = datetime.combine((start + timedelta(days=6)).date(), time.max)
    return start, end


def _collect_titer_owner_names(db: Session) -> list[str]:
    rows = db.scalars(
        select(SerumTiterOrder.titer_owners).where(SerumTiterOrder.titer_owners.is_not(None))
    ).all()
    seen: set[str] = set()
    for owners in rows:
        if not isinstance(owners, list):
            continue
        for owner in owners:
            name = str(owner or "").strip()
            if name:
                seen.add(name)
    return sorted(seen)


def _collect_titer_target_names(db: Session) -> list[str]:
    rows = db.execute(
        select(SerumImmProject.target_name)
        .join(SerumTiterOrder, SerumImmProject.experiment_id == SerumTiterOrder.experiment_id)
        .where(
            or_(SerumImmProject.project_status.is_(None), SerumImmProject.project_status != "deleted"),
            SerumImmProject.target_name.is_not(None),
            SerumImmProject.target_name != "",
        )
        .distinct()
        .order_by(SerumImmProject.target_name)
    ).all()
    return [row[0] for row in rows if row[0]]


def _collect_titer_assay_method_names(db: Session) -> list[str]:
    method_expr = func.coalesce(SerumTiterOrder.assay_method, SerumImmProject.assay_method)
    rows = db.execute(
        select(method_expr)
        .join(SerumImmProject, SerumImmProject.experiment_id == SerumTiterOrder.experiment_id)
        .where(
            or_(SerumImmProject.project_status.is_(None), SerumImmProject.project_status != "deleted"),
            method_expr.is_not(None),
            method_expr != "",
        )
        .distinct()
        .order_by(method_expr)
    ).all()
    return [row[0] for row in rows if row[0]]


def _collect_titer_immune_owner_names(db: Session) -> list[str]:
    rows = db.execute(
        select(SerumImmProject.owner)
        .join(SerumTiterOrder, SerumImmProject.experiment_id == SerumTiterOrder.experiment_id)
        .where(
            or_(SerumImmProject.project_status.is_(None), SerumImmProject.project_status != "deleted"),
            SerumImmProject.owner.is_not(None),
            SerumImmProject.owner != "",
        )
        .distinct()
        .order_by(SerumImmProject.owner)
    ).all()
    return [row[0] for row in rows if row[0]]


def _collect_titer_immune_status_names(db: Session) -> list[str]:
    rows = db.execute(
        select(SerumImmProject.project_status)
        .join(SerumTiterOrder, SerumImmProject.experiment_id == SerumTiterOrder.experiment_id)
        .where(
            or_(SerumImmProject.project_status.is_(None), SerumImmProject.project_status != "deleted"),
            SerumImmProject.project_status.is_not(None),
            SerumImmProject.project_status != "",
        )
        .distinct()
        .order_by(SerumImmProject.project_status)
    ).all()
    return [row[0] for row in rows if row[0]]


def _collect_titer_serum_status_names(db: Session) -> list[str]:
    rows = db.execute(
        select(SerumTiterOrder.serum_status)
        .join(SerumImmProject, SerumImmProject.experiment_id == SerumTiterOrder.experiment_id)
        .where(
            or_(SerumImmProject.project_status.is_(None), SerumImmProject.project_status != "deleted"),
            SerumTiterOrder.serum_status.is_not(None),
            SerumTiterOrder.serum_status != "",
        )
        .distinct()
        .order_by(SerumTiterOrder.serum_status)
    ).all()
    return [row[0] for row in rows if row[0]]


def get_titer_order_page_meta(db: Session) -> dict:
    return {
        "owners": _collect_titer_owner_names(db),
        "targets": _collect_titer_target_names(db),
        "assay_methods": _collect_titer_assay_method_names(db),
        "immune_owners": _collect_titer_immune_owner_names(db),
        "immune_statuses": _collect_titer_immune_status_names(db),
        "serum_statuses": _collect_titer_serum_status_names(db),
        "stats": get_titer_order_stats(db),
    }


def _pending_detection_filters(deleted_filter):
    return (
        deleted_filter,
        SerumTiterOrder.serum_status == "已采血",
        _empty_test_dates_condition(),
    )


def _sum_pending_test_plate_counts(db: Session) -> tuple[int, int]:
    join_on = SerumImmProject.experiment_id == SerumTiterOrder.experiment_id
    deleted_filter = or_(SerumImmProject.project_status.is_(None), SerumImmProject.project_status != "deleted")
    base = (
        select(
            func.coalesce(
                func.sum(func.coalesce(SerumTiterOrder.facs_plate_count, SerumImmProject.facs_plate_count)),
                0,
            ),
            func.coalesce(
                func.sum(func.coalesce(SerumTiterOrder.elisa_plate_count, SerumImmProject.elisa_plate_count)),
                0,
            ),
        )
        .select_from(SerumTiterOrder)
        .join(SerumImmProject, join_on)
        .where(*_pending_detection_filters(deleted_filter))
    )
    facs, elisa = db.execute(base).one()
    return int(facs or 0), int(elisa or 0)


def get_titer_order_stats(db: Session) -> dict[str, int]:
    join_on = SerumImmProject.experiment_id == SerumTiterOrder.experiment_id
    deleted_filter = or_(SerumImmProject.project_status.is_(None), SerumImmProject.project_status != "deleted")

    unassigned = db.scalar(
        select(func.count(SerumTiterOrder.id))
        .select_from(SerumTiterOrder)
        .join(SerumImmProject, join_on)
        .where(deleted_filter, _empty_titer_owners_condition())
    ) or 0
    pending = db.scalar(
        select(func.count(SerumTiterOrder.id))
        .select_from(SerumTiterOrder)
        .join(SerumImmProject, join_on)
        .where(*_pending_detection_filters(deleted_filter))
    ) or 0
    to_report = db.scalar(
        select(func.count(SerumTiterOrder.id))
        .select_from(SerumTiterOrder)
        .join(SerumImmProject, join_on)
        .where(
            deleted_filter,
            SerumTiterOrder.serum_status == "已检测",
            or_(SerumTiterOrder.summary.is_(None), SerumTiterOrder.summary == ""),
        )
    ) or 0

    week_start, week_end = _current_week_range()
    this_week = db.scalar(
        select(func.count(SerumTiterOrder.id))
        .select_from(SerumTiterOrder)
        .join(SerumImmProject, join_on)
        .where(
            deleted_filter,
            _test_dates_in_range_clause(
                week_start.date().isoformat(),
                week_end.date().isoformat(),
            ),
        )
    ) or 0

    pending_facs_plates, pending_elisa_plates = _sum_pending_test_plate_counts(db)

    return {
        "unassigned": unassigned,
        "pending": pending,
        "pendingFacsPlates": pending_facs_plates,
        "pendingElisaPlates": pending_elisa_plates,
        "thisWeek": this_week,
        "toReport": to_report,
    }


_COMPLETED_SERUM_STATUSES = frozenset({"已检测", "已交接", "已销毁"})


def _month_bounds(month_key: str) -> tuple[str, str]:
    year, month = int(month_key[:4]), int(month_key[5:7])
    start = datetime(year, month, 1).date()
    if month == 12:
        end = datetime(year, 12, 31).date()
    else:
        end = datetime(year, month + 1, 1).date() - timedelta(days=1)
    return start.isoformat(), end.isoformat()


def _test_dates_overlap_range(test_dates: Any, range_start: str, range_end: str) -> bool:
    for item in _normalize_test_dates(test_dates):
        if range_start <= item <= range_end:
            return True
    return False


def get_titer_owner_workload_stats(
    db: Session,
    month_start: str | None = None,
    month_end: str | None = None,
) -> dict[str, Any]:
    period_start = period_end = None
    start_key = str(month_start or "").strip()
    if len(start_key) == 7 and start_key[4] == "-":
        period_start, _ = _month_bounds(start_key)
        end_key = str(month_end or start_key).strip()
        if len(end_key) != 7:
            end_key = start_key
        _, period_end = _month_bounds(end_key)
        if period_start > period_end:
            period_start, period_end = period_end, period_start

    def _slot() -> dict[str, dict[str, float]]:
        zero = {"orders": 0.0, "facs": 0.0, "elisa": 0.0}
        return {"total": zero.copy(), "completed": zero.copy(), "remaining": zero.copy(), "period": zero.copy()}

    def _add(target: dict[str, float], unit: dict[str, float]) -> None:
        for key in ("orders", "facs", "elisa"):
            target[key] = round(target[key] + unit[key], 1)

    buckets: dict[str, dict[str, dict[str, float]]] = {}
    summary = _slot()
    for order, project in db.execute(_titer_order_query()).all():
        owners = _normalize_owner_names(order.titer_owners)
        if not owners:
            continue
        count = len(owners)
        facs_plates = _coalesce_follow_int(order.facs_plate_count, project.facs_plate_count) or 0
        elisa_plates = _coalesce_follow_int(order.elisa_plate_count, project.elisa_plate_count) or 0
        unit = {
            "orders": 1,
            "facs": round(facs_plates / count, 1),
            "elisa": round(elisa_plates / count, 1),
        }
        raw_unit = {
            "orders": 1,
            "facs": float(facs_plates),
            "elisa": float(elisa_plates),
        }
        done = str(order.serum_status or "").strip() in _COMPLETED_SERUM_STATUSES
        in_period = bool(
            period_start
            and period_end
            and _test_dates_overlap_range(order.test_dates, period_start, period_end)
        )

        for owner in owners:
            bucket = buckets.setdefault(owner, _slot())
            _add(bucket["total"], unit)
            _add(bucket["completed" if done else "remaining"], unit)
            if in_period:
                _add(bucket["period"], unit)

        _add(summary["total"], raw_unit)
        _add(summary["completed" if done else "remaining"], raw_unit)
        if in_period:
            _add(summary["period"], raw_unit)

    items = [{"owner": owner, **metrics} for owner, metrics in buckets.items()]
    return {"items": items, "summary": summary}


def get_project_options(db: Session, keyword: str = "", limit: int = 20) -> list[dict]:
    keyword = (keyword or "").strip()
    limit = min(max(int(limit or 20), 1), 50)
    stmt = (
        select(SerumImmProject)
        .where(
            SerumImmProject.experiment_id.is_not(None),
            SerumImmProject.experiment_id != "",
            or_(SerumImmProject.project_status.is_(None), SerumImmProject.project_status != "deleted"),
        )
        .order_by(SerumImmProject.id.desc())
    )
    if keyword:
        pattern = f"%{keyword}%"
        stmt = stmt.where(
            or_(
                SerumImmProject.project_code.like(pattern),
                SerumImmProject.experiment_id.like(pattern),
                SerumImmProject.target_name.like(pattern),
            )
        )
    projects = db.scalars(stmt.limit(limit)).all()
    return [
        {
            "id": project.id,
            "experiment_id": project.experiment_id,
            "project_code": project.project_code,
            "project_name": project.project_name,
            "target_name": project.target_name,
            "owner": project.owner,
            "project_status": project.project_status,
        }
        for project in projects
    ]


def _replace_children(db: Session, model_class, experiment_id: str, items: list[dict], id_field: str = "id") -> list[dict]:
    submitted_ids = set()
    created_objs = []
    valid_fields = set(model_class.__table__.columns.keys())
    for item in items:
        item_id = item.get(id_field)
        if item_id:
            obj = db.get(model_class, int(item_id))
            if obj:
                for key, value in item.items():
                    if key != id_field and hasattr(obj, key):
                        setattr(obj, key, value)
                obj.experiment_id = experiment_id
                submitted_ids.add(int(item_id))
                continue
        data = {key: value for key, value in item.items() if key in valid_fields and key != id_field}
        data["experiment_id"] = experiment_id
        obj = model_class(**data)
        db.add(obj)
        created_objs.append(obj)

    db.flush()
    keep_ids = submitted_ids | {getattr(obj, id_field) for obj in created_objs if getattr(obj, id_field, None)}
    existing = db.scalars(select(model_class).where(model_class.experiment_id == experiment_id)).all()
    for obj in existing:
        if getattr(obj, id_field) not in keep_ids:
            db.delete(obj)
    db.commit()
    return [item.to_dict() for item in db.scalars(select(model_class).where(model_class.experiment_id == experiment_id)).all()]


def save_targets(db: Session, experiment_id: str, targets: list[dict]) -> list[dict]:
    return _replace_children(db, SerumTiterTarget, experiment_id, targets)


def save_pcs(db: Session, experiment_id: str, pcs: list[dict]) -> list[dict]:
    return _replace_children(db, SerumTiterPc, experiment_id, pcs)


def get_facs_plates(db: Session, experiment_id: str) -> list[dict]:
    return [item.to_dict() for item in db.scalars(select(SerumFacsPlate).where(SerumFacsPlate.experiment_id == experiment_id)).all()]


PLATE_FIELDS = [
    "qr_code",
    "image_file_id",
    "excel_file_id",
    "immune_stage",
    "x_axis",
    "y_axis",
    "cell_target_id",
    "pc_upper_id",
    "pc_lower_id",
    "upper_group",
    "lower_group",
    "upper_mouse_list",
    "lower_mouse_list",
    "upper_slot_groups",
    "lower_slot_groups",
    "positive_well_list",
    "instrument_type",
]


def save_facs_plate(db: Session, plate_data: dict[str, Any]) -> dict:
    experiment_id = plate_data.get("experiment_id")
    if not experiment_id:
        raise ValueError("缺少实验 ID")

    plate_id = plate_data.get("id")
    if plate_id:
        plate = db.get(SerumFacsPlate, int(plate_id))
        if not plate:
            raise ValueError("板数据不存在")
        if plate.experiment_id != experiment_id:
            raise ValueError("板数据不属于当前实验")
    else:
        plate = SerumFacsPlate(experiment_id=experiment_id)
        db.add(plate)

    for field in PLATE_FIELDS:
        setattr(plate, field, plate_data.get(field))
    db.commit()
    db.refresh(plate)
    return plate.to_dict()


def delete_facs_plate(db: Session, plate_id: int) -> None:
    plate = db.get(SerumFacsPlate, plate_id)
    if not plate:
        raise ValueError("板数据不存在")
    db.delete(plate)
    db.commit()


def get_elisa_plates(db: Session, experiment_id: str) -> list[dict]:
    return [item.to_dict() for item in db.scalars(select(SerumElisaPlate).where(SerumElisaPlate.experiment_id == experiment_id)).all()]


ELISA_PLATE_FIELDS = [
    "qr_code",
    "excel_file_id",
    "immune_stage",
    "protein_target_id",
    "pc_id",
    "mouse_group",
    "antigen_type",
    "slot_groups",
    "upper_slot_list",
    "lower_slot_list",
    "positive_well_list",
    "absorbance_1",
]


def save_elisa_plate(db: Session, plate_data: dict[str, Any]) -> dict:
    experiment_id = plate_data.get("experiment_id")
    if not experiment_id:
        raise ValueError("缺少实验 ID")

    plate_id = plate_data.get("id")
    if plate_id:
        plate = db.get(SerumElisaPlate, int(plate_id))
        if not plate:
            raise ValueError("板数据不存在")
        if plate.experiment_id != experiment_id:
            raise ValueError("板数据不属于当前实验")
    else:
        plate = SerumElisaPlate(experiment_id=experiment_id, immune_stage="")
        db.add(plate)

    for field in ELISA_PLATE_FIELDS:
        setattr(plate, field, plate_data.get(field))
    if not plate.immune_stage:
        plate.immune_stage = ""
    db.commit()
    db.refresh(plate)
    return plate.to_dict()


def delete_elisa_plate(db: Session, plate_id: int) -> None:
    plate = db.get(SerumElisaPlate, plate_id)
    if not plate:
        raise ValueError("板数据不存在")
    db.delete(plate)
    db.commit()


def export_titer_order_list_workbook(db: Session, data: dict[str, Any]) -> tuple[BytesIO, str]:
    from utils.excel import build_list_workbook, cell_text

    items = _titer_order_list_items(db, data or {})
    headers = [
        "项目编号",
        "实验ID",
        "效价工单号",
        "靶点",
        "笼位",
        "采血日期",
        "采血次数",
        "只数",
        "检测方法",
        "FACS",
        "ELISA",
        "免疫负责人",
        "效价负责人",
        "检测日期",
        "血清状态",
        "优先级",
        "备注",
        "效价小结",
        "工单状态",
        "免疫状态",
    ]
    rows = []
    for item in items:
        rows.append([
            item.get("project_code"),
            item.get("experiment_id"),
            item.get("titer_order_id"),
            item.get("target_name"),
            item.get("cage_position"),
            item.get("blood_collection_date"),
            item.get("blood_collection_seq"),
            item.get("mouse_count"),
            item.get("assay_method"),
            item.get("facs_plate_count"),
            item.get("elisa_plate_count"),
            item.get("immune_owner"),
            cell_text(item.get("titer_owners")),
            item.get("test_dates_display") or cell_text(item.get("test_dates")),
            item.get("serum_status"),
            item.get("priority") or TITER_ORDER_PRIORITY_DEFAULT,
            item.get("remark"),
            item.get("summary"),
            item.get("order_status_label") or item.get("order_status"),
            item.get("immune_status"),
        ])
    return build_list_workbook(
        sheet_title="效价实验列表",
        filename_prefix="效价实验列表",
        headers=headers,
        rows=rows,
    )
