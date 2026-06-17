from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from core.response import success
from db.session import get_db
from models.system import SysUser
from modules.auth.dependencies import get_current_user
from modules.auth.routes import router as auth_router
from modules.auth.service import build_user_info
from modules.immunology.cell.routes import router as cell_router
from modules.immunology.serum.routes import router as serum_router
from modules.immunology.titer.routes import router as titer_router
from modules.system.routes import router as system_router

api_router = APIRouter()


@api_router.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


api_router.include_router(auth_router, prefix="/auth", tags=["认证"])
api_router.include_router(serum_router, prefix="/serum", tags=["免疫部-血清"])
api_router.include_router(titer_router, prefix="/serum/titer", tags=["免疫部-效价"])
api_router.include_router(cell_router, prefix="/serum/cell_inventory", tags=["免疫部-细胞"])
api_router.include_router(system_router, prefix="/system", tags=["系统管理"])


@api_router.get("/user/info", tags=["认证"])
def user_info(
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
) -> dict:
    return success(build_user_info(db, current_user))
