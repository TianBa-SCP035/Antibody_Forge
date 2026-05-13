from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from core.config import get_settings


def _create_optional_session_factory(database_url: str | None) -> sessionmaker[Session] | None:
    if not database_url:
        return None
    engine = create_engine(database_url, pool_pre_ping=True, pool_recycle=3600)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)


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
