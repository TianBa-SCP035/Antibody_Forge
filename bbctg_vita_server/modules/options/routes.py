from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from core.response import success
from db.session import get_db
from models.system import SysUser
from modules.auth.dependencies import get_current_user
from modules.options import service
from modules.system.permissions import (
    DEFAULT_PERMISSION_MESSAGE,
    PERMISSION_MESSAGES,
    has_any_permission,
)

router = APIRouter()

# 任何需要靶点 / 人员下拉的业务页权限都可访问；新增业务页时在这里加一项。
OPTION_ACCESS_PERMISSIONS = {
    "serum.page.edit",
    "serum.page.list",
    "serum.page.workbench",
    "serum.page.titer_order",
    "discovery.page.workbench",
    "discovery.workbench.edit",
    "discovery.page.synthesis_progress",
    "discovery.synthesis_progress.edit",
    "discovery.synthesis_progress.pm_edit",
    "discovery.synthesis_progress.eng_edit",
    "discovery.synthesis_progress.affinity_edit",
    "discovery.synthesis_progress.flow_edit",
    "molecular.page.library",
    "molecular.library.edit",
    "molecular.page.library_detail",
    "molecular.library.file.manage",
    "mega.page.flow_work_order",
}


def _require_option_access(db: Session, user: SysUser) -> None:
    if has_any_permission(db, user, OPTION_ACCESS_PERMISSIONS):
        return
    raise HTTPException(
        status_code=403,
        detail=PERMISSION_MESSAGES.get("serum.page.edit", DEFAULT_PERMISSION_MESSAGE),
    )


@router.get("/targets")
def target_options(
    keyword: str = Query(default=""),
    limit: int = Query(default=service.DEFAULT_TARGET_LIMIT, ge=1, le=service.MAX_TARGET_LIMIT),
    codes: str = Query(default=""),
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
) -> dict:
    _require_option_access(db, current_user)
    return success(service.get_target_options(db, keyword, limit, codes.split(",")))


@router.get("/users")
def user_options(
    keyword: str = Query(default=""),
    limit: int = Query(default=service.DEFAULT_USER_LIMIT, ge=1, le=service.MAX_USER_LIMIT),
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
) -> dict:
    _require_option_access(db, current_user)
    return success({"items": service.get_user_options(db, keyword, limit)})
