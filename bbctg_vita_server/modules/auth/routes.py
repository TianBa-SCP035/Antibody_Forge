from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from core.response import success
from db.session import get_db
from models.system import SysUser
from modules.auth.dependencies import get_current_user
from modules.auth.permissions import UserContext, get_user_context
from modules.auth.service import (
    change_user_password,
    login_with_password,
    login_with_yunzhijia_ticket,
    update_profile_signature,
)
from modules.system.audit_context import AuditAction
from modules.system.audit_routes import audit, audit_quiet

router = APIRouter()


@router.post("/login", dependencies=[audit(AuditAction("auth.password_login", "账号密码登录", "login", "sys_user"))])
def login(data: dict, db: Session = Depends(get_db)) -> dict:
    return success(login_with_password(db, data.get("username", ""), data.get("password", "")))


@router.post("/logout", dependencies=[audit_quiet()])
def logout() -> dict:
    return success({"message": "ok"})


@router.get("/codes")
def access_codes(context: UserContext = Depends(get_user_context)) -> dict:
    return success(context.permissions)


@router.put("/user/profile", dependencies=[audit(AuditAction("auth.update_profile", "更新个人资料", "update", "user"))])
def update_user_profile(
    data: dict,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
) -> dict:
    signature = data.get("profileSignature")
    if signature is None:
        signature = data.get("profile_signature")
    return success(update_profile_signature(db, current_user, signature))


@router.post(
    "/user/change_password",
    dependencies=[audit(AuditAction("auth.change_password", "修改密码", "update", "user"))],
)
def change_password(
    data: dict,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
) -> dict:
    new_password = data.get("newPassword")
    if new_password is None:
        new_password = data.get("new_password", "")
    change_user_password(db, current_user, str(new_password))
    return success({"message": "ok"})


@router.get("/yunzhijia")
def yunzhijia_login(ticket: str = Query(...), db: Session = Depends(get_db)) -> dict:
    return success(login_with_yunzhijia_ticket(db, ticket))
