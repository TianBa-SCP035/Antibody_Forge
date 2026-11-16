"""从 ORM 模型推出可写字段和基础校验，模块里不再手写字段清单、长度和日期列。

可写字段 = 模型的列 − 主键和创建/更新记录列 − 模块声明的只读列（系统生成的单号、同步来源等）。
中文名取列注释；文本按 String(n) 限长，日期、整数按列类型校验，报错文案各模块一致。
选项、多值、联动等业务规则仍在模块里先处理，只有普通列交给 clean_field。
"""

from dataclasses import dataclass
from datetime import date
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, create_model
from sqlalchemy import JSON, Date, DateTime, Integer, String, inspect

from models.types import DateString
from utils.filter_values import clean_field_text
from utils.normalize import parse_date

SYSTEM_FIELDS = frozenset({"created_by", "created_at", "updated_by", "updated_at"})
# 队列顺序由排序模块维护：可写，但不进表头筛选，也不参与保存冲突比较
SORT_FIELD = "sort_order"


@dataclass(frozen=True)
class ModelField:
    """kind: text | date | int | json | other；column 是模型类属性，供表头筛选等拼 SQL。"""

    key: str
    label: str
    kind: str
    column: Any
    max_length: int | None = None


def _kind(column_type: Any) -> str:
    if isinstance(column_type, (DateString, Date)) and not isinstance(column_type, DateTime):
        return "date"
    if isinstance(column_type, Integer):
        return "int"
    if isinstance(column_type, String):
        return "text"
    if isinstance(column_type, JSON):
        return "json"
    return "other"


def model_fields(model: type, *, readonly: tuple[str, ...] = ()) -> dict[str, ModelField]:
    props = inspect(model).column_attrs
    unknown = set(readonly) - {prop.key for prop in props}
    if unknown:
        raise ValueError(f"{model.__name__} 没有这些列：{', '.join(sorted(unknown))}")
    skipped = SYSTEM_FIELDS | set(readonly)
    fields: dict[str, ModelField] = {}
    for prop in props:
        column = prop.columns[0]
        if column.primary_key or prop.key in skipped:
            continue
        fields[prop.key] = ModelField(
            key=prop.key,
            label=column.comment or prop.key,
            kind=_kind(column.type),
            column=getattr(model, prop.key),
            max_length=getattr(column.type, "length", None),
        )
    return fields


def _field_description(field: ModelField) -> str:
    if field.kind == "text" and field.max_length:
        return f"{field.label}（最长 {field.max_length} 字）"
    if field.kind == "date":
        return f"{field.label}（YYYY-MM-DD）"
    return field.label


def fields_request_model(name: str, fields: dict[str, ModelField]) -> type[BaseModel]:
    """保存接口的请求模型：列出全部可写字段，说明取列注释，接口文档里就能看到入参。

    值不做类型转换、原样交给模块整理和报错；未登记的键（_expected、联动字段）照常保留。
    取值必须用 model_dump(exclude_unset=True)，否则没传的字段会变成 None 被写入。
    """
    return create_model(
        name,
        __config__=ConfigDict(extra="allow"),
        **{key: (Any, Field(default=None, description=_field_description(field))) for key, field in fields.items()},
    )


def clean_text(field: ModelField, value: Any, *, keep_breaks: bool = False) -> str | None:
    text = clean_field_text(value, keep_breaks=keep_breaks)
    if not text:
        return None
    if field.max_length and len(text) > field.max_length:
        raise ValueError(f"{field.label}不能超过 {field.max_length} 个字符")
    return text


def clean_date(field: ModelField, value: Any) -> date | None:
    try:
        return parse_date(value)
    except ValueError as exc:
        raise ValueError(f"{field.label}格式不正确，应为 YYYY-MM-DD：{str(value).strip()}") from exc


def clean_int(field: ModelField, value: Any) -> int | None:
    if value is None or str(value).strip() == "":
        return None
    message = f"{field.label}必须是非负整数"
    if isinstance(value, bool) or (isinstance(value, float) and not value.is_integer()):
        raise ValueError(message)
    try:
        number = int(value.strip() if isinstance(value, str) else value)
    except (TypeError, ValueError) as exc:
        raise ValueError(message) from exc
    if number < 0:
        raise ValueError(message)
    return number


def clean_field(field: ModelField, value: Any, *, keep_breaks: bool = False) -> Any:
    """普通列的写入值：文本去空白并限长，日期统一格式，整数非负；空值存 NULL。"""
    if field.kind == "text":
        return clean_text(field, value, keep_breaks=keep_breaks)
    if field.kind == "date":
        return clean_date(field, value)
    if field.kind == "int":
        return clean_int(field, value)
    raise TypeError(f"{field.key} 是 {field.kind} 列，要在模块里单独处理")
