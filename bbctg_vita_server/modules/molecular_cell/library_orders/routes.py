from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, Response, StreamingResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session
from urllib.parse import quote

from core.response import error, success
from db.session import get_db
from models.system import SysUser
from modules.auth.dependencies import get_current_user
from modules.molecular_cell.library_orders import service
from modules.system.permissions import (
    DEFAULT_PERMISSION_MESSAGE,
    PERMISSION_MESSAGES,
    has_any_permission,
    require_permission,
)
from integrations.drm_service import prepare_office_download_file, remove_temp_file

router = APIRouter()
PAGE_PERMISSION = "molecular.page.library"
EDIT_PERMISSION = "molecular.library.edit"
DETAIL_PERMISSION = "molecular.page.library_detail"
FILE_PERMISSION = "molecular.library.file.manage"
QC_CONCLUSION_FIELDS = {"qc_result", "qc_owner", "qc_on", "qc_note"}
HANDOFF_PERMISSIONS = ("discovery.workbench.edit", EDIT_PERMISSION)


class OrderSaveRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: int | None = Field(default=None, gt=0)


class OrderUpdateItem(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: int = Field(gt=0)


class OrderBatchSaveRequest(BaseModel):
    items: list[OrderUpdateItem] = Field(min_length=1, max_length=service.MAX_BATCH_SAVE_ITEMS)


class OrderListRequest(BaseModel):
    model_config = ConfigDict(extra="allow")


class OrderIdRequest(BaseModel):
    id: int = Field(gt=0)


class HandoffRequest(BaseModel):
    discovery_workbench_id: int | None = Field(default=None, gt=0)
    discovery_id: str | None = None
    items: list[dict] = Field(min_length=1)


class FileListRequest(BaseModel):
    order_id: int = Field(gt=0)


class FileDeleteRequest(BaseModel):
    link_id: int = Field(gt=0)
    order_id: int | None = Field(default=None, gt=0)


class FileUpdateRequest(BaseModel):
    link_id: int = Field(gt=0)
    order_id: int = Field(gt=0)
    original_name: str | None = Field(default=None, max_length=255)
    is_final_qc: bool | None = None
    qc_regions: list[dict[str, float | str]] | None = None


def _actor_name(user: SysUser) -> str:
    return (user.display_name or user.username or "").strip()


def _is_qc_conclusion_only(payload: dict) -> bool:
    changed = set(payload) - {"id"}
    return bool(changed) and changed <= QC_CONCLUSION_FIELDS


def _require_any(db: Session, user: SysUser, codes: tuple[str, ...]) -> None:
    if has_any_permission(db, user, codes):
        return
    raise HTTPException(
        status_code=403,
        detail=PERMISSION_MESSAGES.get(codes[0], DEFAULT_PERMISSION_MESSAGE),
    )


def _require_handoff_permission(db: Session, user: SysUser) -> None:
    if has_any_permission(db, user, HANDOFF_PERMISSIONS):
        return
    raise HTTPException(
        status_code=403,
        detail=PERMISSION_MESSAGES.get(EDIT_PERMISSION, DEFAULT_PERMISSION_MESSAGE),
    )


def _run_write(db: Session, fn):
    try:
        return success(fn())
    except HTTPException:
        raise
    except ValueError as exc:
        db.rollback()
        message = str(exc)
        if message in {service.MISSING_ROW, service.MISSING_FILE, service.MISSING_DISCOVERY}:
            raise HTTPException(status_code=404, detail=message) from exc
        raise HTTPException(status_code=422, detail=message) from exc
    except Exception as exc:
        db.rollback()
        return error(str(exc))


@router.get("/meta")
def meta(
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
) -> dict:
    require_permission(db, current_user, PAGE_PERMISSION)
    return success(service.get_meta())


@router.post("/list")
def list_orders(
    data: OrderListRequest | None = None,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
) -> dict:
    require_permission(db, current_user, PAGE_PERMISSION)
    try:
        return success(service.get_list(db, data.model_dump() if data else {}))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/by-discovery")
def by_discovery(
    discovery_workbench_id: int | None = Query(default=None),
    discovery_id: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
) -> dict:
    _require_handoff_permission(db, current_user)
    try:
        return success(
            service.list_by_discovery(
                db,
                discovery_id=discovery_id,
                discovery_workbench_id=discovery_workbench_id,
            )
        )
    except ValueError as exc:
        message = str(exc)
        if message == service.MISSING_DISCOVERY:
            raise HTTPException(status_code=404, detail=message) from exc
        raise HTTPException(status_code=422, detail=message) from exc


@router.post("/save")
def save_order(
    data: OrderSaveRequest,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
) -> dict:
    payload = data.model_dump(exclude_unset=True)
    if data.id is not None and _is_qc_conclusion_only(payload):
        _require_any(db, current_user, (EDIT_PERMISSION, FILE_PERMISSION))
    else:
        require_permission(db, current_user, EDIT_PERMISSION)
    return _run_write(db, lambda: service.save(db, payload, created_by=_actor_name(current_user)))


@router.post("/batch_save")
def batch_save_orders(
    data: OrderBatchSaveRequest,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
) -> dict:
    payloads = [item.model_dump(exclude_unset=True) for item in data.items]
    if all(_is_qc_conclusion_only(payload) for payload in payloads):
        _require_any(db, current_user, (EDIT_PERMISSION, FILE_PERMISSION))
    else:
        require_permission(db, current_user, EDIT_PERMISSION)
    return _run_write(db, lambda: service.batch_save(db, payloads))


@router.post("/export_list")
def export_orders(
    data: OrderListRequest | None = None,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
) -> Response:
    from utils.excel import xlsx_response

    require_permission(db, current_user, PAGE_PERMISSION)
    try:
        output, filename = service.export_list_workbook(db, data.model_dump() if data else {})
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return xlsx_response(output, filename)


@router.post("/handoff")
def handoff(
    data: HandoffRequest,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
) -> dict:
    _require_handoff_permission(db, current_user)
    return _run_write(db, lambda: service.handoff(db, data.model_dump(), created_by=_actor_name(current_user)))


@router.post("/delete")
def delete_order(
    data: OrderIdRequest,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
) -> dict:
    require_permission(db, current_user, EDIT_PERMISSION)
    return _run_write(db, lambda: service.delete_order(db, data.id))


@router.post("/files/list")
def file_list(
    data: FileListRequest,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
) -> dict:
    require_permission(db, current_user, DETAIL_PERMISSION)
    try:
        return success(service.list_files(db, data.order_id))
    except ValueError as exc:
        message = str(exc)
        if message == service.MISSING_ROW:
            raise HTTPException(status_code=404, detail=message) from exc
        raise HTTPException(status_code=422, detail=message) from exc


@router.post("/files/upload")
def file_upload(
    file: UploadFile = File(...),
    order_id: int = Form(...),
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
) -> dict:
    require_permission(db, current_user, FILE_PERMISSION)
    return _run_write(
        db,
        lambda: service.upload_file(
            db,
            file,
            order_id,
            _actor_name(current_user),
        ),
    )


@router.post("/files/delete")
def file_delete(
    data: FileDeleteRequest,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
) -> dict:
    require_permission(db, current_user, FILE_PERMISSION)
    return _run_write(db, lambda: service.delete_file(db, data.link_id, data.order_id))


@router.post("/files/update")
def file_update(
    data: FileUpdateRequest,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
) -> dict:
    require_permission(db, current_user, FILE_PERMISSION)
    payload = data.model_dump(exclude_unset=True)
    return _run_write(
        db,
        lambda: service.update_file_link(
            db,
            data.link_id,
            data.order_id,
            payload,
        ),
    )


@router.get("/files/download")
def file_download(
    background_tasks: BackgroundTasks,
    id: int = Query(...),
    preview: str | None = None,
    thumb: str | None = None,
    w: int = Query(default=400, ge=32, le=1600),
    h: int = Query(default=400, ge=32, le=1600),
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
):
    require_permission(db, current_user, DETAIL_PERMISSION)
    try:
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
            serve_path, temp_path = prepare_office_download_file(db, file_path, record.original_name)
            if temp_path is not None:
                background_tasks.add_task(remove_temp_file, temp_path)
        return FileResponse(
            serve_path,
            filename=record.original_name,
            media_type=None,
            headers={
                "Content-Disposition": (
                    f"{'inline' if is_inline_preview else 'attachment'}; "
                    f"filename*=UTF-8''{quote(record.original_name)}"
                )
            },
        )
    except ValueError as exc:
        message = str(exc)
        if message == service.MISSING_FILE:
            raise HTTPException(status_code=404, detail=message) from exc
        raise HTTPException(status_code=422, detail=message) from exc
