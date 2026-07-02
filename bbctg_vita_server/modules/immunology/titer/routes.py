from urllib.parse import quote

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from core.response import error, success
from db.session import get_db
from models.immunology import SerumElisaPlate, SerumFacsPlate, SerumFile, SerumImmProject, SerumTiterOrder
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


_TITER_ORDER_BATCH_FIELD_KEYS = (
    "cage_position",
    "blood_collection_date",
    "mouse_count",
    "assay_method",
    "facs_plate_count",
    "elisa_plate_count",
)
_TITER_ORDER_RECORD_FIELD_KEYS = ("test_dates", "serum_status", "remark")


@router.get("/order/meta")
def titer_order_meta(
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
) -> dict:
    require_permission(db, current_user, "serum.page.titer_order")
    return success(service.get_titer_order_page_meta(db))


@router.get("/order/stats")
def titer_order_stats(
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
) -> dict:
    require_permission(db, current_user, "serum.page.titer_order")
    return success(service.get_titer_order_stats(db))


@router.get("/order/owner_stats")
def titer_order_owner_stats(
    month_start: str = "",
    month_end: str = "",
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
) -> dict:
    require_permission(db, current_user, "serum.page.titer_order")
    return success(
        service.get_titer_owner_workload_stats(
            db,
            month_start or None,
            month_end or None,
        )
    )


@router.get("/order/project_options")
def titer_order_project_options(
    keyword: str = "",
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
) -> dict:
    _require_titer_order_form_access(db, current_user)
    return success({"items": service.get_project_options(db, keyword, limit)})


@router.get("/order/batch_preview")
def titer_order_batch_preview(
    experiment_id: str = "",
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
) -> dict:
    _require_titer_order_form_access(db, current_user)
    try:
        return success(service.get_titer_order_batch_preview(db, experiment_id))
    except ValueError as exc:
        return error(str(exc))


@router.post("/order/list")
def titer_order_list(
    data: dict,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
) -> dict:
    require_permission(db, current_user, "serum.page.titer_order")
    return success(service.get_titer_order_list(db, data or {}))


@router.post("/order/save")
def titer_order_save(
    data: dict,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
) -> dict:
    try:
        _validate_titer_order_save(db, current_user, data or {})
        return success(service.save_titer_order(db, data or {}))
    except HTTPException:
        raise
    except Exception as exc:
        db.rollback()
        return error(str(exc))


@router.post("/order/delete")
def titer_order_delete(
    data: dict,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
) -> dict:
    try:
        require_permission(db, current_user, "serum.titer_order.delete")
        order_id = data.get("id")
        if order_id is None or str(order_id).strip() == "":
            raise ValueError("缺少工单 ID")
        service.delete_titer_order(db, int(order_id))
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
    exp_id = str(project.experiment_id or "").strip()
    if exp_id:
        for owners in db.scalars(
            select(SerumTiterOrder.titer_owners).where(SerumTiterOrder.experiment_id == exp_id)
        ).all():
            if _is_titer_owner(user, owners):
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


def _has_payload_keys(data: dict, keys: tuple[str, ...]) -> bool:
    return any(key in data for key in keys)


def _require_titer_order_form_access(db: Session, user: SysUser) -> None:
    if has_permission(db, user, "serum.titer_order.create"):
        return
    if has_permission(db, user, "serum.titer_order.batch.edit"):
        return
    raise HTTPException(
        status_code=403,
        detail=PERMISSION_MESSAGES.get("serum.titer_order.create", DEFAULT_PERMISSION_MESSAGE),
    )


def _is_titer_owner(user: SysUser, owners: object) -> bool:
    aliases = _owner_aliases(user)
    if not isinstance(owners, list):
        return False
    return any(str(owner or "").strip() in aliases for owner in owners)


def _require_titer_order_record_edit(
    db: Session,
    user: SysUser,
    order: SerumTiterOrder,
    project: SerumImmProject | None = None,
) -> None:
    require_permission(db, user, "serum.titer_order.record.edit")
    if has_permission(db, user, "serum.titer_order.record.edit_all"):
        return
    if _is_titer_owner(user, order.titer_owners):
        return
    if project and _is_owner_name(user, project.owner):
        return
    raise HTTPException(
        status_code=403,
        detail=PERMISSION_MESSAGES.get("serum.titer_order.record.edit", DEFAULT_PERMISSION_MESSAGE),
    )


def _require_titer_order_summary_edit(
    db: Session,
    user: SysUser,
    order: SerumTiterOrder,
    project: SerumImmProject | None,
) -> None:
    require_permission(db, user, "serum.titer_order.summary.edit")
    if has_permission(db, user, "serum.titer_order.summary.edit_all"):
        return
    if project and _is_owner_name(user, project.owner):
        return
    raise HTTPException(
        status_code=403,
        detail=PERMISSION_MESSAGES.get("serum.titer_order.summary.edit", DEFAULT_PERMISSION_MESSAGE),
    )


def _validate_titer_order_save(db: Session, user: SysUser, data: dict) -> None:
    order_id = data.get("id")
    order: SerumTiterOrder | None = None
    project: SerumImmProject | None = None

    if order_id is not None and str(order_id).strip() != "":
        order = db.get(SerumTiterOrder, int(order_id))
        if not order:
            raise ValueError("效价工单不存在")
        project = db.scalar(
            select(SerumImmProject).where(SerumImmProject.experiment_id == order.experiment_id)
        )
    else:
        require_permission(db, user, "serum.titer_order.create")

    if order is not None and _has_payload_keys(data, _TITER_ORDER_BATCH_FIELD_KEYS):
        require_permission(db, user, "serum.titer_order.batch.edit")

    if "titer_owners" in data:
        if order is None:
            raise HTTPException(
                status_code=403,
                detail=PERMISSION_MESSAGES.get("serum.titer_order.owner.edit", DEFAULT_PERMISSION_MESSAGE),
            )
        require_permission(db, user, "serum.titer_order.owner.edit")

    if _has_payload_keys(data, _TITER_ORDER_RECORD_FIELD_KEYS):
        if order is None:
            raise HTTPException(
                status_code=403,
                detail=PERMISSION_MESSAGES.get("serum.titer_order.record.edit", DEFAULT_PERMISSION_MESSAGE),
            )
        _require_titer_order_record_edit(db, user, order, project)

    if "summary" in data:
        if order is None:
            raise HTTPException(
                status_code=403,
                detail=PERMISSION_MESSAGES.get("serum.titer_order.summary.edit", DEFAULT_PERMISSION_MESSAGE),
            )
        _require_titer_order_summary_edit(db, user, order, project)
