from __future__ import annotations

import logging
import re
from typing import Any

from sqlalchemy import bindparam, or_, select, text
from sqlalchemy.orm import Session

from db.external import open_one_db
from models.discovery import DiscoverySynthesisOrder
from modules.discovery.synthesis_progress.constants import (
    DRIFT_COMPARE_FIELDS,
    DRIFT_FIELD_LABELS,
    STATUS_ASSAYING,
    STATUS_SYNTHESIZING,
    STATUS_WAIT_ASSAY,
    STATUS_WAIT_ORDER,
    SUPPLY_MODE_ARRIVAL,
    SYNTHETIC_CORP_OPTIONS,
    TERMINAL_STATUSES,
)
from utils.filter_values import clean_field_text

logger = logging.getLogger(__name__)

_DATE_FULL_RE = re.compile(r"(20\d{2})[./年-](\d{1,2})[./月-](\d{1,2})[日号]?")
_DATE_COMPACT8_RE = re.compile(r"(20\d{2})(\d{2})(\d{2})")
_VALID_ORDER_NO_RE = re.compile(
    r"((?:CN|GS[A-Z]{2,3}|BAO|QK|ORD)\d+(?:-\d+)?)",
    re.IGNORECASE,
)

SNAPSHOT_STORED_FIELDS = (*DRIFT_COMPARE_FIELDS, "synthesis_code", "batch_label")


def _clean_str(value: Any, max_len: int | None = None) -> str | None:
    if value is None:
        return None
    text_val = clean_field_text(value)
    if not text_val or text_val.lower() in {"none", "null", "nan", "/", "//", "--", "---", "#n/a"}:
        return None
    if max_len is not None:
        return text_val[:max_len]
    return text_val


def _clean_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    if isinstance(value, int):
        return value if value > 0 else None
    text_val = _clean_str(value)
    if not text_val:
        return None
    try:
        num = int(float(text_val))
        return num if num > 0 else None
    except (TypeError, ValueError):
        return None


def _clean_order_no(value: Any) -> str | None:
    raw = _clean_str(value, 128)
    if not raw:
        return None
    m = _VALID_ORDER_NO_RE.search(raw)
    return m.group(1).upper()[:64] if m else None


def normalize_date_text(value: Any) -> str | None:
    raw = _clean_str(value, 64)
    if not raw:
        return None
    for regex in (_DATE_FULL_RE, _DATE_COMPACT8_RE):
        m = regex.search(raw)
        if m:
            y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
            if y > 2026:
                y = 2026
            if 1 <= mo <= 12 and 1 <= d <= 31:
                return f"{y:04d}-{mo:02d}-{d:02d}"
    return None


def normalize_synthetic_corp(raw_corp: Any, refstr: Any = None, order_no: Any = None) -> str | None:
    corp = _clean_str(raw_corp, 64)
    if corp in SYNTHETIC_CORP_OPTIONS:
        return corp
    for text_cand in (raw_corp, refstr):
        s = _clean_str(text_cand) or ""
        if "君跻" in s:
            return "君跻"
        if "擎科" in s:
            return "擎科"
        if "金斯瑞" in s:
            return "金斯瑞"
    ord_str = (_clean_str(order_no) or "").upper()
    if ord_str.startswith("CN") or ord_str.startswith("GS"):
        return "君跻"
    if ord_str.startswith("BAO"):
        return "擎科"
    return None


def derive_status_for_row(row: DiscoverySynthesisOrder, *, preserve_terminal: bool = True) -> str:
    cur = (row.status or "").strip()
    if preserve_terminal and cur in TERMINAL_STATUSES:
        return cur
    if row.flow_date or row.flow_count is not None or row.affinity_date or row.affinity_count is not None:
        return STATUS_ASSAYING
    if row.arrival_date or row.arrival_count is not None:
        return STATUS_WAIT_ASSAY
    if row.order_no or (row.supply_mode and row.supply_mode != SUPPLY_MODE_ARRIVAL):
        return STATUS_SYNTHESIZING
    return STATUS_WAIT_ORDER


def build_remote_snapshot(
    source_type: str,
    row_map: dict[str, Any],
    orderhis_map: dict[str, tuple[str, str]] | None = None,
) -> dict[str, Any]:
    synthesis_code = _clean_str(row_map.get("synthesiscode"), 64)
    refstr = _clean_str(row_map.get("refstr"), 255)
    order_no = _clean_order_no(row_map.get("orderno"))
    if not order_no and refstr and orderhis_map:
        stem = re.sub(r"\.(xlsx|xls|csv|tsv)$", "", refstr, flags=re.IGNORECASE)
        if stem in orderhis_map:
            order_no = _clean_order_no(orderhis_map[stem][0])

    synthetic_corp = normalize_synthetic_corp(row_map.get("syntheticcorp"), refstr, order_no)
    synthetic_count = _clean_int(row_map.get("syntheticcount"))
    synthetic_date = normalize_date_text(row_map.get("syntheticdate"))

    arrival_date = normalize_date_text(row_map.get("deliverydate"))
    raw_sup_count = _clean_int(row_map.get("supernatantcounts"))
    if (
        raw_sup_count is not None
        and synthetic_count is not None
        and raw_sup_count > synthetic_count
        and raw_sup_count % 2 == 0
        and (raw_sup_count // 2) <= synthetic_count
    ):
        raw_sup_count = raw_sup_count // 2
    raw_plas_count = _clean_int(row_map.get("plasmidcounts"))
    if (
        raw_plas_count is not None
        and synthetic_count is not None
        and raw_plas_count > synthetic_count
        and raw_plas_count % 2 == 0
        and (raw_plas_count // 2) <= synthetic_count
    ):
        raw_plas_count = raw_plas_count // 2

    if (
        synthetic_date
        and arrival_date
        and synthetic_date > arrival_date
        and order_no
        and re.match(r"^CN(\d{2})(\d{2})(\d{2})\d+$", order_no)
    ):
        m_cn = re.match(r"^CN(\d{2})(\d{2})(\d{2})\d+$", order_no)
        if m_cn:
            cn_date = f"20{m_cn.group(1)}-{m_cn.group(2)}-{m_cn.group(3)}"
            if cn_date <= arrival_date:
                synthetic_date = cn_date

    arrival_count = raw_sup_count if raw_sup_count is not None else raw_plas_count
    task_projectid = _clean_str(row_map.get("task_projectid"), 128)
    task_batchname = _clean_str(row_map.get("task_batchname"), 128)

    return {
        "source_one_type": source_type.lower(),
        "source_one_id": int(row_map["id"]),
        "synthesis_code": synthesis_code,
        "batch_label": task_projectid or task_batchname,
        "order_no": order_no,
        "synthetic_corp": synthetic_corp,
        "synthetic_count": synthetic_count,
        "synthetic_date": synthetic_date,
        "arrival_count": arrival_count,
        "arrival_date": arrival_date,
        "order_state": _clean_str(row_map.get("orderstate"), 64),
        "task_projectid": task_projectid,
        "task_projectcode": _clean_str(row_map.get("task_projectcode"), 128),
        "task_batchname": task_batchname,
    }


def compute_drift_fields(row: DiscoverySynthesisOrder) -> list[dict[str, str]]:
    snapshot = row.source_snapshot if isinstance(row.source_snapshot, dict) else {}
    if not snapshot:
        return []
    drifts: list[dict[str, str]] = []
    for field in DRIFT_COMPARE_FIELDS:
        remote_raw = snapshot.get(field)
        if remote_raw in (None, ""):
            continue
        local_raw = getattr(row, field, None)
        if local_raw in (None, ""):
            continue
        remote_str = str(remote_raw).strip()
        local_str = str(local_raw).strip()
        if field == "order_no" and local_str.upper().startswith("CN") and remote_str.upper().startswith("GS"):
            continue
        if local_str != remote_str:
            drifts.append(
                {
                    "field": field,
                    "label": DRIFT_FIELD_LABELS.get(field, field),
                    "current": local_str,
                    "remote": remote_str,
                }
            )
    return drifts


def apply_remote_snapshot_to_row(
    row: DiscoverySynthesisOrder,
    snapshot: dict[str, Any],
    *,
    replace_from_snapshot: dict[str, Any] | None = None,
) -> bool:
    """Backfills empty execution fields (or replaces fields auto-filled by a previous snapshot) without overwriting user edits."""
    changed = False
    old_snapshot = row.source_snapshot if isinstance(row.source_snapshot, dict) else {}
    new_stored = {f: snapshot.get(f) for f in SNAPSHOT_STORED_FIELDS}
    old_stored = {f: old_snapshot.get(f) for f in SNAPSHOT_STORED_FIELDS}
    if old_stored != new_stored:
        row.source_snapshot = new_stored
        changed = True

    for field in SNAPSHOT_STORED_FIELDS:
        remote_val = snapshot.get(field)
        if remote_val in (None, ""):
            continue
        current_val = getattr(row, field, None)
        should_fill = current_val in (None, "") or (
            replace_from_snapshot is not None
            and replace_from_snapshot.get(field) not in (None, "")
            and current_val == replace_from_snapshot.get(field)
        )
        if should_fill and current_val != remote_val:
            setattr(row, field, remote_val)
            changed = True

    new_status = derive_status_for_row(row, preserve_terminal=True)
    if row.status != new_status and row.status not in TERMINAL_STATUSES:
        row.status = new_status
        changed = True

    return changed


_NGS_QUERY_BASE = """
    SELECT
        a.id AS id,
        a.refstr AS refstr,
        a.orderno AS orderno,
        a.orderstate AS orderstate,
        a.syntheticcount AS syntheticcount,
        a.syntheticcorp AS syntheticcorp,
        a.syntheticdate AS syntheticdate,
        a.plasmidcounts AS plasmidcounts,
        a.supernatantcounts AS supernatantcounts,
        a.deliverydate AS deliverydate,
        t.synthesiscode AS synthesiscode,
        t.projectid AS task_projectid,
        t.projectcode AS task_projectcode,
        t.batchname AS task_batchname
    FROM one_task_ngs_data_analyze a
    LEFT JOIN one_task_ngs_task t ON a.ngstaskid = t.id
    WHERE (a.isdelete IS NULL OR a.isdelete = '0')
      AND NOT (
        COALESCE(a.orderno, '') = ''
        AND COALESCE(a.refstr, '') = ''
        AND COALESCE(a.syntheticcount, '') = ''
        AND COALESCE(a.syntheticdate, '') = ''
      )
"""

_BEACON_QUERY_BASE = """
    SELECT
        a.id AS id,
        a.refstr AS refstr,
        a.orderno AS orderno,
        a.orderstate AS orderstate,
        a.syntheticcount AS syntheticcount,
        a.syntheticcorp AS syntheticcorp,
        a.syntheticdate AS syntheticdate,
        a.plasmidcounts AS plasmidcounts,
        a.supernatantcounts AS supernatantcounts,
        a.deliverydate AS deliverydate,
        t.synthesiscode AS synthesiscode,
        t.projectid AS task_projectid,
        t.projectcode AS task_projectcode,
        t.batchname AS task_batchname
    FROM one_task_beacon_data_analyze a
    LEFT JOIN one_task_beacon_task t ON a.ngstaskid = t.id
    WHERE (a.isdelete IS NULL OR a.isdelete = '0')
      AND NOT (
        COALESCE(a.orderno, '') = ''
        AND COALESCE(a.refstr, '') = ''
        AND COALESCE(a.syntheticcount, '') = ''
        AND COALESCE(a.syntheticdate, '') = ''
      )
"""


def _load_orderhis_map(
    one_db: Session,
    filenames: list[str] | None = None,
) -> dict[str, tuple[str, str]]:
    if filenames is not None and not filenames:
        return {}
    result: dict[str, tuple[str, str]] = {}
    try:
        if filenames:
            stmt = text(
                "SELECT filename, orderNo, sendcorpname FROM orderhis "
                "WHERE orderNo IS NOT NULL AND orderNo != '' AND filename IN :fns"
            ).bindparams(bindparam("fns", expanding=True))
            rows = one_db.execute(stmt, {"fns": list(set(filenames))}).all()
        else:
            rows = one_db.execute(
                text(
                    "SELECT filename, orderNo, sendcorpname FROM orderhis "
                    "WHERE orderNo IS NOT NULL AND orderNo != ''"
                )
            ).all()
        for fn, ord_no, corp in rows:
            if fn and ord_no:
                stem = re.sub(r"\.(xlsx|xls|csv|tsv)$", "", str(fn).strip(), flags=re.IGNORECASE)
                result[stem] = (str(ord_no).strip().upper(), str(corp or "").strip())
    except Exception:
        logger.debug("orderhis lookup skipped", exc_info=True)
    return result


def fetch_remote_snapshots_by_ids(
    one_db: Session,
    ngs_ids: list[int],
    beacon_ids: list[int],
) -> dict[tuple[str, int], dict[str, Any]]:
    raw_rows: list[tuple[str, dict[str, Any]]] = []
    if ngs_ids:
        stmt = text(_NGS_QUERY_BASE + " AND a.id IN :ids").bindparams(
            bindparam("ids", expanding=True)
        )
        for row in one_db.execute(stmt, {"ids": list(set(ngs_ids))}).mappings().all():
            raw_rows.append(("ngs", dict(row)))
    if beacon_ids:
        stmt = text(_BEACON_QUERY_BASE + " AND a.id IN :ids").bindparams(
            bindparam("ids", expanding=True)
        )
        for row in one_db.execute(stmt, {"ids": list(set(beacon_ids))}).mappings().all():
            raw_rows.append(("beacon", dict(row)))

    missing_ord_fns = [
        str(rm["refstr"]).strip()
        for _, rm in raw_rows
        if not _clean_order_no(rm.get("orderno")) and _clean_str(rm.get("refstr"))
    ]
    orderhis_map = _load_orderhis_map(one_db, missing_ord_fns) if missing_ord_fns else None

    result: dict[tuple[str, int], dict[str, Any]] = {}
    for stype, rm in raw_rows:
        rid = int(rm["id"])
        if (stype, rid) not in result:
            result[(stype, rid)] = build_remote_snapshot(stype, rm, orderhis_map)
    return result


def _is_compatible_candidate(row: DiscoverySynthesisOrder, snap: dict[str, Any]) -> bool:
    """Prevents linking rows that have different non-empty order numbers unless GS/CN alias."""
    ord_l = (row.order_no or "").strip().upper()
    ord_r = (snap.get("order_no") or "").strip().upper()
    if not ord_l or not ord_r or ord_l == ord_r:
        return True
    if (ord_l.startswith("CN") and ord_r.startswith("GS")) or (
        ord_l.startswith("GS") and ord_r.startswith("CN")
    ):
        if row.synthetic_count is None or snap.get("synthetic_count") == row.synthetic_count:
            return True
    return False


def _batch_lookup_keys(batch_label: str | None) -> tuple[str, ...]:
    stem = ((batch_label or "").split("|")[0]).strip()
    if not stem:
        return ()
    base = re.sub(r"_\d+$|_C\d+$", "", stem, flags=re.IGNORECASE)
    return (stem, base) if base and base != stem else (stem,)


def _query_candidates_for_rows(
    one_db: Session,
    target_rows: list[DiscoverySynthesisOrder],
    orderhis_map: dict[str, tuple[str, str]] | None = None,
) -> list[dict[str, Any]]:
    ord_vals: set[str] = set()
    bat_vals: set[str] = set()
    syn_vals: set[str] = set()
    for urow in target_rows:
        ord_u = (urow.order_no or "").strip()
        if ord_u:
            ord_vals.add(ord_u)
        syn_u = (urow.synthesis_code or "").strip()
        if syn_u:
            syn_vals.add(syn_u)
        bat_vals.update(_batch_lookup_keys(urow.batch_label))

    clauses: list[str] = []
    params: dict[str, Any] = {}
    expanding_binds = []
    if ord_vals:
        clauses.append("a.orderno IN :ord_vals")
        params["ord_vals"] = list(ord_vals)
        expanding_binds.append(bindparam("ord_vals", expanding=True))
    if bat_vals:
        clauses.append("(t.projectid IN :bat_vals OR t.projectcode IN :bat_vals OR t.batchname IN :bat_vals)")
        params["bat_vals"] = list(bat_vals)
        expanding_binds.append(bindparam("bat_vals", expanding=True))
    if syn_vals:
        clauses.append("(t.synthesiscode IN :syn_vals OR t.projectcode IN :syn_vals)")
        params["syn_vals"] = list(syn_vals)
        expanding_binds.append(bindparam("syn_vals", expanding=True))
    if not clauses:
        return []

    where_or = " OR ".join(clauses)
    raw_cands: list[tuple[str, dict[str, Any]]] = []
    for stype, qbase in (("ngs", _NGS_QUERY_BASE), ("beacon", _BEACON_QUERY_BASE)):
        stmt = text(f"{qbase} AND ({where_or}) ORDER BY a.id DESC").bindparams(*expanding_binds)
        for rm in one_db.execute(stmt, params).mappings().all():
            raw_cands.append((stype, dict(rm)))

    if not raw_cands:
        return []

    if orderhis_map is None:
        missing_fns = [
            str(rm["refstr"]).strip()
            for _, rm in raw_cands
            if not _clean_order_no(rm.get("orderno")) and _clean_str(rm.get("refstr"))
        ]
        orderhis_map = _load_orderhis_map(one_db, missing_fns) if missing_fns else None

    return [build_remote_snapshot(stype, rm, orderhis_map) for stype, rm in raw_cands]


def _taken_sources_for_snaps(
    local_db: Session | None,
    snaps: list[dict[str, Any]],
    exclude_row_ids: list[int] | None = None,
) -> set[tuple[str, int]]:
    if local_db is None or not snaps:
        return set()
    cand_ids = list({int(s["source_one_id"]) for s in snaps})
    stmt = select(
        DiscoverySynthesisOrder.source_one_type,
        DiscoverySynthesisOrder.source_one_id,
    ).where(DiscoverySynthesisOrder.source_one_id.in_(cand_ids))
    if exclude_row_ids:
        stmt = stmt.where(DiscoverySynthesisOrder.id.notin_(exclude_row_ids))
    return {
        (str(st).lower(), int(sid))
        for st, sid in local_db.execute(stmt).all()
        if st and sid is not None
    }


def _match_unlinked_rows_batch(
    one_db: Session,
    unlinked_rows: list[DiscoverySynthesisOrder],
    orderhis_map: dict[str, tuple[str, str]] | None = None,
    taken_sources: set[tuple[str, int]] | None = None,
    local_db: Session | None = None,
    preloaded_snaps: list[dict[str, Any]] | None = None,
) -> dict[int, dict[str, Any]]:
    if not unlinked_rows:
        return {}

    snaps = (
        preloaded_snaps
        if preloaded_snaps is not None
        else _query_candidates_for_rows(one_db, unlinked_rows, orderhis_map)
    )
    if not snaps:
        return {}

    exclude_ids = [int(r.id) for r in unlinked_rows if r.id]
    taken = set(taken_sources or set()) | _taken_sources_for_snaps(local_db, snaps, exclude_ids)

    by_order: dict[str, list[dict[str, Any]]] = {}
    by_batch: dict[str, list[dict[str, Any]]] = {}
    by_syn: dict[str, list[dict[str, Any]]] = {}

    for snap in snaps:
        ono = (snap.get("order_no") or "").upper()
        if ono:
            by_order.setdefault(ono, []).append(snap)
        sc = (snap.get("synthesis_code") or "").upper()
        if sc:
            by_syn.setdefault(sc, []).append(snap)
        for b_field in ("task_projectid", "task_projectcode", "task_batchname"):
            bv = (snap.get(b_field) or "").upper()
            if bv:
                by_batch.setdefault(bv, []).append(snap)

    matched: dict[int, dict[str, Any]] = {}

    def _pick(urow: DiscoverySynthesisOrder, cands: list[dict[str, Any]]) -> dict[str, Any] | None:
        avail = [
            c
            for c in cands
            if (str(c["source_one_type"]).lower(), int(c["source_one_id"])) not in taken
            and _is_compatible_candidate(urow, c)
        ]
        if not avail:
            return None
        if urow.synthetic_count is not None:
            for c in avail:
                if c.get("synthetic_count") == urow.synthetic_count:
                    return c
        return avail[0]

    # Pass 1: Exact order_no match
    for urow in unlinked_rows:
        ord_u = (urow.order_no or "").strip().upper()
        if not ord_u or ord_u not in by_order:
            continue
        chosen = _pick(urow, by_order[ord_u])
        if chosen:
            matched[urow.id] = chosen
            taken.add((str(chosen["source_one_type"]).lower(), int(chosen["source_one_id"])))

    # Pass 2: Batch label match
    for urow in unlinked_rows:
        if urow.id in matched:
            continue
        bat_keys = _batch_lookup_keys(urow.batch_label)
        if not bat_keys:
            continue
        cands: list[dict[str, Any]] = []
        for bk in bat_keys:
            cands.extend(by_batch.get(bk.upper(), []))
        chosen = _pick(urow, cands)
        if chosen:
            matched[urow.id] = chosen
            taken.add((str(chosen["source_one_type"]).lower(), int(chosen["source_one_id"])))

    # Pass 3: Synthesis code match
    for urow in unlinked_rows:
        if urow.id in matched:
            continue
        syn_u = (urow.synthesis_code or "").strip().upper()
        if not syn_u or syn_u not in by_syn:
            continue
        chosen = _pick(urow, by_syn[syn_u])
        if chosen:
            matched[urow.id] = chosen
            taken.add((str(chosen["source_one_type"]).lower(), int(chosen["source_one_id"])))

    return matched


def _collect_local_duplicates(
    db: Session,
    rows: list[DiscoverySynthesisOrder],
) -> dict[str, dict[str, list[str]]]:
    if not rows or len(rows) > 50:
        return {}
    row_ids = {int(r.id) for r in rows if r.id}
    ords = {r.order_no.strip() for r in rows if r.order_no and r.order_no.strip()}
    bats = {r.batch_label.strip() for r in rows if r.batch_label and r.batch_label.strip()}
    syns = {r.synthesis_code.strip() for r in rows if r.synthesis_code and r.synthesis_code.strip()}
    clauses = []
    if ords:
        clauses.append(DiscoverySynthesisOrder.order_no.in_(list(ords)))
    if bats:
        clauses.append(DiscoverySynthesisOrder.batch_label.in_(list(bats)))
    if syns:
        clauses.append(DiscoverySynthesisOrder.synthesis_code.in_(list(syns)))
    if not clauses:
        return {}

    others = db.scalars(
        select(DiscoverySynthesisOrder).where(
            DiscoverySynthesisOrder.id.notin_(list(row_ids)),
            or_(*clauses),
        )
    ).all()
    if not others:
        return {}

    result: dict[str, dict[str, list[str]]] = {}
    for r in rows:
        r_dups: dict[str, list[str]] = {}
        ord_u = (r.order_no or "").strip().upper()
        bat_u = (r.batch_label or "").strip().upper()
        syn_u = (r.synthesis_code or "").strip().upper()
        for o in others:
            if ord_u and (o.order_no or "").strip().upper() == ord_u:
                code_part = o.batch_label or o.synthesis_code or o.synthesis_order_id
                if code_part and code_part not in r_dups.setdefault("order_no", []):
                    r_dups["order_no"].append(code_part)
            if bat_u and (o.batch_label or "").strip().upper() == bat_u:
                code_part = o.order_no or o.synthesis_code or o.synthesis_order_id
                if code_part and code_part not in r_dups.setdefault("batch_label", []):
                    r_dups["batch_label"].append(code_part)
            if syn_u and (o.synthesis_code or "").strip().upper() == syn_u:
                code_part = o.order_no or o.batch_label or o.synthesis_order_id
                if code_part and code_part not in r_dups.setdefault("synthesis_code", []):
                    r_dups["synthesis_code"].append(code_part)
        if r_dups:
            result[str(r.id)] = r_dups
    return result


def _collect_single_row_candidates(
    db: Session,
    row: DiscoverySynthesisOrder,
    snaps: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if not snaps:
        return []
    taken_by_others = _taken_sources_for_snaps(db, snaps, [int(row.id)] if row.id else None)

    syn_u = (row.synthesis_code or "").strip().upper()
    bat_keys_u = tuple(k.upper() for k in _batch_lookup_keys(row.batch_label))

    seen_keys: set[tuple[str, int]] = set()
    items: list[dict[str, Any]] = []
    for s in snaps:
        key = (str(s["source_one_type"]).lower(), int(s["source_one_id"]))
        if key in seen_keys or key in taken_by_others:
            continue
        if (
            row.source_one_id == key[1]
            and (row.source_one_type or "").lower() == key[0]
        ):
            continue
        if not s.get("order_no") and not s.get("batch_label"):
            continue
        s_syn = (s.get("synthesis_code") or "").upper()
        s_batches = {
            (s.get(k) or "").upper()
            for k in ("task_projectid", "task_projectcode", "task_batchname")
            if s.get(k)
        }
        matches_syn = bool(syn_u and s_syn == syn_u)
        matches_bat = bool(bat_keys_u and any(bk in s_batches for bk in bat_keys_u))
        if not (matches_syn or matches_bat):
            continue
        seen_keys.add(key)
        items.append(
            {
                "source_one_type": key[0],
                "source_one_id": key[1],
                "order_no": s.get("order_no"),
                "batch_label": s.get("batch_label"),
                "synthesis_code": s.get("synthesis_code"),
                "synthetic_corp": s.get("synthetic_corp"),
                "synthetic_count": s.get("synthetic_count"),
                "synthetic_date": s.get("synthetic_date"),
                "arrival_count": s.get("arrival_count"),
                "arrival_date": s.get("arrival_date"),
            }
        )
        if len(items) >= 20:
            break
    return items


def check_remote_for_local_rows(
    db: Session,
    local_ids: list[int] | None = None,
    *,
    rows: list[DiscoverySynthesisOrder] | None = None,
    connect_timeout: int = 1,
    read_timeout: int = 1,
    max_rows: int = 500,
    serialize_changed: bool = True,
) -> dict[str, Any]:
    if rows is None:
        clean_ids = sorted({int(i) for i in (local_ids or []) if i and int(i) > 0})[:max_rows]
        if not clean_ids:
            return {"updated_items": [], "linked": 0, "updated": 0, "remote_available": True}
        rows = list(
            db.scalars(
                select(DiscoverySynthesisOrder).where(
                    DiscoverySynthesisOrder.id.in_(clean_ids),
                )
            ).all()
        )
    if not rows:
        return {"updated_items": [], "linked": 0, "updated": 0, "remote_available": True}

    ngs_ids = [
        int(r.source_one_id)
        for r in rows
        if (r.source_one_type or "").lower() == "ngs" and r.source_one_id
    ]
    beacon_ids = [
        int(r.source_one_id)
        for r in rows
        if (r.source_one_type or "").lower() == "beacon" and r.source_one_id
    ]
    unlinked_rows = [
        r
        for r in rows
        if not r.source_one_id and any((r.order_no, r.synthesis_code, r.batch_label))
    ]
    is_single_row = serialize_changed and len(rows) == 1 and any(
        (rows[0].order_no, rows[0].synthesis_code, rows[0].batch_label)
    )
    if not ngs_ids and not beacon_ids and not unlinked_rows and not is_single_row:
        return {"updated_items": [], "linked": 0, "updated": 0, "remote_available": True}

    taken_sources: set[tuple[str, int]] = {
        (str(r.source_one_type).lower(), int(r.source_one_id))
        for r in rows
        if r.source_one_type and r.source_one_id is not None
    }

    unlinked_matches: dict[int, dict[str, Any]] = {}
    single_row_snaps: list[dict[str, Any]] = []
    try:
        with open_one_db(connect_timeout=connect_timeout, read_timeout=read_timeout) as one_db:
            if one_db is None:
                return {
                    "updated_items": [],
                    "linked": 0,
                    "updated": 0,
                    "duplicates": _collect_local_duplicates(db, rows) if serialize_changed else {},
                    "candidates": {},
                    "remote_available": False,
                }
            remote_map = fetch_remote_snapshots_by_ids(one_db, ngs_ids, beacon_ids)
            if is_single_row:
                try:
                    single_row_snaps = _query_candidates_for_rows(one_db, rows)
                except Exception:
                    single_row_snaps = []
            if unlinked_rows:
                unlinked_matches = _match_unlinked_rows_batch(
                    one_db,
                    unlinked_rows,
                    None,
                    taken_sources,
                    local_db=db,
                    preloaded_snaps=single_row_snaps if is_single_row else None,
                )
    except Exception:
        logger.warning("check_remote_for_local_rows failed or timed out", exc_info=True)
        return {
            "updated_items": [],
            "linked": 0,
            "updated": 0,
            "duplicates": _collect_local_duplicates(db, rows) if serialize_changed else {},
            "candidates": {},
            "remote_available": False,
        }

    changed_rows: list[DiscoverySynthesisOrder] = []
    linked_count = 0
    updated_count = 0
    db_dirty = False
    for row in rows:
        newly_linked = False
        replace_snap: dict[str, Any] | None = None
        if row.source_one_id:
            key = (str(row.source_one_type or "").lower(), int(row.source_one_id))
            snap = remote_map.get(key)
        else:
            snap = unlinked_matches.get(row.id)
            if snap:
                if isinstance(row.source_snapshot, dict) and row.source_snapshot:
                    replace_snap = dict(row.source_snapshot)
                row.source_one_type = str(snap["source_one_type"]).lower()
                row.source_one_id = int(snap["source_one_id"])
                newly_linked = True
                linked_count += 1
                db_dirty = True
            elif row.source_snapshot:
                row.source_snapshot = None
                db_dirty = True
                changed_rows.append(row)
        if not snap:
            continue
        prev_drifts = compute_drift_fields(row)
        before_vals = (
            row.status,
            row.synthesis_code,
            row.batch_label,
            *(getattr(row, f, None) for f in DRIFT_COMPARE_FIELDS),
        )
        row_changed = apply_remote_snapshot_to_row(
            row, snap, replace_from_snapshot=replace_snap
        )
        after_vals = (
            row.status,
            row.synthesis_code,
            row.batch_label,
            *(getattr(row, f, None) for f in DRIFT_COMPARE_FIELDS),
        )
        drifts = compute_drift_fields(row)
        if row_changed:
            db_dirty = True
        if before_vals != after_vals or drifts != prev_drifts or newly_linked:
            if before_vals != after_vals and not newly_linked:
                updated_count += 1
            changed_rows.append(row)

    from modules.discovery.synthesis_progress.service import serialize_order

    updated_items = [serialize_order(row) for row in changed_rows] if serialize_changed else []
    if db_dirty:
        db.commit()

    candidates_map: dict[str, list[dict[str, Any]]] = {}
    if is_single_row and single_row_snaps:
        c_list = _collect_single_row_candidates(db, rows[0], single_row_snaps)
        if c_list:
            candidates_map[str(rows[0].id)] = c_list

    return {
        "updated_items": updated_items,
        "linked": linked_count,
        "updated": updated_count,
        "duplicates": _collect_local_duplicates(db, rows) if serialize_changed else {},
        "candidates": candidates_map,
        "remote_available": True,
    }
