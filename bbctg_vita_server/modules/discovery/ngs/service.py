"""NGS 测序：文库构建交接下来的一次上机，做完后按送合成转码交到合成与验证。"""

import secrets
import string
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from core.errors import NotFoundError
from models.discovery import DiscoveryNgsRun, DiscoverySynthesisOrder
from models.molecular_cell import MolecularLibraryOrder
from modules.discovery.synthesis_progress import service as synthesis_service
from modules.discovery.synthesis_progress.constants import ORDER_KIND_NORMAL, SUPPLY_MODE_ARRIVAL
from modules.discovery.workbench.constants import MOUSE_STRAIN_OPTIONS
from modules.molecular_cell.library_orders.service import (
    BUILD_PERIPHERAL_BLOOD,
    BUILD_PHAGE_DISPLAY,
    BUILD_PHAGE_NGS,
    BUILD_PLASMA_NGS,
    BUILD_PLATE,
    BUILD_POOLED_BARCODE,
    BUILD_POOLED_BCR,
    SAMPLE_LITE,
    SAMPLE_NANO,
    SAMPLE_PHAGE,
    SAMPLE_RNVM_BLOOD,
    SAMPLE_SOURCE_LABELS,
)
from modules.molecular_cell.library_orders.service import STATUS_CANCELLED as LIBRARY_CANCELLED
from utils.batch_save import check_expected, lock_rows_by_id, parse_batch_items
from utils.clock import now_local
from utils.filter_values import (
    DEFAULT_RECORDED_TARGET_LIMIT,
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
    target_column,
    without_header_fields,
)
from utils.model_fields import clean_field, clean_text, model_fields
from utils.normalize import join_tokens, normalize_choice, normalize_target_codes, parse_date, parse_row_id
from utils.pagination import paginate_select
from utils.workbench_queue import lock_queue

_O = DiscoveryNgsRun

MISSING_ROW = "测序单不存在"
MISSING_LIBRARY = "文库构建工单不存在"

ORDER_ID_PREFIX = "NGS-"
ORDER_ID_RANDOM_LEN = 6
ORDER_ID_MAX_ATTEMPTS = 20
ORDER_ID_ALPHABET = string.ascii_uppercase + string.digits

SAMPLE_NANO_LIB = "Nano"
SAMPLE_LITE_LIB = "Lite"
SAMPLE_PHAGE_LIB = "噬菌体"
SAMPLE_RND = "研发库"
SAMPLE_EXTERNAL = "外来带样"
SAMPLE_LIBRARIES = (SAMPLE_NANO_LIB, SAMPLE_LITE_LIB, SAMPLE_PHAGE_LIB, SAMPLE_RND, SAMPLE_EXTERNAL)
LIBRARY_SAMPLE = {
    SAMPLE_NANO: SAMPLE_NANO_LIB,
    SAMPLE_LITE: SAMPLE_LITE_LIB,
    SAMPLE_RNVM_BLOOD: SAMPLE_RND,
    SAMPLE_PHAGE: SAMPLE_PHAGE_LIB,
}
NGS_BUILD_TYPES = (
    BUILD_POOLED_BCR,
    BUILD_POOLED_BARCODE,
    BUILD_PERIPHERAL_BLOOD,
    BUILD_PLASMA_NGS,
    BUILD_PHAGE_DISPLAY,
    BUILD_PHAGE_NGS,
)
PHAGE_BUILDS = (BUILD_PHAGE_DISPLAY, BUILD_PHAGE_NGS)

PROJECT_LEVELS = ("公司内部研发", "客户关注", "客户付钱", "PCC过会", "数据包", "公司重点")

STATUS_WAIT = "待上机"
STATUS_RUN = "已上机"
STATUS_SENT = "已送合成"
STATUS_DONE = "已完成"
STATUS_CANCELLED = "已取消"
STATUS_OPTIONS = (STATUS_WAIT, STATUS_RUN, STATUS_SENT, STATUS_DONE, STATUS_CANCELLED)
TERMINAL_STATUSES = (STATUS_DONE, STATUS_CANCELLED)

FIELDS = model_fields(_O, readonly=("ngs_run_id", "source_library_order_id", "synthesis_order_id"))
CUSTOM_FIELDS = frozenset({"sample_library", "project_level", "status", "target_codes", "mouse_strain"})
BREAK_FIELDS = frozenset({"immunogen", "screening_antigen", "screening_goal", "remark", "load_note"})
HANDOFF_LOCKED_FIELDS = (
    "sample_library",
    "synthesis_code",
    "target_name",
    "target_codes",
    "mouse_strain",
    "pm",
    "project_code",
    "study_type",
)
MAX_BATCH_SAVE_ITEMS = 500

TypeScope = frozenset[str] | None

EXPORT_COLUMNS = (
    ("测序单号", "ngs_run_id"),
    ("样品库", "sample_library"),
    ("状态", "status"),
    ("来源文库工单", "source_library_order_id"),
    ("建库编号", "library_code"),
    ("靶点", "target_name"),
    ("靶点编号", "target_codes"),
    ("项目编号", "project_code"),
    ("项目级别", "project_level"),
    ("课题类型", "study_type"),
    ("PM", "pm"),
    ("小鼠品系", "mouse_strain"),
    ("标签形式", "antigen_tag"),
    ("具体免疫原", "immunogen"),
    ("细胞数量", "cell_count"),
    ("建库测序核对", "library_checked"),
    ("上库备注", "load_note"),
    ("建库上机日期", "library_instrument_on"),
    ("测序上机日期", "sequencing_date"),
    ("仪器号", "instrument_no"),
    ("解离液", "dissociation_buffer"),
    ("筛选抗原", "screening_antigen"),
    ("批次号", "batch_name"),
    ("送合成转码", "synthesis_code"),
    ("合成与验证单", "synthesis_order_id"),
    ("RNA冻存位置", "rna_location"),
    ("cDNA冻存位置", "cdna_location"),
    ("库冻存位置", "library_location"),
    ("样品来源", "sample_source"),
    ("筛选目标", "screening_goal"),
    ("片段大小", "fragment_size"),
    ("barcode", "barcode"),
    ("是否已测序", "sequenced"),
    ("负责人", "owner"),
    ("备注", "remark"),
)


def generate_run_id() -> str:
    suffix = "".join(secrets.choice(ORDER_ID_ALPHABET) for _ in range(ORDER_ID_RANDOM_LEN))
    return f"{ORDER_ID_PREFIX}{now_local().strftime('%y%m%d')}-{suffix}"


def _next_run_id(db: Session) -> str:
    for _ in range(ORDER_ID_MAX_ATTEMPTS):
        candidate = generate_run_id()
        if not db.scalar(select(_O.id).where(_O.ngs_run_id == candidate)):
            return candidate
    raise ValueError("无法分配测序单号")


def _sample_library_of(library: MolecularLibraryOrder) -> str:
    if library.build_type in PHAGE_BUILDS or library.sample_type == SAMPLE_PHAGE:
        return SAMPLE_PHAGE_LIB
    return LIBRARY_SAMPLE.get(library.sample_type or "", SAMPLE_RND)


def _apply_status(row: _O, data: dict[str, Any]) -> None:
    chosen = normalize_choice(data.get("status"), STATUS_OPTIONS, "状态") if "status" in data else None
    if row.synthesis_order_id:
        if chosen in TERMINAL_STATUSES:
            row.status = chosen
            return
        if chosen in (None, STATUS_SENT):
            if row.status not in TERMINAL_STATUSES:
                row.status = STATUS_SENT
            return
        raise ValueError("已送合成后只能改为已完成或已取消")
    if chosen == STATUS_SENT:
        raise ValueError("请使用送合成，不要直接改成已送合成")
    if chosen:
        row.status = chosen
        return
    if row.status in TERMINAL_STATUSES:
        return
    if row.sequencing_date and row.status in (None, "", STATUS_WAIT):
        row.status = STATUS_RUN
    elif not row.sequencing_date and row.status == STATUS_RUN and "sequencing_date" in data:
        row.status = STATUS_WAIT
    elif not row.status:
        row.status = STATUS_WAIT


def _apply_fields(row: _O, data: dict[str, Any]) -> None:
    before = {field: getattr(row, field) for field in HANDOFF_LOCKED_FIELDS}
    if "sample_library" in data:
        row.sample_library = str(normalize_choice(data.get("sample_library"), SAMPLE_LIBRARIES, "样品库"))
    if "project_level" in data:
        row.project_level = normalize_choice(data.get("project_level"), PROJECT_LEVELS, "项目级别", nullable=True)
    if "target_codes" in data:
        row.target_codes = normalize_target_codes(data.get("target_codes"))
    if "mouse_strain" in data:
        row.mouse_strain = clean_text(FIELDS["mouse_strain"], join_tokens(data.get("mouse_strain"), MOUSE_STRAIN_OPTIONS))
    for field, spec in FIELDS.items():
        if field in data and field not in CUSTOM_FIELDS:
            setattr(row, field, clean_field(spec, data[field], keep_breaks=field in BREAK_FIELDS))
    _apply_status(row, data)
    if row.synthesis_order_id:
        changed = [FIELDS[field].label for field in HANDOFF_LOCKED_FIELDS if getattr(row, field) != before[field]]
        if changed:
            raise ValueError(f"已交接到合成与验证，不能再改{'、'.join(changed)}")


def serialize_rows(_db: Session, rows: list[_O]) -> list[dict[str, Any]]:
    return [row.to_dict() for row in rows]


def load_run(db: Session, row_id: int, *, lock: bool = False) -> _O:
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
    ngs_run_id=HeaderColumn(_O.ngs_run_id),
    source_library_order_id=HeaderColumn(_O.source_library_order_id),
    synthesis_order_id=HeaderColumn(_O.synthesis_order_id),
    sample_library=HeaderColumn(_O.sample_library, order=SAMPLE_LIBRARIES),
    project_level=HeaderColumn(_O.project_level, order=PROJECT_LEVELS),
    status=HeaderColumn(_O.status, order=STATUS_OPTIONS),
    target_name=target_column(_O.target_name, _O.target_codes),
    mouse_strain=csv_column(_O.mouse_strain, MOUSE_STRAIN_OPTIONS),
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
        ("ngs_run_id", _O.ngs_run_id, True, "测序单号"),
        ("library_code", _O.library_code, False, "建库编号"),
        ("synthesis_code", _O.synthesis_code, False, "送合成转码"),
        ("project_code", _O.project_code, False, "项目编号"),
        ("source_library_order_id", _O.source_library_order_id, True, "来源文库工单号"),
        ("instrument_no", _O.instrument_no, False, "仪器号"),
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
        ("sample_library", _O.sample_library),
        ("project_level", _O.project_level),
        ("status", _O.status),
        ("owner", _O.owner),
    ):
        clause = match_any(column, data.get(key))
        if clause is not None:
            filters.append(clause)
    strains = filter_terms(data.get("mouse_strain"))
    if strains:
        filters.append(or_(*(csv_token_clause(_O.mouse_strain, term) for term in strains)))
    start = parse_date(data.get("sequencing_date_start")) if data.get("sequencing_date_start") else None
    end = parse_date(data.get("sequencing_date_end")) if data.get("sequencing_date_end") else None
    if start:
        filters.append(_O.sequencing_date >= start)
    if end:
        filters.append(_O.sequencing_date <= end)
    filters.extend(header_filter_clauses(db, HEADER_COLUMNS, data.get("field_filters"), except_field=header_except))
    return filters


def _stats(db: Session, payload: dict[str, Any]) -> dict[str, int]:
    filtered = without_header_fields({key: value for key, value in payload.items() if key != "status"}, {"status"})
    counts = dict(
        db.execute(select(_O.status, func.count()).where(*_filters(filtered, db=db)).group_by(_O.status)).all()
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
        "sample_libraries": list(SAMPLE_LIBRARIES),
        "project_levels": list(PROJECT_LEVELS),
        "statuses": list(STATUS_OPTIONS),
        "mouse_strains": list(MOUSE_STRAIN_OPTIONS),
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
        raise ValueError("测序单 ID 不正确")
    if row_id is None:
        row = _O(
            ngs_run_id=_next_run_id(db),
            sample_library=str(normalize_choice(payload.get("sample_library"), SAMPLE_LIBRARIES, "样品库")),
            status=STATUS_WAIT,
            target_codes=[],
            created_by=(created_by or "").strip() or None,
        )
        db.add(row)
    else:
        row = load_run(db, row_id, lock=True)
        check_expected(row.to_dict(), expected, fields=FIELDS)
    _apply_fields(row, payload)
    db.commit()
    db.refresh(row)
    return serialize_rows(db, [row])[0]


def batch_save(db: Session, items: list[dict[str, Any]]) -> dict[str, Any]:
    parsed_items, row_ids = parse_batch_items(
        items,
        invalid_id_message="测序单 ID 不正确",
        duplicate_message="同一测序单不能重复提交",
        require_id=True,
        allow_empty=False,
        empty_message="没有需要保存的测序单",
        max_items=MAX_BATCH_SAVE_ITEMS,
        too_many_message=f"单次最多保存 {MAX_BATCH_SAVE_ITEMS} 条测序单",
    )
    rows_by_id = lock_rows_by_id(db, _O, row_ids, missing_message=MISSING_ROW)
    payloads = []
    for item in parsed_items:
        payload = dict(item)
        expected = payload.pop("_expected", None)
        row = rows_by_id[int(parse_row_id(payload.get("id")))]
        check_expected(row.to_dict(), expected, fields=FIELDS)
        payloads.append((row, payload))
    for row, payload in payloads:
        try:
            _apply_fields(row, payload)
        except ValueError as exc:
            raise ValueError(f"{row.ngs_run_id}：{exc}") from exc
    db.commit()
    rows = [row for row, _payload in payloads]
    for row in rows:
        db.refresh(row)
    return {"items": serialize_rows(db, rows)}


def delete_run(db: Session, row_id: int) -> dict[str, int]:
    row = load_run(db, row_id, lock=True)
    if row.synthesis_order_id:
        raise ValueError(f"已交接到合成与验证 {row.synthesis_order_id}，不能删除")
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
    """测序类文库工单交接为一条 NGS 测序单。同一文库可以多次交接。"""
    library = db.get(MolecularLibraryOrder, library_row_id)
    if library is None or (scope is not None and library.build_type not in scope):
        raise NotFoundError(MISSING_LIBRARY)
    if library.build_type == BUILD_PLATE:
        raise ValueError("单细胞孔板请交接到转染与表达")
    if library.build_type not in NGS_BUILD_TYPES:
        raise ValueError("这种建库类型不能交接到 NGS测序")
    if library.status == LIBRARY_CANCELLED:
        raise ValueError("已取消的文库工单不能交接")
    instrument_on = library.instrument_on.isoformat() if library.instrument_on else None
    source = SAMPLE_SOURCE_LABELS.get(library.sample_source or "", library.sample_source)
    cell_count = str(library.positive_cell_count or "").strip()[:64] or None
    row = _O(
        ngs_run_id=_next_run_id(db),
        sample_library=_sample_library_of(library),
        status=STATUS_WAIT,
        source_library_order_id=library.library_order_id,
        library_code=library.library_code,
        project_code=library.source_project_code,
        study_type=library.study_type,
        target_name=library.target_name,
        target_codes=list(library.target_codes or []),
        pm=library.pm,
        mouse_strain=library.mouse_strain,
        cell_count=cell_count,
        library_instrument_on=instrument_on,
        sample_source=(str(source).strip()[:32] or None) if source else None,
        screening_goal=library.project_goal,
        created_by=(created_by or "").strip() or None,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return serialize_rows(db, [row])[0]


def handoff_to_synthesis(db: Session, row_id: int, created_by: str | None = None) -> dict[str, Any]:
    """按送合成转码新建一条常规合成、合成到货的合成与验证单。"""
    lock_queue(db, DiscoverySynthesisOrder)
    row = load_run(db, row_id, lock=True)
    if row.status == STATUS_CANCELLED:
        raise ValueError("已取消的测序单不能送合成")
    if row.synthesis_order_id:
        raise ValueError(f"已交接到合成与验证 {row.synthesis_order_id}")
    if not (row.synthesis_code or "").strip():
        raise ValueError("请先填写送合成转码")
    if not (row.target_name or "").strip() and not row.target_codes:
        raise ValueError("请先填写靶点")
    if not (row.mouse_strain or "").strip():
        raise ValueError("请先填写小鼠品系")
    if not (row.pm or "").strip():
        raise ValueError("请先填写 PM")
    note = f"由 NGS {row.ngs_run_id} 送合成"
    if (row.remark or "").strip():
        note = f"{note}；{row.remark.strip()}"
    saved = synthesis_service.save(
        db,
        {
            "order_kind": ORDER_KIND_NORMAL,
            "supply_mode": SUPPLY_MODE_ARRIVAL,
            "synthesis_code": row.synthesis_code,
            "project_code": row.project_code,
            "study_type": row.study_type,
            "pm": row.pm,
            "target_name": row.target_name,
            "target_codes": list(row.target_codes or []),
            "mouse_strain": row.mouse_strain,
            "batch_label": row.batch_name,
            "remark": note[:1000],
        },
        created_by,
        commit=False,
        lock_queue=False,
        require_fields=True,
    )
    row.synthesis_order_id = saved["synthesis_order_id"]
    row.status = STATUS_SENT
    db.commit()
    db.refresh(row)
    return {"synthesis_order_id": saved["synthesis_order_id"], "order": serialize_rows(db, [row])[0]}


def export_list_workbook(db: Session, data: dict[str, Any]):
    from utils.excel import build_list_workbook, cell_text

    payload = data or {}
    rows = db.scalars(select(_O).where(*_filters(payload, db=db)).order_by(*_list_order(payload))).all()
    table_rows = []
    for item in serialize_rows(db, list(rows)):
        item["target_codes"] = cell_text(item["target_codes"], "、")
        table_rows.append([cell_text(item.get(key)) for _, key in EXPORT_COLUMNS])
    return build_list_workbook(
        sheet_title="NGS测序",
        filename_prefix="NGS测序",
        headers=[label for label, _ in EXPORT_COLUMNS],
        rows=table_rows,
    )
