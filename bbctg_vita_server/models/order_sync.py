from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Integer, JSON, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from db.session import Base


class OrderSync(Base):
    __tablename__ = "order_sync"
    __table_args__ = (UniqueConstraint("trace_id", name="uk_order_sync_trace_id"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    trace_id: Mapped[str] = mapped_column(String(128), nullable=False)
    file_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    order_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    order_nos: Mapped[object | None] = mapped_column(JSON)
    project_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    project_infos: Mapped[object | None] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(64), nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text)
    received_at: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.current_timestamp())

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "trace_id": self.trace_id,
            "file_path": self.file_path,
            "order_count": self.order_count,
            "order_nos": self.order_nos,
            "project_count": self.project_count,
            "project_infos": self.project_infos,
            "status": self.status,
            "error_message": self.error_message,
            "received_at": self.received_at.isoformat() if self.received_at else None,
        }
