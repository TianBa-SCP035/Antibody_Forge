from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, Boolean, DateTime, Index, Numeric, String, UniqueConstraint, func, text
from sqlalchemy.orm import Mapped, mapped_column

from db.session import Base


class SynthesisSupernatantWell(Base):
    __tablename__ = "synthesis_supernatant_well"
    __log_label__ = "上清板布局"
    __audit_label__ = ("sample_name", "plate_no")
    __table_args__ = (
        UniqueConstraint("order_no", "plate_no", "well_no", name="uk_synthesis_supernatant_well_order_plate_well"),
        Index("idx_synthesis_supernatant_well_sample_name", "sample_name"),
        {"comment": "合成公司推送的上清板布局，一孔一行；未合成的样品一样品一行，不占孔位"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, comment="主键ID")
    order_no: Mapped[str] = mapped_column(String(64), nullable=False, comment="合成订单号")
    corp_name: Mapped[str] = mapped_column(String(64), nullable=False, comment="合成公司")
    plate_no: Mapped[str | None] = mapped_column(String(128), nullable=True, comment="板号，未合成时为空")
    well_no: Mapped[str | None] = mapped_column(String(8), nullable=True, comment="孔号，未合成时为空")
    sample_name: Mapped[str] = mapped_column(String(128), nullable=False, comment="蛋白名称")
    not_synthesized: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("0"), comment="未合成"
    )
    potency: Mapped[Decimal | None] = mapped_column(Numeric(16, 4), nullable=True, comment="浓度(ug/mL)，空表示不适用")
    specs: Mapped[Decimal | None] = mapped_column(Numeric(16, 4), nullable=True, comment="规格(mL/支)，空表示不适用")
    volume: Mapped[Decimal | None] = mapped_column(Numeric(16, 4), nullable=True, comment="体积(mL)，未合成时为空")
    sample_enter_vol: Mapped[Decimal | None] = mapped_column(
        Numeric(16, 4), nullable=True, comment="质粒量(ug)，未合成时为空"
    )
    received_at: Mapped[datetime | None] = mapped_column(
        DateTime, server_default=func.current_timestamp(), comment="接收时间"
    )
