from importlib import import_module

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from core.response import success
from db.session import get_db
from models.system import SysUser
from modules.auth.dependencies import get_current_user
from modules.auth.service import build_user_info
from modules.registry import MOUNTS

api_router = APIRouter()


@api_router.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


for _mount in MOUNTS:
    _module_path, _attribute = _mount.router.split(":")
    api_router.include_router(getattr(import_module(_module_path), _attribute), prefix=_mount.prefix, tags=[_mount.tag])


@api_router.get("/user/info", tags=["认证"])
def user_info(
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
) -> dict:
    return success(build_user_info(db, current_user))
