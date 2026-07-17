from datetime import datetime

from sqlalchemy import BigInteger, CHAR, DateTime, Index, JSON, String, Text, UniqueConstraint, func, text
from sqlalchemy.orm import Mapped, mapped_column

from db.session import Base


class MegaFlowWorkOrder(Base):
    __tablename__ = "mega_flow_work_order"
    __table_args__ = (
        Index("idx_mega_flow_work_order_status", "status"),
        Index("idx_mega_flow_work_order_project_nos", text("(CAST(project_nos AS CHAR(128) ARRAY))")),
        Index("idx_mega_flow_work_order_targets", text("(CAST(targets AS CHAR(128) ARRAY))")),
        Index(
            "idx_mega_flow_work_order_sample_plate_barcodes",
            text("(CAST(sample_plate_barcodes AS CHAR(128) ARRAY))"),
        ),
        Index(
            "idx_mega_flow_work_order_cell_plate_barcodes",
            text("(CAST(cell_plate_barcodes AS CHAR(128) ARRAY))"),
        ),
        Index("idx_mega_flow_work_order_source", "data_type", "source_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    order_name: Mapped[str | None] = mapped_column(String(255))
    order_no: Mapped[str] = mapped_column(String(255), nullable=False)
    data_type: Mapped[str] = mapped_column(String(32), nullable=False, server_default="TITER")
    source_id: Mapped[str | None] = mapped_column(String(128))
    priority: Mapped[str] = mapped_column(String(32), nullable=False, server_default="normal")
    remark: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(64), nullable=False, server_default="draft")
    created_by: Mapped[str | None] = mapped_column(String(128))
    sent_at: Mapped[datetime | None] = mapped_column(DateTime)
    project_nos: Mapped[object | None] = mapped_column(JSON)
    targets: Mapped[object | None] = mapped_column(JSON)
    sample_plate_barcodes: Mapped[object | None] = mapped_column(JSON)
    cell_plate_barcodes: Mapped[object | None] = mapped_column(JSON)
    content: Mapped[object | None] = mapped_column(JSON)
    content_hash: Mapped[str | None] = mapped_column(CHAR(64))
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.current_timestamp())
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
    )

    def to_dict(self, *, include_detail: bool = False) -> dict:
        data = {
            "id": self.id,
            "order_name": self.order_name or "",
            "order_no": self.order_no or "",
            "data_type": self.data_type,
            "source_id": self.source_id or "",
            "priority": self.priority or "normal",
            "remark": self.remark or "",
            "status": self.status,
            "created_by": self.created_by or "",
            "sent_at": self.sent_at.strftime("%Y-%m-%d %H:%M:%S") if self.sent_at else None,
            "project_nos": self.project_nos if isinstance(self.project_nos, list) else [],
            "targets": self.targets if isinstance(self.targets, list) else [],
            "sample_plate_barcodes": self.sample_plate_barcodes if isinstance(self.sample_plate_barcodes, list) else [],
            "cell_plate_barcodes": self.cell_plate_barcodes if isinstance(self.cell_plate_barcodes, list) else [],
            "content_hash": self.content_hash,
            "error_message": self.error_message,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else None,
            "updated_at": self.updated_at.strftime("%Y-%m-%d %H:%M:%S") if self.updated_at else None,
        }
        if include_detail:
            content = self.content if isinstance(self.content, dict) else {}
            data.update(
                {
                    "sample_plates": content.get("sample_plates") or [],
                    "cell_plates": content.get("cell_plates") or [],
                    "base_info": {
                        "order_name": self.order_name or "",
                        "remark": self.remark or "",
                        "pc_infos": content.get("pc_infos") or [],
                    },
                }
            )
        return data


class MegaFlowWorkOrderDispatch(Base):
    __tablename__ = "mega_flow_work_order_dispatch"
    __table_args__ = (
        UniqueConstraint("dispatch_id", name="uk_mega_flow_work_order_dispatch_id"),
        Index("idx_mega_flow_work_order_dispatch_order", "work_order_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    dispatch_id: Mapped[str] = mapped_column(String(64), nullable=False)
    work_order_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    payload: Mapped[object] = mapped_column(JSON, nullable=False)
    payload_hash: Mapped[str] = mapped_column(CHAR(64), nullable=False)
    content_hash_at_send: Mapped[str] = mapped_column(CHAR(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, server_default="pending")
    pause_state: Mapped[str | None] = mapped_column(String(32))
    sent_at: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.current_timestamp())
    created_by: Mapped[str | None] = mapped_column(String(128))
    created_at: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.current_timestamp())

    def to_dict(self, *, include_payload: bool = False) -> dict:
        data = {
            "id": self.id,
            "dispatch_id": self.dispatch_id,
            "status": self.status,
            "pause_state": self.pause_state or "",
            "sent_at": self.sent_at.strftime("%Y-%m-%d %H:%M:%S") if self.sent_at else None,
            "created_by": self.created_by or "",
        }
        if include_payload:
            data["payload"] = self.payload
        return data
