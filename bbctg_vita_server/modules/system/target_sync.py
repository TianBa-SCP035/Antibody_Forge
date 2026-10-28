from __future__ import annotations

from typing import Any

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from models.target import Target
from utils.filter_values import clean_field_text
from utils.target_structure import (
    enrich_missing_targets,
    is_meaningful_structure_feature,
    is_transmembrane_property,
)


TARGET_SOURCE_SQL = text(
    """
    SELECT
      t.id AS external_id,
      t.snum,
      t.name,
      t.type,
      t.status,
      category_tag.sname AS category,
      t.ko_lethal_info,
      t.ko_lethal_info_desc,
      structure_tag.sname AS structural_properties,
      t.structure_feature,
      t.shape_remark,
      t.structure_feature_remark,
      t.ko_mgi,
      t.ko_impc,
      t.effect_cell,
      t.ko_gt,
      t.official_full_name,
      t.human_gene_official_name,
      t.human_gene_alias_name,
      t.human_ncbi_gene_id,
      t.human_chromosome_position,
      t.is_homologous_gene,
      t.mouse_gene_official_name,
      t.mouse_gene_alias_name,
      t.mouse_ncbi_gene_id,
      t.mouse_chromosome_position,
      t.human_mouse_homology,
      t.human_dog_homology,
      t.human_cat_homology,
      t.human_monkey_homology,
      t.human_mouse_homology_expect_functional_domain,
      t.gene_functional_desc,
      t.is_ko_affect_humoral_immunity,
      t.is_ko_affect_humoral_immunity_desc,
      t.is_human_mouse_cross,
      treatment_tags.treatment_field,
      t.indication,
      t.gene_family,
      t.signal_path,
      t.remark
    FROM xdida_platform_biocytogen.target AS t
    LEFT JOIN xdida_platform_biocytogen.org_tag AS category_tag
      ON category_tag.id = t.sort
    LEFT JOIN xdida_platform_biocytogen.org_tag AS structure_tag
      ON structure_tag.id = t.structural_properties
    LEFT JOIN (
      SELECT
        target_tag.target_id,
        GROUP_CONCAT(
          DISTINCT org_tag.sname
          ORDER BY org_tag.order_by, org_tag.id
          SEPARATOR ', '
        ) AS treatment_field
      FROM xdida_platform_biocytogen.target_tag AS target_tag
      INNER JOIN xdida_platform_biocytogen.org_tag AS org_tag
        ON org_tag.id = target_tag.tag_id
      WHERE org_tag.tag_type = 36
        AND org_tag.is_delete = 0
      GROUP BY target_tag.target_id
    ) AS treatment_tags
      ON treatment_tags.target_id = t.id
    """
)

INTEGER_FIELDS = frozenset({"type", "status", "ko_lethal_info"})
BOOLEAN_FIELDS = frozenset({"is_homologous_gene", "is_ko_affect_humoral_immunity"})
TEXT_FIELDS = (
    "snum",
    "name",
    "category",
    "ko_lethal_info_desc",
    "structural_properties",
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
    "treatment_field",
    "indication",
    "gene_family",
    "signal_path",
    "remark",
)


GENE_IDENTITY_FIELDS = (
    "name",
    "human_ncbi_gene_id",
    "mouse_ncbi_gene_id",
    "human_gene_official_name",
    "mouse_gene_official_name",
)


def sync_targets(
    db: Session,
    source_db: Session,
    *,
    dry_run: bool = False,
    enrich_uniprot: bool = False,
) -> dict[str, Any]:
    """全量同步外部靶点主数据；外部表只读，本地缺失记录仅停用不删除。"""
    source_rows = source_db.execute(TARGET_SOURCE_SQL).mappings().all()
    if not source_rows:
        raise ValueError("外部靶点表未返回数据，已取消同步")

    existing_targets = db.scalars(select(Target)).all()
    targets_by_external_id = {target.external_id: target for target in existing_targets}
    targets_by_snum = {target.snum: target for target in existing_targets}
    seen_external_ids: set[int] = set()
    enrichment_candidates: list[Target] = []
    result: dict[str, Any] = {
        "source_total": len(source_rows),
        "valid": 0,
        "created": 0,
        "updated": 0,
        "unchanged": 0,
        "reactivated": 0,
        "deactivated": 0,
        "uniprot_enriched": 0,
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
            )
            db.add(target)
            targets_by_external_id[external_id] = target
            targets_by_snum[snum] = target
            result["created"] += 1
            if not target.structural_properties:
                enrichment_candidates.append(target)
            continue

        old_snum = target.snum
        gene_identity_changed = any(
            getattr(target, f) != values.get(f) for f in GENE_IDENTITY_FIELDS
        )
        changed = _apply_values(target, values) or rebound
        if old_snum != target.snum:
            targets_by_snum.pop(old_snum, None)
            targets_by_snum[target.snum] = target
        if not target.is_active:
            target.is_active = True
            result["reactivated"] += 1
            changed = True
        if changed:
            result["updated"] += 1
        else:
            result["unchanged"] += 1
        if gene_identity_changed and not target.structural_properties:
            enrichment_candidates.append(target)

    for target in existing_targets:
        if target.external_id not in seen_external_ids and target.is_active:
            target.is_active = False
            result["deactivated"] += 1

    if enrichment_candidates:
        enrich_stats = enrich_missing_targets(
            enrichment_candidates,
            list(targets_by_external_id.values()),
            allow_network=enrich_uniprot,
        )
        result["uniprot_enriched"] = (
            enrich_stats["reused_local"] + enrich_stats["fetched_uniprot"]
        )

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
    merged = dict(values)

    # 防冲突规则 1：PM 有 structural_properties 则以 PM 为准；PM 为空则保留本地已有的补齐值
    incoming_sp = merged.get("structural_properties")
    effective_sp = incoming_sp if incoming_sp is not None else target.structural_properties
    merged["structural_properties"] = effective_sp

    # 防冲突规则 2：PM 有有效跨膜次数则以 PM 为准；PM 为空或占位符(NA/未知)且最终类型非“非跨膜冲突”时，保留本地有效跨膜次数
    incoming_sf = merged.get("structure_feature")
    if (
        not is_meaningful_structure_feature(incoming_sf)
        and is_meaningful_structure_feature(target.structure_feature)
        and (effective_sp is None or is_transmembrane_property(effective_sp))
    ):
        merged["structure_feature"] = target.structure_feature

    changed = False
    for field, value in merged.items():
        if getattr(target, field) != value:
            setattr(target, field, value)
            changed = True
    return changed


def _clean(value: Any) -> str | None:
    if value is None:
        return None
    cleaned = clean_field_text(value, keep_breaks=True)
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
