from __future__ import annotations

from typing import Any

from models.mega_automation import MegaFlowWorkOrder

from modules.mega_automation.content import (
    clean_text,
    get_order_content,
    iter_cell_columns,
    safe_list,
)

def well_payload(well: dict[str, Any], pc_names: dict[str, str]) -> dict[str, Any]:
    content_type = clean_text(well.get("content_type")).upper()
    sample_name = clean_text(well.get("sample_code")) or content_type
    pc_id = clean_text(well.get("pc_id")) or None
    return {
        "well_no": clean_text(well.get("well_no")),
        "sample_name": sample_name,
        "content_type": content_type or "SAMPLE",
        "pc_id": pc_id,
        "pc_name": pc_names.get(pc_id or "", ""),
        "batch": clean_text(well.get("batch")),
        "generation": clean_text(well.get("generation")),
    }


def build_dispatch_payload(order: MegaFlowWorkOrder, dispatch_id: str) -> dict[str, Any]:
    content = get_order_content(order)
    sample_plates = safe_list(content.get("sample_plates"))
    cell_plates = safe_list(content.get("cell_plates"))
    pc_infos = safe_list(content.get("pc_infos"))
    pc_names = {
        clean_text(pc.get("pc_id")): clean_text(pc.get("pc_name"))
        for pc in pc_infos
        if isinstance(pc, dict) and clean_text(pc.get("pc_id"))
    }

    cells_by_key = {
        f"{clean_text(cell.get('cell_plate_barcode'))}|{cell.get('column_no')}": cell
        for cell in iter_cell_columns(cell_plates)
    }

    projects: dict[tuple[str, str], dict[str, Any]] = {}
    cells_by_project: dict[tuple[tuple[str, str], str], dict[str, Any]] = {}
    for sample_plate in sample_plates:
        if not isinstance(sample_plate, dict):
            continue
        project_key = (
            clean_text(sample_plate.get("project_no")),
            clean_text(sample_plate.get("target")),
        )
        if project_key not in projects:
            projects[project_key] = {
                "project_no": project_key[0],
                "data_type": order.data_type,
                "extend_info": "",
                "experiment_date": "",
                "target": project_key[1],
                "secondary_antibody": [],
                "cell_board_infos": [],
            }
        antibody = clean_text(sample_plate.get("secondary_antibody")) or "人"
        if antibody not in projects[project_key]["secondary_antibody"]:
            projects[project_key]["secondary_antibody"].append(antibody)

        for cell_key in safe_list(sample_plate.get("cell_keys")):
            normalized_cell_key = clean_text(cell_key)
            cell = cells_by_key.get(normalized_cell_key)
            if not cell:
                continue
            grouped_key = (project_key, normalized_cell_key)
            cell_board_info = cells_by_project.get(grouped_key)
            if cell_board_info is None:
                cell_board_info = {
                    "cell_name": clean_text(cell.get("cell_name")),
                    "cell_type": clean_text(cell.get("cell_type")) or "正常",
                    "batch": clean_text(cell.get("batch")),
                    "generation": clean_text(cell.get("generation")),
                    "cell_plate_barcode": clean_text(cell.get("cell_plate_barcode")),
                    "cell_column_no": cell.get("column_no"),
                    "detect_board_infos": [],
                }
                cells_by_project[grouped_key] = cell_board_info
                projects[project_key]["cell_board_infos"].append(cell_board_info)
            cell_board_info["detect_board_infos"].append(
                {
                    "sample_code": clean_text(sample_plate.get("barcode")),
                    "secondary_antibody": antibody,
                    "cell_plate_barcode": clean_text(cell.get("cell_plate_barcode")),
                    "cell_column_no": cell.get("column_no"),
                    "well_infos": [
                        well_payload(well, pc_names)
                        for well in safe_list(sample_plate.get("wells"))
                        if isinstance(well, dict) and clean_text(well.get("well_no"))
                    ],
                }
            )

    return {
        "dispatch_id": dispatch_id,
        "order_infos": [
            {
                "order_no": order.order_no,
                "order_name": order.order_name or "",
                "priority": order.priority or "normal",
                "project_infos": list(projects.values()),
            }
        ],
    }
