from typing import Any, Callable

from sqlalchemy import case

DEFAULT_PRIORITY = "正常"
PRIORITY_ORDER = ("吉吉国王", "非常紧急", "加急", "正常")


def queued_sort(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        number = int(value)
    except (TypeError, ValueError):
        return None
    return number if number > 0 else None


def list_order_clauses(sort_field: Any, sort_column: Any, id_column: Any) -> tuple:
    if str(sort_field or "").strip() == "sort_order":
        return (
            case((sort_column.is_(None), 1), else_=0),
            sort_column.asc(),
            id_column.asc(),
        )
    return (id_column.desc(),)


def canonicalize_priority(value: Any) -> str:
    return str(value or "").strip() or DEFAULT_PRIORITY


def priority_rank(value: Any) -> int:
    canon = canonicalize_priority(value)
    try:
        return PRIORITY_ORDER.index(canon)
    except ValueError:
        return len(PRIORITY_ORDER)


def band_index_range(others: list[Any], priority: Any) -> tuple[int, int]:
    """Insert indices in ``others`` for priority P: first of band .. after last peer."""
    rank = priority_rank(priority)
    first_insert = 0
    last_peer_index = None
    for index, item in enumerate(others or []):
        item_rank = priority_rank(getattr(item, "priority", None))
        if item_rank < rank:
            first_insert = index + 1
        elif item_rank == rank:
            last_peer_index = index
    last_insert = last_peer_index + 1 if last_peer_index is not None else first_insert
    return first_insert, last_insert


def insert_index_for_target(others: list[Any], priority: Any, target_sort: int) -> int:
    first_insert, last_insert = band_index_range(others, priority)
    desired = max(0, int(target_sort) - 1)
    return min(max(desired, first_insert), last_insert)


def renumber_queue(rows: list[Any]) -> None:
    for index, row in enumerate(rows, start=1):
        row.sort_order = index


def place_row_among(
    others: list[Any],
    row: Any,
    *,
    mode: str,
    target_sort: int | None = None,
) -> None:
    first_insert, last_insert = band_index_range(others, getattr(row, "priority", None))
    if mode == "first":
        index = first_insert
    elif mode == "last":
        index = last_insert
    else:
        index = insert_index_for_target(
            others,
            getattr(row, "priority", None),
            int(target_sort if target_sort is not None else row.sort_order or 0),
        )
    others.insert(index, row)
    renumber_queue(others)


def apply_priority_constraints(
    row: Any,
    *,
    previous_sort: int | None,
    previous_priority: Any,
    place: Callable[..., None],
) -> None:
    current_sort = queued_sort(row.sort_order) or 0
    sort_changed = current_sort != (queued_sort(previous_sort) or 0)
    priority_changed = canonicalize_priority(row.priority) != canonicalize_priority(previous_priority)
    if not sort_changed and not priority_changed:
        return
    if priority_changed and not sort_changed:
        demote = priority_rank(row.priority) > priority_rank(previous_priority)
        place("first" if demote else "last")
        return
    place("snap", current_sort)
