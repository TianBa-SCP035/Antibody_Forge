from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from core.response import error, success
from db.session import get_db
from models.system import SysUser
from modules.auth.dependencies import get_current_user
from modules.discovery.workbench import service
from modules.system.permissions import require_permission

router = APIRouter()
WORKBENCH_VIEW_PERMISSION = "discovery.page.workbench"
WORKBENCH_EDIT_PERMISSION = "discovery.workbench.edit"


class WorkbenchSaveRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: int | None = Field(default=None, gt=0)


class WorkbenchListRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    view_group: Literal["harvest", "library", "sequencing", "cancelled"] | None = None
    boost_filter: Literal["boosting", "need_boost"] | None = None


class WorkbenchBatchSaveRequest(BaseModel):
    items: list[dict] = Field(min_length=1)


class WorkbenchIdRequest(BaseModel):
    id: int = Field(gt=0)


class WorkbenchReorderRequest(BaseModel):
    moved_id: int = Field(gt=0)
    target_id: int = Field(gt=0)


def _actor_name(user: SysUser) -> str:
    return (user.display_name or user.username or "").strip()


def _run_write(db: Session, fn):
    try:
        return success(fn())
    except HTTPException:
        raise
    except ValueError as exc:
        db.rollback()
        message = str(exc)
        if message == service.MISSING_ROW:
            raise HTTPException(status_code=404, detail=message) from exc
        raise HTTPException(status_code=422, detail=message) from exc
    except Exception as exc:
        db.rollback()
        return error(str(exc))


@router.post("/list")
def list_workbench(
    data: WorkbenchListRequest | None = None,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
) -> dict:
    require_permission(db, current_user, WORKBENCH_VIEW_PERMISSION)
    try:
        return success(service.get_list(db, data.model_dump() if data else {}))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/options")
def workbench_options(
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
) -> dict:
    require_permission(db, current_user, WORKBENCH_VIEW_PERMISSION)
    return success(service.get_options(db))


@router.post("/save")
def save_workbench(
    data: WorkbenchSaveRequest,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
) -> dict:
    require_permission(db, current_user, WORKBENCH_EDIT_PERMISSION)
    payload = data.model_dump(exclude_unset=True)
    return _run_write(
        db,
        lambda: service.save(db, payload, created_by=_actor_name(current_user)),
    )


@router.post("/export_list")
def export_workbench_list(
    data: WorkbenchListRequest | None = None,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
) -> Response:
    from utils.excel import xlsx_response

    require_permission(db, current_user, WORKBENCH_VIEW_PERMISSION)
    try:
        output, filename = service.export_list_workbook(
            db,
            data.model_dump() if data else {},
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return xlsx_response(output, filename)


@router.post("/save_batch")
def save_workbench_batch(
    data: WorkbenchBatchSaveRequest,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
) -> dict:
    require_permission(db, current_user, WORKBENCH_EDIT_PERMISSION)
    payload = data.model_dump()
    return _run_write(
        db,
        lambda: service.save_batch(db, payload, created_by=_actor_name(current_user)),
    )


@router.post("/copy")
def copy_workbench(
    data: WorkbenchIdRequest,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
) -> dict:
    require_permission(db, current_user, WORKBENCH_EDIT_PERMISSION)
    return _run_write(
        db,
        lambda: service.copy_row(db, data.id, created_by=_actor_name(current_user)),
    )


@router.post("/delete")
def delete_workbench(
    data: WorkbenchIdRequest,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
) -> dict:
    require_permission(db, current_user, WORKBENCH_EDIT_PERMISSION)

    def _delete():
        service.delete(db, data.id)
        return {"message": "删除成功"}

    return _run_write(db, _delete)


@router.post("/reorder")
def reorder_workbench(
    data: WorkbenchReorderRequest,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
) -> dict:
    require_permission(db, current_user, WORKBENCH_EDIT_PERMISSION)
    return _run_write(
        db,
        lambda: service.reorder(db, data.moved_id, data.target_id),
    )
