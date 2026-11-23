from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from core.response import success
from db.session import get_db
from modules.auth.permissions import UserContext, get_user_context
from modules.options import service
from modules.registry import BUSINESS_PAGE_CODES


def _require_business_access(context: UserContext = Depends(get_user_context)) -> None:
    if not context.allows(*BUSINESS_PAGE_CODES):
        raise HTTPException(status_code=403, detail="没有业务页面权限，不能读取靶点和人员选项")


# 靶点、人员下拉是各业务页共用的基础数据；能打开任一业务页面即可读取，新模块的页面权限自动包含在内。
router = APIRouter(dependencies=[Depends(_require_business_access)])

@router.get("/targets")
def target_options(
    keyword: str = Query(default=""),
    limit: int = Query(default=service.DEFAULT_TARGET_LIMIT, ge=1, le=service.MAX_TARGET_LIMIT),
    codes: str = Query(default=""),
    db: Session = Depends(get_db),
) -> dict:
    return success(service.get_target_options(db, keyword, limit, codes.split(",")))


@router.get("/users")
def user_options(
    keyword: str = Query(default=""),
    limit: int = Query(default=service.DEFAULT_USER_LIMIT, ge=1, le=service.MAX_USER_LIMIT),
    db: Session = Depends(get_db),
) -> dict:
    return success({"items": service.get_user_options(db, keyword, limit)})
