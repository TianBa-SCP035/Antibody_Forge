from typing import Any

from sqlalchemy import Date, String, and_, cast, event, or_
from sqlalchemy.orm import Mapper
from sqlalchemy.types import TypeDecorator

from utils.normalize import normalize_date, parse_date


class DateString(TypeDecorator):
    """数据库按日期存，Python 侧读写都是 "YYYY-MM-DD" 字符串。

    赋值时就统一格式、拒绝非法日期，内存里的对象和库里一致；表还是 VARCHAR 时读出的历史值原样返回。
    和字符串比较（>=、LIKE、== ""）时按字符串绑定参数，VARCHAR 和 DATE 列都能用。
    """

    impl = Date
    cache_ok = True

    def process_bind_param(self, value: Any, dialect: Any):
        return parse_date(value)

    def process_result_value(self, value: Any, dialect: Any):
        if value is None:
            return None
        if hasattr(value, "isoformat"):
            return value.isoformat()[:10]
        return str(value).strip() or None

    def coerce_compared_value(self, op: Any, value: Any):
        return String()


def _normalize_on_set(target: Any, value: Any, oldvalue: Any, initiator: Any) -> str | None:
    return normalize_date(value)


@event.listens_for(Mapper, "mapper_configured")
def _attach_date_normalizers(mapper: Mapper, class_: type) -> None:
    for prop in mapper.column_attrs:
        if any(isinstance(column.type, DateString) for column in prop.columns):
            event.listen(getattr(class_, prop.key), "set", _normalize_on_set, retval=True)


def date_blank(column):
    return or_(column.is_(None), cast(column, String) == "")


def date_present(column):
    return and_(column.is_not(None), cast(column, String) != "")
