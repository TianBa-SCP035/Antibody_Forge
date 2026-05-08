from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from db.session import Base


class BbctgUser(Base):
    __tablename__ = "bbctg_user"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, unique=True)
    username: Mapped[str | None] = mapped_column(String(50))
    jobNo: Mapped[str | None] = mapped_column(String(20))
    openid: Mapped[str | None] = mapped_column(String(100))
    appid: Mapped[str | None] = mapped_column(String(20))
    eid: Mapped[str | None] = mapped_column(String(20))
    role: Mapped[str | None] = mapped_column(String(100))
    role_menu: Mapped[str | None] = mapped_column(String(50))
    create_date: Mapped[datetime | None] = mapped_column(DateTime)
    pro_locked: Mapped[int | None] = mapped_column(Integer)
    pro_open: Mapped[int | None] = mapped_column(Integer)

    def to_dict(self) -> dict:
        roles = self.role.split(",") if self.role else []
        menus = self.role_menu.split(",") if self.role_menu else []
        return {
            "id": self.id,
            "username": self.username,
            "jobNo": self.jobNo,
            "openid": self.openid,
            "appid": self.appid,
            "eid": self.eid,
            "role": roles,
            "role_menu": menus,
            "create_date": self.create_date,
        }
