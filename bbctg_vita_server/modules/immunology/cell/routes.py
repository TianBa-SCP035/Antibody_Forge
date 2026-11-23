from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from core.response import success
from db.session import get_db
from modules.auth.permissions import require
from modules.immunology.cell.service import get_cell_inventory_data

router = APIRouter()


@router.get("/data", dependencies=[require("serum.cell.view")])
def cell_inventory_data(
    db: Session = Depends(get_db),
) -> dict:
    return success(get_cell_inventory_data(db))
