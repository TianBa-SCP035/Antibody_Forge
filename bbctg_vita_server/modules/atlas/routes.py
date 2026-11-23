from fastapi import APIRouter, Body, Depends
from sqlalchemy.orm import Session

from core.response import success
from db.session import get_db
from modules.atlas import service
from modules.auth.permissions import require

router = APIRouter()
TARGET_LIBRARY_PERMISSION = "atlas.page.target_library"


@router.post("/targets/list", dependencies=[require(TARGET_LIBRARY_PERMISSION)])
def target_list(
    data: dict | None = Body(default=None),
    db: Session = Depends(get_db),
) -> dict:
    return success(service.get_target_list(db, data or {}))
