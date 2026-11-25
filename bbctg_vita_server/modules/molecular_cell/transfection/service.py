"""转染与表达工单：列表与编辑、文库单细胞孔板交接进来、交接到合成与验证。转染表（蛋白与重轻链）在 proteins.py。"""

import secrets
import string
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from core.errors import ConflictError, NotFoundError
from models.discovery import DiscoverySynthesisOrder
from models.molecular_cell import (
    MolecularLibraryOrder,
    MolecularTransfectionItem,
    MolecularTransfectionOrder,
    MolecularTransfectionProtein,
)
from modules.discovery.synthesis_progress import service as synthesis_service
from modules.discovery.synthesis_progress.constants import (
    ORDER_KIND_NORMAL,
    SUPPLY_MODE_INTERNAL,
    TRANSFECTION_ORDER_PREFIX,
)
from modules.discovery.workbench.constants import MOUSE_STRAIN_OPTIONS
from modules.molecular_cell.library_orders.service import BUILD_PLATE
from modules.molecular_cell.library_orders.service import STATUS_CANCELLED as LIBRARY_CANCELLED
from utils.batch_save import check_expected, lock_rows_by_id, parse_batch_items
from utils.clock import now_local, today_local
from utils.codes import is_duplicate_key
from utils.filter_values import (
    DEFAULT_RECORDED_TARGET_LIMIT,
    catalog_names_for_pairs,
    code_search_clause,
    filter_terms,
    like_contains,
    match_any,
    recorded_target_clause,
    recorded_target_search,
)
from utils.header_filters import (
    HeaderColumn,
    csv_column,
    csv_token_clause,
    header_column_values,
    header_columns,
    header_filter_clauses,
    header_sort_clauses,
    json_array_column,
    target_column,
    without_header_fields,
)
from utils.model_fields import clean_field, clean_text, model_fields
from utils.normalize import (
    join_tokens,
    normalize_choice,
    normalize_plate_nos,
    normalize_priority,
    normalize_target_codes,
    parse_date,
    parse_row_id,
)
from utils.pagination import paginate_select
from utils.workbench_queue import DEFAULT_PRIORITY, PRIORITY_OPTIONS, lock_queue

_O = MolecularTransfectionOrder
_Item = MolecularTransfectionItem
_Protein = MolecularTransfectionProtein
_Synthesis = DiscoverySynthesisOrder

MISSING_ROW = "转染工单不存在"
MISSING_LIBRARY = "文库构建工单不存在"

ORDER_ID_RANDOM_LEN = 6
ORDER_ID_MAX_ATTEMPTS = 20
ORDER_ID_ALPHABET = string.ascii_uppercase + string.digits

TYPE_PCR = "PCR转染"
TYPE_PLASMID = "质粒转染"
TYPE_OPTIONS = (TYPE_PCR, TYPE_PLASMID)

STATUS_PENDING = "待转染"
STATUS_RUNNING = "转染中"
STATUS_DONE = "已完成"
STATUS_CANCELLED = "已取消"
STATUS_OPTIONS = (STATUS_PENDING, STATUS_RUNNING, STATUS_DONE, STATUS_CANCELLED)

FIELDS = model_fields(_O, readonly=("transfection_order_id", "source_library_order_id"))
# 选项、多值、状态联动由 _apply_fields 单独处理；其余列按模型列类型清洗。
CUSTOM_FIELDS = frozenset({
    "transfection_type",
    "status",
    "priority",
    "target_codes",
    "plate_nos",
    "pcr_rows",
    "mouse_strain",
})
PCR_ROW_LIMITS = {"plate_no": ("板号", 64), "heavy_chain": ("重链", 128), "light_chain": ("轻链", 128)}
MAX_PCR_ROWS = 500
BREAK_FIELDS = frozenset({"remark"})
# 交接到合成与验证后，合成单的合成、到货日期取自这里，这几项不能再改。
HANDOFF_LOCKED_FIELDS = ("transfection_type", "status", "transfected_on", "finished_on")
# 转染表上跟着工单走的字段，见 sync_protein_targets。
PROTEIN_SYNC_FIELDS = ("target_name", "target_codes", "mouse_strain")
MAX_BATCH_SAVE_ITEMS = 500

TypeScope = frozenset[str] | None


def generate_order_id() -> str:
    suffix = "".join(secrets.choice(ORDER_ID_ALPHABET) for _ in range(ORDER_ID_RANDOM_LEN))
    return f"{TRANSFECTION_ORDER_PREFIX}{now_local().strftime('%y%m%d')}-{suffix}"


def _next_order_id(db: Session) -> str:
    for _ in range(ORDER_ID_MAX_ATTEMPTS):
        candidate = generate_order_id()
        if not db.scalar(select(_O.id).where(_O.transfection_order_id == candidate)):
            return candidate
    raise ValueError("无法分配转染工单号")


def _derived_status(row: _O) -> str:
    if row.finished_on:
        return STATUS_DONE
    if row.transfected_on:
        return STATUS_RUNNING
    return STATUS_PENDING


def _apply_status(row: _O, chosen: str | None) -> None:
    """状态跟着转染、完成日期走，只有已取消单独记。手动选状态等于补齐或清掉对应日期。"""
    today = today_local()
    if chosen == STATUS_PENDING:
        row.transfected_on = None
        row.finished_on = None
    elif chosen == STATUS_RUNNING:
        row.transfected_on = row.transfected_on or today
        row.finished_on = None
    elif chosen == STATUS_DONE:
        row.transfected_on = row.transfected_on or today
        row.finished_on = row.finished_on or today
    if row.finished_on and not row.transfected_on:
        raise ValueError("请先填写转染日期")
    if row.finished_on and row.finished_on < row.transfected_on:
        raise ValueError("完成日期不能早于转染日期")
    if chosen == STATUS_CANCELLED or (chosen is None and row.status == STATUS_CANCELLED):
        row.status = STATUS_CANCELLED
    else:
        row.status = _derived_status(row)


def _normalize_pcr_rows(value: Any) -> list[dict[str, Any]]:
    """PCR 转染抽屉里的板号行：板号、重链、轻链、数量；整行空的去掉。"""
    if value in (None, ""):
        return []
    if not isinstance(value, list):
        raise ValueError("板号行格式不正确")
    if len(value) > MAX_PCR_ROWS:
        raise ValueError(f"板号行最多 {MAX_PCR_ROWS} 行")
    rows = []
    for index, item in enumerate(value, start=1):
        if not isinstance(item, dict):
            raise ValueError("板号行格式不正确")
        cleaned: dict[str, Any] = {}
        for key, (label, limit) in PCR_ROW_LIMITS.items():
            text = str(item.get(key) or "").strip()
            if len(text) > limit:
                raise ValueError(f"第 {index} 行{label}不能超过 {limit} 个字符")
            cleaned[key] = text
        raw = item.get("quantity")
        if raw in (None, "") or (isinstance(raw, str) and not raw.strip()):
            cleaned["quantity"] = None
        else:
            try:
                quantity = int(str(raw).strip())
            except ValueError:
                raise ValueError(f"第 {index} 行数量必须是非负整数") from None
            if quantity < 0:
                raise ValueError(f"第 {index} 行数量必须是非负整数")
            cleaned["quantity"] = quantity
        if any(cleaned[key] for key in PCR_ROW_LIMITS) or cleaned["quantity"] is not None:
            rows.append(cleaned)
    return rows


def _apply_fields(row: _O, data: dict[str, Any], *, handed_off: bool) -> None:
    before = {field: getattr(row, field) for field in HANDOFF_LOCKED_FIELDS}
    if "transfection_type" in data:
        row.transfection_type = str(normalize_choice(data.get("transfection_type"), TYPE_OPTIONS, "转染类型"))
    if "priority" in data:
        row.priority = normalize_priority(data.get("priority"))
    if "target_codes" in data:
        row.target_codes = normalize_target_codes(data.get("target_codes"))
    if "plate_nos" in data:
        row.plate_nos = normalize_plate_nos(data.get("plate_nos"))
    if "pcr_rows" in data:
        row.pcr_rows = _normalize_pcr_rows(data.get("pcr_rows"))
    if "mouse_strain" in data:
        row.mouse_strain = clean_text(FIELDS["mouse_strain"], join_tokens(data.get("mouse_strain"), MOUSE_STRAIN_OPTIONS))
    for field, spec in FIELDS.items():
        if field in data and field not in CUSTOM_FIELDS:
            setattr(row, field, clean_field(spec, data[field], keep_breaks=field in BREAK_FIELDS))
    chosen = normalize_choice(data.get("status"), STATUS_OPTIONS, "状态") if "status" in data else None
    _apply_status(row, chosen)
    if handed_off:
        changed = [FIELDS[field].label for field in HANDOFF_LOCKED_FIELDS if getattr(row, field) != before[field]]
        if changed:
            raise ValueError(f"已交接到合成与验证，不能再改{'、'.join(changed)}")


def _handoff_ids(db: Session, codes: list[str]) -> dict[str, str]:
    """转染工单号 → 交接出去的合成与验证单号；交接时合成单的订单号写的就是转染工单号。"""
    if not codes:
        return {}
    rows = db.execute(
        select(_Synthesis.order_no, _Synthesis.synthesis_order_id).where(_Synthesis.order_no.in_(codes))
    ).all()
    return {code: synthesis_id for code, synthesis_id in rows}


def sync_protein_targets(db: Session, protein_ids: set[int]) -> None:
    """转染表的靶点、靶点编号、小鼠品系取自使用它的工单：按工单先后取第一个填了的，工单都没填时保留原值。
    靶点编号都能在靶点库查到时，靶点名称用库里的正式名称。"""
    if not protein_ids:
        return
    rows = db.execute(
        select(_Item.protein_id, _O.target_name, _O.target_codes, _O.mouse_strain)
        .join(_O, _O.id == _Item.order_id)
        .where(_Item.protein_id.in_(protein_ids))
        .order_by(_O.id)
    ).all()
    targets: dict[int, tuple[str | None, list[str]]] = {}
    strains: dict[int, str] = {}
    for protein_id, name, codes, strain in rows:
        if protein_id not in targets and (name or codes):
            targets[protein_id] = (name, list(codes or []))
        if protein_id not in strains and strain:
            strains[protein_id] = strain
    official = catalog_names_for_pairs(db, list(targets.values()))
    for protein in db.scalars(select(_Protein).where(_Protein.id.in_(set(targets) | set(strains)))).all():
        if protein.id in targets:
            name, codes = targets[protein.id]
            names = [official.get(code) for code in codes]
            protein.target_name = "&".join(names) if codes and all(names) else name
            protein.target_codes = codes
        if protein.id in strains:
            protein.mouse_strain = strains[protein.id]


def release_proteins(db: Session, order_id: int, protein_ids: set[int]) -> int:
    """本单清单里的这些蛋白去掉之后（关联已 flush）：本单登记、已没有工单在用的从转染表删除，
    其余重新同步靶点和小鼠品系。返回删除个数。"""
    if not protein_ids:
        return 0
    own = db.scalars(
        select(_Protein).where(_Protein.id.in_(protein_ids), _Protein.source_order_id == order_id).with_for_update()
    ).all()
    still_used = set(db.scalars(select(_Item.protein_id).where(_Item.protein_id.in_(protein_ids))).all())
    removed = {protein.id for protein in own if protein.id not in still_used}
    for protein in own:
        if protein.id in removed:
            db.delete(protein)
    db.flush()
    sync_protein_targets(db, protein_ids - removed)
    return len(removed)


def order_protein_ids(db: Session, order_ids: list[int]) -> set[int]:
    if not order_ids:
        return set()
    return set(db.scalars(select(_Item.protein_id).where(_Item.order_id.in_(order_ids))).all())


def _protein_counts(db: Session, order_ids: list[int]) -> dict[int, int]:
    if not order_ids:
        return {}
    rows = db.execute(
        select(_Item.order_id, func.count()).where(_Item.order_id.in_(order_ids)).group_by(_Item.order_id)
    ).all()
    return {order_id: int(count or 0) for order_id, count in rows}


def serialize_rows(db: Session, rows: list[_O]) -> list[dict[str, Any]]:
    """列表行：工单列 + 蛋白数 + 交接出去的合成与验证单号（未交接为 None）。"""
    counts = _protein_counts(db, [row.id for row in rows])
    handoffs = _handoff_ids(db, [row.transfection_order_id for row in rows])
    return [
        {
            **row.to_dict(),
            "protein_count": counts.get(row.id, 0),
            "synthesis_order_id": handoffs.get(row.transfection_order_id),
        }
        for row in rows
    ]


def handed_off_to(db: Session, row: _O) -> str | None:
    return _handoff_ids(db, [row.transfection_order_id]).get(row.transfection_order_id)


def load_order(db: Session, row_id: int, *, lock: bool = False) -> _O:
    stmt = select(_O).where(_O.id == row_id)
    row = db.scalar(stmt.with_for_update() if lock else stmt)
    if row is None:
        raise NotFoundError(MISSING_ROW)
    return row


def _target_pairs():
    return select(_O.target_name, _O.target_codes)


def search_recorded_targets(db: Session, keyword: str = "", limit: int = DEFAULT_RECORDED_TARGET_LIMIT) -> list[dict]:
    return recorded_target_search(db, _target_pairs(), keyword, limit)


HEADER_COLUMNS = header_columns(
    FIELDS,
    transfection_order_id=HeaderColumn(_O.transfection_order_id),
    source_library_order_id=HeaderColumn(_O.source_library_order_id),
    transfection_type=HeaderColumn(_O.transfection_type, order=TYPE_OPTIONS),
    target_name=target_column(_O.target_name, _O.target_codes),
    status=HeaderColumn(_O.status, order=STATUS_OPTIONS),
    priority=HeaderColumn(_O.priority, order=tuple(PRIORITY_OPTIONS)),
    mouse_strain=csv_column(_O.mouse_strain, tuple(MOUSE_STRAIN_OPTIONS)),
    plate_nos=json_array_column(_O.plate_nos),
)


def _list_order(data: dict[str, Any]):
    spec = HEADER_COLUMNS.get(str(data.get("sort_field") or "").strip())
    direction = str(data.get("sort_dir") or "").strip()
    if spec is not None and direction in {"asc", "desc"}:
        return header_sort_clauses(spec, direction, _O.id)
    return (_O.id.desc(),)


def _filters(data: dict[str, Any], *, db: Session | None, header_except: str | None = None) -> list:
    filters = []
    for key, column, upper, label in (
        ("transfection_order_id", _O.transfection_order_id, True, "系统工单号"),
        ("project_code", _O.project_code, False, "项目编号"),
        ("source_library_order_id", _O.source_library_order_id, True, "来源文库工单号"),
    ):
        clause = code_search_clause(column, data.get(key), upper=upper, label=label)
        if clause is not None:
            filters.append(clause)
    target = recorded_target_clause(db, _O.target_name, _O.target_codes, data.get("target_name"), _target_pairs())
    if target is not None:
        filters.append(target)
    for key, column in (("study_type", _O.study_type), ("pm", _O.pm), ("remark", _O.remark)):
        terms = filter_terms(data.get(key))
        if terms:
            filters.append(or_(*(like_contains(column, term) for term in terms)))
    for key, column in (
        ("transfection_type", _O.transfection_type),
        ("status", _O.status),
        ("owner", _O.owner),
    ):
        clause = match_any(column, data.get(key))
        if clause is not None:
            filters.append(clause)
    strains = filter_terms(data.get("mouse_strain"))
    if strains:
        filters.append(or_(*(csv_token_clause(_O.mouse_strain, term) for term in strains)))
    priority = match_any(_O.priority, [normalize_priority(term) for term in filter_terms(data.get("priority"))])
    if priority is not None:
        filters.append(priority)
    for column, start_key, end_key in (
        (_O.transfected_on, "transfected_on_start", "transfected_on_end"),
        (_O.finished_on, "finished_on_start", "finished_on_end"),
    ):
        start = parse_date(data.get(start_key)) if data.get(start_key) else None
        end = parse_date(data.get(end_key)) if data.get(end_key) else None
        if start:
            filters.append(column >= start)
        if end:
            filters.append(column <= end)
    protein = str(data.get("protein_name") or "").strip()
    if protein:
        filters.append(
            _O.id.in_(
                select(_Item.order_id)
                .join(_Protein, _Protein.id == _Item.protein_id)
                .where(like_contains(_Protein.protein_name, protein))
            )
        )
    filters.extend(header_filter_clauses(db, HEADER_COLUMNS, data.get("field_filters"), except_field=header_except))
    return filters


def _stats(db: Session, payload: dict[str, Any]) -> dict[str, int]:
    """状态统计块不随当前选中的状态（顶部和表头）收缩。"""
    filtered = without_header_fields({key: value for key, value in payload.items() if key != "status"}, {"status"})
    counts = dict(
        db.execute(
            select(_O.status, func.count()).where(*_filters(filtered, db=db)).group_by(_O.status)
        ).all()
    )
    return {status: int(counts.get(status) or 0) for status in STATUS_OPTIONS}


def get_options(db: Session) -> dict[str, list[str]]:
    people: set[str] = set()
    for column in (_O.owner, _O.pm):
        for value in db.scalars(select(column).where(column.is_not(None)).distinct()).all():
            text = str(value or "").strip()
            if text:
                people.add(text)
    return {
        "types": list(TYPE_OPTIONS),
        "statuses": list(STATUS_OPTIONS),
        "priorities": list(PRIORITY_OPTIONS),
        "mouse_strains": list(MOUSE_STRAIN_OPTIONS),
        # 人员下拉未输入关键字时先列出转染工单里的人员，输入后再查询全部在职人员。
        "people": sorted(people),
    }


def get_list(db: Session, data: dict[str, Any]) -> dict[str, Any]:
    payload = data or {}
    filters = _filters(payload, db=db)
    return paginate_select(
        db,
        select(_O).where(*filters),
        select(func.count()).select_from(_O).where(*filters),
        payload,
        order_by=_list_order(payload),
        serialize_rows=lambda rows: serialize_rows(db, rows),
        clamp_page=True,
        stats=_stats(db, payload),
    )


def get_column_values(db: Session, data: dict[str, Any]) -> dict[str, Any]:
    return header_column_values(
        db,
        HEADER_COLUMNS,
        data,
        lambda stmt, payload, field: stmt.where(*_filters(payload, db=db, header_except=field)),
        id_column=_O.id,
    )


def save(db: Session, data: dict[str, Any], created_by: str | None = None) -> dict[str, Any]:
    payload = dict(data or {})
    expected = payload.pop("_expected", None)
    row_id = parse_row_id(payload.get("id"))
    if payload.get("id") not in (None, "") and row_id is None:
        raise ValueError("工单 ID 不正确")
    if row_id is None:
        row = _O(
            transfection_order_id=_next_order_id(db),
            transfection_type=str(normalize_choice(payload.get("transfection_type"), TYPE_OPTIONS, "转染类型")),
            status=STATUS_PENDING,
            priority=DEFAULT_PRIORITY,
            target_codes=[],
            plate_nos=[],
            pcr_rows=[],
            created_by=(created_by or "").strip() or None,
        )
        db.add(row)
        handed_off = False
    else:
        row = load_order(db, row_id, lock=True)
        check_expected(row.to_dict(), expected, fields=FIELDS)
        handed_off = handed_off_to(db, row) is not None
    _apply_fields(row, payload, handed_off=handed_off)
    if row_id is not None and any(field in payload for field in PROTEIN_SYNC_FIELDS):
        db.flush()
        sync_protein_targets(db, order_protein_ids(db, [row.id]))
    db.commit()
    db.refresh(row)
    return serialize_rows(db, [row])[0]


def batch_save(db: Session, items: list[dict[str, Any]]) -> dict[str, Any]:
    parsed_items, row_ids = parse_batch_items(
        items,
        invalid_id_message="工单 ID 不正确",
        duplicate_message="同一工单不能重复提交",
        require_id=True,
        allow_empty=False,
        empty_message="没有需要保存的工单",
        max_items=MAX_BATCH_SAVE_ITEMS,
        too_many_message=f"单次最多保存 {MAX_BATCH_SAVE_ITEMS} 条工单",
    )
    rows_by_id = lock_rows_by_id(db, _O, row_ids, missing_message=MISSING_ROW)
    payloads = []
    for item in parsed_items:
        payload = dict(item)
        expected = payload.pop("_expected", None)
        row = rows_by_id[int(parse_row_id(payload.get("id")))]
        check_expected(row.to_dict(), expected, fields=FIELDS)
        payloads.append((row, payload))
    handoffs = _handoff_ids(db, [row.transfection_order_id for row in rows_by_id.values()])
    for row, payload in payloads:
        try:
            _apply_fields(row, payload, handed_off=row.transfection_order_id in handoffs)
        except ValueError as exc:
            raise ValueError(f"{row.transfection_order_id}：{exc}") from exc
    synced = [row.id for row, payload in payloads if any(field in payload for field in PROTEIN_SYNC_FIELDS)]
    if synced:
        db.flush()
        sync_protein_targets(db, order_protein_ids(db, synced))
    db.commit()
    rows = [row for row, _payload in payloads]
    for row in rows:
        db.refresh(row)
    return {"items": serialize_rows(db, rows)}


def delete_order(db: Session, row_id: int) -> dict[str, int]:
    """删除工单和它的蛋白清单。本单登记的蛋白没有别的工单在用时一起删掉，仍在用的保留、不再归属本单。"""
    row = load_order(db, row_id, lock=True)
    synthesis_id = handed_off_to(db, row)
    if synthesis_id:
        raise ValueError(f"已交接到合成与验证 {synthesis_id}，不能删除")
    items = db.scalars(select(_Item).where(_Item.order_id == row.id)).all()
    for item in items:
        db.delete(item)
    db.flush()
    owned = set(db.scalars(select(_Protein.id).where(_Protein.source_order_id == row.id)).all())
    release_proteins(db, row.id, {item.protein_id for item in items} | owned)
    for protein in db.scalars(select(_Protein).where(_Protein.source_order_id == row.id)).all():
        protein.source_order_id = None
    deleted_id = int(row.id)
    db.delete(row)
    db.commit()
    return {"id": deleted_id}


def handoff_from_library(
    db: Session,
    library_row_id: int,
    created_by: str | None = None,
    scope: TypeScope = None,
) -> dict[str, Any]:
    """文库构建的单细胞孔板工单交接为一条 PCR 转染工单；一条文库工单只能交接一次。"""
    library = db.get(MolecularLibraryOrder, library_row_id)
    if library is None or (scope is not None and library.build_type not in scope):
        raise NotFoundError(MISSING_LIBRARY)
    if library.build_type != BUILD_PLATE:
        raise ValueError("只有单细胞孔板工单可以交接到转染与表达")
    if library.status == LIBRARY_CANCELLED:
        raise ValueError("已取消的文库工单不能交接")
    existing = db.scalar(
        select(_O.transfection_order_id).where(_O.source_library_order_id == library.library_order_id)
    )
    if existing:
        raise ValueError(f"已交接为转染工单 {existing}")
    row = _O(
        transfection_order_id=_next_order_id(db),
        transfection_type=TYPE_PCR,
        source_library_order_id=library.library_order_id,
        project_code=library.source_project_code,
        study_type=library.study_type,
        target_name=library.target_name,
        target_codes=list(library.target_codes or []),
        pm=library.pm,
        mouse_strain=library.mouse_strain,
        plate_nos=list(library.plate_nos or []),
        status=STATUS_PENDING,
        priority=library.priority or DEFAULT_PRIORITY,
        created_by=(created_by or "").strip() or None,
    )
    db.add(row)
    try:
        db.flush()
    except IntegrityError as exc:
        if is_duplicate_key(exc):
            raise ConflictError("这条文库工单刚被交接过，请刷新后查看") from exc
        raise
    db.commit()
    db.refresh(row)
    return serialize_rows(db, [row])[0]


def handoff_to_synthesis(db: Session, row_id: int, created_by: str | None = None) -> dict[str, Any]:
    """已完成的转染工单交接为一条内部转染的合成与验证单，合成、到货日期取转染、完成日期，进合成与验证即为待检测。"""
    # 先锁合成队列再锁本单：锁队列前若本事务还没写过会先提交，反过来会放掉本单的行锁。
    lock_queue(db, _Synthesis)
    row = load_order(db, row_id, lock=True)
    if row.status != STATUS_DONE:
        raise ValueError("只有已完成的转染工单可以交接到合成与验证")
    existing = handed_off_to(db, row)
    if existing:
        raise ValueError(f"已交接到合成与验证 {existing}")
    protein_count = _protein_counts(db, [row.id]).get(row.id, 0)
    if not protein_count:
        raise ValueError("请先导入转染蛋白")
    saved = synthesis_service.save(
        db,
        {
            "order_kind": ORDER_KIND_NORMAL,
            "supply_mode": SUPPLY_MODE_INTERNAL,
            "project_code": row.project_code,
            "study_type": row.study_type,
            "pm": row.pm,
            "target_name": row.target_name,
            "target_codes": list(row.target_codes or []),
            "mouse_strain": row.mouse_strain,
            "priority": row.priority,
            "synthetic_count": protein_count,
            "arrival_count": protein_count,
            "synthetic_date": row.transfected_on.isoformat(),
            "arrival_date": row.finished_on.isoformat(),
        },
        created_by,
        commit=False,
        lock_queue=False,
        require_fields=True,
    )
    # 合成与验证保存时不接受手填转染工单号作订单号，只能在这里直接写入
    synthesis = db.get(_Synthesis, saved["id"])
    synthesis.order_no = row.transfection_order_id
    db.commit()
    return {"synthesis_order_id": synthesis.synthesis_order_id, "order": serialize_rows(db, [row])[0]}


EXPORT_COLUMNS = (
    ("系统工单号", "transfection_order_id"),
    ("来源文库工单号", "source_library_order_id"),
    ("项目编号", "project_code"),
    ("靶点", "target_name"),
    ("靶点编号", "target_codes"),
    ("课题类型", "study_type"),
    ("PM", "pm"),
    ("小鼠品系", "mouse_strain"),
    ("转染类型", "transfection_type"),
    ("板号", "plate_nos"),
    ("蛋白数", "protein_count"),
    ("负责人", "owner"),
    ("状态", "status"),
    ("转染日期", "transfected_on"),
    ("完成日期", "finished_on"),
    ("优先级", "priority"),
    ("合成与验证单号", "synthesis_order_id"),
    ("备注", "remark"),
)


def export_list_workbook(db: Session, data: dict[str, Any]):
    from utils.excel import build_list_workbook, cell_text

    payload = data or {}
    rows = db.scalars(select(_O).where(*_filters(payload, db=db)).order_by(*_list_order(payload))).all()
    table_rows = []
    for item in serialize_rows(db, list(rows)):
        item["plate_nos"] = cell_text(item["plate_nos"], "\n")
        table_rows.append([cell_text(item.get(key)) for _, key in EXPORT_COLUMNS])
    return build_list_workbook(
        sheet_title="转染与表达",
        filename_prefix="转染与表达",
        headers=[label for label, _ in EXPORT_COLUMNS],
        rows=table_rows,
    )
