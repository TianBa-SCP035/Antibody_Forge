"""列表筛选值。单个值保持原样，多个值按「满足任一」合并。"""

import json
import re
from typing import Any, Callable

from sqlalchemy import String, cast, or_, select

_TARGET_NAME_SPLIT = re.compile(r"[&＆,，]")


def _like_literal(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def filter_terms(value: Any) -> list[str]:
    if value is None or value is False:
        return []
    if isinstance(value, (list, tuple, set)):
        terms: list[str] = []
        for item in value:
            text = "" if item is None else str(item).strip()
            if text:
                terms.append(text)
        return terms
    text = str(value).strip()
    return [text] if text else []


def match_any(column, value: Any):
    terms = filter_terms(value)
    if not terms:
        return None
    if len(terms) == 1:
        return column == terms[0]
    return column.in_(tuple(terms))


def combine_any(value: Any, clause_for: Callable[[str], Any]):
    clauses = []
    for term in filter_terms(value):
        clause = clause_for(term)
        if clause is not None:
            clauses.append(clause)
    if not clauses:
        return None
    if len(clauses) == 1:
        return clauses[0]
    return or_(*clauses)


def restrict(stmt, value: Any, clause_for: Callable[[str], Any]):
    condition = combine_any(value, clause_for)
    if condition is None:
        return stmt
    return stmt.where(condition)


def split_target_names(value: Any) -> list[str]:
    return [part.strip() for part in _TARGET_NAME_SPLIT.split(str(value or "")) if part.strip()]


def coerce_target_codes(value: Any) -> list[str]:
    if isinstance(value, list):
        return [text for item in value if (text := str(item or "").strip())]
    if not isinstance(value, str):
        return []
    text = value.strip()
    if not text:
        return []
    if text.startswith("["):
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            parsed = None
        if isinstance(parsed, list):
            return coerce_target_codes(parsed)
    return [part.strip() for part in text.split(",") if part.strip()]


def _one_target_name_clause(column, name: str):
    literal = _like_literal(name)
    clauses = [column == name]
    for sep in ("&", "＆", ",", "，"):
        clauses.append(column.like(f"{literal}{sep}%", escape="\\"))
        clauses.append(column.like(f"%{sep}{literal}", escape="\\"))
        clauses.append(column.like(f"%{sep}{literal}{sep}%", escape="\\"))
    return or_(*clauses)


def target_name_clause(column, selected: Any):
    clauses = [_one_target_name_clause(column, name) for name in filter_terms(selected)]
    if not clauses:
        return None
    if len(clauses) == 1:
        return clauses[0]
    return or_(*clauses)


def codes_for_names(pairs, selected: Any) -> set[str]:
    """只取和所选名称对齐的那一个编号，避免把同一行上的其他靶点也扩进去。"""
    names = set(filter_terms(selected))
    found: set[str] = set()
    for raw_name, raw_codes in pairs:
        tokens = split_target_names(raw_name)
        codes = coerce_target_codes(raw_codes)
        if len(tokens) == len(codes):
            found.update(code for token, code in zip(tokens, codes) if token in names)
        elif len(tokens) == 1 and tokens[0] in names:
            found.update(codes)
    return found


def json_codes_clause(column, codes):
    clauses = []
    for code in codes:
        if not code:
            continue
        literal = _like_literal(code)
        clauses.append(cast(column, String).like(f'%"{literal}"%', escape="\\"))
    if not clauses:
        return None
    if len(clauses) == 1:
        return clauses[0]
    return or_(*clauses)


def recorded_target_clause(db, name_column, codes_column, selected, pair_stmt):
    """按记录上的靶点名称筛选。名称相同、或编号相同的另一种写法，一起命中。"""
    name_clause = target_name_clause(name_column, selected)
    if name_clause is None or db is None:
        return name_clause
    pairs = db.execute(pair_stmt.where(name_clause)).all()
    code_clause = json_codes_clause(codes_column, codes_for_names(pairs, selected))
    if code_clause is None:
        return name_clause
    return or_(name_clause, code_clause)


def catalog_names_for_pairs(db, pairs) -> dict[str, str]:
    """记录上的靶点编号对应靶点库正式名称。库里没有的编号不出现。"""
    from models.target import Target

    codes: set[str] = set()
    for _name, raw_codes in pairs:
        codes.update(coerce_target_codes(raw_codes))
    if not codes or db is None:
        return {}
    rows = db.scalars(select(Target).where(Target.snum.in_(tuple(codes)))).all()
    return {
        str(row.snum): name
        for row in rows
        if row.snum and (name := str(row.name or "").strip())
    }


def _catalog_label(codes: set[str], official_by_code: dict[str, str]) -> str:
    names = sorted({
        official_by_code[code]
        for code in codes
        if official_by_code.get(code)
    })
    if len(names) == 1:
        return names[0]
    return ""


def _target_option(value: str, label: str, aliases: list[str], codes: set[str]) -> dict[str, Any]:
    shown = label or value
    return {
        "value": value,
        "label": shown,
        "aliases": sorted({name for name in aliases if name and name != shown}),
        "codes": sorted(code for code in codes if code),
    }


def target_select_options(pairs, official_by_code: dict[str, str] | None = None) -> list[dict[str, Any]]:
    """下拉默认用靶点库正式名。记录里的其他写法和编号留在选项上，供输入时再露出来。"""
    official_by_code = official_by_code or {}
    full_names: list[str] = []
    seen: set[str] = set()
    single_codes: dict[str, set[str]] = {}
    combo_codes: dict[str, set[str]] = {}
    combo_code_lists: dict[str, list[str]] = {}
    for raw_name, raw_codes in pairs:
        text = str(raw_name or "").strip()
        if not text:
            continue
        ordered = [code for code in coerce_target_codes(raw_codes) if code]
        if text not in seen:
            seen.add(text)
            full_names.append(text)
        if len(split_target_names(text)) == 1:
            single_codes.setdefault(text, set()).update(ordered)
        else:
            combo_codes.setdefault(text, set()).update(ordered)
            combo_code_lists.setdefault(text, ordered)

    parent = {name: name for name in single_codes}

    def find(name: str) -> str:
        while parent[name] != name:
            parent[name] = parent[parent[name]]
            name = parent[name]
        return name

    by_code: dict[str, list[str]] = {}
    for name, codes in single_codes.items():
        for code in codes:
            if code:
                by_code.setdefault(code, []).append(name)
    for names in by_code.values():
        head = find(names[0])
        for other in names[1:]:
            parent[find(other)] = head

    groups: dict[str, list[str]] = {}
    for name in single_codes:
        groups.setdefault(find(name), []).append(name)

    emitted: set[str] = set()
    options: list[dict[str, Any]] = []
    for name in full_names:
        if name not in single_codes:
            codes = combo_codes.get(name, set())
            ordered = combo_code_lists.get(name, [])
            tokens = split_target_names(name)
            if len(tokens) == len(ordered) and ordered:
                shown = [official_by_code.get(code) or token for token, code in zip(tokens, ordered)]
                label = "&".join(shown)
            else:
                label = _catalog_label(codes, official_by_code) or name
            options.append(_target_option(name, label, [name], codes))
            continue
        root = find(name)
        if root in emitted:
            continue
        emitted.add(root)
        members = sorted(groups[root])
        codes: set[str] = set()
        for member in members:
            codes.update(single_codes.get(member, set()))
        label = _catalog_label(codes, official_by_code) or members[0]
        value = label if label in members else members[0]
        options.append(_target_option(value, label, members, codes))
    options.sort(key=lambda item: item["label"])
    return options
