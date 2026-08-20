from datetime import datetime
import re

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from core.config import get_settings
from integrations.yunzhijia import YunzhijiaClient
from models.system import SysUser
from modules.auth.security import create_access_token, hash_password, verify_password
from modules.system.audit import write_operation_log
from modules.system.features import is_feature_enabled
from modules.system.permissions import build_user_context

YUNZHIJIA_AUTO_PROVISION_FEATURE = "feature.yunzhijia_auto_provision"


def login_with_password(db: Session, username: str, password: str) -> dict:
    username = (username or "").strip()
    user = db.scalar(select(SysUser).where(SysUser.username == username))
    if not user or not verify_password(password, user.password_hash or ""):
        write_operation_log(
            db,
            "auth.password_login",
            "sys_user",
            str(user.id) if user else None,
            {"username": username},
            user=user,
            username=username,
            operation_name="账号密码登录",
            operation_type="login",
            target_label=username,
            result="failed",
            error_message="用户名或密码错误",
        )
        db.commit()
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    if user.status != "active":
        write_operation_log(
            db,
            "auth.password_login",
            "sys_user",
            str(user.id),
            {"username": username},
            user=user,
            username=username,
            operation_name="账号密码登录",
            operation_type="login",
            target_label=user.display_name or username,
            result="failed",
            error_message="账号已被禁用",
        )
        db.commit()
        raise HTTPException(status_code=401, detail="账号已被禁用，请联系管理员")
    write_operation_log(
        db,
        "auth.password_login",
        "sys_user",
        str(user.id),
        {"username": user.username},
        user=user,
        operation_name="账号密码登录",
        operation_type="login",
        target_label=user.display_name or user.username,
    )
    _mark_login(db, user)
    return {"accessToken": create_access_token(user.id, user.username)}


def login_with_yunzhijia_ticket(db: Session, ticket: str) -> dict:
    settings = get_settings()
    client = YunzhijiaClient(settings.yunzhijia_appid, settings.yunzhijia_appsecret)
    result = client.acquire_user_context(ticket)
    user_context = result["data"]
    openid = user_context.get("openid")
    if not openid:
        write_operation_log(
            db,
            "auth.yunzhijia_login",
            "sys_user",
            None,
            {},
            operation_name="云之家登录",
            operation_type="login",
            result="failed",
            error_message="云之家未返回用户 openid",
        )
        db.commit()
        raise HTTPException(status_code=401, detail="云之家未返回用户 openid")
    user = db.scalar(select(SysUser).where(SysUser.openid == openid))
    if not user:
        if is_feature_enabled(db, YUNZHIJIA_AUTO_PROVISION_FEATURE, default=False):
            user = _provision_yunzhijia_user(db, user_context)
            write_operation_log(
                db,
                "auth.yunzhijia_auto_provision",
                "sys_user",
                str(user.id) if user.id else None,
                {"openid": openid, "job_no": user.job_no},
                user=user,
                operation_name="云之家自动创建用户",
                operation_type="create",
                target_label=user.display_name or user.username,
            )
        else:
            write_operation_log(
                db,
                "auth.yunzhijia_login",
                "sys_user",
                None,
                {"openid": openid},
                username=openid,
                operation_name="云之家登录",
                operation_type="login",
                target_label=openid,
                result="failed",
                error_message="该云之家账号尚未绑定系统用户",
            )
            db.commit()
            raise HTTPException(status_code=403, detail="该云之家账号尚未绑定系统用户")
    if user.status != "active":
        write_operation_log(
            db,
            "auth.yunzhijia_login",
            "sys_user",
            None,
            {"openid": openid},
            username=openid,
            operation_name="云之家登录",
            operation_type="login",
            target_label=openid,
            result="failed",
            error_message="该云之家账号未启用",
        )
        db.commit()
        raise HTTPException(status_code=403, detail="该云之家账号未启用")
    write_operation_log(
        db,
        "auth.yunzhijia_login",
        "sys_user",
        str(user.id),
        {"openid": openid},
        user=user,
        operation_name="云之家登录",
        operation_type="login",
        target_label=user.display_name or user.username,
    )
    _mark_login(db, user)
    return {"accessToken": create_access_token(user.id, user.username)}


def build_user_info(db: Session, user: SysUser) -> dict:
    context = build_user_context(db, user)
    last_login_at = user.last_login_at.isoformat() if user.last_login_at else None
    return {
        "id": context.id,
        "roles": context.roles,
        "permissions": context.permissions,
        "accessCodes": context.permissions,
        "avatar": "https://wpimg.wallstcn.com/f778738c-e4f8-4870-b634-56703b4acafe.gif",
        "realName": context.display_name,
        "username": context.username,
        "homePath": "/home",
        "isSuperuser": context.is_superuser,
        "department": user.department,
        "groupName": user.group_name,
        "jobNo": user.job_no,
        "positionTitle": user.position_title,
        "gender": user.gender,
        "email": user.email,
        "mobile": user.mobile,
        "profileSignature": user.profile_signature,
        "lastLoginAt": last_login_at,
        "hasPassword": bool(user.password_hash),
    }


def update_profile_signature(db: Session, user: SysUser, signature: str | None) -> dict:
    normalized = (signature or "").strip()
    if len(normalized) > 255:
        raise ValueError("个性名片不能超过 255 个字符")
    user.profile_signature = normalized or None
    write_operation_log(
        db,
        "auth.update_profile_signature",
        "sys_user",
        str(user.id),
        {"field": "profile_signature"},
        user=user,
        operation_name="更新个性名片",
        operation_type="update",
        target_label=user.display_name or user.username,
    )
    db.commit()
    db.refresh(user)
    return build_user_info(db, user)


def change_user_password(db: Session, user: SysUser, new_password: str) -> None:
    password = (new_password or "").strip()
    if len(password) < 6:
        raise ValueError("密码至少需要 6 位")
    mode = "change" if user.password_hash else "set"
    user.password_hash = hash_password(password)
    write_operation_log(
        db,
        "auth.change_password",
        "sys_user",
        str(user.id),
        {"mode": mode},
        user=user,
        operation_name="修改登录密码",
        operation_type="update",
        target_label=user.display_name or user.username,
    )
    db.commit()


def _mark_login(db: Session, user: SysUser) -> None:
    user.last_login_at = datetime.now()
    db.commit()


def _provision_yunzhijia_user(db: Session, user_context: dict) -> SysUser:
    openid = str(user_context["openid"]).strip()
    job_no = _first_present(user_context, "jobNo", "job_no", "jobNumber", "employeeNo")
    display_name = _first_present(user_context, "displayName", "userName", "username", "name", "nickName") or openid
    username = _unique_username(db, job_no or openid)
    user = SysUser(
        username=username,
        display_name=display_name,
        openid=openid,
        job_no=job_no,
        email=_first_present(user_context, "email"),
        mobile=_first_present(user_context, "mobile", "phone", "mobilePhone"),
        status="active",
        employment_status="active",
        is_superuser=False,
    )
    db.add(user)
    db.flush()
    return user


def _first_present(data: dict, *keys: str) -> str | None:
    for key in keys:
        value = data.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return None


def _unique_username(db: Session, raw_value: str) -> str:
    base = re.sub(r"[^0-9A-Za-z_.-]+", "_", raw_value.strip())[:64].strip("._-")
    if not base:
        base = "yunzhijia_user"
    username = base
    suffix = 1
    while db.scalar(select(SysUser.id).where(SysUser.username == username)):
        suffix += 1
        suffix_text = f"_{suffix}"
        username = f"{base[: 64 - len(suffix_text)]}{suffix_text}"
    return username
