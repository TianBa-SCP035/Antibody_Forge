from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Callable
from zoneinfo import ZoneInfo

from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from db.session import SessionLocal
from models.system import SysFeatureFlag, SysJobRunLog
from modules.registry import FEATURE_INDEX
from utils.clock import now_local


JOB_SCHEDULES = ("daily", "weekly", "monthly", "interval")
JOB_INTERVALS = (
    (1, "hour"),
    (2, "hour"),
    (3, "hour"),
    (4, "hour"),
    (6, "hour"),
    (8, "hour"),
    (12, "hour"),
    (2, "day"),
    (3, "day"),
    (7, "day"),
    (14, "day"),
)
_JOB_TIMEZONE = ZoneInfo("Asia/Shanghai")


def list_feature_flags(db: Session) -> list[dict[str, Any]]:
    try:
        persisted = {flag.code: flag for flag in db.scalars(select(SysFeatureFlag)).all()}
    except SQLAlchemyError:
        logging.warning("feature flag list failed, using defaults")
        db.rollback()
        persisted = {}
    items = [_with_overrides(default, persisted.get(code)) for code, default in FEATURE_INDEX.items()]
    return sorted(items, key=lambda item: (item["category"], item["sort_order"]))


def save_feature_flag(db: Session, data: dict[str, Any]) -> dict[str, Any]:
    """只保存管理员能改的启用、显示、排序和配置；名称、分类等取模块登记。"""
    code = str(data.get("code") or "").strip()
    default = FEATURE_INDEX.get(code)
    if default is None:
        raise ValueError("未知功能编码")
    flag = db.scalar(select(SysFeatureFlag).where(SysFeatureFlag.code == code))
    if flag is None:
        flag = SysFeatureFlag(code=code, config={})
        db.add(flag)
    flag.enabled = bool(data.get("enabled"))
    flag.visible = bool(data.get("visible"))
    if "sort_order" in data:
        sort_order = int(data.get("sort_order") or 0)
        flag.sort_order = None if sort_order == default["sort_order"] else sort_order
    if "config" in data:
        flag.config = _normalize_config(default["category"], data.get("config") or {})
    db.commit()
    db.refresh(flag)
    return _with_overrides(default, flag)


def is_feature_enabled(db: Session, code: str) -> bool:
    return bool(get_feature_flag(db, code)["enabled"])


def get_feature_flag(db: Session, code: str) -> dict[str, Any]:
    """库里没有这条开关时用模块登记的默认值。"""
    default = FEATURE_INDEX[code]
    try:
        flag = db.scalar(select(SysFeatureFlag).where(SysFeatureFlag.code == code))
    except SQLAlchemyError:
        logging.exception("feature flag lookup failed, code=%s", code)
        db.rollback()
        flag = None
    return _with_overrides(default, flag)


def _with_overrides(default: dict[str, Any], flag: SysFeatureFlag | None) -> dict[str, Any]:
    if flag is None:
        return dict(default)
    return {
        **default,
        "enabled": bool(flag.enabled),
        "visible": bool(flag.visible),
        "sort_order": default["sort_order"] if flag.sort_order is None else flag.sort_order,
        "config": {**default["config"], **(flag.config or {})},
    }


def get_job_schedule(db: Session, code: str) -> tuple[bool, dict[str, Any]]:
    """读库失败直接抛出，不回退登记默认值：任务默认开启，回退会把库里关掉的任务又开起来。"""
    default_config = FEATURE_INDEX[code]["config"]
    flag = _with_overrides(FEATURE_INDEX[code], db.scalar(select(SysFeatureFlag).where(SysFeatureFlag.code == code)))
    return bool(flag["enabled"]), normalize_job_config(flag["config"], default_config["hour"], default_config["minute"])


def record_job_run(
    *,
    job_code: str,
    job_name: str,
    started_at: datetime,
    finished_at: datetime,
    result: str,
    summary: str,
    detail: dict[str, Any] | None = None,
    error_message: str | None = None,
) -> None:
    db = SessionLocal()
    try:
        duration_ms = int((finished_at - started_at).total_seconds() * 1000)
        db.add(
            SysJobRunLog(
                job_code=job_code,
                job_name=job_name,
                started_at=started_at,
                finished_at=finished_at,
                duration_ms=duration_ms,
                result=result,
                summary=summary,
                detail=detail or {},
                error_message=error_message,
            )
        )
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        logging.exception("record job run failed, job_code=%s", job_code)
    finally:
        db.close()


def run_recorded_job(
    job_code: str,
    job_name: str,
    work: Callable[[Session], Any],
    *,
    summarize: Callable[[Any], str] | None = None,
    skip_summary: str = "已跳过",
) -> None:
    """定时任务统一外壳：开会话执行 work，结果（成功/跳过/失败）写入任务运行记录。

    work 返回 {"skipped": True, ...} 视为跳过；异常只记录不外抛，调度器照常跑下一次。
    """
    started_at = now_local()
    db = SessionLocal()

    def record(result: str, summary: str, detail: Any, error_message: str | None = None) -> None:
        record_job_run(
            job_code=job_code,
            job_name=job_name,
            started_at=started_at,
            finished_at=now_local(),
            result=result,
            summary=summary,
            detail=detail if isinstance(detail, dict) else {"result": detail},
            error_message=error_message,
        )

    try:
        result = work(db)
        logging.info("%s result=%s", job_code, result)
        if isinstance(result, dict) and result.get("skipped") is True:
            record("skipped", str(result.get("message") or skip_summary), result)
        else:
            record("success", (summarize or summarize_job_result)(result), result)
    except Exception as error:
        db.rollback()
        logging.exception("%s failed", job_code)
        record("failed", "执行失败", {}, str(error))
    finally:
        db.close()


def list_job_run_logs(
    db: Session,
    job_code: str = "",
    result: str = "",
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    limit = min(max(limit, 1), 100)
    stmt = select(SysJobRunLog).order_by(SysJobRunLog.started_at.desc(), SysJobRunLog.id.desc())
    if job_code:
        stmt = stmt.where(SysJobRunLog.job_code == job_code)
    if result:
        stmt = stmt.where(SysJobRunLog.result == result)
    if start_date:
        stmt = stmt.where(SysJobRunLog.started_at >= start_date)
    if end_date:
        stmt = stmt.where(SysJobRunLog.started_at <= end_date)
    stmt = stmt.limit(limit)
    try:
        return [item.to_dict() for item in db.scalars(stmt).all()]
    except SQLAlchemyError:
        logging.warning("job run log list failed, using empty list")
        db.rollback()
        return []


def summarize_job_result(result: Any) -> str:
    if isinstance(result, dict):
        parts: list[str] = []
        for key, label in [
            ("created", "新增"),
            ("updated", "更新"),
            ("unchanged", "未变化"),
            ("reactivated", "重新启用"),
            ("deactivated", "停用"),
            ("updated_count", "状态更新"),
            ("titer_order_created_count", "新增效价工单"),
            ("disabled_on_resignation", "离职禁用"),
            ("total", "查询工单"),
            ("applied", "状态更新"),
            ("not_found", "未找到"),
            ("failed", "失败"),
        ]:
            if key in result:
                parts.append(f"{label} {result.get(key) or 0}")
        skipped = result.get("skipped")
        if isinstance(skipped, dict):
            parts.append(f"跳过 {sum(int(value or 0) for value in skipped.values())}")
        if parts:
            return "，".join(parts)
        message = result.get("message")
        if message:
            return str(message)[:255]
    return str(result)[:255]


def normalize_job_config(
    config: dict[str, Any] | None,
    default_hour: int = 0,
    default_minute: int = 0,
) -> dict[str, Any]:
    payload = config or {}
    schedule = str(payload.get("schedule") or "daily").strip()
    if schedule not in JOB_SCHEDULES:
        schedule = "daily"
    every = _bounded_int(payload.get("every"), 1, 14, 1)
    unit = str(payload.get("unit") or "").strip()
    if (every, unit) not in JOB_INTERVALS:
        every, unit = JOB_INTERVALS[0]
    return {
        "schedule": schedule,
        "hour": _bounded_int(payload.get("hour"), 0, 23, default_hour),
        "minute": _bounded_int(payload.get("minute"), 0, 59, default_minute),
        "weekday": _bounded_int(payload.get("weekday"), 0, 6, 0),
        "day": _bounded_int(payload.get("day"), 1, 28, 1),
        "every": every,
        "unit": unit,
    }


def build_job_trigger(config: dict[str, Any]):
    hour = int(config["hour"])
    minute = int(config["minute"])
    schedule = config["schedule"]
    if schedule == "weekly":
        return CronTrigger(day_of_week=int(config["weekday"]), hour=hour, minute=minute, timezone=_JOB_TIMEZONE)
    if schedule == "monthly":
        return CronTrigger(day=int(config["day"]), hour=hour, minute=minute, timezone=_JOB_TIMEZONE)
    if schedule == "interval":
        start = datetime(2020, 1, 1, hour, minute, tzinfo=_JOB_TIMEZONE)
        step = int(config["every"])
        if config["unit"] == "day":
            return IntervalTrigger(days=step, start_date=start, timezone=_JOB_TIMEZONE)
        return IntervalTrigger(hours=step, start_date=start, timezone=_JOB_TIMEZONE)
    return CronTrigger(hour=hour, minute=minute, timezone=_JOB_TIMEZONE)


def _normalize_config(category: str, config: dict[str, Any]) -> dict[str, Any]:
    if category == "job":
        return normalize_job_config(config)
    return config


def _bounded_int(value: Any, minimum: int, maximum: int, default: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return min(max(parsed, minimum), maximum)
