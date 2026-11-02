"""引物库数据查询与写入。"""

from io import BytesIO
import re
from typing import Any

from sqlalchemy import case, func, or_, select
from sqlalchemy.orm import Session

from utils.filter_values import clean_field_text, filter_terms, like_contains, match_any
from utils.header_filters import HeaderColumn, column_values, header_filter_clauses, header_sort_clauses

from models.molecular_cell import (
    LIBRARY_PRIMER_ID_FIELDS,
    MolecularLibraryOrder,
    MolecularPrimerIndexCatalog as Primer,
)

MISSING_PRIMER = "引物不存在"
NAME_TAKEN = "引物名称已存在"
PRIMER_IN_USE = "这条引物已被文库工单使用，可以停用，不能删除"
DEFAULT_PAGE_LIMIT = 20
MAX_PAGE_LIMIT = 500
MAX_OPTIONS = 2000
MAX_BATCH_ITEMS = 1000
MAX_BATCH_IDS = 5000

FIELD_LIMITS = {
    "name": 128,
    "family": 32,
    "direction": 8,
    "version": 16,
    "short_sequence": 64,
    "homology_arm_1": 128,
    "homology_arm_2": 128,
    "note": 500,
}
FIELD_LABELS = {
    "name": "名称",
    "family": "系列",
    "direction": "方向",
    "version": "版本",
    "short_sequence": "显示序列",
    "homology_arm_1": "同源臂1",
    "homology_arm_2": "同源臂2",
    "note": "备注",
}
WRITABLE_FIELDS = (
    "name",
    "family",
    "direction",
    "version",
    "short_sequence",
    "homology_arm_1",
    "homology_arm_2",
    "note",
)
EXPORT_HEADERS = ("名称", "系列", "方向", "显示序列", "核对序列", "备注", "状态")
DNA_PATTERN = re.compile(r"^[ACGTN]+$")
COMPLEMENT = str.maketrans("ACGTN", "TGCAN")
PRESET_LIBRARIES = ("达普Barcode", "UDP")
DIRECTION_LABELS = {"F": "正向", "R": "反向"}
DIRECTION_VALUES = {"F": "F", "R": "R", "正向": "F", "反向": "R"}


def _text(value: Any, field: str, required: bool = False) -> str | None:
    text = clean_field_text(value, keep_breaks=field == "note")
    if required and not text:
        raise ValueError(f"{FIELD_LABELS[field]}不能为空")
    if text and len(text) > FIELD_LIMITS[field]:
        raise ValueError(f"{FIELD_LABELS[field]}不能超过 {FIELD_LIMITS[field]} 个字符")
    return text or None


def _sequence(value: Any, field: str, required: bool = False) -> str | None:
    text = re.sub(r"\s+", "", str(value or "")).upper()
    if required and not text:
        raise ValueError(f"{FIELD_LABELS[field]}不能为空")
    if text and len(text) > FIELD_LIMITS[field]:
        raise ValueError(f"{FIELD_LABELS[field]}不能超过 {FIELD_LIMITS[field]} 个字符")
    if text and not DNA_PATTERN.fullmatch(text):
        raise ValueError(f"{FIELD_LABELS[field]}只能包含 A、C、G、T、N")
    return text or None


def check_sequence(value: str) -> str:
    """核对序列。显示序列按测序读数转过一次，得到的就是测序文件里那一串。"""
    return value.translate(COMPLEMENT)[::-1]


def normalize(data: dict[str, Any]) -> dict[str, Any]:
    family = _text(data.get("family"), "family", True)
    raw_direction = str(data.get("direction") or "").strip()
    direction = DIRECTION_VALUES.get(raw_direction) or DIRECTION_VALUES.get(raw_direction.upper())
    if not direction:
        raise ValueError("方向只能是正向或反向")
    active = data.get("active") if "active" in data else None
    if active is not None and not isinstance(active, bool):
        raise ValueError("启用状态不正确")
    clean = {
        "name": _text(data.get("name"), "name", True),
        "family": family,
        "direction": direction,
        "short_sequence": _sequence(data.get("short_sequence"), "short_sequence", True),
        "note": _text(data.get("note"), "note"),
        "active": active,
    }
    # 表单和导入不再编辑版本、同源臂。缺省或空值不写回，避免把库里的旧值清掉。
    version = _text(data.get("version"), "version") if "version" in data else None
    if version:
        clean["version"] = version
    for field in ("homology_arm_1", "homology_arm_2"):
        if field not in data:
            continue
        arm = _sequence(data.get(field), field)
        if arm:
            clean[field] = arm
    return clean


def _apply(row: Primer, data: dict[str, Any]) -> None:
    for field in WRITABLE_FIELDS:
        if field not in data:
            continue
        setattr(row, field, data[field])
    if data["active"] is not None:
        row.active = data["active"]


def _new(data: dict[str, Any]) -> Primer:
    row = Primer(
        name=data["name"],
        family=data["family"],
        short_sequence=data["short_sequence"],
        active=True if data["active"] is None else data["active"],
    )
    _apply(row, data)
    return row


# 核对序列由显示序列算出，库里没有这一列，靠顶部筛选
HEADER_COLUMNS: dict[str, HeaderColumn] = {
    "name": HeaderColumn(Primer.name),
    "family": HeaderColumn(Primer.family, "enum", order=PRESET_LIBRARIES),
    "direction": HeaderColumn(Primer.direction, "enum", order=tuple(DIRECTION_LABELS)),
    "short_sequence": HeaderColumn(Primer.short_sequence),
    "note": HeaderColumn(Primer.note),
    "active": HeaderColumn(case((Primer.active.is_(True), "active"), else_="inactive"), "enum", order=("active", "inactive")),
}
_VALUE_LABELS = {
    "direction": DIRECTION_LABELS,
    "active": {"active": "启用", "inactive": "停用"},
}
DEFAULT_ORDER = (Primer.family, Primer.direction, Primer.name)


def _list_order(data: dict[str, Any]):
    spec = HEADER_COLUMNS.get(str(data.get("sort_field") or "").strip())
    direction = str(data.get("sort_dir") or "").strip()
    if spec is not None and direction in {"asc", "desc"}:
        return header_sort_clauses(spec, direction, Primer.id)
    return DEFAULT_ORDER


def _filters(data: dict[str, Any], *, include_family: bool = True, header_except: str | None = None) -> list:
    filters = []
    name = str(data.get("name") or "").strip()
    if name:
        filters.append(like_contains(Primer.name, name))
    sequence = re.sub(r"\s+", "", str(data.get("sequence") or "")).upper()
    if sequence:
        filters.append(like_contains(Primer.short_sequence, sequence))
    note = str(data.get("note") or "").strip()
    if note:
        filters.append(like_contains(Primer.note, note))
    check_keyword = re.sub(r"\s+", "", str(data.get("check_keyword") or "")).upper()
    if check_keyword:
        if DNA_PATTERN.fullmatch(check_keyword):
            filters.append(like_contains(Primer.short_sequence, check_sequence(check_keyword)))
        else:
            filters.append(Primer.id < 0)
    if include_family:
        family = match_any(Primer.family, data.get("family"))
        if family is not None:
            filters.append(family)
    directions = [term.upper() for term in filter_terms(data.get("direction"))]
    direction = match_any(Primer.direction, directions)
    if direction is not None:
        filters.append(direction)
    if isinstance(data.get("active"), bool):
        filters.append(Primer.active == data["active"])
    filters.extend(header_filter_clauses(None, HEADER_COLUMNS, data.get("field_filters"), except_field=header_except))
    return filters


def _stats(db: Session, data: dict[str, Any]) -> dict[str, Any]:
    """系列统计不随当前选中的系列（顶部和表头）收缩。两个预置系列始终占位，自建系列有数据才出现。"""
    grouped = {
        name: int(count or 0)
        for name, count in db.execute(
            select(Primer.family, func.count())
            .where(*_filters(data, include_family=False, header_except="family"))
            .group_by(Primer.family)
        ).all()
    }
    names = list(PRESET_LIBRARIES)
    names.extend(sorted(name for name in grouped if name not in names))
    for selected in filter_terms(data.get("family")):
        if selected not in names:
            names.append(selected)
    return {
        "total": sum(grouped.values()),
        "families": [{"name": name, "count": grouped.get(name, 0)} for name in names],
    }


def list_catalog(db: Session, data: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = data or {}
    page = max(int(payload.get("page") or 1), 1)
    limit = min(max(int(payload.get("limit") or DEFAULT_PAGE_LIMIT), 1), MAX_PAGE_LIMIT)
    filters = _filters(payload)
    total = db.scalar(select(func.count()).select_from(Primer).where(*filters)) or 0
    rows = db.scalars(
        select(Primer)
        .where(*filters)
        .order_by(*_list_order(payload))
        .offset((page - 1) * limit)
        .limit(limit)
    ).all()
    stats = _stats(db, payload)
    return {
        "items": [row.to_dict() for row in rows],
        "total": int(total),
        "page": page,
        "limit": limit,
        "stats": stats,
    }


def get_column_values(db: Session, data: dict[str, Any]) -> dict[str, Any]:
    """表头筛选的取值列表：套用除本列表头条件以外的全部筛选。顶部筛选里的本列条件由前端去掉。"""
    payload = data or {}
    field = str(payload.get("field") or "").strip()
    spec = HEADER_COLUMNS.get(field)
    if spec is None:
        raise ValueError(f"不支持按「{field}」表头筛选")
    result = column_values(
        db,
        spec,
        lambda stmt: stmt.where(*_filters(payload, header_except=field)),
        id_column=Primer.id,
        keyword=str(payload.get("value_keyword") or ""),
        limit=payload.get("value_limit"),
        order=str(payload.get("value_order") or "value"),
    )
    labels = _VALUE_LABELS.get(field)
    if labels:
        for item in result["items"]:
            if item["value"] in labels:
                item["label"] = labels[item["value"]]
    return result


def list_options(
    db: Session,
    query: str | None = None,
    family: str | None = None,
    limit: int = 100,
) -> dict[str, Any]:
    stmt = select(Primer).where(Primer.active.is_(True))
    keyword = str(query or "").strip()
    if keyword:
        sequence = re.sub(r"\s+", "", keyword).upper()
        clauses = [like_contains(Primer.name, keyword)]
        if DNA_PATTERN.fullmatch(sequence):
            clauses.append(like_contains(Primer.short_sequence, sequence))
            flipped = check_sequence(sequence)
            if flipped != sequence:
                clauses.append(like_contains(Primer.short_sequence, flipped))
        else:
            clauses.append(like_contains(Primer.short_sequence, keyword.upper()))
        stmt = stmt.where(or_(*clauses))
    if family:
        stmt = stmt.where(Primer.family == family.strip())
    rows = db.scalars(
        stmt.order_by(Primer.family, Primer.direction, Primer.name).limit(min(max(limit, 1), MAX_OPTIONS))
    ).all()
    return {"items": [row.to_dict() for row in rows]}


def save(db: Session, data: dict[str, Any]) -> dict[str, Any]:
    row_id = data.get("id")
    row = db.get(Primer, int(row_id)) if row_id else None
    if row_id and row is None:
        raise ValueError(MISSING_PRIMER)
    clean = normalize(data)
    duplicate = db.scalar(
        select(Primer.id).where(
            Primer.name == clean["name"],
            Primer.id != (row.id if row else 0),
        )
    )
    if duplicate:
        raise ValueError(NAME_TAKEN)
    if row is None:
        row = _new(clean)
        db.add(row)
    else:
        _apply(row, clean)
    db.commit()
    db.refresh(row)
    return row.to_dict()


def list_ids(db: Session, data: dict[str, Any] | None = None) -> list[int]:
    payload = data or {}
    rows = db.scalars(select(Primer.id).where(*_filters(payload)).order_by(*_list_order(payload))).all()
    return [int(row_id) for row_id in rows]


def _id_list(ids: list[int]) -> list[int]:
    clean: list[int] = []
    seen: set[int] = set()
    for raw in ids:
        value = int(raw)
        if value <= 0 or value in seen:
            continue
        seen.add(value)
        clean.append(value)
    if not clean:
        raise ValueError("请先勾选引物")
    if len(clean) > MAX_BATCH_IDS:
        raise ValueError(f"单次最多处理 {MAX_BATCH_IDS} 条引物")
    return clean


def batch_update(
    db: Session,
    ids: list[int],
    *,
    active: bool | None = None,
    family: str | None = None,
    direction: str | None = None,
) -> dict[str, int]:
    if active is None and family is None and direction is None:
        raise ValueError("请选择停用、启用、新系列或方向")
    if active is not None and not isinstance(active, bool):
        raise ValueError("启用状态不正确")
    next_family = _text(family, "family", True) if family is not None else None
    next_direction = None
    if direction is not None:
        raw_direction = str(direction).strip()
        next_direction = DIRECTION_VALUES.get(raw_direction) or DIRECTION_VALUES.get(raw_direction.upper())
        if not next_direction:
            raise ValueError("方向只能是正向或反向")
    id_list = _id_list(ids)
    rows = db.scalars(select(Primer).where(Primer.id.in_(id_list))).all()
    if len(rows) != len(id_list):
        raise ValueError("有引物已不存在，请刷新后再试")
    for row in rows:
        if next_family is not None:
            row.family = next_family
        if next_direction is not None:
            row.direction = next_direction
        if active is not None:
            row.active = active
    db.commit()
    return {"total": len(rows)}


def batch_delete(db: Session, ids: list[int]) -> dict[str, Any]:
    id_list = _id_list(ids)
    rows = db.scalars(select(Primer).where(Primer.id.in_(id_list))).all()
    if len(rows) != len(id_list):
        raise ValueError("有引物已不存在，请刷新后再试")
    used_ids: set[int] = set()
    for field in LIBRARY_PRIMER_ID_FIELDS:
        column = getattr(MolecularLibraryOrder, field)
        found = db.scalars(select(column).where(column.in_(id_list))).all()
        used_ids.update(int(value) for value in found if value)
    skipped: list[str] = []
    deleted = 0
    for row in rows:
        if int(row.id) in used_ids:
            skipped.append(row.name)
            continue
        db.delete(row)
        deleted += 1
    db.commit()
    return {"deleted": deleted, "skipped": skipped}


def delete_primer(db: Session, row_id: int) -> dict[str, int]:
    row = db.get(Primer, int(row_id))
    if row is None:
        raise ValueError(MISSING_PRIMER)
    used = db.scalar(
        select(MolecularLibraryOrder.id).where(
            or_(*(getattr(MolecularLibraryOrder, field) == row.id for field in LIBRARY_PRIMER_ID_FIELDS))
        )
    )
    if used:
        raise ValueError(PRIMER_IN_USE)
    deleted_id = int(row.id)
    db.delete(row)
    db.commit()
    return {"id": deleted_id}


def batch_save(db: Session, items: list[dict[str, Any]]) -> dict[str, int]:
    if not items:
        raise ValueError("没有可导入的引物")
    if len(items) > MAX_BATCH_ITEMS:
        raise ValueError(f"单次最多导入 {MAX_BATCH_ITEMS} 条引物")

    normalized = []
    names = set()
    for index, item in enumerate(items, start=1):
        try:
            clean = normalize(item)
        except ValueError as exc:
            raise ValueError(f"第 {index} 行：{exc}") from exc
        if clean["name"] in names:
            raise ValueError(f"导入数据中名称重复：{clean['name']}")
        names.add(clean["name"])
        normalized.append(clean)

    existing = db.scalars(select(Primer).where(Primer.name.in_(names))).all()
    by_name = {row.name: row for row in existing}
    created = 0
    for clean in normalized:
        row = by_name.get(clean["name"])
        if row is None:
            row = _new(clean)
            db.add(row)
            created += 1
        else:
            _apply(row, clean)
    db.commit()
    return {"total": len(items), "created": created, "updated": len(items) - created}


def export_workbook(db: Session, data: dict[str, Any] | None = None) -> tuple[BytesIO, str]:
    from utils.excel import build_list_workbook

    payload = data or {}
    rows = db.scalars(select(Primer).where(*_filters(payload)).order_by(*_list_order(payload))).all()
    return build_list_workbook(
        sheet_title="引物库",
        filename_prefix="引物库",
        headers=list(EXPORT_HEADERS),
        rows=[
            [
                row.name,
                row.family,
                DIRECTION_LABELS.get(row.direction or "", row.direction),
                row.short_sequence,
                check_sequence(row.short_sequence),
                row.note,
                "启用" if row.active else "停用",
            ]
            for row in rows
        ],
    )
