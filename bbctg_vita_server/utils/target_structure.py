from __future__ import annotations

import json
import logging
import re
import urllib.parse
import urllib.request
from collections.abc import Sequence
from typing import Any

STRUCTURAL_PROPERTIES_META: dict[str, dict[str, Any]] = {
    "Single-pass transmembrane protein Type I": {
        "label": "I型跨膜",
        "serum_type": "I型",
        "broad_group": "跨膜蛋白",
        "is_transmembrane": True,
        "is_secreted": False,
        "aliases": frozenset({
            "i型", "i型跨膜", "一类", "一类跨膜", "1类", "1类跨膜",
            "一型", "一型跨膜", "1型", "1型跨膜", "type i", "跨膜", "跨膜蛋白",
        }),
    },
    "Single-pass transmembrane protein Type II": {
        "label": "II型跨膜",
        "serum_type": "II型",
        "broad_group": "跨膜蛋白",
        "is_transmembrane": True,
        "is_secreted": False,
        "aliases": frozenset({
            "ii型", "ii型跨膜", "二类", "二类跨膜", "2类", "2类跨膜",
            "二型", "二型跨膜", "2型", "2型跨膜", "type ii", "跨膜", "跨膜蛋白",
        }),
    },
    "Single-pass transmembrane protein Type III": {
        "label": "III型跨膜",
        "serum_type": "III型",
        "broad_group": "跨膜蛋白",
        "is_transmembrane": True,
        "is_secreted": False,
        "aliases": frozenset({
            "iii型", "iii型跨膜", "三类", "三类跨膜", "3类", "3类跨膜",
            "三型", "三型跨膜", "3型", "3型跨膜", "type iii", "跨膜", "跨膜蛋白",
        }),
    },
    "Single-pass transmembrane protein Type IV": {
        "label": "IV型跨膜",
        "serum_type": "I型",
        "broad_group": "跨膜蛋白",
        "is_transmembrane": True,
        "is_secreted": False,
        "aliases": frozenset({
            "iv型", "iv型跨膜", "四类", "四类跨膜", "4类", "4类跨膜",
            "四型", "四型跨膜", "4型", "4型跨膜", "type iv", "跨膜", "跨膜蛋白",
        }),
    },
    "Single-pass transmembrane protein": {
        "label": "单次跨膜",
        "serum_type": "I型",
        "broad_group": "跨膜蛋白",
        "is_transmembrane": True,
        "is_secreted": False,
        "aliases": frozenset({
            "单次跨膜", "单次穿膜", "单穿", "一次跨膜", "1次跨膜", "single-pass", "跨膜", "跨膜蛋白",
        }),
    },
    "Multi-pass transmembrane protein": {
        "label": "多次穿膜",
        "serum_type": "多穿",
        "broad_group": "跨膜蛋白",
        "is_transmembrane": True,
        "is_secreted": False,
        "aliases": frozenset({
            "多次穿膜", "多次跨膜", "多次", "多穿", "穿膜", "multi-pass", "跨膜", "跨膜蛋白",
        }),
    },
    "Secreted": {
        "label": "分泌型",
        "serum_type": "分泌",
        "broad_group": "分泌蛋白",
        "is_transmembrane": False,
        "is_secreted": True,
        "aliases": frozenset({"分泌", "分泌型", "分泌蛋白", "可溶性", "secreted"}),
    },
    "Intracellular protein": {
        "label": "胞内蛋白",
        "serum_type": "胞内",
        "broad_group": "胞内蛋白",
        "is_transmembrane": False,
        "is_secreted": False,
        "aliases": frozenset({"胞内", "胞内蛋白", "细胞内", "胞质", "核蛋白", "intracellular"}),
    },
    "GPI-anchored protein": {
        "label": "GPI锚定",
        "serum_type": "GPI",
        "broad_group": "膜关联蛋白",
        "is_transmembrane": False,
        "is_secreted": False,
        "aliases": frozenset({"gpi", "gpi锚定", "gpi锚定蛋白", "gpi-anchored"}),
    },
    "Peripheral membrane protein": {
        "label": "外周膜蛋白",
        "serum_type": "胞内",
        "broad_group": "膜关联蛋白",
        "is_transmembrane": False,
        "is_secreted": False,
        "aliases": frozenset({"外周膜", "外周膜蛋白", "peripheral membrane"}),
    },
    "lipid-anchor protein": {
        "label": "脂锚定蛋白",
        "serum_type": "胞内",
        "broad_group": "膜关联蛋白",
        "is_transmembrane": False,
        "is_secreted": False,
        "aliases": frozenset({"脂锚定", "脂锚定蛋白", "lipid-anchor"}),
    },
    "Cell membrane protein": {
        "label": "细胞膜蛋白",
        "serum_type": "I型",
        "broad_group": "膜关联蛋白",
        "is_transmembrane": False,
        "is_secreted": False,
        "aliases": frozenset({"细胞膜", "细胞膜蛋白", "膜蛋白", "cell membrane"}),
    },
    "Other": {
        "label": "其他",
        "serum_type": None,
        "broad_group": "其他",
        "is_transmembrane": False,
        "is_secreted": False,
        "aliases": frozenset({"其他"}),
    },
}

PLACEHOLDER_VALUES = frozenset({"", "NA", "N/A", "NONE", "NULL", "-", "—", "TBD", "未知", "末知", "无", "/"})


def is_meaningful_structure_feature(value: str | None) -> bool:
    if value is None:
        return False
    cleaned = str(value).strip()
    return bool(cleaned) and cleaned.upper() not in PLACEHOLDER_VALUES


def is_transmembrane_property(structural_properties: str | None) -> bool:
    if not structural_properties:
        return False
    meta = STRUCTURAL_PROPERTIES_META.get(structural_properties.strip())
    if meta is not None:
        return bool(meta["is_transmembrane"])
    return "transmembrane" in structural_properties.lower()


def extract_tm_count(structure_feature: str | None) -> int | None:
    if not is_meaningful_structure_feature(structure_feature):
        return None
    text_val = str(structure_feature).strip()
    if text_val in ("一次", "单次", "单次跨膜"):
        return 1
    match = re.match(r"^(\d+)(?:\s*次(?:跨膜|穿膜)?(?:蛋白)?)?$", text_val)
    if match:
        count = int(match.group(1))
        return count if count > 0 else None
    return None


def parse_target_structure(
    structural_properties: str | None,
    structure_feature: str | None = None,
) -> dict[str, Any]:
    """
    公共映射纯函数：将靶点库的英文 `structural_properties` 与 `structure_feature`（跨膜次数）
    解析为统一的结构化信息，供靶点库展示、搜索以及免疫/发现等下游业务模块二次映射使用。
    """
    raw_prop = str(structural_properties or "").strip() or None
    raw_feat = str(structure_feature or "").strip() or None
    tm_count = extract_tm_count(raw_feat)

    meta = STRUCTURAL_PROPERTIES_META.get(raw_prop) if raw_prop else None
    if meta is not None:
        label = meta["label"]
        serum_type = meta["serum_type"]
        broad_group = meta["broad_group"]
        is_tm = meta["is_transmembrane"]
        is_sec = meta["is_secreted"]
        if is_tm and tm_count is None and raw_prop.startswith("Single-pass"):
            tm_count = 1
    elif tm_count is not None:
        is_tm = True
        is_sec = False
        broad_group = "跨膜蛋白"
        if tm_count == 1:
            label = "单次跨膜"
            serum_type = "I型"
        else:
            label = "多次穿膜"
            serum_type = "多穿"
    elif raw_feat and ("分泌" in raw_feat or raw_feat.lower() == "secreted"):
        label = "分泌型"
        serum_type = "分泌"
        broad_group = "分泌蛋白"
        is_tm = False
        is_sec = True
    elif raw_feat and "胞内" in raw_feat:
        label = "胞内蛋白"
        serum_type = "胞内"
        broad_group = "胞内蛋白"
        is_tm = False
        is_sec = False
    else:
        label = raw_prop
        serum_type = None
        broad_group = None
        is_tm = False
        is_sec = False

    if label and tm_count and tm_count > 0:
        full_label = f"{label}（{tm_count}次跨膜）"
    else:
        full_label = label

    return {
        "raw": raw_prop,
        "raw_feature": raw_feat,
        "label": label,
        "full_label": full_label,
        "tm_count": tm_count,
        "serum_type": serum_type,
        "broad_group": broad_group,
        "is_transmembrane": is_tm,
        "is_secreted": is_sec,
    }


def to_serum_target_type(
    structural_properties: str | None,
    structure_feature: str | None = None,
) -> str | None:
    """二次映射：转换为小鼠免疫模块的靶点类型枚举（I型 / II型 / III型 / 分泌 / 多穿 / 胞内 / GPI）"""
    return parse_target_structure(structural_properties, structure_feature)["serum_type"]


def match_structural_properties_by_keyword(keyword: str | None) -> list[str]:
    """根据用户输入的中文靶点类型搜索词，精确反查对应的 `structural_properties` 枚举原值列表。"""
    if not keyword:
        return []
    kw = keyword.strip().lower()
    if not kw:
        return []
    return [
        raw_key
        for raw_key, meta in STRUCTURAL_PROPERTIES_META.items()
        if kw == meta["label"].lower() or kw in meta["aliases"]
    ]


# ---------------------------------------------------------------------------
# UniProt 自动解析与容错补齐逻辑（用于新靶点入库及缺失数据补齐）
# ---------------------------------------------------------------------------

def strip_species_prefix(name: str | None) -> str | None:
    """
    剥离靶点名称开头的种属标记（如 `dogIGF1` -> `IGF1`, `dogPD-1` -> `PD-1`, `catNGF` -> `NGF`）。
    """
    if not name:
        return None
    match = re.match(
        r"^(?:dog|canine|cat|feline|monkey|cyno|rhesus|equine|bovine)[\s\-_]*([A-Za-z0-9].*)$",
        name.strip(),
        flags=re.IGNORECASE,
    )
    if match:
        core = match.group(1).strip()
        return core or None
    return None


def extract_clean_ncbi_ids(raw_val: str | None) -> list[str]:
    if not raw_val:
        return []
    return re.findall(r"\b\d+\b", str(raw_val))


def extract_clean_symbols(raw_val: str | None) -> list[str]:
    if not raw_val:
        return []
    text_val = str(raw_val).strip()
    if not text_val or text_val.upper() in PLACEHOLDER_VALUES:
        return []
    parts = [p.strip() for p in re.split(r"[,，;/、\s]+", text_val) if p.strip()]
    return [p for p in parts if p.upper() not in PLACEHOLDER_VALUES]


def simplify_uniprot_entry(entry: dict[str, Any]) -> dict[str, Any]:
    """将 UniProt REST API 原始 JSON 条目简化为结构解析所需的最小字典。"""
    go_cc: list[str] = []
    for xref in entry.get("uniProtKBCrossReferences", []):
        if xref.get("database") == "GO":
            for prop in xref.get("properties", []):
                if prop.get("key") == "GoTerm" and str(prop.get("value", "")).startswith("C:"):
                    go_cc.append(str(prop.get("value"))[2:])

    subcell_blocks: list[dict[str, Any]] = []
    for comment in entry.get("comments", []):
        if comment.get("commentType") == "SUBCELLULAR LOCATION":
            locs: list[str] = []
            topos: list[str] = []
            for sub in comment.get("subcellularLocations", []):
                loc = sub.get("location", {}).get("value")
                topo = sub.get("topology", {}).get("value")
                if loc:
                    locs.append(loc)
                if topo:
                    topos.append(topo)
            subcell_blocks.append(
                {
                    "molecule": comment.get("molecule", ""),
                    "locations": locs,
                    "topologies": topos,
                }
            )

    keywords = [kw.get("name") for kw in entry.get("keywords", []) if kw.get("name")]

    tm_features: list[dict[str, Any]] = []
    topo_domains: list[dict[str, Any]] = []
    has_signal = False
    has_gpi_feature = False
    for feat in entry.get("features", []):
        ftype = feat.get("type")
        desc = feat.get("description", "")
        loc = feat.get("location", {})
        start = loc.get("start", {}).get("value")
        end = loc.get("end", {}).get("value")
        if ftype == "Transmembrane":
            tm_features.append({"start": start, "end": end, "desc": desc})
        elif ftype == "Topological domain":
            topo_domains.append({"start": start, "end": end, "desc": desc})
        elif ftype == "Signal":
            has_signal = True
        elif ftype == "Lipidation" and "GPI" in desc.upper():
            has_gpi_feature = True

    return {
        "accession": entry.get("primaryAccession"),
        "subcell_blocks": subcell_blocks,
        "keywords": keywords,
        "tm_features": tm_features,
        "topo_domains": topo_domains,
        "has_signal": has_signal,
        "has_gpi_feature": has_gpi_feature,
        "go_cc": go_cc,
    }


def infer_pm_fields_from_uniprot(entry: dict[str, Any] | None) -> dict[str, str | None]:
    """
    将简化后的 UniProt 条目映射为与 PM 系统 100% 兼容的字段值：
    返回 `{"structural_properties": ..., "structure_feature": ...}`
    """
    if not entry:
        return {"structural_properties": None, "structure_feature": None}

    blocks = entry.get("subcell_blocks", [])
    primary_blocks = [
        b for b in blocks if not b.get("molecule") or "isoform 1" in b.get("molecule", "").lower()
    ]
    if not primary_blocks:
        primary_blocks = blocks

    primary_topos = [t for b in primary_blocks for t in b.get("topologies", [])]
    primary_locs = [loc for b in primary_blocks for loc in b.get("locations", [])]
    all_locs = [loc for b in blocks for loc in b.get("locations", [])]

    keywords = set(entry.get("keywords", []))
    tm_features = entry.get("tm_features", [])
    tm_count = len(tm_features)
    topo_domains = entry.get("topo_domains", [])
    has_signal = bool(entry.get("has_signal", False))
    has_gpi = (
        bool(entry.get("has_gpi_feature", False))
        or ("GPI-anchor" in keywords)
        or any("GPI-anchor" in t for t in primary_topos)
    )
    go_cc = entry.get("go_cc", [])

    if any("Multi-pass membrane protein" in t for t in primary_topos) or tm_count >= 2:
        return {
            "structural_properties": "Multi-pass transmembrane protein",
            "structure_feature": str(tm_count) if tm_count > 0 else None,
        }

    if any("Single-pass type I membrane protein" in t for t in primary_topos):
        return {
            "structural_properties": "Single-pass transmembrane protein Type I",
            "structure_feature": "1",
        }
    if any("Single-pass type II membrane protein" in t for t in primary_topos):
        return {
            "structural_properties": "Single-pass transmembrane protein Type II",
            "structure_feature": "1",
        }
    if any("Single-pass type III membrane protein" in t for t in primary_topos):
        return {
            "structural_properties": "Single-pass transmembrane protein Type III",
            "structure_feature": "1",
        }
    if any("Single-pass type IV membrane protein" in t for t in primary_topos):
        return {
            "structural_properties": "Single-pass transmembrane protein Type IV",
            "structure_feature": "1",
        }

    if has_gpi and tm_count == 0:
        return {
            "structural_properties": "GPI-anchored protein",
            "structure_feature": None,
        }

    if any("Single-pass membrane protein" in t for t in primary_topos) or tm_count == 1:
        tm_desc = (tm_features[0].get("desc", "") if tm_features else "").lower()
        if "type ii" in tm_desc:
            return {
                "structural_properties": "Single-pass transmembrane protein Type II",
                "structure_feature": "1",
            }
        if "type i" in tm_desc:
            return {
                "structural_properties": "Single-pass transmembrane protein Type I",
                "structure_feature": "1",
            }
        if len(topo_domains) >= 2 and tm_features:
            tm_start = tm_features[0].get("start") or 0
            before_tm = [d["desc"].lower() for d in topo_domains if (d.get("end") or 0) <= tm_start]
            after_tm = [d["desc"].lower() for d in topo_domains if (d.get("start") or 0) >= tm_start]
            if any("extracellular" in d for d in before_tm) and any("cytoplasmic" in d for d in after_tm) and has_signal:
                return {
                    "structural_properties": "Single-pass transmembrane protein Type I",
                    "structure_feature": "1",
                }
            if any("cytoplasmic" in d for d in before_tm) and any("extracellular" in d for d in after_tm) and not has_signal:
                return {
                    "structural_properties": "Single-pass transmembrane protein Type II",
                    "structure_feature": "1",
                }
        return {
            "structural_properties": "Single-pass transmembrane protein",
            "structure_feature": "1",
        }

    if any("Secreted" in loc for loc in primary_locs) or "Secreted" in keywords:
        return {
            "structural_properties": "Secreted",
            "structure_feature": None,
        }

    if any("Peripheral membrane protein" in t for t in primary_topos):
        return {
            "structural_properties": "Peripheral membrane protein",
            "structure_feature": None,
        }
    if any("Lipid-anchor" in t for t in primary_topos) or "Lipoprotein" in keywords:
        return {
            "structural_properties": "lipid-anchor protein",
            "structure_feature": None,
        }

    if any("Cell membrane" in loc for loc in primary_locs) or "Cell membrane" in keywords:
        return {
            "structural_properties": "Cell membrane protein",
            "structure_feature": None,
        }

    intracellular_terms = (
        "Cytoplasm",
        "Cytosol",
        "Nucleus",
        "Chromosome",
        "Mitochondrion",
        "Endoplasmic reticulum",
        "Golgi apparatus",
        "Lysosome",
        "Peroxisome",
        "Cytoskeleton",
        "Cytoplasmic vesicle",
        "Endosome",
        "Melanosome",
        "Autophagosome",
        "Centrosome",
        "Sarcoplasmic reticulum",
    )
    if any(any(term.lower() in loc.lower() for term in intracellular_terms) for loc in all_locs) or any(
        k in keywords
        for k in (
            "Cytoplasm",
            "Nucleus",
            "Mitochondrion",
            "Endoplasmic reticulum",
            "Golgi apparatus",
            "Lysosome",
            "Peroxisome",
            "Cytoskeleton",
        )
    ):
        return {
            "structural_properties": "Intracellular protein",
            "structure_feature": None,
        }

    go_joined = " | ".join(go_cc).lower()
    if has_signal and ("extracellular" in go_joined or "secretory" in go_joined or not go_cc):
        return {
            "structural_properties": "Secreted",
            "structure_feature": None,
        }
    if "plasma membrane" in go_joined or "cell surface" in go_joined:
        return {
            "structural_properties": "Cell membrane protein",
            "structure_feature": None,
        }
    if any(
        term in go_joined
        for term in (
            "cytoplasm",
            "cytosol",
            "nucleus",
            "mitochondri",
            "endoplasmic reticulum",
            "golgi",
            "lysosom",
            "cytoskeleton",
            "intracellular",
        )
    ):
        return {
            "structural_properties": "Intracellular protein",
            "structure_feature": None,
        }
    if "extracellular" in go_joined:
        return {
            "structural_properties": "Secreted",
            "structure_feature": None,
        }

    return {"structural_properties": None, "structure_feature": None}


def query_uniprot_single_target(
    human_ncbi_gene_id: str | None,
    mouse_ncbi_gene_id: str | None,
    human_gene_symbol: str | None,
    mouse_gene_symbol: str | None,
    target_name: str | None,
    *,
    timeout: int = 10,
) -> dict[str, Any] | None:
    """
    针对单个靶点按优先级查询 UniProt REST API：
      1. 人源 NCBI Gene ID (Swiss-Prot -> TrEMBL)
      2. 鼠源 NCBI Gene ID (Swiss-Prot -> TrEMBL)
      3. 人源官方基因名 / 剥离 dog 等种属前缀后的名称 (Swiss-Prot)
      4. 鼠源官方基因名 (Swiss-Prot)
    发生任何网络异常时捕获并返回 None，绝不中断主流程。
    """
    queries: list[str] = []
    for gid in extract_clean_ncbi_ids(human_ncbi_gene_id):
        queries.append(f"(xref:geneid-{gid}) AND (organism_id:9606) AND (reviewed:true)")
    for gid in extract_clean_ncbi_ids(mouse_ncbi_gene_id):
        queries.append(f"(xref:geneid-{gid}) AND (organism_id:10090) AND (reviewed:true)")
    for gid in extract_clean_ncbi_ids(human_ncbi_gene_id):
        queries.append(f"(xref:geneid-{gid}) AND (organism_id:9606)")
    for gid in extract_clean_ncbi_ids(mouse_ncbi_gene_id):
        queries.append(f"(xref:geneid-{gid}) AND (organism_id:10090)")

    stripped_name = strip_species_prefix(target_name)
    for sym in [
        *extract_clean_symbols(human_gene_symbol),
        *([stripped_name] if stripped_name else []),
        *extract_clean_symbols(target_name),
    ]:
        clean_sym = re.sub(r'["\(\)\\]', "", sym).strip()
        if clean_sym and len(clean_sym) >= 2:
            queries.append(f'(gene_exact:"{clean_sym}") AND (organism_id:9606) AND (reviewed:true)')

    for sym in extract_clean_symbols(mouse_gene_symbol):
        clean_sym = re.sub(r'["\(\)\\]', "", sym).strip()
        if clean_sym and len(clean_sym) >= 2:
            queries.append(f'(gene_exact:"{clean_sym}") AND (organism_id:10090) AND (reviewed:true)')

    seen_queries: set[str] = set()
    for q in queries:
        if q in seen_queries:
            continue
        seen_queries.add(q)
        params = urllib.parse.urlencode({"query": q, "format": "json", "size": 1})
        url = f"https://rest.uniprot.org/uniprotkb/search?{params}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "AntibodyForge/1.0"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
                results = payload.get("results") or []
                if results:
                    return simplify_uniprot_entry(results[0])
        except Exception as exc:
            logging.warning("UniProt query failed for %s: %s", q, exc)
            continue
    return None


def enrich_missing_targets(
    candidates: Sequence[Any],
    all_targets: Sequence[Any] | None = None,
    *,
    allow_network: bool = True,
    max_network_queries: int = 30,
) -> dict[str, int]:
    """
    对缺失 `structural_properties` 的靶点列表进行无冲突补齐：
      1. 先尝试同库复用（例如 `dogPD-1` 直接复用同库已有的 `PD-1` 的结构特性，或双靶点 `IL17A-IL17F` 复用首靶点 `IL17A`）；
      2. 若同库未命中且允许网络请求（`allow_network=True`），调用 UniProt API 补齐（限制单次任务最大请求数 `max_network_queries` 防止阻塞）。
    只填补空缺字段，绝不覆盖已有有效值。
    """
    stats = {"reused_local": 0, "fetched_uniprot": 0, "failed_or_empty": 0}
    if not candidates:
        return stats

    reference_pool = list(all_targets) if all_targets is not None else list(candidates)
    local_lookup: dict[str, tuple[str, str | None]] = {}
    for item in reference_pool:
        sp = getattr(item, "structural_properties", None)
        if not sp:
            continue
        sf = getattr(item, "structure_feature", None)
        valid_sf = sf if is_meaningful_structure_feature(sf) else None
        for key_attr in ("name", "human_gene_official_name", "mouse_gene_official_name"):
            val = getattr(item, key_attr, None)
            if val and str(val).strip():
                local_lookup.setdefault(str(val).strip().upper(), (sp, valid_sf))

    network_calls = 0
    for target in candidates:
        if getattr(target, "structural_properties", None):
            continue

        # 1. 尝试剥离 dog/cat 等种属前缀或双靶点连字符，在同库已有靶点中直接匹配
        raw_name = str(getattr(target, "name", "") or "").strip()
        lookup_keys: list[str] = []
        stripped = strip_species_prefix(raw_name)
        if stripped:
            lookup_keys.append(stripped.upper())
            lookup_keys.append(stripped.upper().replace("-", ""))
        if "-" in raw_name:
            first_part = raw_name.split("-", 1)[0].strip()
            if len(first_part) >= 3:
                lookup_keys.append(first_part.upper())

        matched_local = None
        for k in lookup_keys:
            if k in local_lookup:
                matched_local = local_lookup[k]
                break

        if matched_local is not None:
            sp, sf = matched_local
            target.structural_properties = sp
            if not is_meaningful_structure_feature(getattr(target, "structure_feature", None)) and sf:
                target.structure_feature = sf
            stats["reused_local"] += 1
            continue

        # 2. 调用 UniProt API 在线补齐
        if not allow_network or network_calls >= max_network_queries:
            stats["failed_or_empty"] += 1
            continue

        network_calls += 1
        entry = query_uniprot_single_target(
            getattr(target, "human_ncbi_gene_id", None),
            getattr(target, "mouse_ncbi_gene_id", None),
            getattr(target, "human_gene_official_name", None),
            getattr(target, "mouse_gene_official_name", None),
            raw_name,
        )
        inferred = infer_pm_fields_from_uniprot(entry)
        if inferred["structural_properties"]:
            target.structural_properties = inferred["structural_properties"]
            if (
                not is_meaningful_structure_feature(getattr(target, "structure_feature", None))
                and inferred["structure_feature"]
            ):
                target.structure_feature = inferred["structure_feature"]
            # 将新解析出的结果加入本地字典，供同批次后续靶点复用
            if raw_name:
                local_lookup.setdefault(
                    raw_name.upper(),
                    (inferred["structural_properties"], inferred["structure_feature"]),
                )
            stats["fetched_uniprot"] += 1
        else:
            stats["failed_or_empty"] += 1

    return stats
