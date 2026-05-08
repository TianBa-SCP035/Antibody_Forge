from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from core.vben_response import vben_success
from db.session import get_db
from modules.auth.routes import router as auth_router
from modules.auth.service import build_user_info, get_development_user
from modules.immunology.cell.routes import router as cell_router
from modules.immunology.serum.routes import router as serum_router
from modules.immunology.titer.routes import router as titer_router

api_router = APIRouter()


@api_router.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


api_router.include_router(auth_router, prefix="/auth", tags=["认证"])
api_router.include_router(serum_router, prefix="/serum", tags=["免疫部-血清"])
api_router.include_router(titer_router, prefix="/serum/titer", tags=["免疫部-效价"])
api_router.include_router(cell_router, prefix="/serum/cell_inventory", tags=["免疫部-细胞"])


@api_router.get("/user/info", tags=["认证"])
def user_info(db: Session = Depends(get_db)) -> dict:
    return vben_success(build_user_info(get_development_user(db)))
