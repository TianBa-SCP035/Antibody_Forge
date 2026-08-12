from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from models.target import Target


TARGET_SOURCE_SQL = text(
    """
    SELECT
      id AS external_id,
      snum,
      name,
      type,
      status,
      ko_lethal_info,
      ko_lethal_info_desc,
      structure_feature,
      shape_remark,
      structure_feature_remark,
      ko_mgi,
      ko_impc,
      effect_cell,
      ko_gt,
      official_full_name,
      human_gene_official_name,
      human_gene_alias_name,
      human_ncbi_gene_id,
      human_chromosome_position,
      is_homologous_gene,
      mouse_gene_official_name,
      mouse_gene_alias_name,
      mouse_ncbi_gene_id,
      mouse_chromosome_position,
      human_mouse_homology,
      human_dog_homology,
      human_cat_homology,
      human_monkey_homology,
      human_mouse_homology_expect_functional_domain,
      gene_functional_desc,
      is_ko_affect_humoral_immunity,
      is_ko_affect_humoral_immunity_desc,
      is_human_mouse_cross,
      indication,
      gene_family,
      signal_path,
      remark
    FROM xdida_platform_biocytogen.target
    """
)

INTEGER_FIELDS = frozenset({"type", "status", "ko_lethal_info"})
BOOLEAN_FIELDS = frozenset({"is_homologous_gene", "is_ko_affect_humoral_immunity"})
TEXT_FIELDS = (
    "snum",
    "name",
    "ko_lethal_info_desc",
    "structure_feature",
    "shape_remark",
    "structure_feature_remark",
    "ko_mgi",
    "ko_impc",
    "effect_cell",
    "ko_gt",
    "official_full_name",
    "human_gene_official_name",
    "human_gene_alias_name",
    "human_ncbi_gene_id",
    "human_chromosome_position",
    "mouse_gene_official_name",
    "mouse_gene_alias_name",
    "mouse_ncbi_gene_id",
    "mouse_chromosome_position",
    "human_mouse_homology",
    "human_dog_homology",
    "human_cat_homology",
    "human_monkey_homology",
    "human_mouse_homology_expect_functional_domain",
    "gene_functional_desc",
    "is_ko_affect_humoral_immunity_desc",
    "is_human_mouse_cross",
    "indication",
    "gene_family",
    "signal_path",
    "remark",
)


def sync_targets(db: Session, source_db: Session, *, dry_run: bool = False) -> dict[str, Any]:
    """全量同步外部靶点主数据；外部表只读，本地缺失记录仅停用不删除。"""
    source_rows = source_db.execute(TARGET_SOURCE_SQL).mappings().all()
    if not source_rows:
        raise ValueError("外部靶点表未返回数据，已取消同步")

    existing_targets = db.scalars(select(Target)).all()
    targets_by_external_id = {target.external_id: target for target in existing_targets}
    targets_by_snum = {target.snum: target for target in existing_targets}
    seen_external_ids: set[int] = set()
    synced_at = datetime.now()
    result: dict[str, Any] = {
        "source_total": len(source_rows),
        "valid": 0,
        "created": 0,
        "updated": 0,
        "unchanged": 0,
        "reactivated": 0,
        "deactivated": 0,
        "skipped": {
            "missing_external_id": 0,
            "missing_snum": 0,
            "missing_name": 0,
            "identity_conflict": 0,
        },
    }

    for row in source_rows:
        external_id = _to_int(row.get("external_id"))
        snum = _clean(row.get("snum"))
        name = _clean(row.get("name"))
        if external_id is None:
            result["skipped"]["missing_external_id"] += 1
            continue
        if not snum:
            result["skipped"]["missing_snum"] += 1
            continue
        if not name:
            result["skipped"]["missing_name"] += 1
            continue

        seen_external_ids.add(external_id)
        result["valid"] += 1
        values = _target_values(row)
        values["snum"] = snum
        values["name"] = name
        target = targets_by_external_id.get(external_id)
        target_by_snum = targets_by_snum.get(snum)
        if target is not None and target_by_snum is not None and target_by_snum is not target:
            result["skipped"]["identity_conflict"] += 1
            continue
        rebound = False
        if target is None and target_by_snum is not None:
            target = target_by_snum
            targets_by_external_id.pop(target.external_id, None)
            target.external_id = external_id
            targets_by_external_id[external_id] = target
            rebound = True
        if target is None:
            target = Target(
                external_id=external_id,
                **values,
                is_active=True,
                synced_at=synced_at,
            )
            db.add(target)
            targets_by_external_id[external_id] = target
            targets_by_snum[snum] = target
            result["created"] += 1
            continue

        old_snum = target.snum
        changed = _apply_values(target, values) or rebound
        if old_snum != target.snum:
            targets_by_snum.pop(old_snum, None)
            targets_by_snum[target.snum] = target
        if not target.is_active:
            target.is_active = True
            result["reactivated"] += 1
            changed = True
        target.synced_at = synced_at
        if changed:
            result["updated"] += 1
        else:
            result["unchanged"] += 1

    for target in existing_targets:
        if target.external_id not in seen_external_ids and target.is_active:
            target.is_active = False
            target.synced_at = synced_at
            result["deactivated"] += 1

    if dry_run:
        db.rollback()
    else:
        db.commit()
    return result


def _target_values(row: Any) -> dict[str, Any]:
    values = {field: _clean(row.get(field)) for field in TEXT_FIELDS}
    values.update({field: _to_int(row.get(field)) for field in INTEGER_FIELDS})
    values.update({field: _to_bool(row.get(field)) for field in BOOLEAN_FIELDS})
    return values


def _apply_values(target: Target, values: dict[str, Any]) -> bool:
    changed = False
    for field, value in values.items():
        if getattr(target, field) != value:
            setattr(target, field, value)
            changed = True
    return changed


def _clean(value: Any) -> str | None:
    if value is None:
        return None
    cleaned = str(value).strip()
    return cleaned or None


def _to_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _to_bool(value: Any) -> bool | None:
    parsed = _to_int(value)
    if parsed is None:
        return None
    return bool(parsed)
