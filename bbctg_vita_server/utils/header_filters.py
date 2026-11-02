"""表头筛选（类 Excel 自动筛选）：按列登记生成筛选条件、取值列表和排序，供各工作台复用。

前端每列只传一份状态：values 只看这些值、exclude 排除这些值、condition 条件、colors 颜色。
空值统一用 ''。一格多个值的列（逗号分隔、靶点）用 kind="multi"，按「含有该值」匹配。
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Callable

from sqlalchemy import String, and_, case, cast, false, func, not_, or_, select
from sqlalchemy.orm import Session

from utils.filter_values import (
    catalog_names_for_pairs,
    like_literal,
    recorded_target_clause,
    split_target_names,
    target_select_options,
)
from utils.normalize import DATE_FORMAT_MESSAGE, normalize_date, split_tokens

TEXT_OPS = frozenset({"contains", "not_contains", "eq", "neq", "starts", "ends"})
RANGE_OPS = frozenset({"eq", "gte", "lte", "between"})
BLANK_OPS = frozenset({"blank", "not_blank"})
VALUE_ORDERS = frozenset({"value", "value_desc", "recent"})
DEFAULT_VALUE_LIMIT = 200
MAX_VALUE_LIMIT = 1000
MAX_FILTER_VALUES = 2000
# 「最近出现」只看最近这么多行：单号类列几乎一行一个值，结果与全表精确计算一致，成本固定。
RECENT_SAMPLE_ROWS = 5000
CSV_SEPARATORS = (",", "，", "、", "+")

Scoped = Callable[[Any], Any]


@dataclass(frozen=True)
class HeaderColumn:
    """kind: text | enum | number | date | multi。

    order 是枚举的业务顺序；multi 列必须提供 match（含有任一值的条件）和 values（取值列表）。
    colors 提供按颜色筛选的条件。blank 是自定义的空白条件（如 JSON 空数组），不能产生 NULL。
    """

    column: Any
    kind: str = "text"
    order: tuple[str, ...] = ()
    match: Callable[[Session | None, list[str]], Any] | None = None
    values: Callable[[Session, Scoped, str], list[dict[str, Any]]] | None = None
    colors: Callable[[list[str]], Any] | None = None
    blank: Any = None


def blank_clause(spec: HeaderColumn):
    if spec.blank is not None:
        return spec.blank
    column = spec.column
    if spec.kind == "number":
        return column.is_(None)
    if spec.kind == "date":
        return or_(column.is_(None), cast(column, String) == "")
    return or_(column.is_(None), column == "")


def _not_blank(spec: HeaderColumn):
    if spec.blank is not None:
        return not_(spec.blank)
    column = spec.column
    if spec.kind == "number":
        return column.is_not(None)
    if spec.kind == "date":
        return and_(column.is_not(None), cast(column, String) != "")
    return and_(column.is_not(None), column != "")


def _is_blank_value(value: Any) -> bool:
    return value is None or str(value).strip() == ""


def _number(value: Any) -> int:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError) as exc:
        raise ValueError("请输入整数") from exc


def _typed(spec: HeaderColumn, value: Any):
    if spec.kind == "number":
        return _number(value)
    if spec.kind == "date":
        text = normalize_date(value)
        if not text:
            raise ValueError(DATE_FORMAT_MESSAGE)
        return text
    return str(value).strip()


def _terms(raw: Any, label: str) -> list[Any]:
    if raw is None:
        return []
    if not isinstance(raw, (list, tuple)):
        raise ValueError(f"表头筛选{label}必须是数组")
    if len(raw) > MAX_FILTER_VALUES:
        raise ValueError(f"表头筛选一次最多 {MAX_FILTER_VALUES} 个值")
    return list(raw)


def _contains_values(db: Session | None, spec: HeaderColumn, values: list[Any]):
    """含有任一非空值的条件。"""
    if spec.kind == "multi":
        return spec.match(db, [str(v).strip() for v in values])
    typed = [_typed(spec, v) for v in values]
    return spec.column.in_(typed)


def _values_clause(db: Session | None, spec: HeaderColumn, values: list[Any]):
    picked = [v for v in values if not _is_blank_value(v)]
    parts = []
    if picked:
        parts.append(_contains_values(db, spec, picked))
    if len(picked) < len(values):
        parts.append(blank_clause(spec))
    if not parts:
        return false()
    return parts[0] if len(parts) == 1 else or_(*parts)


def _exclude_clause(db: Session | None, spec: HeaderColumn, values: list[Any]):
    denied = [v for v in values if not _is_blank_value(v)]
    deny_blank = len(denied) < len(values)
    if not denied:
        return _not_blank(spec) if deny_blank else None
    hit = _contains_values(db, spec, denied)
    if deny_blank:
        return and_(_not_blank(spec), not_(hit))
    return or_(blank_clause(spec), not_(hit))


def _condition_clause(spec: HeaderColumn, condition: Any):
    if not isinstance(condition, dict):
        raise ValueError("表头筛选条件格式不正确")
    op = str(condition.get("op") or "").strip()
    if not op:
        return None
    column = spec.column
    if op == "blank":
        return blank_clause(spec)
    if op == "not_blank":
        return _not_blank(spec)
    value = condition.get("value")
    value2 = condition.get("value2")
    if spec.kind in {"number", "date"}:
        if op not in RANGE_OPS:
            raise ValueError("表头筛选条件不支持该列")
        if op == "between":
            parts = [_not_blank(spec)]
            if not _is_blank_value(value):
                parts.append(column >= _typed(spec, value))
            if not _is_blank_value(value2):
                parts.append(column <= _typed(spec, value2))
            return and_(*parts) if len(parts) > 1 else None
        if _is_blank_value(value):
            return None
        target = _typed(spec, value)
        if op == "eq":
            return column == target
        return and_(_not_blank(spec), column >= target if op == "gte" else column <= target)
    if op not in TEXT_OPS:
        raise ValueError("表头筛选条件不支持该列")
    text = str(value or "").strip()
    if not text:
        return None
    literal = like_literal(text)
    if op == "contains":
        return column.like(f"%{literal}%", escape="\\")
    if op == "not_contains":
        return or_(blank_clause(spec), not_(column.like(f"%{literal}%", escape="\\")))
    if op == "starts":
        return column.like(f"{literal}%", escape="\\")
    if op == "ends":
        return column.like(f"%{literal}", escape="\\")
    if op == "eq":
        return column == text
    return or_(blank_clause(spec), column != text)


def header_filter_clauses(
    db: Session | None,
    columns: dict[str, HeaderColumn],
    field_filters: Any,
    *,
    except_field: str | None = None,
) -> list[Any]:
    if not field_filters:
        return []
    if not isinstance(field_filters, list):
        raise ValueError("表头筛选格式不正确")
    clauses = []
    for item in field_filters:
        if not isinstance(item, dict):
            raise ValueError("表头筛选格式不正确")
        field = str(item.get("field") or "").strip()
        spec = columns.get(field)
        if spec is None:
            raise ValueError(f"不支持按「{field}」表头筛选")
        if field == except_field:
            continue
        if item.get("values") is not None:
            clauses.append(_values_clause(db, spec, _terms(item["values"], "值")))
        exclude = _terms(item.get("exclude"), "排除值")
        if exclude:
            clause = _exclude_clause(db, spec, exclude)
            if clause is not None:
                clauses.append(clause)
        colors = _terms(item.get("colors"), "颜色")
        if colors:
            if spec.colors is None:
                raise ValueError(f"「{field}」不支持按颜色筛选")
            clause = spec.colors([str(c).strip().lower() for c in colors])
            if clause is not None:
                clauses.append(clause)
        if item.get("condition"):
            clause = _condition_clause(spec, item["condition"])
            if clause is not None:
                clauses.append(clause)
    return clauses


def header_sort_expression(spec: HeaderColumn):
    if spec.order:
        return case(
            *[(spec.column == value, index) for index, value in enumerate(spec.order)],
            else_=len(spec.order),
        )
    return spec.column


def header_sort_clauses(spec: HeaderColumn, direction: str, id_column):
    """空值总在最后；有业务顺序的先按业务顺序，顺序外的值再按原值。"""
    keys = [header_sort_expression(spec)]
    if spec.order:
        keys.append(spec.column)
    return (
        case((blank_clause(spec), 1), else_=0),
        *[key.asc() if direction == "asc" else key.desc() for key in keys],
        id_column.desc(),
    )


def _keyword_clause(spec: HeaderColumn, keyword: str):
    literal = like_literal(keyword)
    target = cast(spec.column, String) if spec.kind in {"number", "date"} else spec.column
    return target.like(f"%{literal}%", escape="\\")


def _in_business_order(spec: HeaderColumn, rows: list[tuple[Any, int]]) -> list[tuple[Any, int]]:
    rank = {value: index for index, value in enumerate(spec.order)}
    return sorted(rows, key=lambda item: (rank.get(item[0], len(rank)), str(item[0])))


def column_values(
    db: Session,
    spec: HeaderColumn,
    scoped: Scoped,
    *,
    id_column,
    keyword: str = "",
    limit: int = DEFAULT_VALUE_LIMIT,
    order: str = "value",
) -> dict[str, Any]:
    """scoped(stmt) 给语句套上「除本列以外」的全部筛选。空值单独计数，不受 limit 截断。"""
    keyword = str(keyword or "").strip()
    limit = max(1, min(int(limit or DEFAULT_VALUE_LIMIT), MAX_VALUE_LIMIT))
    if order not in VALUE_ORDERS:
        raise ValueError("取值排序方式不正确")
    column = spec.column

    if spec.kind == "multi":
        listed = spec.values(db, scoped, keyword)
        items = listed[:limit]
        truncated = len(listed) > limit
    elif order == "recent":
        where = [_not_blank(spec)]
        if keyword:
            where.append(_keyword_clause(spec, keyword))
        sample = (
            scoped(select(column.label("v"), id_column.label("rid")).where(*where))
            .order_by(id_column.desc())
            .limit(RECENT_SAMPLE_ROWS)
            .subquery()
        )
        picked = db.scalars(
            select(sample.c.v)
            .group_by(sample.c.v)
            .order_by(func.max(sample.c.rid).desc())
            .limit(limit + 1)
        ).all()
        sampled = db.scalar(select(func.count()).select_from(sample)) or 0
        truncated = len(picked) > limit or sampled >= RECENT_SAMPLE_ROWS
        picked = picked[:limit]
        counts = dict(
            db.execute(
                scoped(select(column, func.count(id_column)).where(column.in_(picked)).group_by(column))
            ).all()
        ) if picked else {}
        items = [{"value": value, "count": int(counts.get(value, 0))} for value in picked]
    else:
        where = [_not_blank(spec)]
        if keyword:
            where.append(_keyword_clause(spec, keyword))
        stmt = scoped(select(column, func.count(id_column)).where(*where).group_by(column))
        if spec.order:
            rows = _in_business_order(spec, db.execute(stmt).all())
        else:
            descending = order == "value_desc"
            rows = db.execute(
                stmt.order_by(column.desc() if descending else column.asc()).limit(limit + 1)
            ).all()
        truncated = len(rows) > limit
        items = [{"value": value, "count": int(count)} for value, count in rows[:limit]]

    if not keyword:
        blank_count = db.scalar(scoped(select(func.count(id_column)).where(blank_clause(spec)))) or 0
        if blank_count:
            items.append({"value": "", "count": int(blank_count)})
    return {"items": items, "truncated": truncated}


def csv_token_clause(column, token: str):
    literal = like_literal(token)
    clauses = [column == token]
    for sep in CSV_SEPARATORS:
        clauses.extend(
            (
                column.like(f"{literal}{sep}%", escape="\\"),
                column.like(f"%{sep}{literal}", escape="\\"),
                column.like(f"%{sep}{literal}{sep}%", escape="\\"),
            )
        )
    return or_(*clauses)


def csv_column(column, presets: tuple[str, ...] = ()) -> HeaderColumn:
    """一格多个值、用逗号/顿号/加号分隔的列。值按预设顺序在前，其余按字母。"""

    def match(_db, tokens: list[str]):
        clauses = [csv_token_clause(column, token) for token in tokens]
        return clauses[0] if len(clauses) == 1 else or_(*clauses)

    def values(db: Session, scoped: Scoped, keyword: str) -> list[dict[str, Any]]:
        rows = db.execute(
            scoped(
                select(column, func.count())
                .where(column.is_not(None), column != "")
                .group_by(column)
            )
        ).all()
        counts: dict[str, int] = defaultdict(int)
        for raw, count in rows:
            for token in split_tokens(raw):
                counts[token] += int(count)
        text = keyword.lower()
        rank = {value: index for index, value in enumerate(presets)}
        found = [token for token in counts if not text or text in token.lower()]
        found.sort(key=lambda token: (rank.get(token, len(rank)), token))
        return [{"value": token, "count": counts[token]} for token in found]

    return HeaderColumn(column, "multi", match=match, values=values)


def target_value_items(
    options: list[dict[str, Any]],
    name_counts: list[tuple[Any, int]],
    keyword: str = "",
) -> list[dict[str, Any]]:
    """把记录上的靶点名称计数归到下拉选项（同编号的不同写法合为一组，组合靶点单独成项）。

    一行含多个靶点时，计入每个靶点；与按靶点筛选「含有该靶点」的口径一致。
    """
    group_of: dict[str, str] = {}
    combos: set[str] = set()
    by_value = {item["value"]: item for item in options}
    for item in options:
        if len(split_target_names(item["value"])) > 1:
            combos.add(item["value"])
            continue
        for name in (item["value"], *item.get("aliases", [])):
            group_of.setdefault(name, item["value"])
    counts: dict[str, int] = defaultdict(int)
    for raw, count in name_counts:
        text = str(raw or "").strip()
        if not text:
            continue
        for value in {group_of.get(token, token) for token in split_target_names(text)}:
            counts[value] += int(count)
        if text in combos:
            counts[text] += int(count)
    needle = str(keyword or "").strip().lower()
    items = []
    for value, count in counts.items():
        option = by_value.get(value) or {"value": value, "label": value, "aliases": [], "codes": []}
        words = [option["label"], value, *option.get("aliases", []), *option.get("codes", [])]
        if needle and not any(needle in str(word).lower() for word in words):
            continue
        items.append({
            "value": value,
            "label": option["label"],
            "aliases": list(option.get("aliases", [])),
            "codes": list(option.get("codes", [])),
            "count": count,
        })
    items.sort(key=lambda item: str(item["label"]))
    return items


def target_column(name_column, codes_column, *, colors: Callable[[list[str]], Any] | None = None) -> HeaderColumn:
    """靶点列：取值按靶点下拉的分组列出，选中按「含有该靶点」匹配，与顶部靶点筛选同一口径。"""

    def match(db: Session | None, names: list[str]):
        return recorded_target_clause(db, name_column, codes_column, names, select(name_column, codes_column))

    def values(db: Session, scoped: Scoped, keyword: str) -> list[dict[str, Any]]:
        # 选项要先按编号归组（同靶点不同写法合一项），不能先按关键字裁掉配对行
        pairs = db.execute(select(name_column, codes_column).distinct()).all()
        options = target_select_options(pairs, catalog_names_for_pairs(db, pairs))
        name_counts = db.execute(
            scoped(
                select(name_column, func.count())
                .where(name_column.is_not(None), name_column != "")
                .group_by(name_column)
            )
        ).all()
        return target_value_items(options, name_counts, keyword)

    return HeaderColumn(name_column, "multi", match=match, values=values, colors=colors)
