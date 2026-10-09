"""引物库数据查询与写入。"""

from io import BytesIO
import re
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from models.molecular_cell import MolecularLibraryOrder, MolecularPrimerIndexCatalog as Primer

MISSING_PRIMER = "引物不存在"
NAME_TAKEN = "引物名称已存在"
PRIMER_IN_USE = "这条引物已被文库工单使用，可以停用，不能删除"
ORDER_PRIMER_FIELDS = (
    "h_forward_primer_id",
    "h_reverse_primer_id",
    "k_forward_primer_id",
    "k_reverse_primer_id",
    "l_forward_primer_id",
    "l_reverse_primer_id",
    "i7_catalog_id",
    "i5_catalog_id",
)
DEFAULT_PAGE_LIMIT = 20
MAX_PAGE_LIMIT = 200
MAX_OPTIONS = 500
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
    text = str(value or "").strip()
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
    """质检测序读到的是另一条链，核对序列就是显示序列的反向互补。"""
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


def _filters(data: dict[str, Any], *, include_family: bool = True) -> list:
    filters = []
    name = str(data.get("name") or "").strip()
    if name:
        filters.append(Primer.name.like(f"%{name}%"))
    sequence = re.sub(r"\s+", "", str(data.get("sequence") or "")).upper()
    if sequence:
        filters.append(Primer.short_sequence.like(f"%{sequence}%"))
    note = str(data.get("note") or "").strip()
    if note:
        filters.append(Primer.note.like(f"%{note}%"))
    check_keyword = re.sub(r"\s+", "", str(data.get("check_keyword") or "")).upper()
    if check_keyword:
        if DNA_PATTERN.fullmatch(check_keyword):
            filters.append(Primer.short_sequence.like(f"%{check_sequence(check_keyword)}%"))
        else:
            filters.append(Primer.id < 0)
    if include_family and data.get("family"):
        filters.append(Primer.family == str(data["family"]).strip())
    if data.get("direction"):
        filters.append(Primer.direction == str(data["direction"]).strip().upper())
    if isinstance(data.get("active"), bool):
        filters.append(Primer.active == data["active"])
    return filters


def _stats(db: Session, data: dict[str, Any]) -> dict[str, Any]:
    """系列统计不随当前选中的系列收缩。两个预置系列始终占位，自建系列有数据才出现。"""
    grouped = {
        name: int(count or 0)
        for name, count in db.execute(
            select(Primer.family, func.count())
            .where(*_filters(data, include_family=False))
            .group_by(Primer.family)
        ).all()
    }
    names = list(PRESET_LIBRARIES)
    names.extend(sorted(name for name in grouped if name not in names))
    selected = str(data.get("family") or "").strip()
    if selected and selected not in names:
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
        .order_by(Primer.family, Primer.direction, Primer.name)
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


def list_options(
    db: Session,
    query: str | None = None,
    family: str | None = None,
    limit: int = 100,
) -> dict[str, Any]:
    stmt = select(Primer).where(Primer.active.is_(True))
    keyword = str(query or "").strip()
    if keyword:
        stmt = stmt.where(
            or_(
                Primer.name.like(f"%{keyword}%"),
                Primer.short_sequence.like(f"%{keyword.upper()}%"),
            )
        )
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
    rows = db.scalars(
        select(Primer.id)
        .where(*_filters(data or {}))
        .order_by(Primer.family, Primer.direction, Primer.name)
    ).all()
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
) -> dict[str, int]:
    if active is None and family is None:
        raise ValueError("请选择停用、启用或新系列")
    if active is not None and not isinstance(active, bool):
        raise ValueError("启用状态不正确")
    next_family = _text(family, "family", True) if family is not None else None
    id_list = _id_list(ids)
    rows = db.scalars(select(Primer).where(Primer.id.in_(id_list))).all()
    if len(rows) != len(id_list):
        raise ValueError("有引物已不存在，请刷新后再试")
    for row in rows:
        if next_family is not None:
            row.family = next_family
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
    for field in ORDER_PRIMER_FIELDS:
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
            or_(*(getattr(MolecularLibraryOrder, field) == row.id for field in ORDER_PRIMER_FIELDS))
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

    rows = db.scalars(
        select(Primer).where(*_filters(data or {})).order_by(Primer.family, Primer.direction, Primer.name)
    ).all()
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
