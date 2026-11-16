from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from core.config import get_settings
from core.response import success
from db.session import get_db
from jobs.registry import (
    apply_job_schedule,
    run_scheduled_job_now,
    scheduler_is_running,
)
from models.system import SysUser
from modules.auth.dependencies import get_current_user
from modules.auth.permissions import require
from modules.system import service
from modules.system.features import (
    list_feature_flags,
    list_job_run_logs,
    save_feature_flag,
)
from utils.clock import now_local

router = APIRouter()


@router.get("/users", dependencies=[require("system.user.manage")])
def list_users(
    keyword: str = "",
    department: list[str] | None = Query(default=None),
    group_name: list[str] | None = Query(default=None),
    gender: list[str] | None = Query(default=None),
    status: list[str] | None = Query(default=None),
    employment_status: list[str] | None = Query(default=None),
    role_id: list[str] | None = Query(default=None),
    has_admin_role: list[str] | None = Query(default=None),
    has_permission_override: list[str] | None = Query(default=None),
    page: int = 1,
    page_size: int = 50,
    db: Session = Depends(get_db),
) -> dict:
    return success(
        service.list_users(
            db,
            keyword=keyword,
            department=department,
            group_name=group_name,
            gender=gender,
            status=status,
            employment_status=employment_status,
            role_id=role_id,
            has_admin_role=has_admin_role,
            has_permission_override=has_permission_override,
            page=page,
            page_size=page_size,
        )
    )


@router.get("/users/suggestions", dependencies=[require("system.user.manage")])
def user_suggestions(
    field: str,
    keyword: str = "",
    limit: int = 20,
    db: Session = Depends(get_db),
) -> dict:
    return success({"items": service.user_suggestions(db, field, keyword, limit)})


@router.post("/users/save", dependencies=[require("system.user.manage", audit="新增或编辑用户")])
def save_user(
    data: dict,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
) -> dict:
    return success({"id": service.save_user(db, data, actor=current_user)})


@router.get("/features", dependencies=[require("system.page.feature")])
def list_features(
    db: Session = Depends(get_db),
) -> dict:
    return success({"items": list_feature_flags(db)})


@router.get("/features/job_logs", dependencies=[require("system.page.feature")])
def feature_job_logs(
    job_code: str = "",
    result: str = "",
    start_date: str = "",
    end_date: str = "",
    limit: int = 20,
    db: Session = Depends(get_db),
) -> dict:
    return success(
        {
            "items": list_job_run_logs(
                db,
                job_code=job_code,
                result=result,
                start_date=_parse_datetime(start_date),
                end_date=_parse_datetime(end_date, end_of_day=True),
                limit=limit,
            )
        }
    )


@router.get("/features/system_status", dependencies=[require("system.page.feature")])
def feature_system_status(
    current_user: SysUser = Depends(get_current_user),
) -> dict:
    return success(
        {
            "server_time": now_local().isoformat(timespec="seconds"),
            "timezone": "Asia/Shanghai",
            "user_id": current_user.id,
            "app_env": get_settings().app_env,
            "scheduler_running": scheduler_is_running(),
        }
    )


def _parse_datetime(value: str, *, end_of_day: bool = False) -> datetime | None:
    text = (value or "").strip()
    if not text:
        return None
    try:
        if len(text) == 10:
            suffix = " 23:59:59" if end_of_day else " 00:00:00"
            return datetime.fromisoformat(text + suffix)
        return datetime.fromisoformat(text)
    except ValueError:
        return None


@router.get("/features/effective")
def effective_features(
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
) -> dict:
    return success(
        {
            "items": [
                {
                    "code": item["code"],
                    "category": item["category"],
                    "enabled": item["enabled"],
                    "sort_order": item["sort_order"],
                    "visible": item["visible"],
                }
                for item in list_feature_flags(db)
                if item["category"] != "job"
            ]
        }
    )


@router.post("/features/save", dependencies=[require("system.feature.manage", audit="保存系统功能配置")])
def save_feature(
    data: dict,
    db: Session = Depends(get_db),
) -> dict:
    saved = save_feature_flag(db, data)
    if saved["category"] == "job":
        apply_job_schedule(saved["code"])
    return success(saved)


@router.post("/features/jobs/run", dependencies=[require("system.feature.manage", audit="手动执行定时任务")])
def run_feature_job(
    data: dict,
) -> dict:
    job_code = str(data.get("job_code") or "").strip()
    if not job_code:
        raise ValueError("任务编码不能为空")
    run_scheduled_job_now(job_code)
    return success({"job_code": job_code, "started": True})


@router.post("/users/delete", dependencies=[require("system.user.manage", audit="删除用户")])
def delete_user(
    data: dict,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
) -> dict:
    service.delete_user(db, int(data.get("id") or 0), actor=current_user)
    return success({"message": "ok"})


@router.post("/users/batch_roles", dependencies=[require("system.user.manage", audit="批量设置用户角色")])
def batch_update_user_roles(
    data: dict,
    db: Session = Depends(get_db),
) -> dict:
    return success({"updated": service.batch_update_user_roles(db, data)})


@router.post("/users/reset_password", dependencies=[require("system.user.manage", audit="重置用户密码")])
def reset_password(
    data: dict,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
) -> dict:
    service.reset_password(db, int(data.get("id")), str(data.get("password") or ""), actor=current_user)
    return success({"message": "ok"})


@router.get("/users/{user_id}/permission_overrides", dependencies=[require("system.permission.manage")])
def get_user_permission_overrides(
    user_id: int,
    db: Session = Depends(get_db),
) -> dict:
    return success(service.get_user_permission_overrides(db, int(user_id)))


@router.post("/users/{user_id}/permission_overrides", dependencies=[require("system.permission.manage", audit="保存用户个人权限覆盖")])
def save_user_permission_overrides(
    user_id: int,
    data: dict,
    db: Session = Depends(get_db),
) -> dict:
    service.save_user_permission_overrides(db, int(user_id), data)
    return success({"message": "ok"})


@router.get("/roles", dependencies=[require("system.role.manage")])
def list_roles(
    db: Session = Depends(get_db),
) -> dict:
    return success({"items": service.list_roles(db)})


@router.post("/roles/save", dependencies=[require("system.role.manage", audit="新增或编辑角色")])
def save_role(
    data: dict,
    db: Session = Depends(get_db),
) -> dict:
    return success({"id": service.save_role(db, data)})


@router.post("/roles/delete", dependencies=[require("system.role.manage", audit="删除角色")])
def delete_role(
    data: dict,
    db: Session = Depends(get_db),
) -> dict:
    service.delete_role(db, int(data.get("id") or 0))
    return success({"message": "ok"})


@router.get("/permissions", dependencies=[require("system.permission.manage")])
def list_permissions() -> dict:
    return success({"items": service.list_permissions()})


@router.get("/permission_bundles", dependencies=[require("system.permission.manage")])
def list_permission_bundles(
    db: Session = Depends(get_db),
) -> dict:
    return success({"items": service.list_permission_bundles(db)})


@router.post("/permission_bundles/save", dependencies=[require("system.permission.manage", audit="新增或编辑权限包")])
def save_permission_bundle(
    data: dict,
    db: Session = Depends(get_db),
) -> dict:
    return success({"id": service.save_permission_bundle(db, data)})


@router.post("/permission_bundles/delete", dependencies=[require("system.permission.manage", audit="删除权限包")])
def delete_permission_bundle(
    data: dict,
    db: Session = Depends(get_db),
) -> dict:
    service.delete_permission_bundle(db, data)
    return success({"message": "ok"})


@router.get("/operation_logs", dependencies=[require("system.operation_log.view")])
def list_operation_logs(
    page: int = 1,
    page_size: int = 50,
    operator: str = "",
    action: str = "",
    target_type: list[str] | None = Query(default=None),
    target: str = "",
    source: list[str] | None = Query(default=None),
    change: str = "",
    result: list[str] | None = Query(default=None),
    error_message: str = "",
    operation_type: list[str] | None = Query(default=None),
    request_id: str = "",
    date_start: str = "",
    date_end: str = "",
    db: Session = Depends(get_db),
) -> dict:
    return success(
        service.list_operation_logs(
            db,
            page=page,
            page_size=page_size,
            operator=operator,
            action=action,
            target_type=target_type,
            target=target,
            source=source,
            change=change,
            result=result,
            error_message=error_message,
            operation_type=operation_type,
            request_id=request_id,
            date_start=date_start,
            date_end=date_end,
        )
    )


@router.get("/operation_logs/{log_id}", dependencies=[require("system.operation_log.view")])
def get_operation_log_detail(
    log_id: int,
    db: Session = Depends(get_db),
) -> dict:
    return success(service.get_operation_log_detail(db, int(log_id)))
