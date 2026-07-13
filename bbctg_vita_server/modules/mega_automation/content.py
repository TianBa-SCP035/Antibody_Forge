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


def clean_text(value: Any) -> str:
    return str(value or "").strip()


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
                    "batch": "",
                    "generation": "",
                }
            )
    return wells


def default_cell_columns() -> list[dict[str, Any]]:
    return [
        {
            "column_no": index,
            "cell_name": "",
            "cell_type": "正常",
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
        "batch": clean_text(normalized.get("batch")),
        "generation": clean_text(normalized.get("generation")),
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


def normalize_sample_plates(sample_plates: list[Any]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for plate in safe_list(sample_plates):
        if not isinstance(plate, dict):
            continue
        plate_data = {key: value for key, value in plate.items() if key != "_rowKey"}
        cell_keys = [clean_text(key) for key in safe_list(plate_data.get("cell_keys")) if clean_text(key)]
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
                "secondary_antibody": clean_text(plate_data.get("secondary_antibody")) or "人",
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
            columns.append(
                {
                    "column_no": column_no,
                    "cell_type": clean_text(column.get("cell_type")) or "正常",
                    "cell_name": clean_text(column.get("cell_name")),
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
        remapped: list[str] = []
        for key in selected_cell_keys(plate):
            if "|" not in key:
                continue
            barcode, column_no = key.split("|", 1)
            canonical = alias_to_canonical.get(barcode, barcode)
            remapped.append(f"{canonical}|{column_no}")
        # 去重且保序
        seen: set[str] = set()
        unique_keys: list[str] = []
        for key in remapped:
            if key in seen:
                continue
            seen.add(key)
            unique_keys.append(key)
        plate["cell_keys"] = unique_keys


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


def selected_cell_keys(sample_plate: dict[str, Any]) -> list[str]:
    return [clean_text(key) for key in safe_list(sample_plate.get("cell_keys")) if clean_text(key)]


def build_content_body(data: dict[str, Any]) -> dict[str, Any]:
    base_info = safe_dict(data.get("base_info"))
    pc_infos, id_remap = normalize_pc_infos(safe_list(base_info.get("pc_infos")))
    sample_plates = remap_sample_plate_pc_ids(safe_list(data.get("sample_plates")), id_remap)
    sample_plates = normalize_sample_plates(sample_plates)
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
        "order_name": order.order_name or "",
        "order_no": order.order_no or "",
        "data_type": order.data_type or "TITER",
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

    data_type = clean_text(data.get("data_type") or (order.data_type if order else "TITER")) or "TITER"
    priority = clean_text(data.get("priority") or (order.priority if order else "normal")) or "normal"
    carrier = SimpleNamespace(
        order_name=clean_text(data.get("order_name") or base_info.get("order_name")),
        order_no=clean_text(data.get("order_no")),
        data_type=data_type,
        priority=priority,
        remark=clean_text(data.get("remark") or base_info.get("remark")),
    )
    return build_content_hash(carrier, content)


def _issue(field: str, message: str) -> dict[str, str]:
    return {"field": field, "message": message}


def validate_sample_plates(sample_plates: list[Any], data_type: str = "") -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    require_project_no = data_type == "TITER"
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
        if not clean_text(plate.get("barcode")):
            issues.append(_issue(f"{prefix}.barcode", f"样本板[{plate_index}]缺少条码"))
        if require_project_no and not clean_text(plate.get("project_no")):
            issues.append(_issue(f"{prefix}.project_no", f"样本板[{plate_index}]缺少项目号"))
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
        if not clean_text(plate.get("barcode")):
            issues.append(_issue(f"{prefix}.barcode", f"细胞板[{plate_index}]缺少二维码/条码"))
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
    named_cells = {
        f"{clean_text(cell.get('cell_plate_barcode'))}|{cell.get('column_no')}"
        for cell in iter_cell_columns(cell_plates)
    }
    issues: list[dict[str, str]] = []
    for plate_index, plate in enumerate(sample_plates, start=1):
        if not isinstance(plate, dict):
            continue
        idx = plate_index - 1
        keys = selected_cell_keys(plate)
        if not keys:
            issues.append(_issue(f"sample_plates.{idx}.cell_keys", f"样本板[{plate_index}]未选择检测细胞"))
            continue
        invalid_keys = [key for key in keys if key not in named_cells]
        if len(invalid_keys) == len(keys):
            issues.append(_issue(f"sample_plates.{idx}.cell_keys", f"样本板[{plate_index}]没有有效的检测细胞"))
            continue
        for cell_key in invalid_keys:
            issues.append(
                _issue(
                    f"sample_plates.{idx}.cell_keys",
                    f"样本板[{plate_index}]引用的细胞列无效：{cell_key}",
                )
            )
    return issues


def collect_validation_issues(
    data: dict[str, Any] | None = None,
    order: MegaFlowWorkOrder | None = None,
    *,
    content: dict[str, Any] | None = None,
) -> list[dict[str, str]]:
    """统一校验入口：返回带 field 的结构化问题列表。"""
    payload = safe_dict(data)
    if content is None:
        existing_content = get_order_content(order) if order else None
        if payload:
            content = build_content_body(payload)
        else:
            content = existing_content or {}

    order_no = clean_text(payload.get("order_no") or (order.order_no if order else ""))
    data_type = clean_text(
        payload.get("data_type") or (order.data_type if order else "TITER")
    ) or "TITER"
    sample_plates = safe_list(content.get("sample_plates"))
    cell_plates = safe_list(content.get("cell_plates"))

    issues: list[dict[str, str]] = []
    if not order_no:
        issues.append(_issue("order_no", "缺少订单编号"))
    issues.extend(validate_sample_plates(sample_plates, data_type))
    issues.extend(validate_cell_plates(cell_plates))
    issues.extend(validate_plate_barcodes(sample_plates, cell_plates))
    issues.extend(validate_pc_refs(content))
    issues.extend(validate_sample_cell_refs(sample_plates, cell_plates))
    return issues