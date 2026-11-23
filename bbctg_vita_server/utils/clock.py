"""业务时间统一按北京时间，与数据库会话时区（+08:00）和调度器一致，不受服务器系统时区影响。"""

from datetime import date, datetime, timedelta, timezone

BUSINESS_TZ = timezone(timedelta(hours=8), "Asia/Shanghai")


def now_local() -> datetime:
    """北京时间的不带时区 datetime，可直接写入 DATETIME 列。"""
    return datetime.now(BUSINESS_TZ).replace(tzinfo=None)


def today_local() -> date:
    return now_local().date()
