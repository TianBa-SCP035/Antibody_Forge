from importlib import import_module

from fastapi import APIRouter, Depends
from fastapi.routing import APIRoute
from sqlalchemy.orm import Session

from core.response import success
from db.session import get_db
from models.system import SysUser
from modules.auth.dependencies import get_current_user
from modules.auth.service import build_user_info
from modules.registry import MOUNTS

API_PREFIX = "/api"

root_router = APIRouter()


@root_router.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@root_router.get("/user/info", tags=["认证"])
def user_info(
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
) -> dict:
    return success(build_user_info(db, current_user))


_mounted: list[tuple[str, APIRouter]] = [("", root_router)]
api_router = APIRouter()
api_router.include_router(root_router)
for _mount in MOUNTS:
    _module_path, _attribute = _mount.router.split(":")
    _router = getattr(import_module(_module_path), _attribute)
    _mounted.append((_mount.prefix, _router))
    api_router.include_router(_router, prefix=_mount.prefix, tags=[_mount.tag])


def api_routes() -> list[tuple[str, APIRoute]]:
    """全部业务接口的完整路径和路由。app.routes 的结构随 FastAPI 版本变化，不能用来枚举接口。"""
    return [
        (API_PREFIX + prefix + route.path, route)
        for prefix, router in _mounted
        for route in router.routes
        if isinstance(route, APIRoute)
    ]
