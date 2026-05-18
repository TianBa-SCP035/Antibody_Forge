from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from core.vben_response import vben_success
from db.session import get_db
from models.system import SysUser
from modules.auth.dependencies import get_current_user
from modules.auth.service import (
    build_user_info,
    change_user_password,
    login_with_password,
    login_with_yunzhijia_ticket,
    update_profile_signature,
)
from modules.system.permissions import get_permission_codes

router = APIRouter()


@router.post("/login")
def login(data: dict, db: Session = Depends(get_db)) -> dict:
    return vben_success(login_with_password(db, data.get("username", ""), data.get("password", "")))


@router.post("/logout")
def logout() -> dict:
    return vben_success({"message": "ok"})


@router.post("/refresh")
def refresh_token(current_user: SysUser = Depends(get_current_user)) -> dict:
    from modules.auth.security import create_access_token

    return vben_success(create_access_token(current_user.id, current_user.username))


@router.get("/codes")
def access_codes(
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
) -> dict:
    return vben_success(get_permission_codes(db, current_user))


@router.get("/user/info")
def user_info(
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
) -> dict:
    return vben_success(build_user_info(db, current_user))


@router.put("/user/profile")
def update_user_profile(
    data: dict,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
) -> dict:
    signature = data.get("profileSignature")
    if signature is None:
        signature = data.get("profile_signature")
    return vben_success(update_profile_signature(db, current_user, signature))


@router.post("/user/change_password")
def change_password(
    data: dict,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
) -> dict:
    new_password = data.get("newPassword")
    if new_password is None:
        new_password = data.get("new_password", "")
    change_user_password(db, current_user, str(new_password))
    return vben_success({"message": "ok"})


@router.get("/yunzhijia")
def yunzhijia_login(ticket: str = Query(...), db: Session = Depends(get_db)) -> dict:
    return vben_success(login_with_yunzhijia_ticket(db, ticket))
