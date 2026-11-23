from sqlalchemy import select
from sqlalchemy.orm import Session

from db.external import get_cell_db
from models.cell_inventory import SamSample
from models.immunology import SerumImmProject


def get_cell_inventory_data(db: Session) -> dict:
    projects = db.scalars(select(SerumImmProject)).all()

    raw_target_projects: dict[str, list[dict]] = {}
    for project in projects:
        target_name = project.target_name
        if not target_name or project.target_type == "分泌":
            continue
        raw_target_projects.setdefault(target_name, []).append(
            {
                "experiment_id": project.experiment_id,
                "project_code": project.project_code,
                "project_name": project.project_name,
                "project_status": project.project_status,
                "target_name": project.target_name,
                "start_date": project.start_date,
                "owner": project.owner,
                "prep_status": project.prep_status,
            }
        )

    target_projects: dict[str, list[dict]] = {}
    target_upper_map: dict[str, str] = {}
    for target_name in raw_target_projects:
        target_upper = target_name.upper()
        if target_upper in target_upper_map:
            existing_name = target_upper_map[target_upper]
            existing_upper_count = sum(1 for char in existing_name if char.isupper())
            new_upper_count = sum(1 for char in target_name if char.isupper())
            if new_upper_count > existing_upper_count:
                target_upper_map[target_upper] = target_name
                target_projects[target_name] = raw_target_projects[target_name] + target_projects[existing_name]
                del target_projects[existing_name]
            else:
                target_projects[existing_name] += raw_target_projects[target_name]
        else:
            target_upper_map[target_upper] = target_name
            target_projects[target_name] = raw_target_projects[target_name]

    cell_db = next(get_cell_db())
    try:
        cells = cell_db.scalars(
            select(SamSample).where(
                SamSample.organId == "139",
                SamSample.sample_type == "Cell-细胞",
            )
        ).all()
    finally:
        cell_db.close()

    target_cells: dict[str, list[dict]] = {}
    for cell in cells:
        matched_target = _match_cell_target(cell, target_projects)
        if matched_target:
            target_cells.setdefault(matched_target, []).append(
                {
                    "id": cell.id,
                    "sample_no": cell.sample_no,
                    "samplename": cell.samplename,
                    "genus": cell.genus,
                    "batch_no": cell.batch_no,
                    "sample_storage_vol": float(cell.sample_storage_vol) if cell.sample_storage_vol else 0,
                    "target": cell.target,
                    "generations": cell.generations,
                }
            )

    return {
        "targets": [
            {"name": target_name, "project_count": len(target_projects[target_name])}
            for target_name in sorted(target_projects.keys())
        ],
        "projects": target_projects,
        "cells": target_cells,
    }


def _match_cell_target(cell: SamSample, target_projects: dict[str, list[dict]]) -> str | None:
    samplename = cell.samplename or ""
    target = cell.target or ""

    if target:
        target_upper = target.upper()
        for target_name in target_projects:
            if target_name.upper() == target_upper:
                return target_name

    if samplename:
        samplename_upper = samplename.upper()
        best_match = None
        best_match_length = 0
        for target_name in target_projects:
            target_upper = target_name.upper()
            if len(target_upper) >= 3 and target_upper in samplename_upper:
                match_pos = samplename_upper.find(target_upper)
                next_char_pos = match_pos + len(target_upper)
                next_char = samplename_upper[next_char_pos] if next_char_pos < len(samplename_upper) else ""
                if next_char.isdigit():
                    continue
                if len(target_upper) > best_match_length:
                    best_match = target_name
                    best_match_length = len(target_upper)
        if best_match:
            return best_match

    return target.upper() if target else None
