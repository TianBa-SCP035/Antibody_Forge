from __future__ import annotations

from datetime import datetime
import hashlib
import json
import random
import re
from typing import Any

from models.mega_automation import MegaFlowWorkOrder

WELL_RE = re.compile(r"^[A-H](0[1-9]|1[0-2])$")
WELL_TYPES = frozenset({"SAMPLE", "PC", "NC", "ISO", "TAG", "BLANK"})
PC_INFO_TYPE_OPTIONS = {"SERUM", "ISO", "TAG"}
WELL_PC_REF_TYPES = {"PC", "ISO", "TAG"}
SAMPLE_BARCODE_RE = re.compile(r"^[A-Za-z0-9()\-]+$")
IDENTIFIER_RE = re.compile(r"^[A-Za-z0-9()_\-]+$")
SAMPLE_CODE_RE = IDENTIFIER_RE
_HIDDEN_RE = re.compile(r"[\x00-\x1f\x7f\u200b\u200c\u200d\ufeff\u2060]")
CELL_CONTENT_FIELDS = (
    "cell_name",
    "cell_type",
    "species",
    "batch",
    "generation",
    "cell_count",
    "catalog_no",
    "source",
)


def clean_text(value: Any) -> str:
    """去掉首尾空白，以及回车、制表符、零宽字符这类粘贴进来的隐藏字符。"""
    return _HIDDEN_RE.sub("", str(value or "")).strip()


def default_secondary_antibody(order_type: Any) -> str:
    return "鼠" if clean_text(order_type).upper() == "TITER" else "人"


def build_cell_key(barcode: Any, column_no: Any) -> dict[str, Any] | None:
    barcode_text = clean_text(barcode)
    try:
        parsed_column = int(column_no)
    except (TypeError, ValueError):
        return None
    if not barcode_text or parsed_column <= 0:
        return None
    return {"barcode": barcode_text, "column_no": parsed_column}


def safe_list(value: Any) -> list:
    return value if isinstance(value, list) else []


def safe_dict(value: Any) -> dict:
    return value if isinstance(value, dict) else {}


def unique_strings(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            result.append(value)
    return result


def format_well(row_index: int, col_index: int) -> str:
    return f"{chr(65 + row_index)}{col_index + 1:02d}"


EXPECTED_WELLS = frozenset(format_well(row, column) for row in range(8) for column in range(12))


def default_sample_wells() -> list[dict[str, Any]]:
    wells: list[dict[str, Any]] = []
    for row_index in range(8):
        for col_index in range(12):
            well_no = format_well(row_index, col_index)
            content_type = "PC" if col_index == 11 else "SAMPLE"
            wells.append(
                {
                    "well_no": well_no,
                    "content_type": content_type,
                    "sample_code": "" if content_type == "PC" else well_no,
                    "pc_id": None,
                }
            )
    return wells


def default_cell_columns() -> list[dict[str, Any]]:
    return [
        {
            "column_no": index,
            "cell_name": "",
            "cell_type": "",
            "batch": "",
            "generation": "",
            "species": "",
            "cell_count": "",
            "catalog_no": "",
            "source": "",
        }
        for index in range(1, 13)
    ]


def generate_pc_id(existing_ids: set[str]) -> str:
    for _ in range(30):
        candidate = str(random.randint(100000, 999999999))
        if candidate not in existing_ids:
            return candidate
    return f"{int(datetime.now().timestamp() * 1000)}{random.randint(100, 999)}"


def normalize_pc_infos(pc_infos: list[Any]) -> tuple[list[dict[str, Any]], dict[str, str]]:
    normalized: list[dict[str, Any]] = []
    id_remap: dict[str, str] = {}
    existing_ids: set[str] = set()

    for pc in pc_infos:
        if not isinstance(pc, dict):
            continue
        raw_id = clean_text(pc.get("pc_id"))
        if not raw_id or raw_id.startswith("tmp-"):
            new_id = generate_pc_id(existing_ids)
            if raw_id:
                id_remap[raw_id] = new_id
            pc_id = new_id
        else:
            pc_id = raw_id
        existing_ids.add(pc_id)
        pc_type = clean_text(pc.get("pc_type")).upper() or "SERUM"
        normalized.append(
            {
                "pc_id": pc_id,
                "pc_type": pc_type,
                "pc_name": clean_text(pc.get("pc_name")),
                "catalog_batch": clean_text(pc.get("catalog_batch")),
                "source": clean_text(pc.get("source")),
                "concentration": clean_text(pc.get("concentration")),
            }
        )
    return normalized, id_remap


def normalize_well(well: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(well or {})
    well_type = clean_text(normalized.get("content_type") or "SAMPLE").upper()
    pc_id = clean_text(normalized.get("pc_id")) or None
    if well_type not in WELL_PC_REF_TYPES:
        pc_id = None
    return {
        "well_no": clean_text(normalized.get("well_no")),
        "content_type": well_type,
        "sample_code": clean_text(normalized.get("sample_code")),
        "pc_id": pc_id,
    }


def remap_sample_plate_pc_ids(sample_plates: list[Any], id_remap: dict[str, str]) -> list[dict[str, Any]]:
    plates: list[dict[str, Any]] = []
    for plate in safe_list(sample_plates):
        if not isinstance(plate, dict):
            continue
        plate_data = {key: value for key, value in plate.items() if key != "_rowKey"}
        wells: list[dict[str, Any]] = []
        for well in safe_list(plate.get("wells")):
            if not isinstance(well, dict):
                continue
            well_data = dict(well)
            pc_id = clean_text(well_data.get("pc_id"))
            if pc_id and pc_id in id_remap:
                pc_id = id_remap[pc_id]
            well_data["pc_id"] = pc_id or None
            well_data.pop("pc_name", None)
            wells.append(well_data)
        plate_data["wells"] = wells
        plates.append(plate_data)
    return plates


def normalize_sample_plates(
    sample_plates: list[Any],
    *,
    order_type: str = "",
) -> list[dict[str, Any]]:
    antibody_default = default_secondary_antibody(order_type)
    result: list[dict[str, Any]] = []
    for plate in safe_list(sample_plates):
        if not isinstance(plate, dict):
            continue
        plate_data = {key: value for key, value in plate.items() if key != "_rowKey"}
        cell_keys: list[dict[str, Any]] = []
        seen_keys: set[tuple[str, int]] = set()
        for raw_key in safe_list(plate_data.get("cell_keys")):
            if not isinstance(raw_key, dict):
                continue
            key = build_cell_key(raw_key.get("barcode"), raw_key.get("column_no"))
            if not key:
                continue
            identity = (key["barcode"], key["column_no"])
            if identity in seen_keys:
                continue
            seen_keys.add(identity)
            cell_keys.append(key)
        wells = [
            normalize_well(well)
            for well in safe_list(plate_data.get("wells"))
            if isinstance(well, dict)
        ]
        result.append(
            {
                "barcode": clean_text(plate_data.get("barcode")),
                "project_no": clean_text(plate_data.get("project_no")),
                "target": clean_text(plate_data.get("target")),
                "secondary_antibody": clean_text(plate_data.get("secondary_antibody")) or antibody_default,
                "cell_keys": cell_keys,
                "wells": wells,
            }
        )
    return result


def normalize_cell_plates(cell_plates: list[Any]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for plate in safe_list(cell_plates):
        if not isinstance(plate, dict):
            continue
        columns: list[dict[str, Any]] = []
        for column in safe_list(plate.get("columns")):
            if not isinstance(column, dict):
                continue
            try:
                column_no = int(column.get("column_no") or 0)
            except (TypeError, ValueError):
                column_no = 0
            cell_name = clean_text(column.get("cell_name"))
            cell_type = clean_text(column.get("cell_type"))
            if cell_name:
                cell_type = cell_type or "正常"
            else:
                cell_type = ""
            columns.append(
                {
                    "column_no": column_no,
                    "cell_type": cell_type,
                    "cell_name": cell_name,
                    "species": clean_text(column.get("species")),
                    "batch": clean_text(column.get("batch")),
                    "generation": clean_text(column.get("generation")),
                    "cell_count": clean_text(column.get("cell_count")),
                    "catalog_no": clean_text(column.get("catalog_no")),
                    "source": clean_text(column.get("source")),
                }
            )
        columns.sort(key=lambda item: item["column_no"])
        result.append(
            {
                "barcode": clean_text(plate.get("barcode")),
                "columns": columns,
            }
        )
    return result


def canonicalize_sample_cell_keys(
    sample_plates: list[dict[str, Any]],
    cell_plates: list[dict[str, Any]],
) -> None:
    """把 cell_keys 里的占位条码（细胞板N）归一到当前真实条码，避免先选细胞后填条码导致引用失效。"""
    alias_to_canonical: dict[str, str] = {}
    for index, plate in enumerate(cell_plates):
        if not isinstance(plate, dict):
            continue
        fallback = f"细胞板{index + 1}"
        canonical = cell_plate_display_barcode(plate, index)
        alias_to_canonical[fallback] = canonical
        if clean_text(plate.get("barcode")):
            alias_to_canonical[canonical] = canonical

    for plate in sample_plates:
        if not isinstance(plate, dict):
            continue
        remapped: list[dict[str, Any]] = []
        seen: set[tuple[str, int]] = set()
        for key in safe_list(plate.get("cell_keys")):
            if not isinstance(key, dict):
                continue
            remapped_key = build_cell_key(
                alias_to_canonical.get(key.get("barcode"), key.get("barcode")),
                key.get("column_no"),
            )
            if not remapped_key:
                continue
            identity = (remapped_key["barcode"], remapped_key["column_no"])
            if identity in seen:
                continue
            seen.add(identity)
            remapped.append(remapped_key)
        plate["cell_keys"] = remapped


def cell_plate_display_barcode(plate: dict[str, Any], index: int) -> str:
    return clean_text(plate.get("barcode")) or f"细胞板{index + 1}"


def iter_cell_columns(cell_plates: list[Any]) -> list[dict[str, Any]]:
    columns: list[dict[str, Any]] = []
    for index, plate in enumerate(cell_plates):
        if not isinstance(plate, dict):
            continue
        plate_barcode = cell_plate_display_barcode(plate, index)
        for column in safe_list(plate.get("columns")):
            if not isinstance(column, dict):
                continue
            if not clean_text(column.get("cell_name")):
                continue
            item = dict(column)
            item["cell_plate_barcode"] = plate_barcode
            try:
                item["column_no"] = int(item.get("column_no") or len(columns) + 1)
            except (TypeError, ValueError):
                item["column_no"] = len(columns) + 1
            columns.append(item)
    return columns


def selected_cell_keys(sample_plate: dict[str, Any]) -> list[dict[str, Any]]:
    keys: list[dict[str, Any]] = []
    for raw_key in safe_list(sample_plate.get("cell_keys")):
        if not isinstance(raw_key, dict):
            continue
        key = build_cell_key(raw_key.get("barcode"), raw_key.get("column_no"))
        if key:
            keys.append(key)
    return keys


def build_content_body(data: dict[str, Any]) -> dict[str, Any]:
    base_info = safe_dict(data.get("base_info"))
    order_type = clean_text(data.get("orderType")) or "TITER"
    pc_infos, id_remap = normalize_pc_infos(safe_list(base_info.get("pc_infos")))
    sample_plates = remap_sample_plate_pc_ids(safe_list(data.get("sample_plates")), id_remap)
    sample_plates = normalize_sample_plates(sample_plates, order_type=order_type)
    cell_plates = normalize_cell_plates(safe_list(data.get("cell_plates")))
    canonicalize_sample_cell_keys(sample_plates, cell_plates)
    return {
        "pc_infos": pc_infos,
        "sample_plates": sample_plates,
        "cell_plates": cell_plates,
    }


def extract_search_arrays(content: dict[str, Any]) -> dict[str, list[str]]:
    sample_plates = safe_list(content.get("sample_plates"))
    cell_plates = safe_list(content.get("cell_plates"))
    project_nos = unique_strings(
        [clean_text(plate.get("project_no")) for plate in sample_plates if isinstance(plate, dict)]
    )
    targets = unique_strings(
        [clean_text(plate.get("target")) for plate in sample_plates if isinstance(plate, dict)]
    )
    sample_barcodes = unique_strings(
        [clean_text(plate.get("barcode")) for plate in sample_plates if isinstance(plate, dict)]
    )
    cell_barcodes = unique_strings(
        [
            cell_plate_display_barcode(plate, index)
            for index, plate in enumerate(cell_plates)
            if isinstance(plate, dict) and clean_text(plate.get("barcode"))
        ]
    )
    return {
        "project_nos": project_nos,
        "targets": targets,
        "sample_plate_barcodes": sample_barcodes,
        "cell_plate_barcodes": cell_barcodes,
    }


def hash_dict(data: dict[str, Any]) -> str:
    payload = json.dumps(data, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def build_content_hash(order: MegaFlowWorkOrder, content: dict[str, Any]) -> str:
    canonical = {
        "orderName": order.orderName or "",
        "orderNum": order.orderNum or "",
        "orderType": order.orderType or "TITER",
        "priority": order.priority or "normal",
        "remark": order.remark or "",
        "content": content,
    }
    return hash_dict(canonical)


def get_order_content(order: MegaFlowWorkOrder) -> dict[str, Any]:
    return safe_dict(order.content)


def compute_hash_from_payload(data: dict[str, Any], order: MegaFlowWorkOrder | None = None) -> str:
    base_info = safe_dict(data.get("base_info"))
    content = build_content_body(data)
    from types import SimpleNamespace

    orderType = clean_text(data.get("orderType") or (order.orderType if order else "TITER")) or "TITER"
    priority = clean_text(data.get("priority") or (order.priority if order else "normal")) or "normal"
    carrier = SimpleNamespace(
        orderName=clean_text(data.get("orderName") or base_info.get("orderName")),
        orderNum=clean_text(data.get("orderNum")),
        orderType=orderType,
        priority=priority,
        remark=clean_text(data.get("remark") or base_info.get("remark")),
    )
    return build_content_hash(carrier, content)


def _issue(field: str, message: str) -> dict[str, str]:
    return {"field": field, "message": message}


def validate_sample_plates(sample_plates: list[Any]) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    barcodes = [clean_text(item.get("barcode")) for item in sample_plates if isinstance(item, dict)]
    if not any(barcodes):
        issues.append(_issue("sample_plates", "至少需要一个样本板条码"))
    duplicates = [value for value in unique_strings(barcodes) if barcodes.count(value) > 1]
    if duplicates:
        issues.append(_issue("sample_plates", f"样本板条码重复：{', '.join(duplicates)}"))

    for plate_index, plate in enumerate(sample_plates, start=1):
        idx = plate_index - 1
        prefix = f"sample_plates.{idx}"
        if not isinstance(plate, dict):
            issues.append(_issue(prefix, f"样本板[{plate_index}]格式不正确"))
            continue
        barcode = clean_text(plate.get("barcode"))
        if not barcode:
            issues.append(_issue(f"{prefix}.barcode", f"样本板[{plate_index}]缺少条码"))
        elif not SAMPLE_BARCODE_RE.match(barcode):
            if "_" in barcode:
                message = f"样本板[{plate_index}]条码不能包含下划线"
            else:
                message = f"样本板[{plate_index}]条码只能包含字母、数字、英文括号和中划线"
            issues.append(_issue(f"{prefix}.barcode", message))
        project_no = clean_text(plate.get("project_no"))
        if not project_no:
            issues.append(_issue(f"{prefix}.project_no", f"样本板[{plate_index}]缺少项目号"))
        elif not IDENTIFIER_RE.match(project_no):
            issues.append(
                _issue(
                    f"{prefix}.project_no",
                    f"样本板[{plate_index}]项目号只能包含字母、数字、英文括号、下划线和中划线",
                )
            )
        if not clean_text(plate.get("target")):
            issues.append(_issue(f"{prefix}.target", f"样本板[{plate_index}]缺少靶点"))

        wells = safe_list(plate.get("wells"))
        if len(wells) != 96:
            issues.append(_issue(f"{prefix}.wells", f"样本板[{plate_index}]必须恰好包含 96 个孔位"))
        well_nos = [clean_text(well.get("well_no")) for well in wells if isinstance(well, dict)]
        invalid = [well for well in well_nos if not WELL_RE.match(well)]
        if invalid:
            issues.append(
                _issue(f"{prefix}.wells", f"样本板[{plate_index}]孔位格式错误：{', '.join(invalid[:5])}")
            )
        dup_wells = [value for value in unique_strings(well_nos) if well_nos.count(value) > 1]
        if dup_wells:
            issues.append(
                _issue(f"{prefix}.wells", f"样本板[{plate_index}]孔位重复：{', '.join(dup_wells[:5])}")
            )
        missing = sorted(EXPECTED_WELLS - set(well_nos))
        if missing:
            issues.append(
                _issue(f"{prefix}.wells", f"样本板[{plate_index}]缺少标准孔位：{', '.join(missing[:5])}")
            )
        for well_index, well in enumerate(wells):
            if not isinstance(well, dict):
                issues.append(_issue(f"{prefix}.wells.{well_index}", "孔位必须是对象"))
                continue
            well_type = clean_text(well.get("content_type")).upper()
            if well_type not in WELL_TYPES:
                issues.append(
                    _issue(
                        f"{prefix}.wells.{well_index}.content_type",
                        f"样本板[{plate_index}]孔位类型不合法：{well_type or '空'}",
                    )
                )
            sample_code = clean_text(well.get("sample_code"))
            if sample_code and not SAMPLE_CODE_RE.match(sample_code):
                well_no = clean_text(well.get("well_no")) or str(well_index + 1)
                issues.append(
                    _issue(
                        f"{prefix}.wells.{well_index}.sample_code",
                        f"样本板[{plate_index}]孔位 {well_no} 的样本编码只能包含字母、数字、英文括号、下划线和中划线",
                    )
                )
    return issues


def validate_cell_plates(cell_plates: list[Any]) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    if not iter_cell_columns(cell_plates):
        issues.append(_issue("cell_plates", "至少需要一个已填写名称的细胞列"))
    barcodes = [clean_text(item.get("barcode")) for item in cell_plates if isinstance(item, dict)]
    duplicates = [value for value in unique_strings(barcodes) if value and barcodes.count(value) > 1]
    if duplicates:
        issues.append(_issue("cell_plates", f"细胞板条码重复：{', '.join(duplicates)}"))

    for plate_index, plate in enumerate(cell_plates, start=1):
        idx = plate_index - 1
        prefix = f"cell_plates.{idx}"
        if not isinstance(plate, dict):
            issues.append(_issue(prefix, f"细胞板[{plate_index}]格式不正确"))
            continue
        cell_barcode = clean_text(plate.get("barcode"))
        if not cell_barcode:
            issues.append(_issue(f"{prefix}.barcode", f"细胞板[{plate_index}]缺少二维码/条码"))
        elif not IDENTIFIER_RE.match(cell_barcode):
            issues.append(
                _issue(
                    f"{prefix}.barcode",
                    f"细胞板[{plate_index}]条码只能包含字母、数字、英文括号、下划线和中划线",
                )
            )
        columns = safe_list(plate.get("columns"))
        if len(columns) != 12:
            issues.append(_issue(f"{prefix}.columns", f"细胞板[{plate_index}]必须恰好包含 12 列"))
        column_nos: list[int] = []
        for column_index, column in enumerate(columns):
            if not isinstance(column, dict):
                issues.append(_issue(f"{prefix}.columns.{column_index}", "细胞列必须是对象"))
                continue
            try:
                col_no = int(column.get("column_no") or 0)
            except (TypeError, ValueError):
                col_no = 0
            column_nos.append(col_no)
            col_field = f"{prefix}.columns.{column_index}"
            if col_no < 1 or col_no > 12:
                issues.append(_issue(col_field, f"细胞板[{plate_index}]列号必须在 1-12 之间"))
            if clean_text(column.get("cell_name")) and not clean_text(column.get("cell_type")):
                issues.append(
                    _issue(f"{col_field}.cell_type", f"细胞板[{plate_index}]第 {col_no} 列缺少细胞类型")
                )
        duplicate_columns = [value for value in sorted(set(column_nos)) if column_nos.count(value) > 1]
        if duplicate_columns:
            issues.append(
                _issue(f"{prefix}.columns", f"细胞板[{plate_index}]列号重复：{duplicate_columns}")
            )
        if set(column_nos) != set(range(1, 13)):
            issues.append(_issue(f"{prefix}.columns", f"细胞板[{plate_index}]列号必须完整覆盖 1-12"))
    return issues


def validate_plate_barcodes(sample_plates: list[Any], cell_plates: list[Any]) -> list[dict[str, str]]:
    sample_barcodes = {
        clean_text(plate.get("barcode")) for plate in sample_plates if isinstance(plate, dict)
    }
    cell_barcodes = {
        clean_text(plate.get("barcode")) for plate in cell_plates if isinstance(plate, dict)
    }
    duplicates = sorted((sample_barcodes & cell_barcodes) - {""})
    if not duplicates:
        return []
    return [_issue("cell_plates", f"样本板与细胞板条码不能重复：{', '.join(duplicates)}")]


def validate_pc_refs(content: dict[str, Any]) -> list[dict[str, str]]:
    pc_infos = safe_list(content.get("pc_infos"))
    pc_types: dict[str, str] = {}
    issues: list[dict[str, str]] = []
    for index, pc in enumerate(pc_infos):
        if not isinstance(pc, dict):
            continue
        pc_id = clean_text(pc.get("pc_id"))
        pc_type = clean_text(pc.get("pc_type")).upper()
        if pc_type not in PC_INFO_TYPE_OPTIONS:
            issues.append(_issue(f"pc_infos.{index}.pc_type", f"PC 类型不合法：{pc_type or '空'}"))
        if pc_id and pc_id in pc_types:
            issues.append(_issue(f"pc_infos.{index}.pc_id", f"PC 编号重复：{pc_id}"))
        if pc_id:
            pc_types[pc_id] = pc_type

    expected_types = {"PC": "SERUM", "ISO": "ISO", "TAG": "TAG"}
    for plate_index, plate in enumerate(safe_list(content.get("sample_plates"))):
        if not isinstance(plate, dict):
            continue
        for well_index, well in enumerate(safe_list(plate.get("wells"))):
            if not isinstance(well, dict):
                continue
            pc_id = clean_text(well.get("pc_id"))
            well_type = clean_text(well.get("content_type")).upper()
            if not pc_id:
                continue
            field = f"sample_plates.{plate_index}.wells.{well_index}.pc_id"
            if pc_id not in pc_types:
                issues.append(_issue(field, f"孔位引用的 PC 不存在：{pc_id}"))
                continue
            expected = expected_types.get(well_type)
            if expected and pc_types[pc_id] != expected:
                issues.append(_issue(field, f"{well_type} 孔位引用了不匹配的 PC 类型"))
    return issues


def validate_sample_cell_refs(sample_plates: list[Any], cell_plates: list[Any]) -> list[dict[str, str]]:
    """样本板必须选择至少一个有效细胞列。"""
    named_by_key = {
        (key["barcode"], key["column_no"]): cell
        for cell in iter_cell_columns(cell_plates)
        if (key := build_cell_key(cell.get("cell_plate_barcode"), cell.get("column_no")))
    }
    named_cells = set(named_by_key)
    issues: list[dict[str, str]] = []
    for plate_index, plate in enumerate(sample_plates, start=1):
        if not isinstance(plate, dict):
            continue
        idx = plate_index - 1
        keys = selected_cell_keys(plate)
        if not keys:
            issues.append(_issue(f"sample_plates.{idx}.cell_keys", f"样本板[{plate_index}]未选择检测细胞"))
            continue
        barcodes = {key["barcode"] for key in keys}
        if len(barcodes) > 1:
            issues.append(
                _issue(
                    f"sample_plates.{idx}.cell_keys",
                    f"样本板[{plate_index}]只能选择同一块细胞板上的列",
                )
            )
        invalid_keys = [key for key in keys if (key["barcode"], key["column_no"]) not in named_cells]
        if len(invalid_keys) == len(keys):
            issues.append(_issue(f"sample_plates.{idx}.cell_keys", f"样本板[{plate_index}]没有有效的检测细胞"))
            continue
        for cell_key in invalid_keys:
            issues.append(
                _issue(
                    f"sample_plates.{idx}.cell_keys",
                    f"样本板[{plate_index}]引用的细胞列无效："
                    f"{cell_key['barcode']} 列{cell_key['column_no']}",
                )
            )
        names = [
            clean_text(named_by_key[(cell_key["barcode"], cell_key["column_no"])].get("cell_name"))
            for cell_key in keys
            if (cell_key["barcode"], cell_key["column_no"]) in named_by_key
        ]
        names = [name for name in names if name]
        duplicates = [value for value in unique_strings(names) if names.count(value) > 1]
        if duplicates:
            issues.append(
                _issue(
                    f"sample_plates.{idx}.cell_keys",
                    f"样本板[{plate_index}]的细胞名称重复：{', '.join(duplicates)}",
                )
            )
    return issues


def validate_pcr_control_plates(sample_plates: list[Any], order_type: Any) -> list[dict[str, str]]:
    """每个靶点至少有一块条码以 -PC 结尾的对照样本板。仅 PCR。"""
    if clean_text(order_type).upper() != "PCR":
        return []
    covered: dict[str, bool] = {}
    for plate in sample_plates:
        if not isinstance(plate, dict):
            continue
        target = clean_text(plate.get("target"))
        if not target:
            continue
        covered.setdefault(target, False)
        if clean_text(plate.get("barcode")).endswith("-PC"):
            covered[target] = True
    missing = [target for target, ok in covered.items() if not ok]
    if not missing:
        return []
    return [_issue("sample_plates", f"PCR 靶点缺少以 -PC 结尾的对照板：{', '.join(missing)}")]


def _column_snapshot(column: dict[str, Any]) -> dict[str, str]:
    return {field: clean_text(column.get(field)) for field in CELL_CONTENT_FIELDS}


def _column_completeness(snapshot: dict[str, str]) -> int:
    return sum(1 for value in snapshot.values() if value)


def _pick_column_record(records: list[dict[str, Any]]) -> dict[str, Any]:
    return max(
        records,
        key=lambda item: (
            int(item.get("completeness") or 0),
            str(item.get("updated_at") or ""),
            int(item.get("id") or 0),
        ),
    )


def _usage_column(
    column_no: int,
    winner: dict[str, Any],
    used_records: list[dict[str, Any]],
    *,
    locked: bool,
    conflict: bool,
) -> dict[str, Any]:
    used_by: list[dict[str, Any]] = []
    seen_ids: set[Any] = set()
    for item in used_records:
        identity = item.get("id")
        if identity in seen_ids:
            continue
        seen_ids.add(identity)
        used_by.append(
            {
                "id": identity,
                "orderNum": item.get("orderNum") or "",
                "status": item.get("status") or "",
            }
        )
    return {
        "column_no": column_no,
        "locked": locked,
        "conflict": conflict,
        "source_order_id": winner.get("id"),
        "source_order_num": winner.get("orderNum") or "",
        "used_by": used_by,
        **winner["column"],
    }


def resolve_cell_plate_usage(barcode: str, peers: list[dict[str, Any]]) -> dict[str, Any]:
    """汇总其他订单里同一细胞板的列：被选中的列锁定，只填写过的列供带入。"""
    barcode_text = clean_text(barcode)
    used_by_column: dict[int, list[dict[str, Any]]] = {}
    filled_by_column: dict[int, list[dict[str, Any]]] = {}

    for peer in peers:
        content = safe_dict(peer.get("content"))
        selected: set[int] = set()
        for plate in safe_list(content.get("sample_plates")):
            if not isinstance(plate, dict):
                continue
            for key in selected_cell_keys(plate):
                if key["barcode"] == barcode_text:
                    selected.add(int(key["column_no"]))
        order_meta = {
            "id": peer.get("id"),
            "orderNum": clean_text(peer.get("orderNum")),
            "status": clean_text(peer.get("status")),
            "updated_at": peer.get("updated_at") or "",
        }
        for plate in safe_list(content.get("cell_plates")):
            if not isinstance(plate, dict) or clean_text(plate.get("barcode")) != barcode_text:
                continue
            for column in safe_list(plate.get("columns")):
                if not isinstance(column, dict):
                    continue
                try:
                    column_no = int(column.get("column_no") or 0)
                except (TypeError, ValueError):
                    continue
                if column_no < 1 or column_no > 12:
                    continue
                snapshot = _column_snapshot(column)
                if _column_completeness(snapshot) == 0:
                    continue
                record = {
                    **order_meta,
                    "column": snapshot,
                    "completeness": _column_completeness(snapshot),
                }
                target = used_by_column if column_no in selected else filled_by_column
                target.setdefault(column_no, []).append(record)

    columns: list[dict[str, Any]] = []
    for column_no in range(1, 13):
        used = used_by_column.get(column_no) or []
        filled = filled_by_column.get(column_no) or []
        pool = used or filled
        if not pool:
            continue
        winner = _pick_column_record(pool)
        names = {item["column"]["cell_name"] for item in pool if item["column"]["cell_name"]}
        types = {item["column"]["cell_type"] for item in pool if item["column"]["cell_type"]}
        columns.append(
            _usage_column(
                column_no,
                winner,
                used,
                locked=bool(used),
                conflict=len(names) > 1 or len(types) > 1,
            )
        )
    return {"barcode": barcode_text, "columns": columns}


def _locked_columns(usage: dict[str, Any] | None) -> dict[int, dict[str, Any]]:
    if not usage:
        return {}
    locked: dict[int, dict[str, Any]] = {}
    for column in safe_list(usage.get("columns")):
        if isinstance(column, dict) and column.get("locked"):
            try:
                locked[int(column.get("column_no") or 0)] = column
            except (TypeError, ValueError):
                continue
    return locked


def _used_by_label(column: dict[str, Any]) -> str:
    numbers = [
        clean_text(item.get("orderNum"))
        for item in safe_list(column.get("used_by"))
        if isinstance(item, dict)
    ]
    numbers = [item for item in numbers if item]
    if numbers:
        return "、".join(numbers)
    return clean_text(column.get("source_order_num")) or "其他订单"


def validate_cell_column_occupancy(
    sample_plates: list[Any],
    cell_plates: list[Any],
    usage_by_barcode: dict[str, dict[str, Any]] | None,
) -> list[dict[str, str]]:
    """已被其他订单选中的细胞列不能再选，也不能改成另一套细胞信息。"""
    if not usage_by_barcode:
        return []
    issues: list[dict[str, str]] = []
    locked_by_barcode = {
        barcode: _locked_columns(usage) for barcode, usage in usage_by_barcode.items()
    }
    for plate_index, plate in enumerate(cell_plates):
        if not isinstance(plate, dict):
            continue
        barcode = clean_text(plate.get("barcode"))
        locked = locked_by_barcode.get(barcode) or {}
        for column_index, column in enumerate(safe_list(plate.get("columns"))):
            if not isinstance(column, dict):
                continue
            try:
                column_no = int(column.get("column_no") or 0)
            except (TypeError, ValueError):
                continue
            remote = locked.get(column_no)
            if not remote:
                continue
            local = _column_snapshot(column)
            if _column_completeness(local) == 0:
                continue
            if any(local[field] != clean_text(remote.get(field)) for field in CELL_CONTENT_FIELDS):
                issues.append(
                    _issue(
                        f"cell_plates.{plate_index}.columns.{column_index}.cell_name",
                        f"细胞板 {barcode} 第 {column_no} 列已被订单 {_used_by_label(remote)} 使用，不能修改该列信息",
                    )
                )
    for plate_index, plate in enumerate(sample_plates, start=1):
        if not isinstance(plate, dict):
            continue
        idx = plate_index - 1
        for cell_key in selected_cell_keys(plate):
            remote = (locked_by_barcode.get(cell_key["barcode"]) or {}).get(cell_key["column_no"])
            if not remote:
                continue
            issues.append(
                _issue(
                    f"sample_plates.{idx}.cell_keys",
                    f"样本板[{plate_index}]不能使用细胞板 {cell_key['barcode']} 第 {cell_key['column_no']} 列，"
                    f"该列已被订单 {_used_by_label(remote)} 使用",
                )
            )
    return issues


def collect_validation_issues(
    data: dict[str, Any] | None = None,
    order: MegaFlowWorkOrder | None = None,
    *,
    content: dict[str, Any] | None = None,
    column_usage: dict[str, dict[str, Any]] | None = None,
) -> list[dict[str, str]]:
    """统一校验入口：返回带 field 的结构化问题列表。"""
    payload = safe_dict(data)
    if content is None:
        existing_content = get_order_content(order) if order else None
        if payload:
            content = build_content_body(payload)
        else:
            content = existing_content or {}

    orderNum = clean_text(payload.get("orderNum") or (order.orderNum if order else ""))
    order_type = clean_text(payload.get("orderType") or (order.orderType if order else "") or "TITER") or "TITER"
    sample_plates = safe_list(content.get("sample_plates"))
    cell_plates = safe_list(content.get("cell_plates"))

    issues: list[dict[str, str]] = []
    if not orderNum:
        issues.append(_issue("orderNum", "缺少订单编号"))
    issues.extend(validate_sample_plates(sample_plates))
    issues.extend(validate_cell_plates(cell_plates))
    issues.extend(validate_plate_barcodes(sample_plates, cell_plates))
    issues.extend(validate_pc_refs(content))
    issues.extend(validate_sample_cell_refs(sample_plates, cell_plates))
    issues.extend(validate_pcr_control_plates(sample_plates, order_type))
    issues.extend(validate_cell_column_occupancy(sample_plates, cell_plates, column_usage))
    return issues