from fastapi import APIRouter, Depends, File, Path, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from core.response import success
from db.session import get_db
from models.system import SysUser
from modules.auth.dependencies import get_current_user
from modules.auth.permissions import UserContext, get_user_context
from modules.auth.service import (
    avatar_file,
    change_user_password,
    login_with_password,
    login_with_yunzhijia_ticket,
    update_avatar,
    update_profile_signature,
    upload_avatar,
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


@router.put("/user/avatar", dependencies=[audit(AuditAction("auth.update_avatar", "更换头像", "update", "user"))])
def set_user_avatar(
    data: dict,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
) -> dict:
    return success(update_avatar(db, current_user, str(data.get("avatar") or "")))


@router.post("/user/avatar/upload", dependencies=[audit(AuditAction("auth.upload_avatar", "上传头像", "update", "user"))])
def upload_user_avatar(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
) -> dict:
    return success(upload_avatar(db, current_user, file))


@router.get("/avatar/{name}")
def get_avatar_file(name: str = Path(min_length=1, max_length=64)) -> FileResponse:
    return FileResponse(avatar_file(name), headers={"Cache-Control": "public, max-age=86400"})


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
