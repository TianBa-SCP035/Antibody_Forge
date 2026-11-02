"""按规则分配的业务编号（如实验号 = 项目编号 + 两位序号）在并发新建时可能撞号。

数据库唯一键兜底：在保存点里插入，撞号就回滚保存点、重新分配，不影响同一事务里的其他改动。
"""

import logging
from collections.abc import Callable
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)
DEFAULT_ATTEMPTS = 8
_MYSQL_DUPLICATE_KEY = 1062


def _is_duplicate_key(error: IntegrityError) -> bool:
    args = getattr(error.orig, "args", ())
    if args and args[0] == _MYSQL_DUPLICATE_KEY:
        return True
    return "UNIQUE constraint failed" in str(error.orig)


def insert_with_retry(
    db: Session,
    obj: Any,
    assign_code: Callable[[int], None],
    *,
    attempts: int = DEFAULT_ATTEMPTS,
    conflict_message: str = "编号分配冲突，请重试",
) -> Any:
    """assign_code(attempt) 给 obj 写入候选编号；插入撞唯一键时重新分配，最多 attempts 次。

    非空、外键等其他约束失败与编号无关，直接抛出。
    """
    for attempt in range(attempts):
        assign_code(attempt)
        try:
            with db.begin_nested():
                db.add(obj)
                db.flush()
            return obj
        except IntegrityError as error:
            if not _is_duplicate_key(error):
                raise
            logger.info("code conflict on %s, attempt %s: %s", type(obj).__name__, attempt + 1, error.orig)
    raise ValueError(conflict_message)
