from collections.abc import Generator
from typing import Any

from fastapi import Request
from sqlalchemy import create_engine, event, inspect
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from core.config import get_settings
from utils.filter_values import clean_field_text


class Base(DeclarativeBase):
    pass


class AuditedSession(Session):
    """Primary-database session; audit listeners are scoped to this subclass."""


_SKIP_SANITIZE_TABLES = frozenset({
    "sys_operation_log",
    "sys_operation_log_item",
    "sys_job_run_log",
})
_SKIP_SANITIZE_COLUMNS = frozenset({"password_hash"})


@event.listens_for(Session, "before_flush", insert=True)
def _sanitize_orm_strings(session: Session, _flush_context: Any, _instances: Any) -> None:
    """ORM 写入兜底：自动清除任何模型字符串字段中的制表符、回车、零宽/控制字符及首尾空白。"""
    for obj in (*session.new, *session.dirty):
        state = inspect(obj)
        if state.mapper.local_table.name in _SKIP_SANITIZE_TABLES:
            continue
        is_new = obj in session.new
        for prop in state.mapper.column_attrs:
            key = prop.key
            if key in _SKIP_SANITIZE_COLUMNS or key not in state.dict:
                continue
            value = state.dict[key]
            if not isinstance(value, str):
                continue
            if not is_new and not state.attrs[key].history.has_changes():
                continue
            cleaned = clean_field_text(value, keep_breaks=True)
            if cleaned != value:
                setattr(obj, key, cleaned)


settings = get_settings()
if settings.database_url.startswith("mysql"):
    engine = create_engine(
        settings.database_url,
        pool_pre_ping=True,
        pool_recycle=1800,
        connect_args={"init_command": "SET time_zone = '+08:00'"},
    )
else:
    engine = create_engine(settings.database_url, pool_pre_ping=True, pool_recycle=1800)
SessionLocal = sessionmaker(
    bind=engine,
    class_=AuditedSession,
    autoflush=False,
    autocommit=False,
)


def get_db(request: Request) -> Generator[Session, None, None]:
    db = SessionLocal()
    db.info["audit_read_only"] = request.method in {"GET", "HEAD", "OPTIONS"}
    try:
        yield db
    finally:
        db.close()
