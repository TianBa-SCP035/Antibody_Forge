"""转染表：蛋白与重、轻链质粒的对应。工单里导入三列表格登记和改清单，查询页只读。

蛋白名称全库唯一（库里按不区分大小写比较）。一个蛋白只有在「本单首次登记、且没有别的工单在用」时，
本单重新导入才能改它的重轻链、或在清单里去掉时从转染表删除；历史录入和别的工单在用的蛋白都不能再改。
"""

from collections import defaultdict
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from core.errors import ConflictError
from models.molecular_cell import (
    MolecularTransfectionItem,
    MolecularTransfectionOrder,
    MolecularTransfectionProtein,
)
from modules.discovery.workbench.constants import MOUSE_STRAIN_OPTIONS
from modules.molecular_cell.transfection.service import (
    handed_off_to,
    load_order,
    release_proteins,
    serialize_rows,
)
from utils.codes import is_duplicate_key
from utils.filter_values import code_search_clause, like_contains
from utils.header_filters import (
    csv_column,
    header_column_values,
    header_columns,
    header_filter_clauses,
    header_sort_clauses,
    target_column,
)
from utils.model_fields import clean_text, model_fields
from utils.pagination import paginate_select

_O = MolecularTransfectionOrder
_Item = MolecularTransfectionItem
_Protein = MolecularTransfectionProtein

IMPORT_HEADERS = ("抗体名称", "重链名称", "轻链名称")
MAX_IMPORT_ROWS = 5000
MAX_PROBLEMS_SHOWN = 50
SOURCE_ORDER = "order"
SOURCE_HISTORY = "history"

FIELDS = model_fields(_Protein, readonly=("source_order_id",))
HEADER_COLUMNS = header_columns(
    FIELDS,
    target_name=target_column(_Protein.target_name, _Protein.target_codes),
    mouse_strain=csv_column(_Protein.mouse_strain, tuple(MOUSE_STRAIN_OPTIONS)),
)


def _key(name: str) -> str:
    return name.lower()


def _problem_message(problems: list[str]) -> str:
    shown = problems[:MAX_PROBLEMS_SHOWN]
    more = len(problems) - len(shown)
    lines = [f"文件有 {len(problems)} 处问题，整个文件未导入："] + shown
    if more:
        lines.append(f"……另有 {more} 处未列出")
    return "\n".join(lines)


def _parse_items(items: list[dict[str, Any]]) -> tuple[list[tuple[int, str, str, str | None]], list[str]]:
    """逐行整理三列，返回（行号、蛋白名称、重链、轻链）和问题清单；行号是表格里的行号。"""
    parsed: list[tuple[int, str, str, str | None]] = []
    problems: list[str] = []
    first_line: dict[str, int] = {}
    for index, item in enumerate(items, start=2):
        line = int(item.get("row") or index)
        try:
            name = clean_text(FIELDS["protein_name"], item.get("protein_name"))
            heavy = clean_text(FIELDS["heavy_chain"], item.get("heavy_chain"))
            light = clean_text(FIELDS["light_chain"], item.get("light_chain"))
        except ValueError as exc:
            problems.append(f"第 {line} 行：{exc}")
            continue
        if not name or not heavy:
            problems.append(f"第 {line} 行：{'缺少蛋白名称' if not name else '缺少重链'}")
            continue
        key = _key(name)
        if key in first_line:
            problems.append(f"第 {line} 行：蛋白名称 {name} 与第 {first_line[key]} 行重复")
            continue
        first_line[key] = line
        parsed.append((line, name, heavy, light))
    return parsed, problems


def _editable_order(db: Session, order_id: int) -> _O:
    order = load_order(db, order_id, lock=True)
    synthesis_id = handed_off_to(db, order)
    if synthesis_id:
        raise ValueError(f"已交接到合成与验证 {synthesis_id}，蛋白清单不能再改")
    return order


def import_proteins(
    db: Session,
    order_id: int,
    items: list[dict[str, Any]],
    created_by: str | None = None,
) -> dict[str, Any]:
    """用导入的表格替换本单的蛋白清单；任何一行有问题整个文件不导入，并列出全部问题行。"""
    order = _editable_order(db, order_id)
    if not items:
        raise ValueError("文件里没有蛋白")
    if len(items) > MAX_IMPORT_ROWS:
        raise ValueError(f"单次最多导入 {MAX_IMPORT_ROWS} 个蛋白")
    parsed, problems = _parse_items(items)

    existing = {
        _key(protein.protein_name): protein
        for protein in db.scalars(
            select(_Protein)
            .where(func.lower(_Protein.protein_name).in_([_key(name) for _, name, _, _ in parsed]))
            .order_by(_Protein.id)
            .with_for_update()
        ).all()
    }
    used_elsewhere = set(
        db.scalars(
            select(_Item.protein_id).where(
                _Item.protein_id.in_([protein.id for protein in existing.values()]),
                _Item.order_id != order.id,
            )
        ).all()
    ) if existing else set()

    def editable(protein: _Protein) -> bool:
        return protein.source_order_id == order.id and protein.id not in used_elsewhere

    for line, name, heavy, light in parsed:
        protein = existing.get(_key(name))
        if protein is None or (protein.heavy_chain, protein.light_chain) == (heavy, light) or editable(protein):
            continue
        problems.append(
            f"第 {line} 行：{protein.protein_name} 已登记为 重链 {protein.heavy_chain}、"
            f"轻链 {protein.light_chain or '无'}，与文件不一致"
        )
    if problems:
        raise ValueError(_problem_message(problems))

    old_items = db.scalars(select(_Item).where(_Item.order_id == order.id)).all()
    previous_ids = {item.protein_id for item in old_items}
    for item in old_items:
        db.delete(item)
    actor = (created_by or "").strip() or None
    created = updated = 0
    proteins: list[_Protein] = []
    for _line, name, heavy, light in parsed:
        protein = existing.get(_key(name))
        if protein is None:
            protein = _Protein(
                protein_name=name, heavy_chain=heavy, light_chain=light, source_order_id=order.id, created_by=actor
            )
            db.add(protein)
            created += 1
        elif (protein.heavy_chain, protein.light_chain) != (heavy, light):
            protein.heavy_chain = heavy
            protein.light_chain = light
            updated += 1
        proteins.append(protein)
    try:
        db.flush()
    except IntegrityError as exc:
        if is_duplicate_key(exc):
            raise ConflictError("有蛋白刚被其他工单登记，请重新导入") from exc
        raise
    for protein in proteins:
        db.add(_Item(order_id=order.id, protein_id=protein.id))
    db.flush()

    removed = release_proteins(db, order.id, previous_ids | {protein.id for protein in proteins})
    db.commit()
    db.refresh(order)
    return {
        "total": len(proteins),
        "created": created,
        "updated": updated,
        "removed": removed,
        "order": serialize_rows(db, [order])[0],
    }


def clear_proteins(db: Session, order_id: int) -> dict[str, Any]:
    """整批删除本单蛋白清单；其中本单登记、别的工单没在用的一并从转染表删除。"""
    order = _editable_order(db, order_id)
    items = db.scalars(select(_Item).where(_Item.order_id == order.id)).all()
    if not items:
        raise ValueError("本单还没有蛋白")
    for item in items:
        db.delete(item)
    db.flush()
    removed = release_proteins(db, order.id, {item.protein_id for item in items})
    db.commit()
    db.refresh(order)
    return {"total": len(items), "removed": removed, "order": serialize_rows(db, [order])[0]}


def _proteins_of(db: Session, order_id: int) -> list[_Protein]:
    return list(
        db.scalars(
            select(_Protein)
            .join(_Item, _Item.protein_id == _Protein.id)
            .where(_Item.order_id == order_id)
            .order_by(_Item.id)
        ).all()
    )


def order_proteins(db: Session, order_id: int) -> dict[str, Any]:
    """工单的蛋白清单，按导入时的行序；registered_here 表示由本单首次登记。"""
    order = load_order(db, order_id)
    rows = _proteins_of(db, order.id)
    return {
        "items": [
            {
                "id": protein.id,
                "protein_name": protein.protein_name,
                "heavy_chain": protein.heavy_chain,
                "light_chain": protein.light_chain,
                "registered_here": protein.source_order_id == order.id,
            }
            for protein in rows
        ],
    }


def _list_order(data: dict[str, Any]):
    spec = HEADER_COLUMNS.get(str(data.get("sort_field") or "").strip())
    direction = str(data.get("sort_dir") or "").strip()
    if spec is not None and direction in {"asc", "desc"}:
        return header_sort_clauses(spec, direction, _Protein.id)
    return (_Protein.id.desc(),)


def _filters(
    data: dict[str, Any], *, db: Session, include_source: bool = True, header_except: str | None = None
) -> list:
    filters = []
    for key in ("protein_name", "heavy_chain", "light_chain"):
        text = str(data.get(key) or "").strip()
        if text:
            filters.append(like_contains(getattr(_Protein, key), text))
    matched = code_search_clause(_O.transfection_order_id, data.get("order_code"), upper=True, label="使用工单")
    if matched is not None:
        filters.append(
            _Protein.id.in_(select(_Item.protein_id).join(_O, _O.id == _Item.order_id).where(matched))
        )
    source = str(data.get("source") or "").strip()
    if include_source and source == SOURCE_ORDER:
        filters.append(_Protein.source_order_id.is_not(None))
    elif include_source and source == SOURCE_HISTORY:
        filters.append(_Protein.source_order_id.is_(None))
    filters.extend(header_filter_clauses(db, HEADER_COLUMNS, data.get("field_filters"), except_field=header_except))
    return filters


def _stats(db: Session, data: dict[str, Any]) -> dict[str, int]:
    """来源统计不随当前选中的来源收缩。"""
    total, from_orders = db.execute(
        select(func.count(), func.count(_Protein.source_order_id))
        .select_from(_Protein)
        .where(*_filters(data, db=db, include_source=False))
    ).one()
    total = int(total or 0)
    from_orders = int(from_orders or 0)
    return {"total": total, SOURCE_ORDER: from_orders, SOURCE_HISTORY: total - from_orders}


def _serialize_proteins(db: Session, rows: list[_Protein]) -> list[dict[str, Any]]:
    ids = [protein.id for protein in rows]
    used: dict[int, list[str]] = defaultdict(list)
    if ids:
        for protein_id, code in db.execute(
            select(_Item.protein_id, _O.transfection_order_id)
            .join(_O, _O.id == _Item.order_id)
            .where(_Item.protein_id.in_(ids))
            .order_by(_O.id)
        ).all():
            used[protein_id].append(code)
    source_ids = {protein.source_order_id for protein in rows if protein.source_order_id}
    sources = dict(
        db.execute(select(_O.id, _O.transfection_order_id).where(_O.id.in_(source_ids))).all()
    ) if source_ids else {}
    return [
        {
            **protein.to_dict(),
            "source_order": sources.get(protein.source_order_id),
            "orders": used.get(protein.id, []),
        }
        for protein in rows
    ]


def list_proteins(db: Session, data: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = data or {}
    filters = _filters(payload, db=db)
    return paginate_select(
        db,
        select(_Protein).where(*filters),
        select(func.count()).select_from(_Protein).where(*filters),
        payload,
        order_by=_list_order(payload),
        serialize_rows=lambda rows: _serialize_proteins(db, rows),
        clamp_page=True,
        stats=_stats(db, payload),
    )


def get_column_values(db: Session, data: dict[str, Any]) -> dict[str, Any]:
    return header_column_values(
        db,
        HEADER_COLUMNS,
        data,
        lambda stmt, payload, field: stmt.where(*_filters(payload, db=db, header_except=field)),
        id_column=_Protein.id,
    )


EXPORT_HEADERS = ("蛋白名称", "重链", "轻链", "靶点", "靶点编号", "小鼠品系", "登记工单", "使用工单", "登记时间")


def export_workbook(db: Session, data: dict[str, Any] | None = None):
    from utils.excel import build_list_workbook, cell_text

    payload = data or {}
    rows = db.scalars(select(_Protein).where(*_filters(payload, db=db)).order_by(*_list_order(payload))).all()
    return build_list_workbook(
        sheet_title="转染表",
        filename_prefix="转染表",
        headers=list(EXPORT_HEADERS),
        rows=[
            [
                item["protein_name"],
                item["heavy_chain"],
                item["light_chain"],
                item["target_name"],
                cell_text(item["target_codes"]),
                item["mouse_strain"],
                item["source_order"],
                cell_text(item["orders"]),
                item["created_at"],
            ]
            for item in _serialize_proteins(db, list(rows))
        ],
    )


def export_order_proteins(db: Session, order_id: int):
    """本单蛋白清单按导入格式导出，改完可直接导回；清单为空时就是导入模板。"""
    from utils.excel import build_list_workbook

    order = load_order(db, order_id)
    return build_list_workbook(
        sheet_title="转染蛋白",
        filename_prefix=f"转染蛋白_{order.transfection_order_id}",
        headers=list(IMPORT_HEADERS),
        rows=[[p.protein_name, p.heavy_chain, p.light_chain] for p in _proteins_of(db, order.id)],
    )
