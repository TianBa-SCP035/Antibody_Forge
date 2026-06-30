from datetime import datetime, time, timedelta
from io import BytesIO
from pathlib import Path
import json
import random
from typing import Any

from fastapi import UploadFile
from PIL import Image
from sqlalchemy import JSON, String, and_, bindparam, cast, func, or_, select, text
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

_ASSAY_METHOD_COMBO_FILTERS: dict[str, tuple[tuple[str, ...], tuple[str, ...]]] = {
    ASSAY_FILTER_FACS: (("FACS",), ("ELISA",)),
    ASSAY_FILTER_ELISA: (("ELISA",), ("FACS",)),
    ASSAY_FILTER_FACS_ELISA: (("FACS", "ELISA"), ()),
}


def _has_positive_plate_count(column):
    return and_(column.is_not(None), column > 0)


def _missing_positive_plate_count(column):
    return or_(column.is_(None), column <= 0)


def _assay_column_filter(*, include: tuple[str, ...], exclude: tuple[str, ...]):
    parts = []
    for method in include:
        column = SerumTiterOrder.facs_plate_count if method == "FACS" else SerumTiterOrder.elisa_plate_count
        parts.append(_has_positive_plate_count(column))
    for method in exclude:
        column = SerumTiterOrder.facs_plate_count if method == "FACS" else SerumTiterOrder.elisa_plate_count
        parts.append(_missing_positive_plate_count(column))
    return and_(*parts)


def _apply_assay_method_filter(stmt, assay_method: str):
    """检测方法筛选：FACS/ELISA/组合走板数列；其余为展示文案精确匹配。"""
    combo = _ASSAY_METHOD_COMBO_FILTERS.get(assay_method)
    if combo:
        include, exclude = combo
        return stmt.where(_assay_column_filter(include=include, exclude=exclude))
    target = str(assay_method or "").strip()
    if not target:
        return stmt
    return stmt.where(SerumTiterOrder.assay_method == target)


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


def _mode_cage_position(mice: list[SerumImmMouse]) -> str:
    counts: dict[str, int] = {}
    for mouse in mice:
        value = str(mouse.cage_position or "").strip()
        if not value:
            continue
        counts[value] = counts.get(value, 0) + 1
    if not counts:
        return ""
    return max(counts, key=lambda cage: (counts[cage], cage))


def _blood_collection_date(steps: list[SerumImmStep]) -> str | None:
    dates = [
        str(step.date_actual).strip()
        for step in steps
        if str(step.stage_name or "").strip() == "采血" and str(step.date_actual or "").strip()
    ]
    return min(dates) if dates else None


def _immune_batch_fields(
    project: SerumImmProject,
    mice: list[SerumImmMouse],
    steps: list[SerumImmStep],
) -> dict[str, Any]:
    return {
        "cage_position": _mode_cage_position(mice) or None,
        "blood_collection_date": _blood_collection_date(steps),
        "mouse_count": _sum_mouse_count(mice),
        "assay_method": project.assay_method,
        "facs_plate_count": project.facs_plate_count,
        "elisa_plate_count": project.elisa_plate_count,
    }


def _immune_batch_for_experiment(db: Session, experiment_id: str) -> tuple[SerumImmProject, dict[str, Any]]:
    experiment_id = str(experiment_id or "").strip()
    if not experiment_id:
        raise ValueError("请选择免疫实验")
    project = db.scalar(select(SerumImmProject).where(SerumImmProject.experiment_id == experiment_id))
    if not project:
        raise ValueError("免疫实验不存在")
    mice = list(db.scalars(select(SerumImmMouse).where(SerumImmMouse.experiment_id == experiment_id)).all())
    steps = list(db.scalars(select(SerumImmStep).where(SerumImmStep.experiment_id == experiment_id)).all())
    return project, _immune_batch_fields(project, mice, steps)


def _apply_batch_fields_to_order(order: SerumTiterOrder, batch: dict[str, Any]) -> None:
    order.cage_position = batch.get("cage_position")
    order.blood_collection_date = batch.get("blood_collection_date")
    order.mouse_count = batch.get("mouse_count")
    order.assay_method = batch.get("assay_method")
    order.facs_plate_count = batch.get("facs_plate_count")
    order.elisa_plate_count = batch.get("elisa_plate_count")


BATCH_FIELD_KEYS = (
    "cage_position",
    "blood_collection_date",
    "mouse_count",
    "assay_method",
    "facs_plate_count",
    "elisa_plate_count",
)


def _batch_fields_to_preview(batch: dict[str, Any]) -> dict[str, Any]:
    return {
        "cage_position": batch.get("cage_position") or "",
        "blood_collection_date": batch.get("blood_collection_date") or "",
        "mouse_count": batch.get("mouse_count"),
        "assay_method": batch.get("assay_method") or "",
        "facs_plate_count": batch.get("facs_plate_count"),
        "elisa_plate_count": batch.get("elisa_plate_count"),
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
    for key in BATCH_FIELD_KEYS:
        if key in overrides:
            setattr(order, key, overrides[key])


def get_titer_order_batch_preview(db: Session, experiment_id: str) -> dict[str, Any]:
    project, batch = _immune_batch_for_experiment(db, experiment_id)
    return {
        "experiment_id": project.experiment_id,
        "project_code": project.project_code or "",
        "target_name": project.target_name or "",
        **_batch_fields_to_preview(batch),
    }


def _order_to_list_item(order: SerumTiterOrder, project: SerumImmProject) -> dict:
    item = order.to_dict()
    item.update(
        {
            "project_id": project.id,
            "project_code": project.project_code or "",
            "target_name": project.target_name or "",
            "immune_owner": project.owner or "",
            "immune_status": project.project_status or "",
            "order_status": "",
        }
    )
    return item


def _titer_order_query():
    return (
        select(SerumTiterOrder, SerumImmProject)
        .join(SerumImmProject, SerumImmProject.experiment_id == SerumTiterOrder.experiment_id)
        .where(or_(SerumImmProject.project_status.is_(None), SerumImmProject.project_status != "deleted"))
    )


def _empty_titer_owners_condition():
    return or_(
        SerumTiterOrder.titer_owners.is_(None),
        cast(SerumTiterOrder.titer_owners, String).in_(("[]", "null")),
    )


def get_titer_order_list(db: Session, data: dict[str, Any]) -> dict:
    page = int(data.get("page", 1) or 1)
    limit = int(data.get("limit", 20) or 20)
    stmt = _titer_order_query()

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
    assay_method = str(data.get("assay_method") or "").strip()
    if assay_method:
        stmt = _apply_assay_method_filter(stmt, assay_method)
    if data.get("summary_empty"):
        stmt = stmt.where(or_(SerumTiterOrder.summary.is_(None), SerumTiterOrder.summary == ""))
    if data.get("summary_filled"):
        stmt = stmt.where(SerumTiterOrder.summary.is_not(None), SerumTiterOrder.summary != "")

    blood_start, blood_end = _filter_date_bounds(data, "blood_collection_start", "blood_collection_end")
    if blood_start:
        stmt = stmt.where(SerumTiterOrder.blood_collection_date >= blood_start)
    if blood_end:
        stmt = stmt.where(SerumTiterOrder.blood_collection_date <= blood_end)

    test_start, test_end = _filter_date_bounds(data, "test_dates_start", "test_dates_end")
    if test_start or test_end:
        stmt = stmt.where(
            _test_dates_in_range_clause(
                test_start or "0000-01-01",
                test_end or "9999-12-31",
            )
        )

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.execute(
        stmt.order_by(SerumTiterOrder.id.desc()).offset((page - 1) * limit).limit(limit)
    ).all()

    return {
        "items": [
            _order_to_list_item(order, project)
            for order, project in rows
        ],
        "total": total,
    }


def create_titer_order_from_immune_if_absent(
    db: Session,
    experiment_id: str,
    *,
    serum_status: str | None = None,
) -> bool:
    """从免疫实验复制批次字段新建工单；该 experiment_id 已有任意工单则跳过。不 commit。"""
    experiment_id = str(experiment_id or "").strip()
    if not experiment_id:
        return False
    exists = db.scalar(
        select(SerumTiterOrder.id).where(SerumTiterOrder.experiment_id == experiment_id).limit(1)
    )
    if exists:
        return False
    project, immune_batch = _immune_batch_for_experiment(db, experiment_id)
    order = SerumTiterOrder(
        experiment_id=experiment_id,
        titer_order_id=generate_titer_order_id(db, project.project_code, experiment_id),
        titer_owners=[],
        test_dates=[],
        serum_status=str(serum_status).strip() if serum_status else None,
    )
    _apply_batch_fields_to_order(order, immune_batch)
    db.add(order)
    return True


def save_titer_order(db: Session, data: dict[str, Any]) -> dict:
    order_id = data.get("id")
    if order_id:
        order = db.get(SerumTiterOrder, int(order_id))
        if not order:
            raise ValueError("效价工单不存在")
    else:
        experiment_id = str(data.get("experiment_id") or "").strip()
        if not experiment_id:
            raise ValueError("请选择免疫实验")
        project, immune_batch = _immune_batch_for_experiment(db, experiment_id)
        order = SerumTiterOrder(
            experiment_id=experiment_id,
            titer_order_id=generate_titer_order_id(db, project.project_code, experiment_id),
            titer_owners=[],
            test_dates=[],
        )
        _apply_batch_fields_to_order(order, immune_batch)
        db.add(order)

    overrides = _normalize_batch_fields_payload(data)
    if overrides:
        _apply_batch_overrides(order, overrides)

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

    db.commit()
    db.refresh(order)
    return order.to_dict()


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
    rows = db.execute(
        select(SerumTiterOrder.assay_method)
        .join(SerumImmProject, SerumImmProject.experiment_id == SerumTiterOrder.experiment_id)
        .where(
            or_(SerumImmProject.project_status.is_(None), SerumImmProject.project_status != "deleted"),
            SerumTiterOrder.assay_method.is_not(None),
            SerumTiterOrder.assay_method != "",
        )
        .distinct()
        .order_by(SerumTiterOrder.assay_method)
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


def get_titer_order_page_meta(db: Session) -> dict:
    return {
        "owners": _collect_titer_owner_names(db),
        "targets": _collect_titer_target_names(db),
        "assay_methods": _collect_titer_assay_method_names(db),
        "immune_owners": _collect_titer_immune_owner_names(db),
        "immune_statuses": _collect_titer_immune_status_names(db),
        "stats": get_titer_order_stats(db),
    }


def _sum_pending_test_plate_counts(db: Session) -> tuple[int, int]:
    join_on = SerumImmProject.experiment_id == SerumTiterOrder.experiment_id
    deleted_filter = or_(SerumImmProject.project_status.is_(None), SerumImmProject.project_status != "deleted")
    base = (
        select(
            func.coalesce(func.sum(SerumTiterOrder.facs_plate_count), 0),
            func.coalesce(func.sum(SerumTiterOrder.elisa_plate_count), 0),
        )
        .select_from(SerumTiterOrder)
        .join(SerumImmProject, join_on)
        .where(deleted_filter, SerumTiterOrder.serum_status == "已采血")
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
        .where(deleted_filter, SerumTiterOrder.serum_status == "已采血")
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


_COMPLETED_SERUM_STATUSES = frozenset({"已检测", "已交接"})


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
    for order, _project in db.execute(_titer_order_query()).all():
        owners = _normalize_owner_names(order.titer_owners)
        if not owners:
            continue
        count = len(owners)
        facs_plates = order.facs_plate_count or 0
        elisa_plates = order.elisa_plate_count or 0
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
