from fastapi import APIRouter, Body, Depends
from sqlalchemy.orm import Session

from core.response import success
from db.session import get_db
from models.system import SysUser
from modules.auth.dependencies import get_current_user
from modules.discovery import service
from modules.system.permissions import require_permission


router = APIRouter()
TARGET_LIBRARY_PERMISSION = "discovery.page.target_library"


@router.post("/targets/list")
def target_list(
    data: dict | None = Body(default=None),
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
) -> dict:
    require_permission(db, current_user, TARGET_LIBRARY_PERMISSION)
    return success(service.get_target_list(db, data or {}))
