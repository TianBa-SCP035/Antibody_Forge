from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Index, Integer, JSON, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from db.session import Base


def _format_time(value: datetime | None) -> str | None:
    return value.strftime("%Y-%m-%d %H:%M:%S") if value else None


class OrderSync(Base):
    __tablename__ = "order_sync"
    __log_label__ = "工单回传"
    __audit_label__ = ("trace_id",)
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
    http_status: Mapped[int | None] = mapped_column(Integer)
    response_body: Mapped[object | None] = mapped_column(JSON)
    import_status: Mapped[str | None] = mapped_column(String(32))
    processed_at: Mapped[datetime | None] = mapped_column(DateTime)
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
            "http_status": self.http_status,
            "import_status": self.import_status,
            "processed_at": _format_time(self.processed_at),
            "received_at": _format_time(self.received_at),
        }


class OrderSyncBoard(Base):
    __tablename__ = "order_sync_board"
    __log_label__ = "工单回传检测板"
    __audit_label__ = ("order_no", "sample_barcode")
    __table_args__ = (
        Index("idx_order_sync_board_sync", "sync_id"),
        Index("idx_order_sync_board_work_order", "work_order_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    sync_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    seq: Mapped[int] = mapped_column(Integer, nullable=False)
    order_no: Mapped[str] = mapped_column(String(255), nullable=False)
    data_type: Mapped[str | None] = mapped_column(String(32))
    work_order_id: Mapped[int | None] = mapped_column(BigInteger)
    dispatch_id: Mapped[str | None] = mapped_column(String(64))
    detect_barcode: Mapped[str | None] = mapped_column(String(128))
    sample_barcode: Mapped[str | None] = mapped_column(String(128))
    cell_name: Mapped[str | None] = mapped_column(String(255))
    experiment_date: Mapped[str | None] = mapped_column(String(32))
    image_path: Mapped[str | None] = mapped_column(String(1024))
    csv_path: Mapped[str | None] = mapped_column(String(1024))
    verify_status: Mapped[str] = mapped_column(String(32), nullable=False)
    verify_message: Mapped[str | None] = mapped_column(Text)
    import_status: Mapped[str] = mapped_column(String(32), nullable=False)
    import_message: Mapped[str | None] = mapped_column(Text)
    experiment_id: Mapped[str | None] = mapped_column(String(64))
    facs_plate_id: Mapped[int | None] = mapped_column(BigInteger)
    image_file_id: Mapped[int | None] = mapped_column(BigInteger)
    excel_file_id: Mapped[int | None] = mapped_column(BigInteger)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, server_default=func.current_timestamp())
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "sync_id": self.sync_id,
            "seq": self.seq,
            "order_no": self.order_no,
            "data_type": self.data_type,
            "work_order_id": self.work_order_id,
            "dispatch_id": self.dispatch_id,
            "detect_barcode": self.detect_barcode,
            "sample_barcode": self.sample_barcode,
            "cell_name": self.cell_name,
            "experiment_date": self.experiment_date,
            "image_path": self.image_path,
            "csv_path": self.csv_path,
            "verify_status": self.verify_status,
            "verify_message": self.verify_message,
            "import_status": self.import_status,
            "import_message": self.import_message,
            "experiment_id": self.experiment_id,
            "facs_plate_id": self.facs_plate_id,
            "image_file_id": self.image_file_id,
            "excel_file_id": self.excel_file_id,
            "updated_at": _format_time(self.updated_at),
        }
