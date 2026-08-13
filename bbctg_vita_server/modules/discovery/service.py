from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import case, func, or_, select
from sqlalchemy.orm import Session

from models.target import Target


SEARCH_FIELDS = (
    Target.snum,
    Target.name,
    Target.official_full_name,
    Target.human_gene_official_name,
    Target.human_gene_alias_name,
    Target.human_ncbi_gene_id,
    Target.mouse_gene_official_name,
    Target.mouse_gene_alias_name,
    Target.mouse_ncbi_gene_id,
)
GENE_NAME_FIELDS = (
    Target.human_gene_official_name,
    Target.mouse_gene_official_name,
)
ALIAS_FIELDS = (
    Target.human_gene_alias_name,
    Target.mouse_gene_alias_name,
)
NCBI_ID_FIELDS = (
    Target.human_ncbi_gene_id,
    Target.mouse_ncbi_gene_id,
)

TARGET_FIELDS = tuple(column.key for column in Target.__table__.columns)


def get_target_list(db: Session, data: dict[str, Any]) -> dict[str, Any]:
    page = max(_to_int(data.get("page"), 1), 1)
    limit = min(max(_to_int(data.get("limit"), 20), 1), 100)
    conditions = []

    if not _to_bool(data.get("include_inactive")):
        conditions.append(Target.is_active.is_(True))

    keyword = str(data.get("keyword") or "").strip()
    order_by = [Target.name.asc(), Target.snum.asc()]
    if keyword:
        escaped_keyword = _escape_like(keyword)
        exact_pattern = escaped_keyword
        prefix_pattern = f"{escaped_keyword}%"
        contains_pattern = f"%{escaped_keyword}%"
        conditions.append(
            or_(*(_matches(field, contains_pattern) for field in SEARCH_FIELDS))
        )
        relevance = case(
            (_matches(Target.snum, exact_pattern), 0),
            (_matches(Target.name, exact_pattern), 1),
            (or_(*(_matches(field, exact_pattern) for field in GENE_NAME_FIELDS)), 2),
            (or_(*(_matches(field, exact_pattern) for field in NCBI_ID_FIELDS)), 3),
            (
                or_(
                    _matches(Target.official_full_name, exact_pattern),
                    *(_matches(field, exact_pattern) for field in ALIAS_FIELDS),
                ),
                4,
            ),
            (_matches(Target.snum, prefix_pattern), 10),
            (
                or_(
                    _matches(Target.name, prefix_pattern),
                    *(_matches(field, prefix_pattern) for field in GENE_NAME_FIELDS),
                ),
                11,
            ),
            (_matches(Target.name, contains_pattern), 20),
            (or_(*(_matches(field, contains_pattern) for field in GENE_NAME_FIELDS)), 21),
            (_matches(Target.snum, contains_pattern), 22),
            (or_(*(_matches(field, contains_pattern) for field in ALIAS_FIELDS)), 30),
            (_matches(Target.official_full_name, contains_pattern), 40),
            (or_(*(_matches(field, contains_pattern) for field in NCBI_ID_FIELDS)), 50),
            else_=60,
        )
        name_match_length = case(
            (_matches(Target.name, contains_pattern), func.length(Target.name)),
            else_=9999,
        )
        order_by = [relevance.asc(), name_match_length.asc(), *order_by]

    status = data.get("status")
    if status == "unknown":
        conditions.append(Target.status.is_(None))
    elif status not in (None, "", "all"):
        try:
            conditions.append(Target.status == int(status))
        except (TypeError, ValueError):
            pass

    total = db.scalar(select(func.count(Target.id)).where(*conditions)) or 0
    targets = db.scalars(
        select(Target)
        .where(*conditions)
        .order_by(*order_by)
        .offset((page - 1) * limit)
        .limit(limit)
    ).all()

    return {
        "items": [_target_to_dict(target) for target in targets],
        "total": total,
        "page": page,
        "limit": limit,
        "stats": _get_target_stats(db),
    }


def _get_target_stats(db: Session) -> dict[str, Any]:
    row = db.execute(
        select(
            func.count(Target.id),
            func.count(case((Target.status == 1, 1))),
            func.count(case((Target.status == 2, 1))),
            func.count(case((Target.status.is_(None), 1))),
            func.max(Target.synced_at),
        ).where(Target.is_active.is_(True))
    ).one()
    return {
        "total": int(row[0] or 0),
        "developed": int(row[1] or 0),
        "undeveloped": int(row[2] or 0),
        "unmarked": int(row[3] or 0),
        "synced_at": _serialize(row[4]),
    }


def _target_to_dict(target: Target) -> dict[str, Any]:
    return {field: _serialize(getattr(target, field)) for field in TARGET_FIELDS}


def _serialize(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat(sep=" ", timespec="seconds")
    return value


def _to_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _to_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def _escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _matches(field: Any, pattern: str) -> Any:
    return field.ilike(pattern, escape="\\")
