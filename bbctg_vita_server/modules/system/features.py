from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from db.session import SessionLocal
from models.system import SysFeatureFlag, SysJobRunLog


DEFAULT_FEATURE_FLAGS: list[dict[str, Any]] = [
    {
        "code": "menu.discovery",
        "name": "千鼠万抗",
        "category": "menu",
        "description": "控制千鼠万抗父级菜单显示",
        "enabled": True,
        "visible": True,
        "sort_order": 5,
        "config": {"path": "/discovery", "icon": "lucide:network"},
    },
    {
        "code": "menu.discovery.target_library",
        "name": "靶点情报",
        "category": "menu",
        "description": "控制靶点情报页面显示",
        "enabled": True,
        "visible": True,
        "sort_order": 10,
        "config": {
            "path": "/discovery/targets",
            "icon": "lucide:database",
            "parent_code": "menu.discovery",
        },
    },
    {
        "code": "menu.system",
        "name": "系统管理",
        "category": "menu",
        "description": "控制系统管理父级菜单显示",
        "enabled": True,
        "visible": True,
        "sort_order": 90,
        "config": {"path": "/system", "icon": "lucide:settings"},
    },
    {
        "code": "menu.serum",
        "name": "血清实验菜单",
        "category": "menu",
        "description": "控制血清实验模块菜单显示",
        "enabled": True,
        "visible": True,
        "sort_order": 10,
        "config": {"path": "/serum", "icon": "lucide:test-tube"},
    },
    {
        "code": "menu.serum.list",
        "name": "免疫实验列表",
        "category": "menu",
        "description": "控制免疫实验列表菜单显示",
        "enabled": True,
        "visible": True,
        "sort_order": 10,
        "config": {
            "path": "/serum/list",
            "icon": "lucide:list",
            "parent_code": "menu.serum",
        },
    },
    {
        "code": "menu.serum.titer_order",
        "name": "效价实验列表",
        "category": "menu",
        "description": "控制效价实验列表菜单显示",
        "enabled": True,
        "visible": True,
        "sort_order": 20,
        "config": {
            "path": "/serum/titer-orders",
            "icon": "lucide:clipboard-list",
            "parent_code": "menu.serum",
        },
    },
    {
        "code": "menu.system.user_permission",
        "name": "用户权限菜单",
        "category": "menu",
        "description": "控制系统管理下用户权限页面显示",
        "enabled": True,
        "visible": True,
        "sort_order": 10,
        "config": {"path": "/system/user-permission", "icon": "lucide:shield-check", "parent_code": "menu.system"},
    },
    {
        "code": "menu.system.features",
        "name": "系统功能菜单",
        "category": "menu",
        "description": "控制系统管理下系统功能页面显示",
        "enabled": True,
        "visible": True,
        "sort_order": 20,
        "config": {"path": "/system/features", "icon": "lucide:sliders-horizontal", "parent_code": "menu.system"},
    },
    {
        "code": "feature.yunzhijia_auto_provision",
        "name": "云之家自动创建用户",
        "category": "feature",
        "description": "允许云之家登录时自动创建未绑定用户",
        "enabled": False,
        "visible": True,
        "sort_order": 110,
        "config": {},
    },
    {
        "code": "feature.drm_file_security",
        "name": "DRM 文件安全模块",
        "category": "feature",
        "description": "控制上传自动解密、下载前加密等 DRM 文件安全能力；失败时不阻断正常上传下载",
        "enabled": False,
        "visible": True,
        "sort_order": 120,
        "config": {},
    },
    {
        "code": "job.employee_profile_sync",
        "name": "员工资料定时同步",
        "category": "job",
        "description": "每天 00:30 同步外部员工基础资料",
        "enabled": True,
        "visible": True,
        "sort_order": 200,
        "config": {"hour": 0, "minute": 30, "cron": "30 0 * * *", "restart_required": True},
    },
    {
        "code": "job.target_master_sync",
        "name": "靶点主数据定时同步",
        "category": "job",
        "description": "每天 00:45 同步外部靶点主数据",
        "enabled": True,
        "visible": True,
        "sort_order": 205,
        "config": {"hour": 0, "minute": 45, "cron": "45 0 * * *", "restart_required": True},
    },
    {
        "code": "job.serum_auto_update_status",
        "name": "免疫状态自动更新",
        "category": "job",
        "description": "每天 01:00 自动更新免疫实验状态",
        "enabled": True,
        "visible": True,
        "sort_order": 210,
        "config": {"hour": 1, "minute": 0, "cron": "0 1 * * *", "restart_required": True},
    },
    {
        "code": "job.mega_labillion_status_sync",
        "name": "镁伽工单状态同步",
        "category": "job",
        "description": "每天 02:00 同步镁伽非终态工单状态",
        "enabled": True,
        "visible": True,
        "sort_order": 220,
        "config": {"hour": 2, "minute": 0, "cron": "0 2 * * *", "restart_required": True},
    },
]

DEFAULT_FEATURE_INDEX = {item["code"]: item for item in DEFAULT_FEATURE_FLAGS}
OBSOLETE_FEATURE_CODES = {
    "feature.employee_sync",
    "setting.maintenance_enabled",
    "setting.site_title",
    "setting.default_theme",
    "setting.default_language",
    "setting.default_home_path",
}


def list_feature_flags(db: Session) -> list[dict[str, Any]]:
    try:
        persisted = {flag.code: flag for flag in db.scalars(select(SysFeatureFlag)).all()}
    except SQLAlchemyError:
        logging.warning("feature flag list failed, using defaults")
        db.rollback()
        persisted = {}
    items: list[dict[str, Any]] = []
    for default in DEFAULT_FEATURE_FLAGS:
        flag = persisted.get(default["code"])
        if flag:
            flag_data = flag.to_dict()
            data = {
                **default,
                **flag_data,
                "config": {**(default.get("config") or {}), **(flag_data.get("config") or {})},
                "name": default["name"],
                "description": default.get("description"),
            }
        else:
            data = dict(default)
        items.append(data)
    extras = [
        flag.to_dict()
        for code, flag in persisted.items()
        if code not in DEFAULT_FEATURE_INDEX and code not in OBSOLETE_FEATURE_CODES
    ]
    return sorted([*items, *extras], key=lambda item: (item.get("category") or "", item.get("sort_order") or 0))


def save_feature_flag(db: Session, data: dict[str, Any]) -> dict[str, Any]:
    code = str(data.get("code") or "").strip()
    if not code:
        raise ValueError("功能编码不能为空")
    default = next((item for item in DEFAULT_FEATURE_FLAGS if item["code"] == code), None)
    flag = db.scalar(select(SysFeatureFlag).where(SysFeatureFlag.code == code))
    if flag is None:
        source = default or {}
        flag = SysFeatureFlag(
            code=code,
            name=str(data.get("name") or source.get("name") or code),
            category=str(data.get("category") or source.get("category") or "feature"),
            description=data.get("description") or source.get("description"),
            sort_order=int(data.get("sort_order") if data.get("sort_order") is not None else source.get("sort_order") or 0),
            config=_normalize_config(
                str(data.get("category") or source.get("category") or "feature"),
                data.get("config") or source.get("config") or {},
            ),
        )
        db.add(flag)
    flag.name = str(data.get("name") or flag.name)
    flag.category = str(data.get("category") or flag.category)
    flag.description = data.get("description") if "description" in data else flag.description
    flag.enabled = bool(data.get("enabled"))
    flag.visible = bool(data.get("visible"))
    if "sort_order" in data:
        flag.sort_order = int(data.get("sort_order") or 0)
    if "config" in data:
        flag.config = _normalize_config(flag.category, data.get("config") or {})
    db.commit()
    db.refresh(flag)
    return flag.to_dict()


def is_feature_enabled(db: Session, code: str, default: bool = True) -> bool:
    try:
        flag = db.scalar(select(SysFeatureFlag).where(SysFeatureFlag.code == code))
    except SQLAlchemyError:
        logging.exception("feature flag lookup failed, code=%s", code)
        db.rollback()
        return default
    if flag is None:
        return default
    return bool(flag.enabled)


def get_feature_flag(db: Session, code: str) -> dict[str, Any] | None:
    default = DEFAULT_FEATURE_INDEX.get(code)
    try:
        flag = db.scalar(select(SysFeatureFlag).where(SysFeatureFlag.code == code))
    except SQLAlchemyError:
        logging.warning("feature flag lookup failed, using default, code=%s", code)
        db.rollback()
        flag = None
    if flag is None:
        return dict(default) if default else None
    flag_data = flag.to_dict()
    return {
        **(default or {}),
        **flag_data,
        "config": {**((default or {}).get("config") or {}), **(flag_data.get("config") or {})},
    }


def get_job_schedule(db: Session, code: str, default_hour: int, default_minute: int) -> tuple[bool, int, int]:
    flag = get_feature_flag(db, code)
    if flag is None:
        return True, default_hour, default_minute
    config = flag.get("config") or {}
    hour = _bounded_int(config.get("hour"), 0, 23, default_hour)
    minute = _bounded_int(config.get("minute"), 0, 59, default_minute)
    return bool(flag.get("enabled", True)), hour, minute


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


def _normalize_config(category: str, config: dict[str, Any]) -> dict[str, Any]:
    if category == "job":
        hour = _bounded_int(config.get("hour"), 0, 23, 0)
        minute = _bounded_int(config.get("minute"), 0, 59, 0)
        return {
            **config,
            "hour": hour,
            "minute": minute,
            "cron": f"{minute} {hour} * * *",
            "restart_required": bool(config.get("restart_required", True)),
        }
    return config


def _bounded_int(value: Any, minimum: int, maximum: int, default: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return min(max(parsed, minimum), maximum)
