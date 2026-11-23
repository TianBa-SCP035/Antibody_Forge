from decimal import Decimal

from sqlalchemy import BigInteger, Numeric, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class ExternalBase(DeclarativeBase):
    pass


class SamSample(ExternalBase):
    __tablename__ = "sam_sample"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    sample_no: Mapped[str | None] = mapped_column(String(20))
    samplename: Mapped[str | None] = mapped_column(String(500))
    sample_type: Mapped[str | None] = mapped_column(String(50))
    sample_storage_vol: Mapped[Decimal | None] = mapped_column(Numeric(20, 5))
    organId: Mapped[str | None] = mapped_column(String(20))
    genus: Mapped[str | None] = mapped_column(String(20))
    target: Mapped[str | None] = mapped_column(String(50))
    generations: Mapped[str | None] = mapped_column(String(20))
    batch_no: Mapped[str | None] = mapped_column(String(50))

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "sample_no": self.sample_no,
            "samplename": self.samplename,
            "sample_storage_vol": float(self.sample_storage_vol) if self.sample_storage_vol else None,
            "genus": self.genus,
            "target": self.target,
            "generations": self.generations,
            "batch_no": self.batch_no,
        }
