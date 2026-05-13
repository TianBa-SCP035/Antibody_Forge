from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from core.response import error, success
from db.session import get_db
from models.system import SysUser
from modules.auth.dependencies import get_current_user
from modules.immunology.cell.service import get_cell_inventory_data
from modules.system.permissions import require_permission

router = APIRouter()


@router.get("/data")
def cell_inventory_data(
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
) -> dict:
    try:
        require_permission(db, current_user, "serum.cell.view")
        return success(get_cell_inventory_data(db))
    except HTTPException:
        raise
    except Exception as exc:
        return error(str(exc))
