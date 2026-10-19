"""列表筛选值。单个值保持原样，多个值按「满足任一」合并。"""

from typing import Any, Callable

from sqlalchemy import or_


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
