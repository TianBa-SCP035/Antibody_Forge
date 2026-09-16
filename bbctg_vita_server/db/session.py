from collections.abc import Generator

from fastapi import Request
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from core.config import get_settings


class Base(DeclarativeBase):
    pass


class AuditedSession(Session):
    """Primary-database session; audit listeners are scoped to this subclass."""


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
