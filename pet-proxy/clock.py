"""Dates as the users see them (the lab is in UTC+8, whatever the server clock's zone)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

TZ = timezone(timedelta(hours=8))
_WEEKDAYS = "一二三四五六日"


def weekday(d: datetime) -> str:
    return "周" + _WEEKDAYS[d.weekday()]


def today() -> tuple[str, str]:
    now = datetime.now(TZ)
    return now.strftime("%Y-%m-%d"), weekday(now)
