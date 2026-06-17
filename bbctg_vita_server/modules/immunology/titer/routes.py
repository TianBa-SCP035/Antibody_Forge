from urllib.parse import quote

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from core.response import error, success
from db.session import get_db
from models.immunology import SerumElisaPlate, SerumFacsPlate, SerumFile, SerumImmProject
from models.system import SysUser
from modules.auth.dependencies import get_current_user
from integrations.drm_service import prepare_office_download_file, remove_temp_file
from modules.immunology.titer import service
from modules.system.permissions import (
    DEFAULT_PERMISSION_MESSAGE,
    PERMISSION_MESSAGES,
    has_permission,
    require_permission,
)

router = APIRouter()

_TITER_READ_PERMISSIONS = ("serum.page.detail", "serum.page.titer")


def _require_titer_read(db: Session, user: SysUser) -> None:
    if any(has_permission(db, user, code) for code in _TITER_READ_PERMISSIONS):
        return
    raise HTTPException(
        status_code=403,
        detail=PERMISSION_MESSAGES.get("serum.page.detail", DEFAULT_PERMISSION_MESSAGE),
    )


@router.post("/file/list")
def file_list(
    data: dict,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
) -> dict:
    _require_titer_read(db, current_user)
    return success({"items": service.get_file_list(db, data.get("experiment_id"))})


@router.post("/file/save")
def file_save(
    file: UploadFile = File(...),
    experiment_id: str = Form(...),
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
) -> dict:
    try:
        require_permission(db, current_user, "serum.file.manage")
        _require_project_owner_or_edit_all(db, current_user, experiment_id=experiment_id)
        return success(service.save_file(db, file, experiment_id, _operator_name(current_user)))
    except HTTPException:
        raise
    except Exception as exc:
        db.rollback()
        return error(str(exc))


@router.post("/file/delete")
def file_delete(
    data: dict,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
) -> dict:
    try:
        require_permission(db, current_user, "serum.file.manage")
        _require_project_owner_or_edit_all(db, current_user, file_id=int(data.get("id")))
        service.delete_file(db, int(data.get("id")))
        return success({"message": "删除成功"})
    except HTTPException:
        raise
    except Exception as exc:
        db.rollback()
        return error(str(exc))


@router.post("/file/rename")
def file_rename(
    data: dict,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
) -> dict:
    try:
        require_permission(db, current_user, "serum.file.manage")
        _require_project_owner_or_edit_all(db, current_user, file_id=int(data.get("id")))
        service.rename_file(db, int(data.get("id")), data.get("new_name"))
        return success({"message": "重命名成功"})
    except HTTPException:
        raise
    except Exception as exc:
        db.rollback()
        return error(str(exc))


@router.post("/file/replace")
def file_replace(
    file: UploadFile = File(...),
    id: int = Form(...),
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
) -> dict:
    try:
        require_permission(db, current_user, "serum.file.manage")
        _require_project_owner_or_edit_all(db, current_user, file_id=id)
        return success(service.replace_file(db, id, file, _operator_name(current_user)))
    except HTTPException:
        raise
    except Exception as exc:
        db.rollback()
        return error(str(exc))


@router.get("/file/download")
def file_download(
    background_tasks: BackgroundTasks,
    id: int = Query(...),
    preview: str | None = None,
    thumb: str | None = None,
    w: int = 400,
    h: int = 400,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    try:
        _require_titer_read(db, current_user)
        record, file_path = service.get_download_record(db, id)
        if thumb and thumb.lower() in {"1", "true"}:
            thumbnail = service.create_thumbnail(file_path, w, h)
            if thumbnail:
                output, media_type = thumbnail
                return StreamingResponse(output, media_type=media_type)

        is_inline_preview = preview == "true"
        serve_path = file_path
        temp_path = None
        if not is_inline_preview:
            serve_path, temp_path = prepare_office_download_file(db, file_path, record.file_name)
            if temp_path is not None:
                background_tasks.add_task(remove_temp_file, temp_path)

        return FileResponse(
            serve_path,
            filename=record.file_name,
            media_type=None,
            headers={"Content-Disposition": f"{'inline' if is_inline_preview else 'attachment'}; filename*=UTF-8''{quote(record.file_name)}"},
        )
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/target/save")
def target_save(
    data: dict,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
) -> dict:
    try:
        require_permission(db, current_user, "serum.titer.edit")
        _require_project_owner_or_edit_all(db, current_user, experiment_id=data.get("experiment_id"))
        return success({"items": service.save_targets(db, data.get("experiment_id"), data.get("targets", []))})
    except HTTPException:
        raise
    except Exception as exc:
        db.rollback()
        return error(str(exc))


@router.post("/pc/save")
def pc_save(
    data: dict,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
) -> dict:
    try:
        require_permission(db, current_user, "serum.titer.edit")
        _require_project_owner_or_edit_all(db, current_user, experiment_id=data.get("experiment_id"))
        return success({"items": service.save_pcs(db, data.get("experiment_id"), data.get("pcs", []))})
    except HTTPException:
        raise
    except Exception as exc:
        db.rollback()
        return error(str(exc))


@router.post("/plate/list")
def plate_list(
    data: dict,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
) -> dict:
    _require_titer_read(db, current_user)
    return success({"items": service.get_facs_plates(db, data.get("experiment_id"))})


@router.post("/plate/save")
def plate_save(
    data: dict,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
) -> dict:
    try:
        require_permission(db, current_user, "serum.titer.edit")
        _require_project_owner_or_edit_all(db, current_user, experiment_id=(data or {}).get("experiment_id"))
        return success(service.save_facs_plate(db, data or {}))
    except HTTPException:
        raise
    except Exception as exc:
        db.rollback()
        return error(str(exc))


@router.post("/plate/delete")
def plate_delete(
    data: dict,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
) -> dict:
    try:
        require_permission(db, current_user, "serum.titer.edit")
        _require_project_owner_or_edit_all(db, current_user, plate_id=int(data.get("id")))
        service.delete_facs_plate(db, int(data.get("id")))
        return success({"message": "删除成功"})
    except HTTPException:
        raise
    except Exception as exc:
        db.rollback()
        return error(str(exc))


@router.post("/elisa/plate/list")
def elisa_plate_list(
    data: dict,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
) -> dict:
    _require_titer_read(db, current_user)
    return success({"items": service.get_elisa_plates(db, data.get("experiment_id"))})


@router.post("/elisa/plate/save")
def elisa_plate_save(
    data: dict,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
) -> dict:
    try:
        require_permission(db, current_user, "serum.titer.edit")
        _require_project_owner_or_edit_all(db, current_user, experiment_id=(data or {}).get("experiment_id"))
        return success(service.save_elisa_plate(db, data or {}))
    except HTTPException:
        raise
    except Exception as exc:
        db.rollback()
        return error(str(exc))


@router.post("/elisa/plate/delete")
def elisa_plate_delete(
    data: dict,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
) -> dict:
    try:
        require_permission(db, current_user, "serum.titer.edit")
        _require_project_owner_or_edit_all(db, current_user, elisa_plate_id=int(data.get("id")))
        service.delete_elisa_plate(db, int(data.get("id")))
        return success({"message": "删除成功"})
    except HTTPException:
        raise
    except Exception as exc:
        db.rollback()
        return error(str(exc))


def _require_project_owner_or_edit_all(
    db: Session,
    user: SysUser,
    *,
    experiment_id: str | None = None,
    file_id: int | None = None,
    plate_id: int | None = None,
    elisa_plate_id: int | None = None,
) -> None:
    project = _resolve_project(
        db,
        experiment_id=experiment_id,
        file_id=file_id,
        plate_id=plate_id,
        elisa_plate_id=elisa_plate_id,
    )
    if not project:
        raise ValueError("项目不存在")
    if _is_owner_name(user, project.owner):
        return
    require_permission(db, user, "serum.titer.edit_all")


def _resolve_project(
    db: Session,
    *,
    experiment_id: str | None = None,
    file_id: int | None = None,
    plate_id: int | None = None,
    elisa_plate_id: int | None = None,
) -> SerumImmProject | None:
    target_experiment_id = experiment_id
    if file_id is not None:
        record = db.get(SerumFile, file_id)
        if not record:
            raise ValueError("文件不存在")
        target_experiment_id = record.experiment_id
    if plate_id is not None:
        plate = db.get(SerumFacsPlate, plate_id)
        if not plate:
            raise ValueError("板数据不存在")
        target_experiment_id = plate.experiment_id
    if elisa_plate_id is not None:
        plate = db.get(SerumElisaPlate, elisa_plate_id)
        if not plate:
            raise ValueError("板数据不存在")
        target_experiment_id = plate.experiment_id
    if not target_experiment_id:
        return None
    return db.scalar(select(SerumImmProject).where(SerumImmProject.experiment_id == target_experiment_id))


def _operator_name(user: SysUser) -> str:
    return (user.display_name or user.username or "unknown").strip()


def _owner_aliases(user: SysUser) -> set[str]:
    values = {user.username, user.display_name, _operator_name(user)}
    aliases = {str(value).strip() for value in values if str(value or "").strip()}
    for value in list(aliases):
        aliases.add(value.split()[0])
    return aliases


def _is_owner_name(user: SysUser, owner: str | None) -> bool:
    owner_name = str(owner or "").strip()
    return bool(owner_name and owner_name in _owner_aliases(user))
