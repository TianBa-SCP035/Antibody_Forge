from collections.abc import Callable, Mapping, Sequence
from typing import Any

from sqlalchemy.orm import Session

DEFAULT_PAGE_LIMIT = 20
MAX_PAGE_LIMIT = 500


def parse_page_limit(
    data: Mapping[str, Any] | None,
    *,
    default_limit: int = DEFAULT_PAGE_LIMIT,
    max_limit: int = MAX_PAGE_LIMIT,
) -> tuple[int, int]:
    payload = data or {}
    try:
        page = int(payload.get("page", 1) or 1)
    except (TypeError, ValueError):
        page = 1
    try:
        limit = int(payload.get("limit", default_limit) or default_limit)
    except (TypeError, ValueError):
        limit = default_limit
    return max(page, 1), min(max(limit, 1), max_limit)


def paginate_select(
    db: Session,
    stmt: Any,
    count_stmt: Any,
    data: Mapping[str, Any] | None = None,
    *,
    order_by: Sequence[Any] = (),
    serialize_rows: Callable[[list[Any]], list[Any]] | None = None,
    unique: bool = False,
    clamp_page: bool = False,
    stats: dict[str, Any] | None = None,
    default_limit: int = DEFAULT_PAGE_LIMIT,
    max_limit: int = MAX_PAGE_LIMIT,
) -> dict[str, Any]:
    page, limit = parse_page_limit(data, default_limit=default_limit, max_limit=max_limit)
    total = int(db.scalar(count_stmt) or 0)
    if clamp_page:
        last_page = max(1, (total + limit - 1) // limit)
        if page > last_page:
            page = last_page
    ordered = stmt.order_by(*order_by) if order_by else stmt
    scalars = db.scalars(ordered.offset((page - 1) * limit).limit(limit))
    if unique:
        scalars = scalars.unique()
    rows = list(scalars.all())
    items = (
        serialize_rows(rows)
        if serialize_rows is not None
        else [row.to_dict() for row in rows]
    )
    result: dict[str, Any] = {
        "items": items,
        "total": total,
        "page": page,
        "limit": limit,
    }
    if stats is not None:
        result["stats"] = stats
    return result
