from dataclasses import dataclass
from typing import Any, Callable

from sqlalchemy import case, event, inspect, select, update
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import set_committed_value

from core.errors import NotFoundError

DEFAULT_PRIORITY = "正常"
PRIORITY_ORDER = ("吉吉国王", "非常紧急", "加急", "正常")
# 下拉选项按从低到高排列，与队列顺序相反。
PRIORITY_OPTIONS = tuple(reversed(PRIORITY_ORDER))

_WROTE_KEY = "workbench_queue_wrote"


@event.listens_for(Session, "after_flush")
def _mark_flushed(session: Session, _flush_context: Any) -> None:
    session.info[_WROTE_KEY] = True


@event.listens_for(Session, "do_orm_execute")
def _mark_dml(state: Any) -> None:
    if state.is_insert or state.is_update or state.is_delete:
        state.session.info[_WROTE_KEY] = True


@event.listens_for(Session, "after_transaction_end")
def _clear_wrote(session: Session, transaction: Any) -> None:
    if transaction.parent is None:
        session.info.pop(_WROTE_KEY, None)


def lock_queue(db: Session, model: Any) -> None:
    """队列写入前锁住整表的行（按主键顺序，避免死锁），并发写入者排队分配队列位。

    可重复读下，事务里第一次普通查询（如登录校验）就定了读快照，等锁期间别人提交的改动加锁后仍读不到；
    本事务还没写过东西时先提交，让加锁之后的读取从锁后开始。
    加锁前不自动 flush：会话里已改的行若先被 UPDATE，就会按任意顺序先占行锁，破坏按主键加锁的顺序。
    """
    if not (db.new or db.dirty or db.deleted or db.info.get(_WROTE_KEY)):
        db.commit()
    with db.no_autoflush:
        db.scalars(select(model.id).order_by(model.id.asc()).with_for_update()).all()


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
    """返回该优先级在 others 中可插入的首个位置和同级末尾后一位。"""
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


_SHIFT_CHUNK = 500


def renumber_queue(rows: list[Any], *, moved: Any = None) -> None:
    """按列表顺序重编 1..N。

    只是被顺移的行合并成批量 UPDATE、不进审计（否则一次出队要逐行写上千条）；
    moved 和本会话里已改过排序的行照常走 ORM，保留审计。
    """
    shifted: dict[Any, dict[Any, int]] = {}
    for index, row in enumerate(rows, start=1):
        if row.sort_order == index:
            continue
        state = inspect(row, raiseerr=False)
        if (
            row is moved
            or state is None
            or not state.persistent
            or state.attrs.sort_order.history.has_changes()
        ):
            row.sort_order = index
            continue
        shifted.setdefault((state.session, state.mapper.local_table), {})[row.id] = index
        set_committed_value(row, "sort_order", index)
    for (session, table), orders in shifted.items():
        ids = list(orders)
        for start in range(0, len(ids), _SHIFT_CHUNK):
            chunk = {row_id: orders[row_id] for row_id in ids[start : start + _SHIFT_CHUNK]}
            session.execute(
                update(table)
                .where(table.c.id.in_(list(chunk)))
                .values(sort_order=case(chunk, value=table.c.id))
            )


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
    renumber_queue(others, moved=row)


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


@dataclass(frozen=True)
class QueueSpec:
    model: Any
    active_stmt: Callable[[], Any]
    missing_message: str
    is_terminal_row: Callable[[Session, Any], bool]
    unique_rows: bool = False


def _parse_id(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def queue_rows(db: Session, spec: QueueSpec) -> list[Any]:
    stmt = spec.active_stmt().order_by(
        spec.model.sort_order.asc(),
        spec.model.id.asc(),
    )
    scalars = db.scalars(stmt)
    if spec.unique_rows:
        scalars = scalars.unique()
    return list(scalars.all())


def place_row(
    db: Session,
    spec: QueueSpec,
    row: Any,
    *,
    mode: str,
    target_sort: int | None = None,
) -> None:
    if not getattr(row, "id", None):
        db.flush()
    others = [item for item in queue_rows(db, spec) if int(item.id) != int(row.id)]
    place_row_among(others, row, mode=mode, target_sort=target_sort)


def repack_queue(db: Session, spec: QueueSpec, *, exclude_id: int | None = None) -> None:
    rows = queue_rows(db, spec)
    if exclude_id is not None:
        rows = [item for item in rows if int(item.id) != int(exclude_id)]
    renumber_queue(rows)


def apply_queue(
    db: Session,
    spec: QueueSpec,
    row: Any,
    *,
    previous_sort: int | None,
    previous_priority: Any,
    target_sort: int | None = None,
    is_new: bool = False,
    is_terminal: bool | None = None,
) -> None:
    terminal = is_terminal if is_terminal is not None else spec.is_terminal_row(db, row)
    if terminal:
        leaving = (
            queued_sort(previous_sort) is not None
            or queued_sort(row.sort_order) is not None
        )
        row.sort_order = None
        if leaving:
            repack_queue(db, spec, exclude_id=int(row.id or 0) if getattr(row, "id", None) else None)
        return
    if is_new or queued_sort(previous_sort) is None:
        place_row(db, spec, row, mode="snap" if target_sort else "last", target_sort=target_sort)
        return
    apply_priority_constraints(
        row,
        previous_sort=previous_sort,
        previous_priority=previous_priority,
        place=lambda mode, sort_target=None: place_row(
            db, spec, row, mode=mode, target_sort=sort_target
        ),
    )


def reorder_queue(
    db: Session,
    spec: QueueSpec,
    moved_id: Any,
    target_id: Any,
    *,
    authorize: Callable[[Any], None] | None = None,
) -> list[Any]:
    lock_queue(db, spec.model)
    parsed_moved_id = _parse_id(moved_id)
    parsed_target_id = _parse_id(target_id)
    if parsed_moved_id is None or parsed_target_id is None:
        raise ValueError("排序记录 ID 不正确")
    moved = db.get(spec.model, parsed_moved_id)
    target = db.get(spec.model, parsed_target_id)
    if not moved or not target:
        raise NotFoundError(spec.missing_message)
    if authorize is not None:
        authorize(moved)
    if parsed_moved_id == parsed_target_id:
        return [moved]
    for row in (moved, target):
        if spec.is_terminal_row(db, row) or queued_sort(row.sort_order) is None:
            raise ValueError("终态记录不参与排序")
    place_row(
        db,
        spec,
        moved,
        mode="snap",
        target_sort=queued_sort(target.sort_order),
    )
    db.commit()
    return [moved, target]
