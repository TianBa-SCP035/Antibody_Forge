"""写入前的字段清洗，各业务模块共用，报错文案一致。"""

import re
from collections.abc import Iterable
from datetime import date, datetime
from typing import Any

from utils.workbench_queue import PRIORITY_ORDER, canonicalize_priority

DATE_FORMAT_MESSAGE = "日期必须是 YYYY-MM-DD"
# 接受 2026/1/5、2026.1.5 和带时间的写法，统一存成 YYYY-MM-DD。
_DATE_PATTERN = re.compile(
    r"(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})(?:[ T]\d{1,2}:\d{2}(?::\d{2}(?:\.\d+)?)?)?"
)
_TOKEN_SPLIT = re.compile(r"[,，、+\r\n\t]")
_OPTION_SPLIT = re.compile(r"[,，]")


def parse_date(value: Any) -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    if not text:
        return None
    matched = _DATE_PATTERN.fullmatch(text)
    if not matched:
        raise ValueError(f"{DATE_FORMAT_MESSAGE}：{text}")
    try:
        return date(*(int(part) for part in matched.groups()))
    except ValueError as exc:
        raise ValueError(f"{DATE_FORMAT_MESSAGE}：{text}") from exc


def normalize_date(value: Any) -> str | None:
    parsed = parse_date(value)
    return parsed.isoformat() if parsed else None


def optional_int(value: Any) -> int | None:
    """宽松取整：空值或不是整数都当作没填。"""
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def parse_row_id(value: Any) -> int | None:
    """解析正整数记录 ID，空值或非正整数返回 None。"""
    number = optional_int(value)
    return number if number is not None and number > 0 else None


def normalize_positive_int(value: Any, message: str) -> int:
    number = optional_int(value)
    if number is None or number <= 0:
        raise ValueError(message)
    return number


def normalize_target_codes(value: Any, *, upper: bool = False) -> list[str]:
    if value is None or value == "":
        return []
    if isinstance(value, str):
        items = value.replace("，", ",").replace("、", ",").split(",")
    elif isinstance(value, list):
        items = value
    else:
        raise ValueError("靶点编号必须是数组")
    codes = [str(item).strip() for item in items if str(item).strip()]
    return [code.upper() for code in codes] if upper else codes


def normalize_choice(
    value: Any,
    options: Iterable[str],
    label: str,
    *,
    default: str | None = None,
    nullable: bool = False,
) -> str | None:
    text = str(value or "").strip() or (default or "")
    if not text and nullable:
        return None
    if text not in options:
        raise ValueError(f"{label}不在允许的选项中")
    return text


def normalize_priority(value: Any) -> str:
    text = canonicalize_priority(value)
    if text not in PRIORITY_ORDER:
        raise ValueError("优先级不在允许的选项中")
    return text


def split_tokens(value: Any) -> list[str]:
    """一格多值（逗号、顿号、加号、换行、制表符分隔）拆成去重后的列表，保留原顺序。"""
    if value is None:
        return []
    raw = value if isinstance(value, (list, tuple)) else _TOKEN_SPLIT.split(str(value))
    tokens: list[str] = []
    for item in raw:
        token = str(item or "").strip()
        if token and token not in tokens:
            tokens.append(token)
    return tokens


def order_tokens(tokens: list[str], options: tuple[str, ...]) -> list[str]:
    """预设选项按预设顺序在前，自填的值按填写顺序在后。"""
    known = set(options)
    return [option for option in options if option in tokens] + [t for t in tokens if t not in known]


def join_tokens(value: Any, options: tuple[str, ...] = ()) -> str | None:
    return "、".join(order_tokens(split_tokens(value), options)) or None


def join_known_options(value: Any, options: tuple[str, ...], error: str, separator: str = ",") -> str | None:
    """只允许预设选项的多选，按预设顺序拼接。"""
    if value is None:
        return None
    if isinstance(value, (list, tuple)):
        tokens = [str(item).strip() for item in value if str(item).strip()]
    else:
        tokens = [part.strip() for part in _OPTION_SPLIT.split(str(value)) if part.strip()]
    allowed = set(options)
    if any(token not in allowed for token in tokens):
        raise ValueError(error)
    return separator.join(option for option in options if option in tokens) or None
