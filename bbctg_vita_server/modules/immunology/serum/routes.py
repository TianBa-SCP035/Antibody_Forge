from urllib.parse import quote

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from core.response import error, success
from db.session import get_db
from modules.immunology.serum import service

router = APIRouter()


@router.get("/stats")
def stats(db: Session = Depends(get_db)) -> dict:
    return success(service.get_stats(db))


@router.post("/list")
def list_serum(data: dict, db: Session = Depends(get_db)) -> dict:
    return success(service.get_list(db, data or {}))


@router.get("/detail")
def detail(id: int = Query(...), db: Session = Depends(get_db)) -> dict:
    data = service.get_detail(db, id)
    if data is None:
        return error("Project not found", 404)
    return success(data)


@router.get("/next_id")
def next_id(code: str = Query(...), db: Session = Depends(get_db)) -> dict:
    return success({"next_id": service.generate_next_id(db, code)})


@router.post("/save")
def save(data: dict, db: Session = Depends(get_db)) -> dict:
    try:
        return success(service.save_serum(db, data or {}))
    except Exception as exc:
        db.rollback()
        return error(str(exc))


@router.post("/delete")
def delete(data: dict, db: Session = Depends(get_db)) -> dict:
    try:
        service.delete_serum(db, int(data.get("id")))
        return success({"message": "Deleted successfully"})
    except Exception as exc:
        db.rollback()
        return error(str(exc))


@router.get("/filter_options")
def filter_options(db: Session = Depends(get_db)) -> dict:
    return success(service.get_filter_options(db))


@router.post("/update_status")
def update_status(data: dict, db: Session = Depends(get_db)) -> dict:
    try:
        service.update_status(db, int(data.get("id")), data.get("project_status"))
        return success({"message": "Status updated successfully"})
    except Exception as exc:
        db.rollback()
        return error(str(exc))


@router.post("/update_cage_position")
def update_cage_position(data: dict, db: Session = Depends(get_db)) -> dict:
    try:
        service.update_cage_position(db, int(data.get("id")), data.get("cage_position"))
        return success({"message": "笼位更新成功"})
    except Exception as exc:
        db.rollback()
        return error(str(exc), 20001)


@router.post("/project/prep_status")
def update_prep_status(data: dict, db: Session = Depends(get_db)) -> dict:
    try:
        service.update_prep_status(db, data.get("experiment_id"), data.get("prep_status"))
        return success({"message": "Prep status updated successfully"})
    except Exception as exc:
        db.rollback()
        return error(str(exc))


@router.post("/auto_update_status")
def auto_update_status(data: dict, db: Session = Depends(get_db)) -> dict:
    try:
        return success(service.auto_update_status(db, data or {}))
    except Exception as exc:
        db.rollback()
        return error(str(exc))


@router.post("/export_mouse")
def export_mouse(data: dict, db: Session = Depends(get_db)) -> StreamingResponse:
    output, filename = service.export_mouse_workbook(db, data or {})
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"},
    )
