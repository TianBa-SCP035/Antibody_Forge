from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from core.response import error, success
from db.session import get_db
from modules.immunology.cell.service import get_cell_inventory_data

router = APIRouter()


@router.get("/data")
def cell_inventory_data(db: Session = Depends(get_db)) -> dict:
    try:
        return success(get_cell_inventory_data(db))
    except Exception as exc:
        return error(str(exc))
