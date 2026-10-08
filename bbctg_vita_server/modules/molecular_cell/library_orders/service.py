from datetime import date, datetime, time
from decimal import Decimal, InvalidOperation
from io import BytesIO
from pathlib import Path
import hashlib
import math
import re
import secrets
import string
from typing import Any

from fastapi import UploadFile
from PIL import Image
from sqlalchemy import String, cast, func, or_, select
from sqlalchemy.orm import Session

from core.config import get_settings
from integrations import drm_service
from models.discovery import DiscoveryWorkbench
from models.molecular_cell import (
    MolecularLibraryOrder,
    MolecularLibraryResultFile,
    MolecularLibraryResultLink,
    MolecularPrimerIndexCatalog,
)
from utils.workbench_queue import DEFAULT_PRIORITY, PRIORITY_ORDER

DISCOVERY_PLANNING = "规划中"
DISCOVERY_WAIT_BOOST = "待冲击"
DISCOVERY_WAIT_HARVEST = "待剖鼠"
DISCOVERY_WAIT_LIBRARY = "待建库"
DISCOVERY_WAIT_PHAGE = "待噬菌体"
DISCOVERY_WAIT_SEQ = "待测序"
DISCOVERY_DONE = "已完成"
DISCOVERY_CANCELLED = "已取消"

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
STATUS_DONE = "已完成"
STATUS_QC_FAIL = "质检不通过"
STATUS_CANCELLED = "已取消"
STATUS_OPTIONS = (
    STATUS_PENDING,
    STATUS_IN_PROGRESS,
    STATUS_WAIT_QC,
    STATUS_DONE,
    STATUS_QC_FAIL,
    STATUS_CANCELLED,
)
STATUS_TRANSITIONS = {
    STATUS_PENDING: {STATUS_PENDING, STATUS_IN_PROGRESS, STATUS_CANCELLED},
    STATUS_IN_PROGRESS: {STATUS_PENDING, STATUS_IN_PROGRESS, STATUS_WAIT_QC, STATUS_CANCELLED},
    STATUS_WAIT_QC: {
        STATUS_IN_PROGRESS,
        STATUS_WAIT_QC,
        STATUS_DONE,
        STATUS_QC_FAIL,
        STATUS_CANCELLED,
    },
    STATUS_QC_FAIL: {STATUS_IN_PROGRESS, STATUS_WAIT_QC, STATUS_QC_FAIL, STATUS_CANCELLED},
    STATUS_DONE: {STATUS_DONE},
    STATUS_CANCELLED: {STATUS_CANCELLED, STATUS_PENDING},
}

BUILD_PLATE = "plate_single_cell"
BUILD_POOLED_BCR = "pooled_bcr"
BUILD_PHAGE_DISPLAY = "phage_display"
BUILD_PHAGE_NGS = "phage_ngs"
BUILD_PERIPHERAL_BLOOD = "peripheral_blood_bcr"
BUILD_TYPE_ORDER = (
    BUILD_PLATE,
    BUILD_POOLED_BCR,
    BUILD_PHAGE_DISPLAY,
    BUILD_PHAGE_NGS,
    BUILD_PERIPHERAL_BLOOD,
)
BUILD_TYPE_LABELS = {
    BUILD_PLATE: "单细胞孔板",
    BUILD_POOLED_BCR: "混管 BCR",
    BUILD_PHAGE_DISPLAY: "噬菌体展示",
    BUILD_PHAGE_NGS: "噬菌体 NGS",
    BUILD_PERIPHERAL_BLOOD: "外周血 BCR",
}
BUILD_TYPE_HINTS = {
    BUILD_PLATE: "Beacon、达普打板的单细胞恢复",
    BUILD_POOLED_BCR: "达普打管样品的 BCR 扩增",
    BUILD_PHAGE_DISPLAY: "用于展示筛选的噬菌体建库",
    BUILD_PHAGE_NGS: "展示筛选产物的 NGS 建库",
    BUILD_PERIPHERAL_BLOOD: "外周血样品的 BCR 扩增",
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
    "RN": SAMPLE_NANO,
    "RN-KO": SAMPLE_NANO,
    "RL": SAMPLE_LITE,
    "RL-KO": SAMPLE_LITE,
}


def _auto_sample_type(mouse_model: Any) -> str | None:
    tokens = [
        item.strip().upper()
        for item in re.split(r"[,，、]", str(mouse_model or ""))
        if item.strip()
    ]
    if not tokens:
        return None
    return AUTO_SAMPLE_TYPES.get(tokens[0])


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

PROFILE_SOURCES = {
    BUILD_PLATE: (SOURCE_BEACON, SOURCE_DAPU_PLATE, SOURCE_BEACON_DAPU),
    BUILD_POOLED_BCR: (SOURCE_DAPU_TUBE,),
    BUILD_PHAGE_DISPLAY: (SOURCE_DIRECT,),
    BUILD_PHAGE_NGS: (SOURCE_PHAGE_DISPLAY, SOURCE_PHAGE_PANNING),
    BUILD_PERIPHERAL_BLOOD: (SOURCE_RETRO_BLOOD, SOURCE_OTHER_BLOOD),
}

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
    "pcr_started_at",
    "pcr_finished_at",
    "pcr_owner",
    "pcr_qc_owner",
    "transfected_at",
    "transfection_owner",
} | INDEX_FIELDS
POOLED_FIELDS = {
    "instrument_on",
    "positive_cell_count",
    "cell_type",
    "rna_location",
    "cdna_location",
    "library_location",
    "cdna_concentration",
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
PHAGE_DISPLAY_FIELDS = {
    "source_experiment_type",
    "project_goal",
    "instrument_on",
    "cell_type",
    "target_forms",
    "rna_location",
    "cdna_location",
    "library_location",
    "initial_library_size",
    "effective_library_size",
} | INDEX_FIELDS
PHAGE_NGS_FIELDS = {
    "source_experiment_type",
    "project_goal",
    "library_batch_no",
    "rna_location",
    "cdna_location",
    "library_location",
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
    "fragment_size_bp",
} | INDEX_FIELDS
PROFILE_FIELDS = {
    BUILD_PLATE: PLATE_FIELDS,
    BUILD_POOLED_BCR: POOLED_FIELDS,
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
    "mouse_model": 128,
    "positive_cell_count": 64,
    "cell_type": 64,
    "notebook_no": 64,
    "immunization_stage": 64,
    "library_batch_no": 64,
    "owner": 64,
    "pcr_owner": 64,
    "pcr_qc_owner": 64,
    "transfection_owner": 64,
    "rna_location": 255,
    "cdna_location": 255,
    "library_location": 255,
    "initial_library_size": 64,
    "effective_library_size": 64,
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
    "pcr_started_at",
    "pcr_finished_at",
    "transfected_at",
)
INTEGER_FIELDS = (
    "fragment_size_bp",
)
DECIMAL_FIELDS = (
    "cdna_concentration",
    "h_primer_concentration",
    "k_primer_concentration",
    "l_primer_concentration",
)
CATALOG_REFERENCE_FIELDS = (
    ("h_forward_primer_id", "h_forward_primer_name", None),
    ("h_reverse_primer_id", "h_reverse_primer_name", None),
    ("k_forward_primer_id", "k_forward_primer_name", None),
    ("k_reverse_primer_id", "k_reverse_primer_name", None),
    ("l_forward_primer_id", "l_forward_primer_name", None),
    ("l_reverse_primer_id", "l_reverse_primer_name", None),
    ("i7_catalog_id", "i7_name", "i7_sequence"),
    ("i5_catalog_id", "i5_name", "i5_sequence"),
)
INSTRUMENT_DATE_BUILDS = frozenset({BUILD_PLATE, BUILD_POOLED_BCR, BUILD_PHAGE_DISPLAY})
POSITIVE_CELL_COUNT_BUILDS = frozenset({BUILD_PLATE, BUILD_POOLED_BCR, BUILD_PERIPHERAL_BLOOD})

FIELD_LABELS = {
    "source_project_code": "项目编号",
    "study_type": "课题类型",
    "source_experiment_type": "实验类型",
    "project_goal": "实验目标",
    "target_name": "靶点",
    "target_codes": "靶点编号",
    "pm": "PM",
    "mouse_model": "归类鼠型",
    "sample_type": "样品类型",
    "sample_source": "样品来源",
    "received_on": "样品交接日期",
    "instrument_on": "上机日期",
    "positive_cell_count": "阳性细胞数",
    "fragment_size_bp": "片段大小",
    "status": "状态",
    "priority": "优先级",
    "owner": "负责人",
    "library_code": "建库编号",
}

FILE_KIND_PCR_QC = "PCR检测报告"
FILE_KIND_GEL = "胶图"
FILE_KIND_PRIMER_QC = "引物质检文件"
FILE_KIND_OTHER = "其他"
MAX_FILE_BYTES = 50 * 1024 * 1024
GEL_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".gif"}
PRIMER_QC_EXTENSIONS = {".ab1", ".abi", ".seq", ".clc", ".fasta", ".fa"}
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


def _normalize_nonnegative_int(value: Any, label: str) -> int | None:
    if value in (None, ""):
        return None
    try:
        number = Decimal(str(value).strip())
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"{label}必须是非负整数") from exc
    if not number.is_finite() or number < 0 or number != number.to_integral_value():
        raise ValueError(f"{label}必须是非负整数")
    return int(number)


def _normalize_nonnegative_decimal(value: Any, label: str) -> Decimal | None:
    if value in (None, ""):
        return None
    try:
        number = Decimal(str(value).strip())
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"{label}必须是非负数") from exc
    if not number.is_finite() or number < 0:
        raise ValueError(f"{label}必须是非负数")
    return number


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
    return max(page, 1), min(max(limit, 1), 200)


def _current_status(row: MolecularLibraryOrder) -> str:
    return str(row.status or "").strip() or STATUS_PENDING


def _clear_inapplicable_fields(row: MolecularLibraryOrder, build_type: str) -> None:
    allowed = PROFILE_FIELDS[build_type]
    for field in PROFILE_SCOPED_FIELDS - allowed:
        if field in {"target_forms", "plate_nos"}:
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
        if name_field in data:
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
        next_status = _normalize_status(data.get("status"))
        if next_status not in STATUS_TRANSITIONS[previous_status]:
            raise ValueError(f"状态不能从“{previous_status}”改为“{next_status}”")
        row.status = next_status

    if "priority" in data:
        row.priority = _normalize_priority(data.get("priority"))
    if "library_code" in data:
        row.library_code = _normalize_library_code(data.get("library_code"))
    if "target_codes" in data:
        row.target_codes = _normalize_string_list(data.get("target_codes"), "靶点编号")
    if "target_forms" in data:
        row.target_forms = _normalize_string_list(data.get("target_forms"), "靶点形式")
    if "plate_nos" in data:
        row.plate_nos = _normalize_string_list(data.get("plate_nos"), "板号")

    for field, max_len in STRING_FIELDS.items():
        if field == "library_code" or field not in data:
            continue
        if field in {"i7_sequence", "i5_sequence"}:
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
    elif "mouse_model" in data:
        auto_type = _auto_sample_type(row.mouse_model)
        if auto_type:
            row.sample_type = auto_type
    for field in DATE_FIELDS:
        if field in data:
            setattr(row, field, _normalize_date(data.get(field)))
    for field in INTEGER_FIELDS:
        if field in data:
            setattr(
                row,
                field,
                _normalize_nonnegative_int(data.get(field), FIELD_LABELS.get(field, field)),
            )
    for field in DECIMAL_FIELDS:
        if field in data:
            setattr(
                row,
                field,
                _normalize_nonnegative_decimal(data.get(field), FIELD_LABELS.get(field, field)),
            )

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
    for id_field, name_field, sequence_field in CATALOG_REFERENCE_FIELDS:
        _apply_catalog_reference(db, row, data, id_field, name_field, sequence_field)
    _validate_profile(row)


def _validate_profile(row: MolecularLibraryOrder) -> None:
    build_type = _normalize_build_type(row.build_type)
    _clear_inapplicable_fields(row, build_type)
    if row.sample_source and row.sample_source not in PROFILE_SOURCES[build_type]:
        raise ValueError("样品来源与建库类型不匹配")
    if build_type == BUILD_POOLED_BCR and row.cell_type:
        _normalize_choice(row.cell_type, CELL_TYPE_OPTIONS, "细胞类型")
    mode = row.index_mode
    if mode in (None, INDEX_NONE):
        row.i7_catalog_id = row.i7_name = row.i7_sequence = None
        row.i5_catalog_id = row.i5_name = row.i5_sequence = None
    elif mode == INDEX_I7:
        row.i5_catalog_id = row.i5_name = row.i5_sequence = None
    elif mode == INDEX_I5:
        row.i7_catalog_id = row.i7_name = row.i7_sequence = None


def get_meta() -> dict[str, Any]:
    return {
        "build_types": [
            {
                "code": code,
                "label": BUILD_TYPE_LABELS[code],
                "hint": BUILD_TYPE_HINTS[code],
                "fields": sorted(PROFILE_FIELDS[code]),
                "sample_sources": list(PROFILE_SOURCES[code]),
            }
            for code in BUILD_TYPE_ORDER
        ],
        "sample_sources": [
            {"code": code, "label": label}
            for code, label in SAMPLE_SOURCE_LABELS.items()
        ],
        "sample_types": [
            {"code": code, "label": label}
            for code, label in SAMPLE_TYPE_LABELS.items()
        ],
        "phage_experiment_types": list(PHAGE_EXPERIMENT_TYPES),
        "index_modes": [
            {"code": code, "label": label}
            for code, label in INDEX_MODE_LABELS.items()
        ],
        "statuses": list(STATUS_OPTIONS),
        "priorities": list(PRIORITY_ORDER),
        "qc_results": list(QC_RESULT_OPTIONS),
        "cell_types": list(CELL_TYPE_OPTIONS),
        "field_labels": FIELD_LABELS,
    }


def list_catalog(
    db: Session,
    query: str | None = None,
    family: str | None = None,
    limit: int = 100,
) -> dict[str, Any]:
    stmt = select(MolecularPrimerIndexCatalog).where(MolecularPrimerIndexCatalog.active.is_(True))
    text = str(query or "").strip()
    if text:
        like = f"%{text}%"
        stmt = stmt.where(
            or_(
                MolecularPrimerIndexCatalog.name.like(like),
                MolecularPrimerIndexCatalog.short_sequence.like(f"%{text.upper()}%"),
            )
        )
    family_text = str(family or "").strip()
    if family_text:
        stmt = stmt.where(MolecularPrimerIndexCatalog.family == family_text)
    rows = db.scalars(
        stmt.order_by(MolecularPrimerIndexCatalog.family, MolecularPrimerIndexCatalog.name)
        .limit(min(max(int(limit or 100), 1), 500))
    ).all()
    return {"items": [row.to_dict() for row in rows]}


def _contains(column, value: Any, *, upper: bool = False):
    text = str(value or "").strip()
    if not text:
        return None
    return column.like(f"%{text.upper() if upper else text}%")


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


def _append_datetime_range(
    filters: list,
    column,
    data: dict[str, Any],
    start_key: str,
    end_key: str,
) -> None:
    start = _normalize_date(data.get(start_key)) if data.get(start_key) else None
    end = _normalize_date(data.get(end_key)) if data.get(end_key) else None
    if start:
        filters.append(column >= datetime.combine(start, time.min))
    if end:
        filters.append(column <= datetime.combine(end, time.max))


def _apply_list_filters(stmt, data: dict[str, Any]):
    filters = []
    keyword = str(data.get("keyword") or "").strip()
    if keyword:
        like = f"%{keyword}%"
        filters.append(
            or_(
                MolecularLibraryOrder.library_code.like(f"%{keyword.upper()}%"),
                MolecularLibraryOrder.source_project_code.like(like),
                MolecularLibraryOrder.library_batch_no.like(like),
            )
        )
    target_clauses = []
    target_code = str(data.get("target") or "").strip()
    target_name = str(data.get("target_name") or "").strip()
    if target_code:
        target_clauses.append(
            cast(MolecularLibraryOrder.target_codes, String).like(f"%{target_code}%")
        )
    if target_name:
        target_clauses.append(MolecularLibraryOrder.target_name.like(f"%{target_name}%"))
    if target_clauses:
        filters.append(or_(*target_clauses))
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
        ("mouse_model", MolecularLibraryOrder.mouse_model),
    ):
        value = str(data.get(key) or "").strip()
        if value and value != "all":
            filters.append(column == value)
    priority = str(data.get("priority") or "").strip()
    if priority:
        filters.append(MolecularLibraryOrder.priority == _normalize_priority(priority))
    _append_date_range(
        filters,
        MolecularLibraryOrder.instrument_on,
        data,
        "instrument_on_start",
        "instrument_on_end",
    )
    _append_datetime_range(filters, MolecularLibraryOrder.started_at, data, "started_at_start", "started_at_end")
    _append_datetime_range(filters, MolecularLibraryOrder.finished_at, data, "finished_at_start", "finished_at_end")
    return stmt.where(*filters) if filters else stmt


def _list_stats(db: Session, payload: dict[str, Any]) -> dict[str, int]:
    stats = {code: 0 for code in BUILD_TYPE_ORDER}
    filtered = dict(payload or {})
    filtered.pop("build_type", None)
    stmt = _apply_list_filters(
        select(
            MolecularLibraryOrder.build_type,
            func.count(),
        )
        .select_from(MolecularLibraryOrder)
        .group_by(MolecularLibraryOrder.build_type),
        filtered,
    )
    for build_type, count in db.execute(stmt).all():
        number = int(count or 0)
        if build_type in stats:
            stats[build_type] += number
    return stats


def get_list(db: Session, data: dict[str, Any]) -> dict[str, Any]:
    payload = data or {}
    page, limit = _page_limit(payload)
    stmt = _apply_list_filters(select(MolecularLibraryOrder), payload)
    total = db.scalar(
        _apply_list_filters(select(func.count()).select_from(MolecularLibraryOrder), payload)
    ) or 0
    rows = db.scalars(
        stmt.order_by(MolecularLibraryOrder.id.desc())
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


def save(
    db: Session,
    data: dict[str, Any],
    created_by: str | None = None,
) -> dict[str, Any]:
    payload = dict(data or {})
    for protected in (
        "library_order_id",
        "source_discovery_id",
        "created_by",
    ):
        payload.pop(protected, None)
    row_id = _parse_row_id(payload.get("id"))
    if payload.get("id") not in (None, "") and row_id is None:
        raise ValueError("工单 ID 不正确")
    if row_id is None:
        build_type = _normalize_build_type(payload.get("build_type"))
        row = MolecularLibraryOrder(
            library_order_id=_next_library_order_id(db),
            build_type=build_type,
            status=STATUS_PENDING,
            priority=DEFAULT_PRIORITY,
            target_codes=[],
            target_forms=[],
            plate_nos=[],
            created_by=(created_by or "").strip() or None,
        )
        db.add(row)
    else:
        row = db.get(MolecularLibraryOrder, row_id)
        if not row:
            raise ValueError(MISSING_ROW)
    _apply_fields(db, row, payload)
    db.commit()
    db.refresh(row)
    return row.to_dict()


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
    for link in links:
        db.delete(link)
    db.flush()
    files_to_remove: list[Path] = []
    for file_id, record in records.items():
        remaining = _count_file_links(db, file_id)
        if not record or remaining:
            continue
        files_to_remove.append(_full_path(record.storage_path))
        db.delete(record)
    deleted_id = int(row.id)
    db.delete(row)
    db.commit()
    for path in files_to_remove:
        _remove_file_if_exists(path)
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
        "mouse_model": row.mouse_strain_category,
        "sample_type": _auto_sample_type(row.mouse_strain_category),
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
    has_beacon = "Beacon" in methods
    has_dapu = "达普" in methods
    if BUILD_PLATE not in existing_types:
        if has_beacon and has_dapu:
            suggested.append(
                {"build_type": BUILD_PLATE, "sample_source": SOURCE_BEACON_DAPU}
            )
        elif has_beacon:
            suggested.append(
                {"build_type": BUILD_PLATE, "sample_source": SOURCE_BEACON}
            )
    if "噬菌体" in methods and BUILD_PHAGE_DISPLAY not in existing_types:
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


def _validate_handoff_item(row: DiscoveryWorkbench, item: dict[str, Any]) -> tuple[str, str]:
    build_type = _normalize_build_type(item.get("build_type"))
    sample_source = str(
        _normalize_choice(
            item.get("sample_source"),
            PROFILE_SOURCES[build_type],
            "样品来源",
            nullable=False,
        )
    )
    if build_type in INSTRUMENT_DATE_BUILDS:
        if not str(row.harvest_date or "").strip():
            raise ValueError("请先在发现台填写剖鼠日期（将作为上机日期）")
    return build_type, sample_source


def _apply_discovery_status(row: DiscoveryWorkbench, created_types: list[str]) -> None:
    current = str(row.status or "").strip() or DISCOVERY_PLANNING
    if current in {DISCOVERY_DONE, DISCOVERY_CANCELLED, DISCOVERY_WAIT_SEQ}:
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
    if str(row.status or "").strip() in {DISCOVERY_DONE, DISCOVERY_CANCELLED}:
        raise ValueError("已完成或已取消的发现安排不能交接")
    normalized = [_validate_handoff_item(row, item) for item in raw_items]
    codes = row.target_codes if isinstance(row.target_codes, list) else []
    created: list[MolecularLibraryOrder] = []
    for build_type, sample_source in normalized:
        mouse_model = str(row.mouse_strain_category or "").strip() or None
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
            mouse_model=mouse_model,
            sample_type=_auto_sample_type(mouse_model),
            instrument_on=(
                _normalize_date(row.harvest_date)
                if build_type in INSTRUMENT_DATE_BUILDS
                else None
            ),
            positive_cell_count=(
                _normalize_text(row.positive_cell_count, STRING_FIELDS["positive_cell_count"])
                if build_type in POSITIVE_CELL_COUNT_BUILDS
                else None
            ),
            status=STATUS_PENDING,
            priority=row.priority or DEFAULT_PRIORITY,
            target_forms=[],
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
    ("归类鼠型", "mouse_model"),
    ("样品类型", "sample_type"),
    ("样品交接日期", "received_on"),
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
    ("PCR开始时间", "pcr_started_at"),
    ("PCR结束时间", "pcr_finished_at"),
    ("PCR操作人", "pcr_owner"),
    ("PCR检测人", "pcr_qc_owner"),
    ("转染时间", "transfected_at"),
    ("转染人", "transfection_owner"),
    ("RNA位置", "rna_location"),
    ("cDNA位置", "cdna_location"),
    ("文库位置", "library_location"),
    ("cDNA浓度", "cdna_concentration"),
    ("初始库容", "initial_library_size"),
    ("有效库容", "effective_library_size"),
    ("片段大小", "fragment_size_bp"),
    ("H正向引物", "h_forward_primer_name"),
    ("H反向引物", "h_reverse_primer_name"),
    ("H浓度", "h_primer_concentration"),
    ("K正向引物", "k_forward_primer_name"),
    ("K反向引物", "k_reverse_primer_name"),
    ("K浓度", "k_primer_concentration"),
    ("L正向引物", "l_forward_primer_name"),
    ("L反向引物", "l_reverse_primer_name"),
    ("L浓度", "l_primer_concentration"),
    ("Barcode方式", "index_mode"),
    ("i7名称", "i7_name"),
    ("i7序列", "i7_sequence"),
    ("i5名称", "i5_name"),
    ("i5序列", "i5_sequence"),
    ("质检结论", "qc_result"),
    ("质检人", "qc_owner"),
    ("质检日期", "qc_on"),
    ("质检说明", "qc_note"),
    ("备注", "remark"),
)


def export_list_workbook(db: Session, data: dict[str, Any]):
    from utils.excel import build_list_workbook, cell_text

    rows = db.scalars(
        _apply_list_filters(select(MolecularLibraryOrder), data or {}).order_by(
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
        for list_key in ("target_codes", "target_forms", "plate_nos"):
            if isinstance(item.get(list_key), list):
                item[list_key] = "、".join(item[list_key])
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
    suffix = Path(filename or "").suffix.lower()
    if suffix in GEL_EXTENSIONS:
        return FILE_KIND_GEL
    if suffix in PRIMER_QC_EXTENSIONS:
        return FILE_KIND_PRIMER_QC
    if suffix in {".xlsx", ".xls", ".csv", ".ppt", ".pptx"}:
        return FILE_KIND_PCR_QC
    return FILE_KIND_OTHER


def _load_order(db: Session, order_id: int) -> MolecularLibraryOrder:
    row = db.get(MolecularLibraryOrder, int(order_id))
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
        "result_kind": _infer_file_kind(link.original_name),
        "original_name": link.original_name,
        "is_final_qc": bool(link.is_final_qc),
        "qc_regions": link.qc_regions if isinstance(link.qc_regions, list) else [],
        "uploaded_by": link.uploaded_by,
        "created_at": link.to_dict()["created_at"],
        "mime_type": record.mime_type,
        "byte_size": record.byte_size,
        "linked_order_count": int(linked_order_count),
    }


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
        .where(MolecularLibraryResultLink.order_id == order.id)
        .order_by(
            MolecularLibraryResultLink.is_final_qc.desc(),
            MolecularLibraryResultLink.id.desc(),
        )
    ).all()
    return {
        "order": order.to_dict(),
        "items": [
            _link_payload(link, record, linked_order_count)
            for link, record, linked_order_count in rows
        ],
    }


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


def upload_file(
    db: Session,
    file_obj: UploadFile,
    order_id: int,
    user_name: str = "unknown",
) -> dict[str, Any]:
    order = _load_order(db, order_id)
    filename = Path(file_obj.filename or "").name
    if not filename:
        raise ValueError("缺少文件名")
    content = file_obj.file.read(MAX_FILE_BYTES + 1)
    if not content:
        raise ValueError("文件内容为空")
    if len(content) > MAX_FILE_BYTES:
        raise ValueError("文件不能超过 50MB")
    now = datetime.now()
    extension = Path(filename).suffix.lower()
    uploads_root = Path(get_settings().repository_root) / "uploads"
    temp_path = (
        uploads_root
        / "library_results"
        / ".tmp"
        / f"{secrets.token_hex(16)}{extension}"
    )
    created_path: Path | None = None
    try:
        _write_content(temp_path, content)
        drm_service.decrypt_upload_file_if_available(db, temp_path)
        stored_content = temp_path.read_bytes()
        digest = _hash_bytes(stored_content)
        record = db.scalar(
            select(MolecularLibraryResultFile).where(
                MolecularLibraryResultFile.sha256 == digest
            )
        )
        if record is None:
            relative = (
                f"library_results/{now.strftime('%Y')}/{now.strftime('%m')}/"
                f"{digest}{extension}"
            )
            full_path = uploads_root / relative
            full_path.parent.mkdir(parents=True, exist_ok=True)
            temp_path.replace(full_path)
            created_path = full_path
            record = MolecularLibraryResultFile(
                storage_path=f"/{relative.replace(chr(92), '/')}",
                mime_type=file_obj.content_type,
                byte_size=len(stored_content),
                sha256=digest,
            )
            db.add(record)
            db.flush()
        else:
            existing_path = _full_path(record.storage_path)
            if not existing_path.exists():
                existing_path.parent.mkdir(parents=True, exist_ok=True)
                temp_path.replace(existing_path)
                created_path = existing_path
            else:
                _remove_file_if_exists(temp_path)
        link = db.scalar(
            select(MolecularLibraryResultLink).where(
                MolecularLibraryResultLink.file_id == record.id,
                MolecularLibraryResultLink.order_id == order.id,
            )
        )
        if link is None:
            link = MolecularLibraryResultLink(
                file_id=record.id,
                order_id=order.id,
                original_name=filename,
                uploaded_by=(user_name or "").strip() or None,
            )
            db.add(link)
        else:
            link.original_name = filename
            link.uploaded_by = (user_name or "").strip() or None
        db.commit()
    except Exception:
        db.rollback()
        _remove_file_if_exists(temp_path)
        if created_path is not None:
            _remove_file_if_exists(created_path)
        raise
    db.refresh(link)
    return _link_payload(link, record, _count_file_links(db, record.id))


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
    if "is_final_qc" in data:
        link.is_final_qc = bool(data.get("is_final_qc"))
    if "qc_regions" in data:
        link.qc_regions = _normalize_qc_regions(data.get("qc_regions"))
    if "original_name" in data:
        link.original_name = _normalize_result_filename(
            data.get("original_name"),
            link.original_name,
        )
    db.commit()
    db.refresh(link)
    record = db.get(MolecularLibraryResultFile, link.file_id)
    if not record:
        raise ValueError(MISSING_FILE)
    return _link_payload(link, record, _count_file_links(db, record.id))


def delete_file(db: Session, link_id: int, order_id: int | None = None) -> dict[str, Any]:
    link = db.get(MolecularLibraryResultLink, int(link_id))
    if not link:
        raise ValueError(MISSING_FILE)
    if order_id:
        _load_order(db, order_id)
        if link.order_id != int(order_id):
            raise ValueError(MISSING_FILE)
    record = db.get(MolecularLibraryResultFile, link.file_id)
    full_path: Path | None = None
    db.delete(link)
    db.flush()
    remaining = _count_file_links(db, link.file_id)
    if record and not remaining:
        full_path = _full_path(record.storage_path)
        db.delete(record)
    db.commit()
    file_deleted = full_path is not None and _remove_file_if_exists(full_path)
    return {"id": int(link_id), "file_deleted": file_deleted}


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
