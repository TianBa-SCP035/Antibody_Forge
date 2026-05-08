from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session

from core.response import error, success
from db.session import get_db
from modules.immunology.titer import service

router = APIRouter()


@router.post("/file/list")
def file_list(data: dict, db: Session = Depends(get_db)) -> dict:
    return success({"items": service.get_file_list(db, data.get("experiment_id"))})


@router.post("/file/save")
def file_save(
    file: UploadFile = File(...),
    experiment_id: str = Form(...),
    user_name: str = Form("unknown"),
    db: Session = Depends(get_db),
) -> dict:
    try:
        return success(service.save_file(db, file, experiment_id, user_name))
    except Exception as exc:
        db.rollback()
        return error(str(exc))


@router.post("/file/delete")
def file_delete(data: dict, db: Session = Depends(get_db)) -> dict:
    try:
        service.delete_file(db, int(data.get("id")))
        return success({"message": "Success"})
    except Exception as exc:
        db.rollback()
        return error(str(exc))


@router.post("/file/rename")
def file_rename(data: dict, db: Session = Depends(get_db)) -> dict:
    try:
        service.rename_file(db, int(data.get("id")), data.get("new_name"))
        return success({"message": "Success"})
    except Exception as exc:
        db.rollback()
        return error(str(exc))


@router.post("/file/replace")
def file_replace(
    file: UploadFile = File(...),
    id: int = Form(...),
    user_name: str = Form("unknown"),
    db: Session = Depends(get_db),
) -> dict:
    try:
        return success(service.replace_file(db, id, file, user_name))
    except Exception as exc:
        db.rollback()
        return error(str(exc))


@router.get("/file/download")
def file_download(
    id: int = Query(...),
    preview: str | None = None,
    thumb: str | None = None,
    w: int = 400,
    h: int = 400,
    db: Session = Depends(get_db),
):
    try:
        record, file_path = service.get_download_record(db, id)
        if thumb and thumb.lower() in {"1", "true"}:
            thumbnail = service.create_thumbnail(file_path, w, h)
            if thumbnail:
                output, media_type = thumbnail
                return StreamingResponse(output, media_type=media_type)
        return FileResponse(
            file_path,
            filename=record.file_name,
            media_type=None,
            headers={"Content-Disposition": f"{'inline' if preview == 'true' else 'attachment'}; filename*=UTF-8''{quote(record.file_name)}"},
        )
    except Exception as exc:
        return error(str(exc))


@router.post("/target/save")
def target_save(data: dict, db: Session = Depends(get_db)) -> dict:
    try:
        return success({"items": service.save_targets(db, data.get("experiment_id"), data.get("targets", []))})
    except Exception as exc:
        db.rollback()
        return error(str(exc))


@router.post("/pc/save")
def pc_save(data: dict, db: Session = Depends(get_db)) -> dict:
    try:
        return success({"items": service.save_pcs(db, data.get("experiment_id"), data.get("pcs", []))})
    except Exception as exc:
        db.rollback()
        return error(str(exc))


@router.post("/plate/list")
def plate_list(data: dict, db: Session = Depends(get_db)) -> dict:
    return success({"items": service.get_facs_plates(db, data.get("experiment_id"))})


@router.post("/plate/save")
def plate_save(data: dict, db: Session = Depends(get_db)) -> dict:
    try:
        return success(service.save_facs_plate(db, data or {}))
    except Exception as exc:
        db.rollback()
        return error(str(exc))


@router.post("/plate/delete")
def plate_delete(data: dict, db: Session = Depends(get_db)) -> dict:
    try:
        service.delete_facs_plate(db, int(data.get("id")))
        return success({"message": "Success"})
    except Exception as exc:
        db.rollback()
        return error(str(exc))
