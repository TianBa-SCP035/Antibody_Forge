from datetime import date, datetime
from io import BytesIO
from pathlib import Path
import hashlib
import math
import re
import secrets
import shutil
import string
from typing import Any, NamedTuple

from fastapi import UploadFile
from PIL import Image
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from core.config import get_settings
from utils.filter_values import (
    catalog_names_for_pairs,
    filter_terms,
    match_any,
    recorded_target_clause,
    target_select_options,
)
from integrations import drm_service
from models.discovery import DiscoveryWorkbench
from models.molecular_cell import (
    LIBRARY_PRIMER_REFERENCE_FIELDS,
    MolecularLibraryOrder,
    MolecularLibraryResultFile,
    MolecularLibraryResultLink,
    MolecularLibraryResultPackage,
    MolecularPrimerIndexCatalog,
)
from modules.discovery.workbench.constants import (
    PLAN_STATUS_PLANNING as DISCOVERY_PLANNING,
    PLAN_STATUS_WAIT_BOOST as DISCOVERY_WAIT_BOOST,
    PLAN_STATUS_WAIT_HARVEST as DISCOVERY_WAIT_HARVEST,
    PLAN_STATUS_WAIT_LIBRARY as DISCOVERY_WAIT_LIBRARY,
    PLAN_STATUS_WAIT_PHAGE as DISCOVERY_WAIT_PHAGE,
    PLAN_STATUS_WAIT_SEQ as DISCOVERY_WAIT_SEQ,
    SCREENING_METHOD_BEACON,
    SCREENING_METHOD_DAPU,
    SCREENING_METHOD_PHAGE,
    TERMINAL_STATUSES as DISCOVERY_TERMINAL_STATUSES,
    MOUSE_STRAIN_OPTIONS,
)
from modules.molecular_cell.library_orders.result_upload import (
    ROLE_GEL,
    ROLE_READ,
    ARM_STATUSES,
    MATCHED_STATUSES,
    SEQUENCE_NOT_FOUND,
    extension_of,
    IMAGE_EXTENSIONS,
    library_code_stem,
    library_codes_in_name,
    longest_library_code,
    month_directory,
    normalize_relative_path,
    other_directory,
    package_file_role,
    package_name,
    package_signature,
    plan_upload_paths,
    read_direction,
    READ_EXTENSIONS,
    safe_path_part,
    is_short,
    plain_status,
    sequence_check,
    sequence_check_text,
    TRACE_EXTENSIONS,
    loose_file_role,
)
from utils.workbench_queue import DEFAULT_PRIORITY, PRIORITY_ORDER

MISSING_ROW = "文库构建工单不存在"
MISSING_FILE = "结果文件不存在"
MISSING_DISCOVERY = "发现工作台记录不存在"
MISSING_CATALOG = "引物或Index字典记录不存在"

LIBRARY_ID_PREFIX = "LIB"
LIBRARY_ID_RANDOM_LEN = 6
LIBRARY_ID_MAX_ATTEMPTS = 20
LIBRARY_ID_ALPHABET = string.ascii_uppercase + string.digits

STATUS_PENDING = "待处理"
STATUS_IN_PROGRESS = "建库中"
STATUS_WAIT_QC = "待质检"
STATUS_QC_HOLD = "质检待确认"
STATUS_QC_PASS = "质检通过"
STATUS_DONE = "已完成"
STATUS_QC_FAIL = "质检不通过"
STATUS_CANCELLED = "已取消"
STATUS_OPTIONS = (
    STATUS_PENDING,
    STATUS_IN_PROGRESS,
    STATUS_WAIT_QC,
    STATUS_QC_HOLD,
    STATUS_QC_PASS,
    STATUS_DONE,
    STATUS_QC_FAIL,
    STATUS_CANCELLED,
)
QC_PASS = "通过"
QC_FAIL = "不通过"

BUILD_PLATE = "plate_single_cell"
BUILD_POOLED_BCR = "pooled_bcr"
BUILD_POOLED_BARCODE = "pooled_barcode"
BUILD_PLASMA_NGS = "plasma_ngs"
BUILD_PHAGE_DISPLAY = "phage_display"
BUILD_PHAGE_NGS = "phage_ngs"
BUILD_PERIPHERAL_BLOOD = "peripheral_blood_bcr"
BUILD_TYPE_ORDER = (
    BUILD_PLATE,
    BUILD_POOLED_BCR,
    BUILD_POOLED_BARCODE,
    BUILD_PERIPHERAL_BLOOD,
    BUILD_PLASMA_NGS,
    BUILD_PHAGE_DISPLAY,
    BUILD_PHAGE_NGS,
)
BUILD_TYPE_LABELS = {
    BUILD_PLATE: "单细胞孔板",
    BUILD_POOLED_BCR: "混管 H/K/L",
    BUILD_POOLED_BARCODE: "混管 Barcode",
    BUILD_PLASMA_NGS: "浆细胞 NGS",
    BUILD_PHAGE_DISPLAY: "噬菌体展示",
    BUILD_PHAGE_NGS: "噬菌体 NGS",
    BUILD_PERIPHERAL_BLOOD: "外周血 BCR",
}

SOURCE_BEACON = "beacon"
SOURCE_DAPU_PLATE = "dapu_plate"
SOURCE_BEACON_DAPU = "beacon_dapu"
SOURCE_DAPU_TUBE = "dapu_tube"
SOURCE_DIRECT = "direct"
SOURCE_PHAGE_DISPLAY = "phage_display"
SOURCE_PHAGE_PANNING = "phage_panning"
SOURCE_RETRO_BLOOD = "retro_orbital_blood"
SOURCE_OTHER_BLOOD = "other_blood"
SOURCE_SPLEEN = "spleen_grind"
SAMPLE_SOURCE_LABELS = {
    SOURCE_BEACON: "Beacon",
    SOURCE_DAPU_PLATE: "达普打板",
    SOURCE_BEACON_DAPU: "Beacon+达普打板",
    SOURCE_DAPU_TUBE: "达普打管",
    SOURCE_DIRECT: "细胞/核酸",
    SOURCE_PHAGE_DISPLAY: "噬菌体展示产物",
    SOURCE_PHAGE_PANNING: "噬菌体筛选产物",
    SOURCE_RETRO_BLOOD: "眼眶血",
    SOURCE_OTHER_BLOOD: "其他外周血",
    SOURCE_SPLEEN: "脾脏研磨",
}

SAMPLE_NANO = "nano"
SAMPLE_LITE = "lite"
SAMPLE_RNVM_BLOOD = "rnvm_blood"
SAMPLE_PHAGE = "phage"
SAMPLE_TYPE_LABELS = {
    SAMPLE_NANO: "Nano",
    SAMPLE_LITE: "Lite",
    SAMPLE_RNVM_BLOOD: "RNVM眼眶血",
    SAMPLE_PHAGE: "噬菌体",
}
AUTO_SAMPLE_TYPES = {
    "RL": SAMPLE_LITE,
    "RLB/C": SAMPLE_LITE,
    "RLSJL": SAMPLE_LITE,
    "RLKO": SAMPLE_LITE,
    "RLCKO": SAMPLE_LITE,
    "RLDF": SAMPLE_LITE,
    "RN": SAMPLE_NANO,
    "RNKO": SAMPLE_NANO,
    "RNVR": SAMPLE_NANO,
    "RNVM": SAMPLE_NANO,
    "RNVMKO": SAMPLE_NANO,
}


def _mouse_strain_tokens(value: Any) -> list[str]:
    if value is None:
        return []
    raw = value if isinstance(value, (list, tuple)) else re.split(r"[,，、+]", str(value))
    tokens: list[str] = []
    seen: set[str] = set()
    for item in raw:
        token = str(item or "").strip()
        if not token or token in seen:
            continue
        seen.add(token)
        tokens.append(token)
    return tokens


def _normalize_mouse_strain(value: Any) -> str | None:
    tokens = _mouse_strain_tokens(value)
    if not tokens:
        return None
    known = set(MOUSE_STRAIN_OPTIONS)
    ordered = [item for item in MOUSE_STRAIN_OPTIONS if item in tokens]
    extras = [item for item in tokens if item not in known]
    kept: list[str] = []
    for item in [*ordered, *extras]:
        nxt = "、".join([*kept, item])
        if len(nxt) > 128:
            break
        kept.append(item)
    return "、".join(kept) or None


def _auto_sample_type(mouse_strain: Any) -> str | None:
    text = _normalize_mouse_strain(mouse_strain)
    if not text:
        return None
    return AUTO_SAMPLE_TYPES.get(text.split("、", 1)[0])


PHAGE_EXPERIMENT_TYPES = ("抗体发现", "亲和力改造")

INDEX_NONE = "none"
INDEX_I7 = "single_i7"
INDEX_I5 = "single_i5"
INDEX_DUAL = "dual"
INDEX_MODE_LABELS = {
    INDEX_NONE: "不加 Barcode",
    INDEX_I7: "i7",
    INDEX_I5: "i5",
    INDEX_DUAL: "双端 i7 + i5",
}
QC_RESULT_OPTIONS = ("待判定", "通过", "不通过")
CELL_TYPE_OPTIONS = ("全细胞", "浆细胞", "流穿液")
DEFAULT_PLASMA_CELL_TYPE = "浆细胞"
TARGET_FORM_OPTIONS = ("多穿", "分泌", "I型", "II型")
PROFILE_SOURCES = {
    BUILD_PLATE: (SOURCE_BEACON, SOURCE_DAPU_PLATE, SOURCE_BEACON_DAPU),
    BUILD_POOLED_BCR: (SOURCE_DAPU_TUBE,),
    BUILD_POOLED_BARCODE: (SOURCE_DAPU_TUBE,),
    BUILD_PLASMA_NGS: (SOURCE_SPLEEN,),
    BUILD_PHAGE_DISPLAY: (SOURCE_DIRECT,),
    BUILD_PHAGE_NGS: (SOURCE_PHAGE_DISPLAY, SOURCE_PHAGE_PANNING),
    BUILD_PERIPHERAL_BLOOD: (SOURCE_RETRO_BLOOD, SOURCE_OTHER_BLOOD),
}
PLASMA_SAMPLE_TYPES = (SAMPLE_NANO, SAMPLE_LITE)

INDEX_FIELDS = {
    "index_mode",
    "i7_catalog_id",
    "i7_name",
    "i7_sequence",
    "i5_catalog_id",
    "i5_name",
    "i5_sequence",
}
PLATE_FIELDS = {
    "instrument_on",
    "positive_cell_count",
    "plate_nos",
    "cdna_location",
}
POOLED_FIELDS = {
    "instrument_on",
    "positive_cell_count",
    "rna_location",
    "cdna_location",
    "library_location",
    "cdna_concentration",
    "library_concentration",
    "fragment_size_bp",
    "h_forward_primer_id",
    "h_forward_primer_name",
    "h_reverse_primer_id",
    "h_reverse_primer_name",
    "h_primer_concentration",
    "k_forward_primer_id",
    "k_forward_primer_name",
    "k_reverse_primer_id",
    "k_reverse_primer_name",
    "k_primer_concentration",
    "l_forward_primer_id",
    "l_forward_primer_name",
    "l_reverse_primer_id",
    "l_reverse_primer_name",
    "l_primer_concentration",
}
POOLED_BARCODE_FIELDS = {
    "instrument_on",
    "positive_cell_count",
    "rna_location",
    "cdna_location",
    "library_location",
    "cdna_concentration",
    "library_concentration",
    "fragment_size_bp",
} | INDEX_FIELDS
PLASMA_FIELDS = {
    "instrument_on",
    "positive_cell_count",
    "cell_type",
    "rna_location",
    "cdna_location",
    "library_location",
    "library_concentration",
    "fragment_size_bp",
}
PHAGE_DISPLAY_FIELDS = {
    "source_experiment_type",
    "project_goal",
    "instrument_on",
    "cell_type",
    "library_batch_no",
    "target_forms",
    "rna_location",
    "cdna_location",
    "library_location",
    "initial_library_size",
    "effective_library_size",
}
PHAGE_NGS_FIELDS = {
    "source_experiment_type",
    "project_goal",
    "library_batch_no",
    "library_location",
    "library_concentration",
    "fragment_size_bp",
} | INDEX_FIELDS
PERIPHERAL_FIELDS = {
    "blood_collected_on",
    "immunization_stage",
    "positive_cell_count",
    "rna_location",
    "cdna_location",
    "library_location",
    "cdna_concentration",
    "library_concentration",
    "fragment_size_bp",
} | INDEX_FIELDS
PROFILE_FIELDS = {
    BUILD_PLATE: PLATE_FIELDS,
    BUILD_POOLED_BCR: POOLED_FIELDS,
    BUILD_POOLED_BARCODE: POOLED_BARCODE_FIELDS,
    BUILD_PLASMA_NGS: PLASMA_FIELDS,
    BUILD_PHAGE_DISPLAY: PHAGE_DISPLAY_FIELDS,
    BUILD_PHAGE_NGS: PHAGE_NGS_FIELDS,
    BUILD_PERIPHERAL_BLOOD: PERIPHERAL_FIELDS,
}
PROFILE_SCOPED_FIELDS = set().union(*PROFILE_FIELDS.values())

STRING_FIELDS = {
    "library_code": 64,
    "source_project_code": 64,
    "study_type": 64,
    "project_goal": 1000,
    "target_name": 128,
    "pm": 64,
    "mouse_strain": 128,
    "positive_cell_count": 64,
    "fragment_size_bp": 64,
    "cell_type": 64,
    "notebook_no": 64,
    "immunization_stage": 64,
    "library_batch_no": 64,
    "owner": 64,
    "rna_location": 255,
    "cdna_location": 255,
    "library_location": 255,
    "initial_library_size": 64,
    "effective_library_size": 64,
    "cdna_concentration": 64,
    "library_concentration": 64,
    "h_primer_concentration": 64,
    "k_primer_concentration": 64,
    "l_primer_concentration": 64,
    "h_forward_primer_name": 128,
    "h_reverse_primer_name": 128,
    "k_forward_primer_name": 128,
    "k_reverse_primer_name": 128,
    "l_forward_primer_name": 128,
    "l_reverse_primer_name": 128,
    "i7_name": 128,
    "i7_sequence": 64,
    "i5_name": 128,
    "i5_sequence": 64,
    "qc_owner": 64,
    "qc_note": 1000,
    "remark": 1000,
}
DATE_FIELDS = (
    "received_on",
    "instrument_on",
    "blood_collected_on",
    "qc_on",
    "started_at",
    "finished_at",
)
INSTRUMENT_DATE_BUILDS = frozenset({
    BUILD_PLATE,
    BUILD_POOLED_BCR,
    BUILD_POOLED_BARCODE,
    BUILD_PHAGE_DISPLAY,
})
POSITIVE_CELL_COUNT_BUILDS = frozenset({
    BUILD_PLATE,
    BUILD_POOLED_BCR,
    BUILD_POOLED_BARCODE,
    BUILD_PLASMA_NGS,
    BUILD_PERIPHERAL_BLOOD,
})
FILLS_INSTRUMENT_ON = INSTRUMENT_DATE_BUILDS | {BUILD_PLASMA_NGS}
CELL_TYPE_CHOICE_BUILDS = frozenset({BUILD_PLASMA_NGS, BUILD_PHAGE_DISPLAY})

FILE_KIND_PCR_QC = "PCR检测报告"
FILE_KIND_GEL = "胶图"
FILE_KIND_PRIMER_QC = "引物质检文件"
FILE_KIND_OTHER = "其他"
MAX_FILE_BYTES = 50 * 1024 * 1024
MAX_BATCH_BYTES = 500 * 1024 * 1024
MAX_UPLOAD_FILES = 400
GEL_EXTENSIONS = IMAGE_EXTENSIONS
PRIMER_QC_EXTENSIONS = READ_EXTENSIONS | {".clc", ".fasta", ".fa"}
INLINE_PREVIEW_EXTENSIONS = GEL_EXTENSIONS | {
    ".seq",
    ".txt",
    ".fa",
    ".fasta",
    ".md",
    ".log",
    ".xls",
    ".xlsx",
    ".csv",
    ".pdf",
    ".docx",
    ".mp4",
    ".webm",
    ".ogg",
    ".ogv",
    ".mov",
}
SEQUENCE_PATTERN = re.compile(r"^[ACGTRYSWKMBDHVN]+$", re.IGNORECASE)


def _today_stamp(now: datetime | None = None) -> str:
    return (now or datetime.now()).strftime("%y%m%d")


def generate_library_order_id(now: datetime | None = None) -> str:
    suffix = "".join(secrets.choice(LIBRARY_ID_ALPHABET) for _ in range(LIBRARY_ID_RANDOM_LEN))
    return f"{LIBRARY_ID_PREFIX}-{_today_stamp(now)}-{suffix}"


def _next_library_order_id(db: Session) -> str:
    for _ in range(LIBRARY_ID_MAX_ATTEMPTS):
        candidate = generate_library_order_id()
        exists = db.scalar(
            select(MolecularLibraryOrder.id).where(
                MolecularLibraryOrder.library_order_id == candidate
            )
        )
        if not exists:
            return candidate
    raise ValueError("无法分配文库工单号")


def _normalize_text(value: Any, max_len: int) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if len(text) > max_len:
        raise ValueError(f"字段长度不能超过 {max_len}")
    return text


def _normalize_library_code(value: Any) -> str | None:
    text = _normalize_text(value, STRING_FIELDS["library_code"])
    return text.upper() if text else None


def _normalize_date(value: Any) -> date | None:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip().replace("T", " ")
    matched = re.fullmatch(r"(\d{4}-\d{2}-\d{2})(?: \d{2}:\d{2}(?::\d{2})?)?", text)
    if not matched:
        raise ValueError("日期必须是 YYYY-MM-DD")
    try:
        return datetime.strptime(matched.group(1), "%Y-%m-%d").date()
    except ValueError as exc:
        raise ValueError("日期必须是 YYYY-MM-DD") from exc


def _normalize_string_list(value: Any, label: str) -> list[str]:
    if value in (None, "", []):
        return []
    if isinstance(value, str):
        values = re.split(r"[,，、]", value)
    elif isinstance(value, list):
        values = value
    else:
        raise ValueError(f"{label}必须是数组")
    result: list[str] = []
    for item in values:
        text = str(item).strip()
        if text and text not in result:
            result.append(text)
    return result


def _normalize_sequence(value: Any, max_len: int = 64) -> str | None:
    text = _normalize_text(value, max_len)
    if not text:
        return None
    text = re.sub(r"\s+", "", text).upper()
    if not SEQUENCE_PATTERN.fullmatch(text):
        raise ValueError("Barcode序列只能包含IUPAC碱基字符")
    return text


def _normalize_target_form(value: Any) -> str | None:
    if isinstance(value, list):
        items = [str(item or "").strip() for item in value if str(item or "").strip()]
        if len(items) > 1:
            raise ValueError("靶点形式只能选一个")
        value = items[0] if items else None
    return _normalize_choice(value, TARGET_FORM_OPTIONS, "靶点形式", nullable=True)


def _normalize_choice(value: Any, options, label: str, *, nullable: bool = False) -> str | None:
    text = str(value or "").strip()
    if nullable and not text:
        return None
    if text not in options:
        raise ValueError(f"{label}不在允许的选项中")
    return text


def _normalize_build_type(value: Any) -> str:
    result = _normalize_choice(value, BUILD_TYPE_ORDER, "建库类型")
    return str(result)


def _normalize_status(value: Any) -> str:
    result = _normalize_choice(value, STATUS_OPTIONS, "状态")
    return str(result)


def _normalize_priority(value: Any) -> str:
    text = str(value or "").strip()
    if text not in PRIORITY_ORDER:
        raise ValueError("优先级不在允许的选项中")
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
        limit = int(data.get("limit", 20) or 20)
    except (TypeError, ValueError):
        page, limit = 1, 20
    return max(page, 1), min(max(limit, 1), 500)


def _current_status(row: MolecularLibraryOrder) -> str:
    return str(row.status or "").strip() or STATUS_PENDING


def _clear_inapplicable_fields(row: MolecularLibraryOrder, build_type: str) -> None:
    allowed = PROFILE_FIELDS[build_type]
    for field in PROFILE_SCOPED_FIELDS - allowed:
        if field == "plate_nos":
            setattr(row, field, [])
        else:
            setattr(row, field, None)


def _apply_catalog_reference(
    db: Session,
    row: MolecularLibraryOrder,
    data: dict[str, Any],
    id_field: str,
    name_field: str,
    sequence_field: str | None = None,
) -> None:
    if id_field not in data:
        if name_field not in data:
            return
        name = str(data.get(name_field) or "").strip()
        if not name:
            setattr(row, id_field, None)
            setattr(row, name_field, None)
            if sequence_field:
                setattr(row, sequence_field, None)
            return
        catalog = db.scalar(
            select(MolecularPrimerIndexCatalog).where(
                MolecularPrimerIndexCatalog.name == name,
                MolecularPrimerIndexCatalog.active.is_(True),
            )
        )
        if catalog is not None:
            setattr(row, id_field, catalog.id)
            setattr(row, name_field, catalog.name)
            if sequence_field:
                setattr(row, sequence_field, catalog.short_sequence)
            return
        setattr(row, id_field, None)
        if sequence_field and sequence_field not in data:
            setattr(row, sequence_field, None)
        return
    catalog_id = _parse_row_id(data.get(id_field))
    if data.get(id_field) not in (None, "") and catalog_id is None:
        raise ValueError("引物或Index字典ID不正确")
    setattr(row, id_field, catalog_id)
    if catalog_id is None:
        if name_field not in data:
            setattr(row, name_field, None)
        if sequence_field and sequence_field not in data:
            setattr(row, sequence_field, None)
        return
    catalog = db.get(MolecularPrimerIndexCatalog, catalog_id)
    if not catalog or not catalog.active:
        raise ValueError(MISSING_CATALOG)
    setattr(row, name_field, catalog.name)
    if sequence_field:
        setattr(row, sequence_field, catalog.short_sequence)


def _apply_fields(db: Session, row: MolecularLibraryOrder, data: dict[str, Any]) -> None:
    previous_type = str(row.build_type or "").strip()
    previous_status = _current_status(row)

    if "build_type" in data:
        next_type = _normalize_build_type(data.get("build_type"))
        if next_type != previous_type:
            if previous_status != STATUS_PENDING:
                raise ValueError("仅待处理状态可改建库类型")
            row.build_type = next_type
            _clear_inapplicable_fields(row, next_type)
            if row.sample_source not in PROFILE_SOURCES[next_type]:
                row.sample_source = None

    if "status" in data:
        row.status = _normalize_status(data.get("status"))

    if "priority" in data:
        row.priority = _normalize_priority(data.get("priority"))
    if "library_code" in data:
        row.library_code = _normalize_library_code(data.get("library_code"))
    if "target_codes" in data:
        row.target_codes = _normalize_string_list(data.get("target_codes"), "靶点编号")
    if "target_forms" in data:
        row.target_forms = _normalize_target_form(data.get("target_forms"))
    if "plate_nos" in data:
        row.plate_nos = _normalize_string_list(data.get("plate_nos"), "板号")

    for field, max_len in STRING_FIELDS.items():
        if field == "library_code" or field not in data:
            continue
        if field == "mouse_strain":
            setattr(row, field, _normalize_mouse_strain(data.get(field)))
        elif field in {"i7_sequence", "i5_sequence"}:
            setattr(row, field, _normalize_sequence(data.get(field), max_len))
        else:
            setattr(row, field, _normalize_text(data.get(field), max_len))
    if "sample_type" in data:
        row.sample_type = _normalize_choice(
            data.get("sample_type"),
            SAMPLE_TYPE_LABELS,
            "样品类型",
            nullable=True,
        )
    elif "mouse_strain" in data:
        auto_type = _auto_sample_type(row.mouse_strain)
        if auto_type:
            row.sample_type = auto_type
    for field in DATE_FIELDS:
        if field in data:
            setattr(row, field, _normalize_date(data.get(field)))
    if "sample_source" in data:
        row.sample_source = _normalize_choice(
            data.get("sample_source"),
            SAMPLE_SOURCE_LABELS,
            "样品来源",
            nullable=True,
        )
    if "source_experiment_type" in data:
        row.source_experiment_type = _normalize_choice(
            data.get("source_experiment_type"),
            PHAGE_EXPERIMENT_TYPES,
            "实验类型",
            nullable=True,
        )
    if "index_mode" in data:
        row.index_mode = _normalize_choice(
            data.get("index_mode"),
            INDEX_MODE_LABELS,
            "Barcode方式",
            nullable=True,
        )
    if "qc_result" in data:
        row.qc_result = _normalize_choice(
            data.get("qc_result"), QC_RESULT_OPTIONS, "质检结论", nullable=True
        )
    for id_field, name_field, sequence_field in LIBRARY_PRIMER_REFERENCE_FIELDS:
        _apply_catalog_reference(db, row, data, id_field, name_field, sequence_field)
    _validate_profile(row)
    if row.id and any(field in data for field in _SEQUENCE_RECHECK_FIELDS):
        _recheck_order_sequences(db, row)
    _advance_order_status(
        db,
        row,
        status_chosen="status" in data,
    )
    _stamp_work_dates(row)


def _validate_profile(row: MolecularLibraryOrder) -> None:
    build_type = _normalize_build_type(row.build_type)
    _clear_inapplicable_fields(row, build_type)
    if row.sample_source and row.sample_source not in PROFILE_SOURCES[build_type]:
        raise ValueError("样品来源与建库类型不匹配")
    if build_type == BUILD_PLASMA_NGS and not str(row.cell_type or "").strip():
        row.cell_type = DEFAULT_PLASMA_CELL_TYPE
    if build_type in CELL_TYPE_CHOICE_BUILDS and row.cell_type:
        _normalize_choice(row.cell_type, CELL_TYPE_OPTIONS, "细胞类型")
    if build_type == BUILD_PLASMA_NGS and row.sample_type not in (None, *PLASMA_SAMPLE_TYPES):
        raise ValueError("浆细胞 NGS 的样品类型只能是 Nano 或 Lite")
    mode = row.index_mode
    if mode in (None, INDEX_NONE):
        row.i7_catalog_id = row.i7_name = row.i7_sequence = None
        row.i5_catalog_id = row.i5_name = row.i5_sequence = None
    elif mode == INDEX_I7:
        row.i5_catalog_id = row.i5_name = row.i5_sequence = None
    elif mode == INDEX_I5:
        row.i7_catalog_id = row.i7_name = row.i7_sequence = None


def _text_filled(value: Any) -> bool:
    return bool(str(value or "").strip())


_SEQUENCE_RECHECK_FIELDS = frozenset({
    "build_type",
    "index_mode",
    *(
        field
        for id_field, name_field, sequence_field in LIBRARY_PRIMER_REFERENCE_FIELDS
        for field in (id_field, name_field, sequence_field)
        if field
    ),
})
_HKL_PRIMER_SLOTS = (
    ("hF", "h_forward_primer_id"),
    ("hR", "h_reverse_primer_id"),
    ("kF", "k_forward_primer_id"),
    ("kR", "k_reverse_primer_id"),
    ("lF", "l_forward_primer_id"),
    ("lR", "l_reverse_primer_id"),
)
_BARCODE_BUILDS = frozenset({
    BUILD_POOLED_BARCODE,
    BUILD_PHAGE_NGS,
    BUILD_PERIPHERAL_BLOOD,
})


def _configured_primers(db: Session, order: MolecularLibraryOrder) -> dict[str, str]:
    """只收录这份工单真正要核对的引物。不加、或这个方向没填，就不出现。"""
    primers: dict[str, str] = {}
    if order.build_type == BUILD_POOLED_BCR:
        for key, id_field in _HKL_PRIMER_SLOTS:
            catalog_id = getattr(order, id_field, None)
            if not catalog_id:
                continue
            catalog = db.get(MolecularPrimerIndexCatalog, catalog_id)
            sequence = str(getattr(catalog, "short_sequence", "") or "").strip().upper()
            if sequence:
                primers[key] = sequence
        return primers
    if order.build_type not in _BARCODE_BUILDS:
        return primers
    mode = order.index_mode or INDEX_NONE
    if mode in {INDEX_I5, INDEX_DUAL} and _text_filled(order.i5_sequence):
        primers["i5"] = re.sub(r"\s+", "", str(order.i5_sequence).upper())
    if mode in {INDEX_I7, INDEX_DUAL} and _text_filled(order.i7_sequence):
        primers["i7"] = re.sub(r"\s+", "", str(order.i7_sequence).upper())
    return primers


def _final_names(links) -> set[str]:
    return {link.original_name.casefold() for link in links if link.is_final_qc}


def _replaced_by_final(link: MolecularLibraryResultLink, final_names: set[str]) -> bool:
    """同名文件里另有一份标了最终时，这份不再参与质检。"""
    return not link.is_final_qc and link.original_name.casefold() in final_names


class QcFileFacts(NamedTuple):
    has_gel: bool
    has_read: bool
    conflict: bool
    all_matched: bool
    partial: bool
    checks_primers: bool
    arm_only: bool
    short: bool


def _qc_file_facts(db: Session, order: MolecularLibraryOrder) -> QcFileFacts:
    if not order.id:
        return QcFileFacts(False, False, False, False, False, False, False, False)
    links = db.scalars(
        select(MolecularLibraryResultLink).where(
            MolecularLibraryResultLink.order_id == order.id,
        )
    ).all()
    final_names = _final_names(links)
    has_gel = False
    has_read = False
    short = False
    by_target: dict[str, set[str]] = {}
    for link in links:
        if _replaced_by_final(link, final_names):
            continue
        suffix = extension_of(link.original_name)
        if suffix in GEL_EXTENSIONS:
            has_gel = True
        if suffix in READ_EXTENSIONS:
            has_read = True
        if (
            suffix not in TRACE_EXTENSIONS
            and link.sequence_target
            and link.sequence_status
        ):
            by_target.setdefault(link.sequence_target, set()).add(plain_status(link.sequence_status))
            short = short or is_short(link.sequence_status)
    statuses = [by_target.get(target, set()) for target in _configured_primers(db, order)]
    failed = {SEQUENCE_NOT_FOUND, *ARM_STATUSES}
    primer_conflict = any(found & failed for found in statuses)
    all_matched = all(found & MATCHED_STATUSES and not (found & failed) for found in statuses)
    return QcFileFacts(
        has_gel,
        has_read,
        primer_conflict or (short and all_matched),
        all_matched,
        any(found & MATCHED_STATUSES and found & failed for found in statuses),
        bool(statuses),
        any(found & ARM_STATUSES for found in statuses),
        short,
    )


def _advance_order_status(
    db: Session,
    row: MolecularLibraryOrder,
    *,
    status_chosen: bool = False,
) -> None:
    """按当前实验事实辅助刷新；当次手工选择及终态不覆盖。"""
    if row.status == STATUS_CANCELLED:
        return
    if row.qc_result == QC_FAIL:
        row.status = STATUS_QC_FAIL
        return
    if row.qc_result == QC_PASS:
        row.status = STATUS_DONE if _text_filled(row.library_location) else STATUS_QC_PASS
        return
    if status_chosen or row.status in {STATUS_DONE, STATUS_QC_FAIL}:
        return
    facts = _qc_file_facts(db, row)
    if facts.has_read and facts.conflict:
        row.status = STATUS_QC_HOLD
        return
    if facts.has_gel and facts.has_read and facts.all_matched:
        row.status = STATUS_QC_PASS
        return
    if facts.has_gel or facts.has_read:
        row.status = STATUS_WAIT_QC
        return
    if (
        _text_filled(row.rna_location) or _text_filled(row.cdna_location)
    ):
        row.status = STATUS_IN_PROGRESS
        return
    if row.status in {STATUS_WAIT_QC, STATUS_QC_HOLD, STATUS_QC_PASS}:
        row.status = STATUS_PENDING


def _stamp_work_dates(row: MolecularLibraryOrder) -> None:
    """位置填上才记日期，已有日期不改，清空位置也不收回。"""
    today = date.today()
    if row.started_at is None and (
        _text_filled(row.rna_location) or _text_filled(row.cdna_location)
    ):
        row.started_at = today
    if row.finished_at is None and _text_filled(row.library_location):
        row.finished_at = today


def _advance_linked_orders(db: Session, links: list[MolecularLibraryResultLink]) -> None:
    seen: set[int] = set()
    for link in links:
        if link.order_id in seen:
            continue
        seen.add(link.order_id)
        order = db.get(MolecularLibraryOrder, link.order_id)
        if order is not None:
            _advance_order_status(db, order)


def _qc_status_detail(
    status: str,
    *,
    has_gel: bool,
    has_read: bool,
    all_matched: bool,
    partial: bool = False,
    checks_primers: bool = False,
    arm_only: bool = False,
    short: bool = False,
) -> str:
    if status in {STATUS_QC_PASS, STATUS_DONE}:
        return "引物已对上" if checks_primers else ""
    if status == STATUS_QC_HOLD:
        if arm_only and not partial:
            return "引物错误"
        if short and all_matched:
            return "读段过短"
        return "有文件没对上引物" if partial else "引物未对上"
    if status != STATUS_WAIT_QC:
        return ""
    if not checks_primers:
        if has_gel and not has_read:
            return "还没有测序结果"
        if has_read and not has_gel:
            return "还没有胶图"
        return "质检材料还没齐"
    if all_matched and not has_gel:
        return "引物已对上，还没有胶图"
    if has_gel and not has_read:
        return "还没有测序结果"
    if has_read and not all_matched:
        return "引物还没对全"
    return "质检材料还没齐"


def _qc_order_rows(db: Session, order_ids: set[int]) -> list[dict[str, str]]:
    rows = []
    for order_id in order_ids:
        order = db.get(MolecularLibraryOrder, order_id)
        if order is None:
            continue
        code = str(order.library_code or "").strip().upper()
        if not code:
            continue
        facts = _qc_file_facts(db, order)
        status = order.status or ""
        rows.append({
            "id": order.id,
            "library_code": code,
            "status": status,
            "detail": _qc_status_detail(
                status,
                has_gel=facts.has_gel,
                has_read=facts.has_read,
                all_matched=facts.all_matched,
                partial=facts.partial,
                checks_primers=facts.checks_primers,
                arm_only=facts.arm_only,
                short=facts.short,
            ),
        })
    rows.sort(key=lambda row: row["library_code"])
    return rows


def _contains(column, value: Any, *, upper: bool = False):
    terms = [term.upper() if upper else term for term in filter_terms(value)]
    if not terms:
        return None
    clauses = [column.like(f"%{term}%") for term in terms]
    if len(clauses) == 1:
        return clauses[0]
    return or_(*clauses)


def _strain_token_filter(column, value: str):
    return or_(
        column == value,
        column.like(f"{value}、%"),
        column.like(f"%、{value}"),
        column.like(f"%、{value}、%"),
    )


def _append_contains(filters: list, column, value: Any, *, upper: bool = False) -> None:
    clause = _contains(column, value, upper=upper)
    if clause is not None:
        filters.append(clause)


def _append_date_range(filters: list, column, data: dict[str, Any], start_key: str, end_key: str) -> None:
    start = _normalize_date(data.get(start_key)) if data.get(start_key) else None
    end = _normalize_date(data.get(end_key)) if data.get(end_key) else None
    if start:
        filters.append(column >= start)
    if end:
        filters.append(column <= end)


_CODE_SEARCH_SEPARATORS = (",", "\t", "\n", "\r", "，", "、", " ")
_CODE_SEARCH_SPLIT = re.compile(r"[,，、\s]+")
_MAX_CODE_SEARCH = 500


def _append_code_search(
    filters: list,
    column,
    value: Any,
    *,
    upper: bool = False,
    label: str,
) -> None:
    text = str(value or "").strip()
    if not text:
        return
    parts = [part for part in _CODE_SEARCH_SPLIT.split(text) if part]
    if not parts:
        return
    if upper:
        parts = [part.upper() for part in parts]
    if any(separator in text for separator in _CODE_SEARCH_SEPARATORS):
        if len(parts) > _MAX_CODE_SEARCH:
            raise ValueError(f"{label}一次最多搜索 {_MAX_CODE_SEARCH} 个")
        filters.append(column.in_(parts))
        return
    filters.append(column.like(f"%{parts[0]}%"))


def _library_target_pairs():
    return select(MolecularLibraryOrder.target_name, MolecularLibraryOrder.target_codes)


def get_filter_options(db: Session) -> dict[str, Any]:
    pairs = db.execute(_library_target_pairs()).all()
    return {
        "targets": target_select_options(pairs, catalog_names_for_pairs(db, pairs)),
    }


def _apply_list_filters(stmt, data: dict[str, Any], *, db: Session | None = None):
    filters = []
    _append_code_search(
        filters,
        MolecularLibraryOrder.library_code,
        data.get("library_code"),
        upper=True,
        label="建库编号",
    )
    _append_code_search(
        filters,
        MolecularLibraryOrder.source_project_code,
        data.get("source_project_code"),
        label="项目编号",
    )
    _append_code_search(
        filters,
        MolecularLibraryOrder.library_batch_no,
        data.get("library_batch_no"),
        label="建库批号",
    )
    target_clause = recorded_target_clause(
        db,
        MolecularLibraryOrder.target_name,
        MolecularLibraryOrder.target_codes,
        data.get("target_name"),
        _library_target_pairs(),
    )
    if target_clause is not None:
        filters.append(target_clause)
    for key, column in (
        ("study_type", MolecularLibraryOrder.study_type),
        ("pm", MolecularLibraryOrder.pm),
        ("cell_type", MolecularLibraryOrder.cell_type),
        ("notebook_no", MolecularLibraryOrder.notebook_no),
        ("remark", MolecularLibraryOrder.remark),
        ("source_discovery_id", MolecularLibraryOrder.source_discovery_id),
    ):
        _append_contains(filters, column, data.get(key))
    for key, column in (
        ("build_type", MolecularLibraryOrder.build_type),
        ("sample_source", MolecularLibraryOrder.sample_source),
        ("sample_type", MolecularLibraryOrder.sample_type),
        ("status", MolecularLibraryOrder.status),
        ("owner", MolecularLibraryOrder.owner),
    ):
        terms = [term for term in filter_terms(data.get(key)) if term != "all"]
        condition = match_any(column, terms)
        if condition is not None:
            filters.append(condition)
    strain_terms = [term for term in filter_terms(data.get("mouse_strain")) if term != "all"]
    if strain_terms:
        filters.append(or_(*(_strain_token_filter(MolecularLibraryOrder.mouse_strain, term) for term in strain_terms)))
    priority_terms = [_normalize_priority(term) for term in filter_terms(data.get("priority"))]
    priority = match_any(MolecularLibraryOrder.priority, priority_terms)
    if priority is not None:
        filters.append(priority)
    _append_date_range(
        filters,
        MolecularLibraryOrder.instrument_on,
        data,
        "instrument_on_start",
        "instrument_on_end",
    )
    _append_date_range(filters, MolecularLibraryOrder.started_at, data, "started_at_start", "started_at_end")
    _append_date_range(filters, MolecularLibraryOrder.finished_at, data, "finished_at_start", "finished_at_end")
    return stmt.where(*filters) if filters else stmt


def _list_stats(db: Session, payload: dict[str, Any]) -> dict[str, int]:
    stats = {code: 0 for code in BUILD_TYPE_ORDER}
    for sample_type in PLASMA_SAMPLE_TYPES:
        stats[f"{BUILD_PLASMA_NGS}:{sample_type}"] = 0
    filtered = dict(payload or {})
    filtered.pop("build_type", None)
    filtered.pop("sample_type", None)
    stmt = _apply_list_filters(
        select(
            MolecularLibraryOrder.build_type,
            func.count(),
        )
        .select_from(MolecularLibraryOrder)
        .group_by(MolecularLibraryOrder.build_type),
        filtered,
        db=db,
    )
    for build_type, count in db.execute(stmt).all():
        number = int(count or 0)
        if build_type in stats:
            stats[build_type] += number
    plasma_stmt = _apply_list_filters(
        select(
            MolecularLibraryOrder.sample_type,
            func.count(),
        )
        .select_from(MolecularLibraryOrder)
        .where(MolecularLibraryOrder.build_type == BUILD_PLASMA_NGS)
        .group_by(MolecularLibraryOrder.sample_type),
        filtered,
        db=db,
    )
    for sample_type, count in db.execute(plasma_stmt).all():
        key = f"{BUILD_PLASMA_NGS}:{sample_type}"
        if key in stats:
            stats[key] += int(count or 0)
    return stats


def get_list(db: Session, data: dict[str, Any]) -> dict[str, Any]:
    payload = data or {}
    page, limit = _page_limit(payload)
    stmt = _apply_list_filters(select(MolecularLibraryOrder), payload, db=db)
    total = db.scalar(
        _apply_list_filters(select(func.count()).select_from(MolecularLibraryOrder), payload, db=db)
    ) or 0
    last_page = max(1, (int(total) + limit - 1) // limit)
    if page > last_page:
        page = last_page
    ordering = (
        MolecularLibraryOrder.id.asc()
        if str(payload.get("order") or "").strip() == "id_asc"
        else MolecularLibraryOrder.id.desc()
    )
    rows = db.scalars(
        stmt.order_by(ordering)
        .offset((page - 1) * limit)
        .limit(limit)
    ).all()
    return {
        "items": [row.to_dict() for row in rows],
        "total": int(total),
        "page": page,
        "limit": limit,
        "stats": _list_stats(db, payload),
    }


PROTECTED_SAVE_FIELDS = ("library_order_id", "source_discovery_id", "created_by")
MAX_BATCH_SAVE_ITEMS = 500


def _ensure_unique_library_codes(
    db: Session,
    pairs: list[tuple[int | None, Any]],
) -> None:
    """有内容的建库编号不能和别的工单相同。空编号不占号。"""
    claims: dict[str, int | None] = {}
    for row_id, raw in pairs:
        code = _normalize_library_code(raw)
        if not code:
            continue
        if code in claims:
            raise ValueError(f"建库编号 {code} 重复")
        claims[code] = row_id
    if not claims:
        return
    rows = db.execute(
        select(MolecularLibraryOrder.id, MolecularLibraryOrder.library_code).where(
            MolecularLibraryOrder.library_code.in_(list(claims))
        )
    ).all()
    claimed_ids = {row_id for row_id in claims.values() if row_id}
    taken = sorted({
        str(code or "").strip().upper()
        for row_id, code in rows
        if row_id not in claimed_ids and str(code or "").strip().upper() in claims
    })
    if taken:
        raise ValueError(f"建库编号 {'、'.join(taken)} 已存在")


def _writable_payload(data: dict[str, Any] | None) -> dict[str, Any]:
    payload = dict(data or {})
    for protected in PROTECTED_SAVE_FIELDS:
        payload.pop(protected, None)
    return payload


def save(
    db: Session,
    data: dict[str, Any],
    created_by: str | None = None,
) -> dict[str, Any]:
    payload = _writable_payload(data)
    row_id = _parse_row_id(payload.get("id"))
    if payload.get("id") not in (None, "") and row_id is None:
        raise ValueError("工单 ID 不正确")
    if "library_code" in payload:
        _ensure_unique_library_codes(db, [(row_id, payload.get("library_code"))])
    if row_id is None:
        build_type = _normalize_build_type(payload.get("build_type"))
        row = MolecularLibraryOrder(
            library_order_id=_next_library_order_id(db),
            build_type=build_type,
            status=STATUS_PENDING,
            priority=DEFAULT_PRIORITY,
            target_codes=[],
            target_forms=None,
            plate_nos=[],
            created_by=(created_by or "").strip() or None,
        )
        db.add(row)
    else:
        row = db.scalar(
            select(MolecularLibraryOrder)
            .where(MolecularLibraryOrder.id == row_id)
            .with_for_update()
        )
        if not row:
            raise ValueError(MISSING_ROW)
    _apply_fields(db, row, payload)
    db.commit()
    db.refresh(row)
    return row.to_dict()


def batch_save(db: Session, items: list[dict[str, Any]]) -> dict[str, Any]:
    if not items:
        raise ValueError("没有需要保存的工单")
    if len(items) > MAX_BATCH_SAVE_ITEMS:
        raise ValueError(f"单次最多保存 {MAX_BATCH_SAVE_ITEMS} 条工单")
    payloads = []
    seen_ids: set[int] = set()
    for item in items:
        payload = _writable_payload(item)
        row_id = _parse_row_id(payload.get("id"))
        if row_id is None:
            raise ValueError("工单 ID 不正确")
        if row_id in seen_ids:
            raise ValueError("同一工单不能重复提交")
        seen_ids.add(row_id)
        payloads.append((row_id, payload))
    locked_rows = db.scalars(
        select(MolecularLibraryOrder)
        .where(MolecularLibraryOrder.id.in_(sorted(seen_ids)))
        .order_by(MolecularLibraryOrder.id)
        .with_for_update()
    ).all()
    rows_by_id = {int(row.id): row for row in locked_rows}
    if len(rows_by_id) != len(seen_ids):
        raise ValueError(MISSING_ROW)
    _ensure_unique_library_codes(
        db,
        [
            (row_id, payload.get("library_code"))
            for row_id, payload in payloads
            if "library_code" in payload
        ],
    )
    rows = []
    for row_id, payload in payloads:
        row = rows_by_id[row_id]
        try:
            _apply_fields(db, row, payload)
        except ValueError as exc:
            raise ValueError(f"{row.library_order_id}：{exc}") from exc
        rows.append(row)
    db.commit()
    for row in rows:
        db.refresh(row)
    return {"items": [row.to_dict() for row in rows]}


def delete_order(db: Session, row_id: int) -> dict[str, int]:
    row = db.get(MolecularLibraryOrder, int(row_id))
    if not row:
        raise ValueError(MISSING_ROW)
    links = list(
        db.scalars(
            select(MolecularLibraryResultLink).where(
                MolecularLibraryResultLink.order_id == row.id
            )
        ).all()
    )
    records = {
        link.file_id: db.get(MolecularLibraryResultFile, link.file_id)
        for link in links
    }
    package_ids = {
        int(record.package_id)
        for record in records.values()
        if record and record.package_id
    }
    owned_packages = list(
        db.scalars(
            select(MolecularLibraryResultPackage).where(
                MolecularLibraryResultPackage.owner_order_id == row.id
            )
        ).all()
    )
    package_ids.update(int(package.id) for package in owned_packages)
    for package in owned_packages:
        package.owner_order_id = None
    for link in links:
        db.delete(link)
    db.flush()
    files_to_remove: list[Path] = []
    for file_id, record in records.items():
        remaining = _count_file_links(db, file_id)
        if not record or record.package_id or remaining:
            continue
        files_to_remove.append(_full_path(record.storage_path))
        db.delete(record)
    package_dirs_to_remove: list[Path] = []
    for package_id in package_ids:
        package = db.get(MolecularLibraryResultPackage, package_id)
        if not package:
            continue
        remaining = int(
            db.scalar(
                select(func.count())
                .select_from(MolecularLibraryResultLink)
                .join(
                    MolecularLibraryResultFile,
                    MolecularLibraryResultFile.id == MolecularLibraryResultLink.file_id,
                )
                .where(MolecularLibraryResultFile.package_id == package.id)
            )
            or 0
        )
        if remaining or package.owner_order_id is not None:
            continue
        package_dirs_to_remove.append(_full_path(package.storage_prefix))
        package_records = db.scalars(
            select(MolecularLibraryResultFile).where(
                MolecularLibraryResultFile.package_id == package.id
            )
        ).all()
        for package_record in package_records:
            db.delete(package_record)
        db.delete(package)
    deleted_id = int(row.id)
    db.delete(row)
    db.commit()
    for path in files_to_remove:
        _remove_file_if_exists(path)
    for directory in package_dirs_to_remove:
        shutil.rmtree(directory, ignore_errors=True)
    return {"id": deleted_id}


def _load_discovery(
    db: Session,
    *,
    discovery_workbench_id: int | None = None,
    discovery_id: str | None = None,
) -> DiscoveryWorkbench:
    row = None
    if discovery_workbench_id:
        row = db.get(DiscoveryWorkbench, int(discovery_workbench_id))
    elif discovery_id:
        row = db.scalar(
            select(DiscoveryWorkbench).where(
                DiscoveryWorkbench.discovery_id == str(discovery_id).strip()
            )
        )
    if not row:
        raise ValueError(MISSING_DISCOVERY)
    return row


def _handoff_preview(row: DiscoveryWorkbench) -> dict[str, Any]:
    return {
        "id": row.id,
        "discovery_id": row.discovery_id,
        "project_code": row.project_code,
        "target_name": row.target_name,
        "target_codes": row.target_codes if isinstance(row.target_codes, list) else [],
        "pm": row.pm,
        "study_type": row.study_type,
        "mouse_strain": row.mouse_strain,
        "sample_type": _auto_sample_type(row.mouse_strain),
        "instrument_on": row.harvest_date,
        "positive_cell_count": row.positive_cell_count,
        "screening_methods": row.screening_methods,
        "priority": row.priority or DEFAULT_PRIORITY,
        "status": row.status,
    }


def _suggested_handoff(
    row: DiscoveryWorkbench,
    existing: list[MolecularLibraryOrder],
) -> list[dict[str, str]]:
    existing_types = {
        item.build_type
        for item in existing
        if item.status != STATUS_CANCELLED
    }
    methods = {part.strip() for part in str(row.screening_methods or "").split(",") if part.strip()}
    suggested: list[dict[str, str]] = []
    has_beacon = SCREENING_METHOD_BEACON in methods
    has_dapu = SCREENING_METHOD_DAPU in methods
    if BUILD_PLATE not in existing_types:
        if has_beacon and has_dapu:
            suggested.append(
                {"build_type": BUILD_PLATE, "sample_source": SOURCE_BEACON_DAPU}
            )
        elif has_beacon:
            suggested.append(
                {"build_type": BUILD_PLATE, "sample_source": SOURCE_BEACON}
            )
    if SCREENING_METHOD_PHAGE in methods and BUILD_PHAGE_DISPLAY not in existing_types:
        suggested.append(
            {"build_type": BUILD_PHAGE_DISPLAY, "sample_source": SOURCE_DIRECT}
        )
    return suggested


def list_by_discovery(
    db: Session,
    discovery_id: str | None = None,
    discovery_workbench_id: int | None = None,
) -> dict[str, Any]:
    row = _load_discovery(
        db,
        discovery_workbench_id=discovery_workbench_id,
        discovery_id=discovery_id,
    )
    items = db.scalars(
        select(MolecularLibraryOrder)
        .where(MolecularLibraryOrder.source_discovery_id == row.discovery_id)
        .order_by(MolecularLibraryOrder.id.desc())
    ).all()
    return {
        "discovery": _handoff_preview(row),
        "items": [item.to_dict() for item in items],
        "suggested_items": _suggested_handoff(row, items),
    }


def _validate_handoff_item(row: DiscoveryWorkbench, item: dict[str, Any]) -> tuple[str, str, str | None]:
    build_type = _normalize_build_type(item.get("build_type"))
    sample_source = str(
        _normalize_choice(
            item.get("sample_source"),
            PROFILE_SOURCES[build_type],
            "样品来源",
            nullable=False,
        )
    )
    raw_sample_type = item.get("sample_type")
    sample_type = (
        _normalize_choice(raw_sample_type, SAMPLE_TYPE_LABELS, "样品类型", nullable=True)
        if raw_sample_type not in (None, "")
        else None
    )
    if build_type == BUILD_PLASMA_NGS and sample_type not in (None, *PLASMA_SAMPLE_TYPES):
        raise ValueError("浆细胞 NGS 的样品类型只能是 Nano 或 Lite")
    if build_type in INSTRUMENT_DATE_BUILDS:
        if not str(row.harvest_date or "").strip():
            raise ValueError("请先在发现台填写剖鼠日期（将作为上机日期）")
    return build_type, sample_source, sample_type


def _apply_discovery_status(row: DiscoveryWorkbench, created_types: list[str]) -> None:
    current = str(row.status or "").strip() or DISCOVERY_PLANNING
    if current in DISCOVERY_TERMINAL_STATUSES or current == DISCOVERY_WAIT_SEQ:
        return
    if BUILD_PHAGE_DISPLAY in created_types and current in {
        DISCOVERY_PLANNING,
        DISCOVERY_WAIT_BOOST,
        DISCOVERY_WAIT_HARVEST,
        DISCOVERY_WAIT_LIBRARY,
    }:
        row.status = DISCOVERY_WAIT_PHAGE
    elif current in {DISCOVERY_PLANNING, DISCOVERY_WAIT_BOOST, DISCOVERY_WAIT_HARVEST}:
        row.status = DISCOVERY_WAIT_LIBRARY


def handoff(
    db: Session,
    data: dict[str, Any],
    created_by: str | None = None,
) -> dict[str, Any]:
    payload = data or {}
    raw_items = payload.get("items") or []
    if not isinstance(raw_items, list) or not raw_items:
        raise ValueError("请选择本次要建的工艺")
    if any(not isinstance(item, dict) for item in raw_items):
        raise ValueError("交接工艺格式不正确")
    row = _load_discovery(
        db,
        discovery_workbench_id=_parse_row_id(payload.get("discovery_workbench_id")),
        discovery_id=str(payload.get("discovery_id") or "").strip() or None,
    )
    if str(row.status or "").strip() in DISCOVERY_TERMINAL_STATUSES:
        raise ValueError("已完成或已取消的发现安排不能交接")
    normalized = [_validate_handoff_item(row, item) for item in raw_items]
    codes = row.target_codes if isinstance(row.target_codes, list) else []
    created: list[MolecularLibraryOrder] = []
    for build_type, sample_source, sample_type in normalized:
        mouse_strain = _normalize_mouse_strain(row.mouse_strain)
        resolved_sample_type = sample_type or _auto_sample_type(mouse_strain)
        if build_type == BUILD_PLASMA_NGS and resolved_sample_type not in (None, *PLASMA_SAMPLE_TYPES):
            resolved_sample_type = None
        order = MolecularLibraryOrder(
            library_order_id=_next_library_order_id(db),
            build_type=build_type,
            sample_source=sample_source,
            source_discovery_id=row.discovery_id,
            source_project_code=row.project_code,
            study_type=row.study_type,
            target_name=row.target_name,
            target_codes=list(codes),
            pm=row.pm,
            mouse_strain=mouse_strain,
            sample_type=resolved_sample_type,
            instrument_on=(
                _normalize_date(row.harvest_date)
                if build_type in FILLS_INSTRUMENT_ON and str(row.harvest_date or "").strip()
                else None
            ),
            cell_type=DEFAULT_PLASMA_CELL_TYPE if build_type == BUILD_PLASMA_NGS else None,
            positive_cell_count=(
                _normalize_text(row.positive_cell_count, STRING_FIELDS["positive_cell_count"])
                if build_type in POSITIVE_CELL_COUNT_BUILDS
                else None
            ),
            status=STATUS_PENDING,
            priority=row.priority or DEFAULT_PRIORITY,
            target_forms=None,
            plate_nos=[],
            created_by=(created_by or "").strip() or None,
        )
        db.add(order)
        db.flush()
        created.append(order)
    _apply_discovery_status(row, [item[0] for item in normalized])
    db.commit()
    return {
        "items": [item.to_dict() for item in created],
        "discovery_status": row.status,
    }


def has_orders_for_discovery(db: Session, discovery_id: str) -> bool:
    if not discovery_id:
        return False
    exists = db.scalar(
        select(MolecularLibraryOrder.id).where(
            MolecularLibraryOrder.source_discovery_id == discovery_id,
        )
    )
    return bool(exists)


EXPORT_COLUMNS = (
    ("系统工单号", "library_order_id"),
    ("来源发现 ID", "source_discovery_id"),
    ("建库编号", "library_code"),
    ("建库批号", "library_batch_no"),
    ("建库类型", "build_type"),
    ("样品来源", "sample_source"),
    ("项目编号", "source_project_code"),
    ("课题类型", "study_type"),
    ("实验类型", "source_experiment_type"),
    ("实验目标", "project_goal"),
    ("靶点", "target_name"),
    ("靶点编号", "target_codes"),
    ("PM", "pm"),
    ("小鼠品系", "mouse_strain"),
    ("样品类型", "sample_type"),
    ("交接日期", "received_on"),
    ("上机日期", "instrument_on"),
    ("采血日期", "blood_collected_on"),
    ("免疫阶段", "immunization_stage"),
    ("阳性细胞数", "positive_cell_count"),
    ("板号", "plate_nos"),
    ("细胞类型", "cell_type"),
    ("靶点形式", "target_forms"),
    ("实验记录本号", "notebook_no"),
    ("状态", "status"),
    ("优先级", "priority"),
    ("负责人", "owner"),
    ("开始时间", "started_at"),
    ("完成时间", "finished_at"),
    ("RNA 位置", "rna_location"),
    ("cDNA 位置", "cdna_location"),
    ("文库位置", "library_location"),
    ("cDNA 浓度", "cdna_concentration"),
    ("文库浓度", "library_concentration"),
    ("初始库容", "initial_library_size"),
    ("有效库容", "effective_library_size"),
    ("片段大小", "fragment_size_bp"),
    ("H 正向引物", "h_forward_primer_name"),
    ("H 反向引物", "h_reverse_primer_name"),
    ("H 浓度", "h_primer_concentration"),
    ("K 正向引物", "k_forward_primer_name"),
    ("K 反向引物", "k_reverse_primer_name"),
    ("K 浓度", "k_primer_concentration"),
    ("L 正向引物", "l_forward_primer_name"),
    ("L 反向引物", "l_reverse_primer_name"),
    ("L 浓度", "l_primer_concentration"),
    ("Barcode 方式", "index_mode"),
    ("i7 名称", "i7_name"),
    ("i7 序列", "i7_sequence"),
    ("i5 名称", "i5_name"),
    ("i5 序列", "i5_sequence"),
    ("质检结论", "qc_result"),
    ("质检人", "qc_owner"),
    ("质检日期", "qc_on"),
    ("质检说明", "qc_note"),
    ("备注", "remark"),
)


def export_list_workbook(db: Session, data: dict[str, Any]):
    from utils.excel import build_list_workbook, cell_text

    rows = db.scalars(
        _apply_list_filters(select(MolecularLibraryOrder), data or {}, db=db).order_by(
            MolecularLibraryOrder.id.desc()
        )
    ).all()
    table_rows = []
    for row in rows:
        item = row.to_dict()
        item["build_type"] = BUILD_TYPE_LABELS.get(item["build_type"], item["build_type"])
        item["sample_source"] = SAMPLE_SOURCE_LABELS.get(
            item["sample_source"], item["sample_source"]
        )
        item["sample_type"] = SAMPLE_TYPE_LABELS.get(
            item["sample_type"], item["sample_type"]
        )
        item["index_mode"] = INDEX_MODE_LABELS.get(item["index_mode"], item["index_mode"])
        table_rows.append(
            [cell_text(item.get(key)) for _, key in EXPORT_COLUMNS]
        )
    return build_list_workbook(
        sheet_title="文库构建",
        filename_prefix="文库构建",
        headers=[label for label, _ in EXPORT_COLUMNS],
        rows=table_rows,
    )


def _full_path(relative_path: str) -> Path:
    return Path(get_settings().repository_root) / "uploads" / relative_path.lstrip("/")


def _infer_file_kind(filename: str) -> str:
    suffix = extension_of(filename)
    if suffix in GEL_EXTENSIONS:
        return FILE_KIND_GEL
    if suffix in PRIMER_QC_EXTENSIONS:
        return FILE_KIND_PRIMER_QC
    if suffix in {".xlsx", ".xls", ".csv", ".ppt", ".pptx"}:
        return FILE_KIND_PCR_QC
    return FILE_KIND_OTHER


def _load_order(
    db: Session,
    order_id: int,
    *,
    for_update: bool = False,
) -> MolecularLibraryOrder:
    row = (
        db.scalar(
            select(MolecularLibraryOrder)
            .where(MolecularLibraryOrder.id == int(order_id))
            .with_for_update()
        )
        if for_update
        else db.get(MolecularLibraryOrder, int(order_id))
    )
    if not row:
        raise ValueError(MISSING_ROW)
    return row


def _link_payload(
    link: MolecularLibraryResultLink,
    record: MolecularLibraryResultFile,
    linked_order_count: int,
) -> dict[str, Any]:
    return {
        "id": link.id,
        "package_id": record.package_id,
        "result_kind": _infer_file_kind(link.original_name),
        "original_name": link.original_name,
        "is_final_qc": bool(link.is_final_qc),
        "qc_regions": link.qc_regions if isinstance(link.qc_regions, list) else [],
        "uploaded_by": link.uploaded_by,
        "sequence_status": link.sequence_status,
        "sequence_target": link.sequence_target,
        "sequence_check": sequence_check_text(
            link.sequence_status,
            link.sequence_target,
        ),
        "order_id": link.order_id,
        "created_at": link.to_dict()["created_at"],
        "mime_type": record.mime_type,
        "byte_size": record.byte_size,
        "linked_order_count": int(linked_order_count),
    }


def _sequencing_packages(
    db: Session,
    order: MolecularLibraryOrder,
) -> list[dict[str, Any]]:
    linked_package_ids = (
        select(MolecularLibraryResultFile.package_id)
        .join(
            MolecularLibraryResultLink,
            MolecularLibraryResultLink.file_id == MolecularLibraryResultFile.id,
        )
        .where(
            MolecularLibraryResultLink.order_id == order.id,
            MolecularLibraryResultFile.package_id.is_not(None),
        )
    )
    rows = db.scalars(
        select(MolecularLibraryResultPackage)
        .where(
            or_(
                MolecularLibraryResultPackage.owner_order_id == order.id,
                MolecularLibraryResultPackage.id.in_(linked_package_ids),
            )
        )
        .order_by(MolecularLibraryResultPackage.id.desc())
    ).all()
    packages = []
    for package in rows:
        records = db.scalars(
            select(MolecularLibraryResultFile)
            .where(MolecularLibraryResultFile.package_id == package.id)
            .order_by(
                MolecularLibraryResultFile.relative_path,
                MolecularLibraryResultFile.id,
            )
        ).all()
        record_ids = [record.id for record in records]
        own_links = db.scalars(
            select(MolecularLibraryResultLink).where(
                MolecularLibraryResultLink.order_id == order.id,
                MolecularLibraryResultLink.file_id.in_(record_ids),
            )
        ).all() if record_ids else []
        own_by_file = {link.file_id: link for link in own_links}
        linked_orders = set(
            db.scalars(
                select(MolecularLibraryResultLink.order_id)
                .join(
                    MolecularLibraryResultFile,
                    MolecularLibraryResultFile.id == MolecularLibraryResultLink.file_id,
                )
                .where(
                    MolecularLibraryResultFile.package_id == package.id,
                )
                .distinct()
            ).all()
        )
        if package.owner_order_id:
            linked_orders.add(package.owner_order_id)
        files = []
        for record in records:
            own = own_by_file.get(record.id)
            relative = record.relative_path or Path(record.storage_path).name
            display_name = own.original_name if own else relative.rsplit("/", 1)[-1]
            files.append(
                {
                    "file_id": record.id,
                    "link_id": own.id if own else None,
                    "original_name": display_name,
                    "relative_path": relative,
                    "byte_size": record.byte_size,
                    "mime_type": record.mime_type,
                    "result_kind": _infer_file_kind(display_name),
                    "sequence_status": own.sequence_status if own else None,
                    "sequence_target": own.sequence_target if own else None,
                    "sequence_check": (
                        sequence_check_text(own.sequence_status, own.sequence_target)
                        if own else None
                    ),
                    "for_qc": own is not None,
                }
            )
        packages.append(
            {
                "id": package.id,
                "name": package.original_name,
                "file_count": len(files),
                "qc_count": sum(
                    1
                    for item in files
                    if item["for_qc"]
                    and extension_of(item["original_name"]) in READ_EXTENSIONS
                ),
                "linked_count": sum(1 for item in files if item["for_qc"]),
                "shared": len(linked_orders) > 1,
                "linked_order_count": len(linked_orders),
                "owned": package.owner_order_id == order.id,
                "created_at": package.to_dict()["created_at"],
                "files": files,
            }
        )
    return packages


def _refresh_listed_sequences(
    db: Session,
    order: MolecularLibraryOrder,
    rows: list,
) -> bool:
    """打开质检页时按当前算法重核。核对结果没变就不改记录。"""
    primers = _configured_primers(db, order)
    changed = False
    for link, record, _count in rows:
        previous = (link.sequence_status, link.sequence_target)
        _recheck_link_sequence(link, record, order, primers)
        if (link.sequence_status, link.sequence_target) != previous:
            changed = True
    if changed:
        _advance_order_status(db, order)
    return changed


def list_files(db: Session, order_id: int) -> dict[str, Any]:
    order = _load_order(db, order_id)
    link_counts = (
        select(
            MolecularLibraryResultLink.file_id.label("file_id"),
            func.count().label("linked_order_count"),
        )
        .group_by(MolecularLibraryResultLink.file_id)
        .subquery()
    )
    rows = db.execute(
        select(
            MolecularLibraryResultLink,
            MolecularLibraryResultFile,
            link_counts.c.linked_order_count,
        )
        .join(
            MolecularLibraryResultFile,
            MolecularLibraryResultFile.id == MolecularLibraryResultLink.file_id,
        )
        .join(link_counts, link_counts.c.file_id == MolecularLibraryResultLink.file_id)
        .where(
            MolecularLibraryResultLink.order_id == order.id,
        )
        .order_by(
            MolecularLibraryResultLink.is_final_qc.desc(),
            MolecularLibraryResultLink.id.desc(),
        )
    ).all()
    changed = _refresh_listed_sequences(db, order, rows)
    final_names = _final_names(link for link, _record, _count in rows)
    items = [
        {
            **_link_payload(link, record, linked_order_count),
            "replaced": _replaced_by_final(link, final_names),
        }
        for link, record, linked_order_count in rows
    ]
    payload = {
        "order": order.to_dict(),
        "primer_sequences": _configured_primers(db, order),
        "items": items,
        "packages": _sequencing_packages(db, order),
    }
    if changed:
        db.commit()
    return payload


def _hash_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _write_content(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


def _remove_file_if_exists(path: Path) -> bool:
    try:
        path.unlink(missing_ok=True)
        return True
    except OSError:
        return False


def _count_file_links(db: Session, file_id: int) -> int:
    return int(
        db.scalar(
            select(func.count())
            .select_from(MolecularLibraryResultLink)
            .where(MolecularLibraryResultLink.file_id == int(file_id))
        )
        or 0
    )


def _uploads_root() -> Path:
    return Path(get_settings().repository_root) / "uploads"


def _storage_path(relative: str) -> str:
    return f"/{relative.replace(chr(92), '/')}"


def _read_upload(file_obj: UploadFile, db: Session) -> tuple[str, str | None, bytes]:
    filename = Path(file_obj.filename or "").name
    if not filename or len(filename) > 255:
        raise ValueError("缺少文件名")
    content = file_obj.file.read(MAX_FILE_BYTES + 1)
    if not content:
        raise ValueError(f"{filename}：文件内容为空")
    if len(content) > MAX_FILE_BYTES:
        raise ValueError(f"{filename}：文件不能超过 50MB")
    extension = extension_of(filename)
    temp_path = _uploads_root() / "library_results" / ".tmp" / f"{secrets.token_hex(16)}{extension}"
    try:
        _write_content(temp_path, content)
        drm_service.decrypt_upload_file_if_available(db, temp_path)
        stored = temp_path.read_bytes()
    finally:
        _remove_file_if_exists(temp_path)
    if not stored:
        raise ValueError(f"{filename}：文件内容为空")
    if len(stored) > MAX_FILE_BYTES:
        raise ValueError(f"{filename}：文件不能超过 50MB")
    return filename, file_obj.content_type, stored


def _find_gel_record(db: Session, digest: str) -> MolecularLibraryResultFile | None:
    return db.scalar(
        select(MolecularLibraryResultFile).where(
            MolecularLibraryResultFile.dedupe_key == f"gel:{digest}"
        )
    )


def _place_bytes(
    relative: str,
    content: bytes,
    created_paths: list[Path],
) -> str:
    uploads_root = _uploads_root()
    target = uploads_root / relative
    if target.exists():
        path = Path(relative)
        relative = f"{path.parent.as_posix()}/{path.stem}-{secrets.token_hex(3)}{path.suffix}"
        target = uploads_root / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(content)
    created_paths.append(target)
    return relative


def _place_shared_bytes(relative: str, content: bytes) -> bool:
    """按确定路径排他写入可复用文件；已存在时不覆盖。"""
    target = _uploads_root() / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        with target.open("xb") as output:
            output.write(content)
        return True
    except FileExistsError:
        return False


def _get_or_create_gel_record(
    db: Session,
    entry: dict[str, Any],
    now: datetime,
    created_paths: list[Path],
) -> MolecularLibraryResultFile:
    digest = entry["digest"]
    record = _find_gel_record(db, digest)
    if record is not None:
        if not _full_path(record.storage_path).exists():
            _place_shared_bytes(record.storage_path.lstrip("/"), entry["content"])
        return record

    relative = f"{month_directory('gels', now)}/{digest}{extension_of(entry['filename'])}"
    created_path = _place_shared_bytes(relative, entry["content"])
    try:
        if db.get_bind().dialect.name == "sqlite":
            record = _new_file_record(
                db,
                relative,
                entry["content"],
                entry["mime_type"],
                digest,
                dedupe_key=f"gel:{digest}",
            )
        else:
            with db.begin_nested():
                record = _new_file_record(
                    db,
                    relative,
                    entry["content"],
                    entry["mime_type"],
                    digest,
                    dedupe_key=f"gel:{digest}",
                )
    except IntegrityError:
        record = _find_gel_record(db, digest)
        if record is None:
            raise
        if created_path and record.storage_path != _storage_path(relative):
            _remove_file_if_exists(_uploads_root() / relative)
            created_path = False
    if created_path:
        created_paths.append(_uploads_root() / relative)
    return record


def _orders_for_code(db: Session, code: str) -> list[MolecularLibraryOrder]:
    if not code:
        return []
    return list(db.scalars(
        select(MolecularLibraryOrder)
        .where(MolecularLibraryOrder.library_code == code)
        .with_for_update()
    ).all())


def _linked_same_file(
    db: Session,
    digest: str,
    order_id: int,
    filename: str,
) -> MolecularLibraryResultLink | None:
    return db.scalar(
        select(MolecularLibraryResultLink)
        .join(
            MolecularLibraryResultFile,
            MolecularLibraryResultFile.id == MolecularLibraryResultLink.file_id,
        )
        .where(
            MolecularLibraryResultFile.sha256 == digest,
            MolecularLibraryResultLink.order_id == order_id,
            MolecularLibraryResultLink.original_name == filename,
        )
    )


def _existing_link(
    db: Session,
    record: MolecularLibraryResultFile,
    order: MolecularLibraryOrder,
) -> MolecularLibraryResultLink | None:
    return db.scalar(
        select(MolecularLibraryResultLink).where(
            MolecularLibraryResultLink.file_id == record.id,
            MolecularLibraryResultLink.order_id == order.id,
        )
    )


def _attach_link(
    db: Session,
    record: MolecularLibraryResultFile,
    order: MolecularLibraryOrder,
    filename: str,
    user_name: str,
    sequence_status: str | None,
    sequence_target: str | None,
) -> MolecularLibraryResultLink:
    link = MolecularLibraryResultLink(
        file_id=record.id,
        order_id=order.id,
        original_name=filename,
        uploaded_by=(user_name or "").strip() or None,
        sequence_status=sequence_status,
        sequence_target=sequence_target,
    )
    db.add(link)
    db.flush()
    return link


def _new_file_record(
    db: Session,
    relative: str,
    content: bytes,
    mime_type: str | None,
    digest: str,
    *,
    package_id: int | None = None,
    relative_path: str | None = None,
    dedupe_key: str | None = None,
) -> MolecularLibraryResultFile:
    record = MolecularLibraryResultFile(
        package_id=package_id,
        relative_path=relative_path,
        storage_path=_storage_path(relative),
        mime_type=mime_type,
        byte_size=len(content),
        sha256=digest,
        dedupe_key=dedupe_key,
    )
    db.add(record)
    db.flush()
    return record


def _safe_inner_path(value: str) -> str:
    parts = [
        safe_path_part(part, "file")
        for part in normalize_relative_path(value, value).split("/")
    ]
    return "/".join(parts)


def _read_targets(
    filename: str,
    orders: list[MolecularLibraryOrder],
) -> tuple[list[MolecularLibraryOrder], str]:
    stem = library_code_stem(filename)
    if not stem:
        return [], "文件名里没有建库编号"
    code = longest_library_code(filename, [order.library_code for order in orders])
    if not code:
        return [], f"建库编号 {stem} 还没有对应工单"
    found = [order for order in orders if (order.library_code or "").upper() == code]
    if len(found) > 1:
        return [], f"建库编号 {code} 对应多个工单"
    return found, ""


def _orders_for_stems(
    db: Session,
    stems: set[str],
    *,
    lock: bool,
) -> list[MolecularLibraryOrder]:
    if not stems:
        return []
    query = select(MolecularLibraryOrder).where(or_(*(
        MolecularLibraryOrder.library_code.like(f"{stem}%")
        for stem in sorted(stems)
    )))
    if lock:
        query = query.with_for_update()
    return list(db.scalars(query).all())


def _resolve_upload_targets(
    role: str,
    filename: str,
    lookup,
) -> tuple[list[MolecularLibraryOrder], str]:
    if role != ROLE_GEL:
        return [], ""
    codes = [code for code in library_codes_in_name(filename) if code]
    if not codes:
        return [], "图片文件名里没有建库编号"
    targets: list[MolecularLibraryOrder] = []
    seen: set[int] = set()
    for code in codes:
        found = lookup(code)
        if len(found) > 1:
            return [], f"建库编号 {code} 对应多个工单"
        if len(found) == 1 and found[0].id not in seen:
            seen.add(found[0].id)
            targets.append(found[0])
    if targets:
        return targets, ""
    return [], f"建库编号 {codes[0]} 还没有对应工单"


def _upload_targets(
    db: Session,
    role: str,
    filename: str,
) -> tuple[list[MolecularLibraryOrder], str]:
    if role == ROLE_READ:
        stem = library_code_stem(filename)
        if not stem:
            return [], "文件名里没有建库编号"
        return _read_targets(filename, _orders_for_stems(db, {stem}, lock=True))
    return _resolve_upload_targets(
        role,
        filename,
        lambda code: _orders_for_code(db, code),
    )


def _issue_rows(reasons: list[str]) -> list[dict[str, Any]]:
    counts: dict[str, int] = {}
    for reason in reasons:
        if reason:
            counts[reason] = counts.get(reason, 0) + 1
    return [{"reason": reason, "count": count} for reason, count in counts.items()]


def _merge_preflight_summary(
    actual: list[dict[str, Any]],
    preliminary: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """把未上传项和预检告警并入真实上传结果。"""
    by_key = {
        item.get("group_id") or item["name"]: item
        for item in actual
    }
    for preview in preliminary:
        current = by_key.get(preview.get("group_id") or preview["name"])
        if current is None:
            if preview["outcome"] == "skipped":
                actual.append(preview)
            continue
        for key in (
            "group_id",
            "kind",
            "source_path",
            "file_count",
            "accepted_count",
            "matched_count",
            "matched_codes",
            "matched_files",
        ):
            if key in preview:
                current[key] = preview[key]
        issue_counts = {
            issue["reason"]: int(issue["count"])
            for issue in current.get("issues", [])
        }
        for issue in preview.get("issues", []):
            reason = issue["reason"]
            issue_counts[reason] = max(
                issue_counts.get(reason, 0),
                int(issue["count"]),
            )
        current["issues"] = [
            {"reason": reason, "count": count}
            for reason, count in issue_counts.items()
        ]
    return actual


def _preflight_order_map(
    db: Session,
    codes: set[str],
) -> dict[str, list[MolecularLibraryOrder]]:
    if not codes:
        return {}
    rows = db.scalars(
        select(MolecularLibraryOrder).where(
            MolecularLibraryOrder.library_code.in_(sorted(codes))
        )
    ).all()
    result: dict[str, list[MolecularLibraryOrder]] = {}
    for row in rows:
        code = str(row.library_code or "").strip().upper()
        result.setdefault(code, []).append(row)
    return result


def _preflight_targets(
    role: str,
    filename: str,
    orders_by_code: dict[str, list[MolecularLibraryOrder]],
    read_orders: list[MolecularLibraryOrder],
) -> tuple[list[MolecularLibraryOrder], str]:
    if role == ROLE_READ:
        return _read_targets(filename, read_orders)
    return _resolve_upload_targets(
        role,
        filename,
        lambda code: orders_by_code.get(code, []),
    )


def preflight_upload(
    db: Session,
    relative_paths: list[str],
) -> dict[str, Any]:
    """只检查批量入口的路径、文件名和工单匹配，不读取文件内容。"""
    if not relative_paths:
        raise ValueError("请选择文件")
    if len(relative_paths) > MAX_UPLOAD_FILES:
        raise ValueError(f"一次最多上传 {MAX_UPLOAD_FILES} 个文件")
    plan = plan_upload_paths(relative_paths)
    roles: dict[int, str] = {}
    names = {
        index: Path(path).name
        for index, path in enumerate(plan.paths)
    }
    codes: set[str] = set()
    stems: set[str] = set()

    for group in plan.packages:
        for index, inner_path in group.entries:
            role = package_file_role(inner_path)
            roles[index] = role
            if role == ROLE_READ:
                stem = library_code_stem(names[index])
                if stem:
                    stems.add(stem)
    for index in plan.loose_indexes:
        role = loose_file_role(plan.paths[index], current_order=False)
        roles[index] = role
        if role == ROLE_GEL:
            codes.update(code for code in library_codes_in_name(names[index]) if code)
        elif role == ROLE_READ:
            stem = library_code_stem(names[index])
            if stem:
                stems.add(stem)

    orders_by_code = _preflight_order_map(db, codes)
    read_orders = _orders_for_stems(db, stems, lock=False)
    accepted: set[int] = set()
    summary: list[dict[str, Any]] = []

    for group in plan.packages:
        prepared: list[int] = []
        reasons: list[str] = []
        matched_count = 0
        matched_codes: set[str] = set()
        matched_files: dict[str, int] = {}
        has_target = False
        for index, _inner_path in group.entries:
            role = roles[index]
            prepared.append(index)
            if role != ROLE_READ:
                continue
            targets, reason = _preflight_targets(role, names[index], orders_by_code, read_orders)
            if targets:
                has_target = True
                matched_count += 1
                hit_codes = {
                    str(target.library_code or "").strip().upper()
                    for target in targets
                    if target.library_code
                }
                matched_codes.update(hit_codes)
                for code in hit_codes:
                    matched_files[code] = matched_files.get(code, 0) + 1
            elif reason:
                reasons.append(reason)
        if has_target:
            accepted.update(prepared)
        summary.append({
            "group_id": f"package:{group.root.casefold()}",
            "kind": "package",
            "source_path": group.root,
            "name": package_name(group.root),
            "outcome": "ready" if has_target else "skipped",
            "file_count": len(prepared),
            "accepted_count": len(prepared) if has_target else 0,
            "matched_count": matched_count,
            "matched_codes": sorted(matched_codes),
            "matched_files": [
                {"code": code, "count": matched_files[code]}
                for code in sorted(matched_files)
            ],
            "issues": _issue_rows(
                reasons or ([] if has_target else ["测序包里没有文件能唯一匹配工单"])
            ),
        })

    loose_reasons: list[str] = []
    loose_accepted = 0
    loose_matched_codes: set[str] = set()
    loose_matched_files: dict[str, int] = {}
    for index in plan.loose_indexes:
        role = roles[index]
        targets, reason = _preflight_targets(role, names[index], orders_by_code, read_orders)
        if targets:
            accepted.add(index)
            loose_accepted += 1
            hit_codes = {
                str(target.library_code or "").strip().upper()
                for target in targets
                if target.library_code
            }
            loose_matched_codes.update(hit_codes)
            for code in hit_codes:
                loose_matched_files[code] = loose_matched_files.get(code, 0) + 1
        else:
            loose_reasons.append(reason or "无法按建库编号归入工单")
    if plan.loose_indexes:
        summary.append({
            "group_id": "loose",
            "kind": "loose",
            "name": "零散文件",
            "outcome": "ready" if loose_accepted else "skipped",
            "file_count": len(plan.loose_indexes),
            "accepted_count": loose_accepted,
            "matched_count": loose_accepted,
            "matched_codes": sorted(loose_matched_codes),
            "matched_files": [
                {"code": code, "count": loose_matched_files[code]}
                for code in sorted(loose_matched_files)
            ],
            "issues": _issue_rows(loose_reasons),
        })
    return {
        "accepted_indexes": sorted(accepted),
        "summary": summary,
    }


def _package_file_rows(
    db: Session,
    package_id: int,
) -> list[MolecularLibraryResultFile]:
    return list(db.scalars(
        select(MolecularLibraryResultFile)
        .where(MolecularLibraryResultFile.package_id == package_id)
        .order_by(MolecularLibraryResultFile.id)
    ).all())


def _same_named_packages(
    db: Session,
    name: str,
) -> list[MolecularLibraryResultPackage]:
    rows = db.scalars(
        select(MolecularLibraryResultPackage)
        .where(func.lower(MolecularLibraryResultPackage.original_name) == name.casefold())
        .order_by(MolecularLibraryResultPackage.id.desc())
        .with_for_update()
    ).all()
    return list(rows)


def _extendable_package(
    db: Session,
    name: str,
    prepared: list[dict[str, Any]],
) -> MolecularLibraryResultPackage | None:
    """同名包里的文件这次都原样还在（路径和内容都相同），才往里追加。"""
    incoming = {(entry["inner_path"].casefold(), entry["digest"]) for entry in prepared}
    best = None
    best_count = 0
    for candidate in _same_named_packages(db, name):
        stored = {
            (str(record.relative_path or "").casefold(), record.sha256)
            for record in _package_file_rows(db, candidate.id)
        }
        if stored and stored <= incoming and len(stored) > best_count:
            best = candidate
            best_count = len(stored)
    return best


def _store_package(
    db: Session,
    *,
    root: str,
    entries: list[dict[str, Any]],
    current_order: MolecularLibraryOrder | None,
    user_name: str,
    created_paths: list[Path],
    now: datetime,
) -> tuple[list[MolecularLibraryResultLink], dict[str, Any]]:
    name = package_name(root)
    prepared = []
    reasons: list[str] = []
    matched: list[tuple[dict[str, Any], MolecularLibraryOrder]] = []
    matched_keys: set[tuple[str, int]] = set()
    matched_order_ids: set[int] = set()
    for entry in entries:
        inner_path = entry["inner_path"]
        role = package_file_role(inner_path)
        entry["role"] = role
        prepared.append(entry)
        if current_order is not None:
            # 质检页：整包挂当前工单，只关联编号属于当前工单的测序文件
            if role != ROLE_READ:
                continue
            targets, _reason = _upload_targets(db, role, entry["filename"])
            if not any(target.id == current_order.id for target in targets):
                continue
            key = (entry["inner_path"], int(current_order.id))
            if key not in matched_keys:
                matched_keys.add(key)
                matched.append((entry, current_order))
            matched_order_ids.add(int(current_order.id))
            continue
        targets, reason = _upload_targets(db, role, entry["filename"])
        if role == ROLE_READ and not targets and reason:
            reasons.append(reason)
        for target in targets:
            key = (entry["inner_path"], int(target.id))
            if key not in matched_keys:
                matched_keys.add(key)
                matched.append((entry, target))
            matched_order_ids.add(int(target.id))

    if not prepared:
        return [], {
            "group_id": f"package:{root.casefold()}",
            "kind": "package",
            "source_path": root,
            "name": name,
            "outcome": "skipped",
            "linked": 0,
            "newly_linked": 0,
            "issues": _issue_rows(reasons or ["文件夹里没有可保存的文件"]),
        }
    normalized_paths = [entry["inner_path"].casefold() for entry in prepared]
    if len(normalized_paths) != len(set(normalized_paths)):
        raise ValueError(f"测序包 {name} 中存在重复相对路径")
    if current_order is None and not matched_order_ids:
        return [], {
            "group_id": f"package:{root.casefold()}",
            "kind": "package",
            "source_path": root,
            "name": name,
            "outcome": "skipped",
            "linked": 0,
            "newly_linked": 0,
            "issues": _issue_rows(reasons or ["测序包里没有文件能唯一匹配工单"]),
        }

    signature = package_signature(
        name,
        [
            (entry["inner_path"], entry["digest"], len(entry["content"]))
            for entry in prepared
        ],
    )
    package = db.scalar(
        select(MolecularLibraryResultPackage)
        .where(MolecularLibraryResultPackage.signature == signature)
        .with_for_update()
    )
    if package is None:
        package = _extendable_package(db, name, prepared)
    created = False
    if package is None:
        folder = f"{safe_path_part(name, 'package')}--{signature[:8]}"
        storage_prefix = f"{month_directory('sequencing', now)}/{folder}"
        candidate = MolecularLibraryResultPackage(
            original_name=name,
            signature=signature,
            storage_prefix=_storage_path(storage_prefix),
            uploaded_by=(user_name or "").strip() or None,
        )
        try:
            if db.get_bind().dialect.name == "sqlite":
                db.add(candidate)
                db.flush()
            else:
                with db.begin_nested():
                    db.add(candidate)
                    db.flush()
            package = candidate
            created = True
        except IntegrityError:
            package = db.scalar(
                select(MolecularLibraryResultPackage)
                .where(MolecularLibraryResultPackage.signature == signature)
                .with_for_update()
            )
            if package is None:
                raise
    if (
        current_order is not None
        and not matched
        and package.owner_order_id not in {None, current_order.id}
    ):
        return [], {
            "group_id": f"package:{root.casefold()}",
            "kind": "package",
            "source_path": root,
            "name": name,
            "outcome": "skipped",
            "linked": 0,
            "newly_linked": 0,
            "issues": _issue_rows(["相同文件夹已挂在其他工单"]),
        }

    storage_prefix = package.storage_prefix.lstrip("/")
    stored = {} if created else {
        str(record.relative_path or "").casefold(): record
        for record in _package_file_rows(db, package.id)
    }
    added = False
    for entry in prepared:
        path_key = entry["inner_path"].casefold()
        record = stored.get(path_key)
        if record is not None:
            if not _full_path(record.storage_path).exists():
                _place_shared_bytes(record.storage_path.lstrip("/"), entry["content"])
            continue
        relative = _place_bytes(
            f"{storage_prefix}/{_safe_inner_path(entry['inner_path'])}",
            entry["content"],
            created_paths,
        )
        stored[path_key] = _new_file_record(
            db,
            relative,
            entry["content"],
            entry["mime_type"],
            entry["digest"],
            package_id=package.id,
            relative_path=entry["inner_path"],
        )
        added = True

    links: list[MolecularLibraryResultLink] = []
    new_link_count = 0
    for entry, target in matched:
        record = stored[entry["inner_path"].casefold()]
        link = _existing_link(db, record, target)
        if link is None:
            status, sequence_target = (
                sequence_check(
                    entry["filename"],
                    entry["content"],
                    _configured_primers(db, target),
                )
                if entry["role"] == ROLE_READ else (None, None)
            )
            link = _attach_link(
                db,
                record,
                target,
                entry["filename"],
                user_name,
                status,
                sequence_target,
            )
            new_link_count += 1
        links.append(link)

    owner_added = False
    if current_order is not None:
        owner_added = package.owner_order_id is None
        if owner_added:
            package.owner_order_id = current_order.id
        if created:
            outcome = "stored" if matched else "pinned"
        elif new_link_count or added:
            outcome = "reused"
        elif owner_added:
            outcome = "pinned"
        else:
            outcome = "already"
    else:
        outcome = "stored" if created else ("reused" if new_link_count or added else "already")

    return links, {
        "group_id": f"package:{root.casefold()}",
        "kind": "package",
        "source_path": root,
        "id": package.id,
        "name": name,
        "outcome": outcome,
        "linked": len(matched),
        "newly_linked": new_link_count,
        "issues": _issue_rows(reasons),
    }


def _restrict_qc_page_loose_targets(
    targets: list[MolecularLibraryOrder],
    current_order: MolecularLibraryOrder,
) -> tuple[list[MolecularLibraryOrder], str]:
    """质检页零散文件只挂当前工单。明确属于其他工单的不保存。"""
    own = [item for item in targets if item.id == current_order.id]
    if own:
        return own, ""
    others = [item for item in targets if item.id != current_order.id]
    if not others:
        return [current_order], ""
    codes: list[str] = []
    for item in others:
        code = str(item.library_code or "").strip().upper()
        if code and code not in codes:
            codes.append(code)
    label = "、".join(codes) if codes else "其他工单"
    return [], f"建库编号 {label} 属于其他工单"


def _store_loose(
    db: Session,
    *,
    entry: dict[str, Any],
    current_order: MolecularLibraryOrder | None,
    user_name: str,
    created_paths: list[Path],
    now: datetime,
) -> tuple[list[MolecularLibraryResultLink], str, int]:
    role = loose_file_role(entry["path"], current_order=current_order is not None)
    filename = entry["filename"]
    targets, reason = _upload_targets(db, role, filename)
    if current_order is not None:
        targets, reason = _restrict_qc_page_loose_targets(targets, current_order)
    if not targets:
        return [], reason or "无法按建库编号归入工单", 0

    if role == ROLE_GEL:
        record = _get_or_create_gel_record(db, entry, now, created_paths)
        links = []
        new_count = 0
        for target in targets:
            link = _existing_link(db, record, target)
            if link is None:
                link = _attach_link(db, record, target, filename, user_name, None, None)
                new_count += 1
            links.append(link)
        return links, "", new_count

    links = []
    new_count = 0
    for target in targets:
        existing = _linked_same_file(
            db,
            entry["digest"],
            target.id,
            filename,
        )
        if existing is not None:
            links.append(existing)
            continue
        can_check = (
            role == ROLE_READ
            and bool(library_code_stem(filename))
            and read_direction(filename) in {"F", "R"}
        )
        status, sequence_target = (
            sequence_check(filename, entry["content"], _configured_primers(db, target))
            if can_check else (None, None)
        )
        new_count += 1
        relative = _place_bytes(
            f"{other_directory(target, now)}/{safe_path_part(filename, 'file')}",
            entry["content"],
            created_paths,
        )
        record = _new_file_record(
            db,
            relative,
            entry["content"],
            entry["mime_type"],
            entry["digest"],
        )
        links.append(
            _attach_link(
                db,
                record,
                target,
                filename,
                user_name,
                status,
                sequence_target,
            )
        )
    return links, "", new_count


def upload_file(
    db: Session,
    file_obj: UploadFile,
    order_id: int,
    user_name: str = "unknown",
) -> dict[str, Any]:
    result = upload_batch(
        db,
        [file_obj],
        [file_obj.filename or "file"],
        user_name,
        order_id,
    )
    if not result["items"]:
        issue = next(
            (
                issue["reason"]
                for summary in result["summary"]
                for issue in summary.get("issues", [])
            ),
            "文件未保存",
        )
        raise ValueError(issue)
    return result["items"][0]


def upload_batch(
    db: Session,
    files: list[UploadFile],
    relative_paths: list[str],
    user_name: str = "unknown",
    order_id: int | None = None,
) -> dict[str, Any]:
    if not files:
        raise ValueError("请选择文件")
    if len(files) > MAX_UPLOAD_FILES:
        raise ValueError(f"一次最多上传 {MAX_UPLOAD_FILES} 个文件")
    raw_paths = [
        relative_paths[index] if index < len(relative_paths) else (file_obj.filename or "file")
        for index, file_obj in enumerate(files)
    ]
    preliminary_summary: list[dict[str, Any]] = []
    if order_id is None:
        preflight = preflight_upload(db, raw_paths)
        accepted_indexes = preflight["accepted_indexes"]
        preliminary_summary = preflight["summary"]
        if not accepted_indexes:
            return {"items": [], "summary": preliminary_summary}
        files = [files[index] for index in accepted_indexes]
        raw_paths = [raw_paths[index] for index in accepted_indexes]

    prepared: list[dict[str, Any]] = []
    total_bytes = 0
    for index, file_obj in enumerate(files):
        filename, mime_type, content = _read_upload(file_obj, db)
        total_bytes += len(content)
        if total_bytes > MAX_BATCH_BYTES:
            raise ValueError("一次上传的文件总大小不能超过 500MB")
        raw_path = raw_paths[index] if index < len(raw_paths) else filename
        prepared.append({
            "filename": filename,
            "path": normalize_relative_path(raw_path, filename),
            "mime_type": mime_type,
            "content": content,
            "digest": _hash_bytes(content),
        })

    current_order = _load_order(db, order_id, for_update=True) if order_id else None
    paths = [entry["path"] for entry in prepared]
    path_plan = plan_upload_paths(paths)
    grouped = {
        group.root: [
            {**prepared[index], "inner_path": inner_path}
            for index, inner_path in group.entries
        ]
        for group in path_plan.packages
    }
    loose = [prepared[index] for index in path_plan.loose_indexes]

    created_paths: list[Path] = []
    links: list[MolecularLibraryResultLink] = []
    summary: list[dict[str, Any]] = []
    summary_order_ids: list[set[int]] = []
    now = datetime.now()
    try:
        for root, entries in grouped.items():
            stored_links, result = _store_package(
                db,
                root=root,
                entries=entries,
                current_order=current_order,
                user_name=user_name,
                created_paths=created_paths,
                now=now,
            )
            links.extend(stored_links)
            summary.append(result)
            summary_order_ids.append({int(link.order_id) for link in stored_links})
        loose_reasons: list[str] = []
        loose_links = []
        loose_new_count = 0
        for entry in loose:
            stored_links, reason, new_count = _store_loose(
                db,
                entry=entry,
                current_order=current_order,
                user_name=user_name,
                created_paths=created_paths,
                now=now,
            )
            loose_links.extend(stored_links)
            loose_new_count += new_count
            if reason:
                loose_reasons.append(reason)
        links.extend(loose_links)
        if loose or loose_reasons:
            summary.append({
                "group_id": "loose",
                "kind": "loose",
                "name": "零散文件",
                "outcome": (
                    "stored"
                    if loose_new_count
                    else "already"
                    if loose_links
                    else "skipped"
                ),
                "linked": len(loose_links),
                "newly_linked": loose_new_count,
                "issues": _issue_rows(loose_reasons),
            })
            summary_order_ids.append({int(link.order_id) for link in loose_links})
        _advance_linked_orders(db, links)
        for item, order_ids in zip(summary, summary_order_ids, strict=True):
            item["orders"] = _qc_order_rows(db, order_ids)
        db.commit()
    except Exception:
        db.rollback()
        for path in created_paths:
            try:
                relative = path.relative_to(_uploads_root()).as_posix()
                referenced = db.scalar(
                    select(MolecularLibraryResultFile.id).where(
                        MolecularLibraryResultFile.storage_path == _storage_path(relative)
                    )
                )
            except Exception:
                db.rollback()
                referenced = None
            if referenced is None:
                _remove_file_if_exists(path)
        raise
    items = []
    for link in links:
        db.refresh(link)
        record = db.get(MolecularLibraryResultFile, link.file_id)
        items.append(_link_payload(
            link,
            record,
            _count_file_links(db, record.id),
        ))
    return {
        "items": items,
        "summary": _merge_preflight_summary(summary, preliminary_summary),
    }


def _normalize_qc_region(value: Any) -> dict[str, float | str]:
    if not isinstance(value, dict):
        raise ValueError("质检区域格式不正确")
    try:
        region = {
            key: round(float(value[key]), 6)
            for key in ("x", "y", "width", "height")
        }
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("质检区域格式不正确") from exc
    if not all(math.isfinite(number) for number in region.values()):
        raise ValueError("质检区域格式不正确")
    if (
        region["x"] < 0
        or region["y"] < 0
        or region["width"] <= 0
        or region["height"] <= 0
        or region["x"] + region["width"] > 1.000001
        or region["y"] + region["height"] > 1.000001
    ):
        raise ValueError("质检区域必须位于图片范围内")
    label = str(value.get("label") or "").strip()
    if len(label) > 24:
        raise ValueError("质检区域名称不能超过 24 个字符")
    if label:
        region["label"] = label
    return region


def _normalize_qc_regions(value: Any) -> list[dict[str, float | str]] | None:
    if value in (None, ""):
        return None
    values = [value] if isinstance(value, dict) else value
    if not isinstance(values, list):
        raise ValueError("质检区域格式不正确")
    if len(values) > 20:
        raise ValueError("单个文件最多框选 20 个质检区域")
    regions = [_normalize_qc_region(item) for item in values]
    return regions or None


def _normalize_result_filename(value: Any, current_name: str) -> str:
    name = str(value or "").strip()
    if not name or Path(name).name != name or len(name) > 255:
        raise ValueError("文件名不正确")
    current_suffix = Path(current_name or "").suffix
    next_suffix = Path(name).suffix
    if current_suffix and not next_suffix:
        name = f"{name}{current_suffix}"
    elif next_suffix.lower() != current_suffix.lower():
        raise ValueError("改名时不能修改文件扩展名")
    return name


def _recheck_link_sequence(
    link: MolecularLibraryResultLink,
    record: MolecularLibraryResultFile,
    order: MolecularLibraryOrder,
    primers: dict[str, str],
) -> None:
    if extension_of(link.original_name) not in READ_EXTENSIONS:
        link.sequence_status = None
        link.sequence_target = None
        return
    path = _full_path(record.storage_path)
    if not path.exists():
        return
    status, target = sequence_check(link.original_name, path.read_bytes(), primers)
    link.sequence_status = status
    link.sequence_target = target


def _recheck_order_sequences(
    db: Session,
    order: MolecularLibraryOrder,
) -> None:
    rows = db.execute(
        select(MolecularLibraryResultLink, MolecularLibraryResultFile)
        .join(
            MolecularLibraryResultFile,
            MolecularLibraryResultFile.id == MolecularLibraryResultLink.file_id,
        )
        .where(
            MolecularLibraryResultLink.order_id == order.id,
        )
    ).all()
    primers = _configured_primers(db, order)
    for link, record in rows:
        _recheck_link_sequence(link, record, order, primers)


def update_file_link(
    db: Session,
    link_id: int,
    order_id: int,
    data: dict[str, Any],
) -> dict[str, Any]:
    order = _load_order(db, order_id)
    link = db.get(MolecularLibraryResultLink, int(link_id))
    if not link or link.order_id != order.id:
        raise ValueError(MISSING_FILE)
    if "qc_regions" in data:
        link.qc_regions = _normalize_qc_regions(data.get("qc_regions"))
    if "original_name" in data:
        link.original_name = _normalize_result_filename(
            data.get("original_name"),
            link.original_name,
        )
        record = db.get(MolecularLibraryResultFile, link.file_id)
        if record:
            _recheck_link_sequence(link, record, order, _configured_primers(db, order))
    if "is_final_qc" in data:
        link.is_final_qc = bool(data.get("is_final_qc"))
        if link.is_final_qc:
            others = db.scalars(
                select(MolecularLibraryResultLink).where(
                    MolecularLibraryResultLink.order_id == order.id,
                    MolecularLibraryResultLink.id != link.id,
                    MolecularLibraryResultLink.is_final_qc.is_(True),
                )
            ).all()
            for other in others:
                if other.original_name.casefold() == link.original_name.casefold():
                    other.is_final_qc = False
    if "original_name" in data or "is_final_qc" in data:
        db.flush()
        _advance_order_status(db, order)
    db.commit()
    db.refresh(link)
    record = db.get(MolecularLibraryResultFile, link.file_id)
    if not record:
        raise ValueError(MISSING_FILE)
    return _link_payload(
        link,
        record,
        _count_file_links(db, record.id),
    )


def _finish_file_delete(
    db: Session,
    orders: list[MolecularLibraryOrder | None],
    path: Path | None,
) -> bool:
    for order in orders:
        if order is not None:
            _advance_order_status(db, order)
    db.commit()
    return path is not None and _remove_file_if_exists(path)


def delete_file(db: Session, link_id: int, order_id: int | None = None) -> dict[str, Any]:
    link = db.get(MolecularLibraryResultLink, int(link_id))
    if not link:
        raise ValueError(MISSING_FILE)
    if order_id:
        _load_order(db, order_id)
        if link.order_id != int(order_id):
            raise ValueError(MISSING_FILE)
    record = db.get(MolecularLibraryResultFile, link.file_id)
    in_package = bool(record and record.package_id)
    affected_order = db.get(MolecularLibraryOrder, link.order_id)
    full_path: Path | None = None
    db.delete(link)
    db.flush()
    if record and not in_package and not _count_file_links(db, link.file_id):
        full_path = _full_path(record.storage_path)
        db.delete(record)
    return {
        "id": int(link_id),
        "file_deleted": _finish_file_delete(db, [affected_order], full_path),
    }


def delete_stored_file(db: Session, order_id: int, file_id: int) -> dict[str, Any]:
    """文件夹预览里删除：取消所有工单关联，并删除磁盘文件。"""
    order = _load_order(db, order_id)
    record = db.get(MolecularLibraryResultFile, int(file_id))
    if not record or not record.package_id:
        raise ValueError(MISSING_FILE)
    package = db.get(MolecularLibraryResultPackage, record.package_id)
    if not package:
        raise ValueError(MISSING_FILE)
    visible = package.owner_order_id == order.id or db.scalar(
        select(MolecularLibraryResultLink.id)
        .join(
            MolecularLibraryResultFile,
            MolecularLibraryResultFile.id == MolecularLibraryResultLink.file_id,
        )
        .where(
            MolecularLibraryResultFile.package_id == package.id,
            MolecularLibraryResultLink.order_id == order.id,
        )
        .limit(1)
    )
    if not visible:
        raise ValueError(MISSING_FILE)
    links = list(db.scalars(
        select(MolecularLibraryResultLink).where(
            MolecularLibraryResultLink.file_id == record.id
        )
    ).all())
    affected_ids = {int(link.order_id) for link in links}
    for link in links:
        db.delete(link)
    full_path = _full_path(record.storage_path)
    db.delete(record)
    db.flush()
    affected = [db.get(MolecularLibraryOrder, affected_id) for affected_id in affected_ids]
    return {
        "id": int(file_id),
        "file_deleted": _finish_file_delete(db, affected, full_path),
    }


def delete_package(db: Session, order_id: int, package_id: int) -> dict[str, Any]:
    order = _load_order(db, order_id)
    package = db.get(MolecularLibraryResultPackage, int(package_id))
    if not package:
        raise ValueError(MISSING_FILE)
    records = list(db.scalars(
        select(MolecularLibraryResultFile).where(
            MolecularLibraryResultFile.package_id == package.id
        )
    ).all())
    record_ids = [record.id for record in records]
    own_links = list(db.scalars(
        select(MolecularLibraryResultLink).where(
            MolecularLibraryResultLink.order_id == order.id,
            MolecularLibraryResultLink.file_id.in_(record_ids),
        )
    ).all()) if record_ids else []
    owns_package = package.owner_order_id == order.id or bool(own_links)
    if not owns_package:
        raise ValueError(MISSING_FILE)
    for link in own_links:
        db.delete(link)
    if package.owner_order_id == order.id:
        package.owner_order_id = None
    db.flush()
    remaining_links = int(
        db.scalar(
            select(func.count())
            .select_from(MolecularLibraryResultLink)
            .join(
                MolecularLibraryResultFile,
                MolecularLibraryResultFile.id == MolecularLibraryResultLink.file_id,
            )
            .where(MolecularLibraryResultFile.package_id == package.id)
        )
        or 0
    )
    package_deleted = not remaining_links and package.owner_order_id is None
    storage_dir = _full_path(package.storage_prefix)
    if package_deleted:
        for record in records:
            db.delete(record)
        db.delete(package)
    _advance_order_status(db, order)
    db.commit()
    if package_deleted:
        shutil.rmtree(storage_dir, ignore_errors=True)
    return {
        "id": int(package_id),
        "package_deleted": package_deleted,
        "unlinked": len(own_links),
    }


def get_stored_file(db: Session, file_id: int) -> tuple[str, Path]:
    record = db.get(MolecularLibraryResultFile, int(file_id))
    if not record or record.package_id is None:
        raise ValueError(MISSING_FILE)
    full_path = _full_path(record.storage_path)
    if not full_path.exists():
        raise ValueError("磁盘上找不到文件")
    name = (record.relative_path or Path(record.storage_path).name).rsplit("/", 1)[-1]
    return name, full_path


def get_download_record(
    db: Session,
    link_id: int,
) -> tuple[MolecularLibraryResultLink, Path]:
    link = db.get(MolecularLibraryResultLink, int(link_id))
    if not link:
        raise ValueError(MISSING_FILE)
    record = db.get(MolecularLibraryResultFile, link.file_id)
    if not record:
        raise ValueError(MISSING_FILE)
    full_path = _full_path(record.storage_path)
    if not full_path.exists():
        raise ValueError("磁盘上找不到文件")
    return link, full_path


def create_thumbnail(
    file_path: Path,
    width: int,
    height: int,
) -> tuple[BytesIO, str] | None:
    if file_path.suffix.lower() not in GEL_EXTENSIONS:
        return None
    try:
        with Image.open(file_path) as image:
            image.thumbnail((width, height), Image.Resampling.LANCZOS)
            output = BytesIO()
            image_format = image.format or "JPEG"
            image.save(output, format=image_format, quality=85)
    except (OSError, ValueError):
        return None
    output.seek(0)
    return output, f"image/{image_format.lower()}"


def read_trace_preview(file_path: Path) -> dict[str, Any]:
    """读取 ABI/AB1 峰图，返回给前端绘制所需的结构化数据。"""
    try:
        from Bio import SeqIO

        record = SeqIO.read(file_path, "abi")
        raw = record.annotations["abif_raw"]
        order_value = raw.get("FWO_1", b"GATC")
        order = (
            order_value.decode("ascii", "ignore")
            if isinstance(order_value, bytes)
            else str(order_value)
        )
        channels = {
            base: tuple(raw[f"DATA{9 + index}"])
            for index, base in enumerate(order[:4])
            if base in {"A", "C", "G", "T"} and f"DATA{9 + index}" in raw
        }
        if set(channels) != {"A", "C", "G", "T"}:
            raise ValueError("峰图中没有通道数据")
        sample_count = min(min(len(values) for values in channels.values()), 100_000)
        if sample_count < 2:
            raise ValueError("峰图通道数据不完整")
        base_calls = raw.get("PBAS2", bytes(str(record.seq), "ascii"))
        if isinstance(base_calls, bytes):
            base_calls = base_calls.decode("ascii", "ignore")
        base_positions = tuple(raw.get("PLOC2", ()))
        qualities = tuple(raw.get("PCON2", ()))
    except (KeyError, OSError, TypeError, ValueError) as exc:
        raise ValueError("ABI/AB1 峰图解析失败") from exc

    base_entries = [
        {
            "base": base,
            "position": int(position),
            "quality": int(qualities[index]) if index < len(qualities) else None,
        }
        for index, (base, position) in enumerate(zip(base_calls, base_positions))
        if 0 <= int(position) < sample_count
    ]
    percentile_step = max(1, sample_count // 20_000)
    values = sorted(
        value
        for channel in channels.values()
        for value in channel[:sample_count:percentile_step]
    )
    signal_max = max(values[min(int(len(values) * 0.995), len(values) - 1)], 1)
    average_spacing = (
        (base_entries[-1]["position"] - base_entries[0]["position"])
        / max(len(base_entries) - 1, 1)
        if len(base_entries) > 1
        else 12
    )
    return {
        "sample_count": sample_count,
        "signal_max": signal_max,
        "initial_window": min(
            sample_count - 1,
            max(300, int(average_spacing * 30)),
        ),
        "channels": {
            base: list(channels[base][:sample_count])
            for base in ("A", "C", "G", "T")
        },
        "bases": base_entries,
    }
