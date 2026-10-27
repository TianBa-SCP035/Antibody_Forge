from collections.abc import Generator
from contextlib import contextmanager
from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from core.config import get_settings


def _create_optional_session_factory(
    database_url: str | None,
    *,
    connect_timeout: int | None = None,
    read_timeout: int | None = None,
) -> sessionmaker[Session] | None:
    if not database_url:
        return None
    connect_args: dict = {}
    if database_url.startswith("mysql"):
        if connect_timeout is not None:
            connect_args["connect_timeout"] = connect_timeout
        if read_timeout is not None:
            connect_args["read_timeout"] = read_timeout
    engine = create_engine(
        database_url,
        pool_pre_ping=True,
        pool_recycle=3600,
        connect_args=connect_args,
    )
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)


@lru_cache(maxsize=8)
def _cached_one_session_factory(database_url: str, connect_timeout: int, read_timeout: int) -> sessionmaker[Session]:
    factory = _create_optional_session_factory(
        database_url,
        connect_timeout=connect_timeout,
        read_timeout=read_timeout,
    )
    assert factory is not None
    return factory


def get_cell_db() -> Generator[Session, None, None]:
    settings = get_settings()
    factory = _create_optional_session_factory(settings.cell_db_url)
    if factory is None:
        raise RuntimeError("CELL_DB_URL 未配置")

    db = factory()
    try:
        yield db
    finally:
        db.close()


def get_employee_db() -> Generator[Session, None, None]:
    settings = get_settings()
    factory = _create_optional_session_factory(settings.employee_db_url)
    if factory is None:
        raise RuntimeError("EMPLOYEE_DB_URL 未配置")

    db = factory()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def open_one_db(
    *,
    connect_timeout: int = 1,
    read_timeout: int = 1,
) -> Generator[Session | None, None, None]:
    settings = get_settings()
    url = (settings.one_db_url or "").strip()
    if not url:
        yield None
        return
    factory = _cached_one_session_factory(url, connect_timeout, read_timeout)
    db = factory()
    try:
        yield db
    finally:
        db.close()

