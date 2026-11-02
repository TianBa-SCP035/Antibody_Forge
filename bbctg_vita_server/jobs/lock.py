"""定时任务的跨进程互斥：MySQL 命名锁，同一任务同一时刻只在一个进程里跑。

锁挂在单独的连接上，任务结束（或进程退出、连接断开）即释放。非 MySQL（测试用 SQLite）不加锁。
连接用 AUTOCOMMIT：任务可能跑很久，不能让这条连接一直挂着一个打开的事务。
"""

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import text

from db.session import engine

_PREFIX = "vita_job:"


def _lock_name(job_id: str) -> str:
    return f"{_PREFIX}{job_id}"[:64]


@contextmanager
def job_lock(job_id: str) -> Iterator[bool]:
    if engine.dialect.name != "mysql":
        yield True
        return
    name = _lock_name(job_id)
    with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
        acquired = bool(conn.execute(text("SELECT GET_LOCK(:name, 0)"), {"name": name}).scalar())
        try:
            yield acquired
        finally:
            if acquired:
                conn.execute(text("SELECT RELEASE_LOCK(:name)"), {"name": name})
