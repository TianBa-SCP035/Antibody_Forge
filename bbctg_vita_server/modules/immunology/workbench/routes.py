from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from core.response import error, success
from db.session import get_db
from models.system import SysUser
from modules.auth.dependencies import get_current_user
from modules.immunology.serum.routes import require_serum_project_edit_permission
from modules.immunology.workbench import service
from modules.system.permissions import build_user_context, require_permission

router = APIRouter()
WORKBENCH_VIEW_PERMISSION = "serum.page.workbench"
WORKBENCH_EDIT_PERMISSION = "serum.workbench.edit"
WORKBENCH_DRAFT_EDIT_PERMISSION = "serum.workbench.draft_edit"
WORKBENCH_SUPPORT_EDIT_PERMISSION = "serum.workbench.support_edit"


class WorkbenchSaveRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: int | None = Field(default=None, gt=0)


class WorkbenchListRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    view_group: Literal["planned", "ongoing", "completed", "cancelled"] | None = None


class WorkbenchBatchSaveRequest(BaseModel):
    items: list[dict] = Field(min_length=1)


class WorkbenchSchemeSaveRequest(WorkbenchSaveRequest):
    id: int = Field(gt=0)
    scheme_revision: str = Field(min_length=1)
    mouse_groups: list[dict]
    antigens: list[dict]
    steps: list[dict]
    titer_targets: list[dict]
    titer_pcs: list[dict]


class WorkbenchIdRequest(BaseModel):
    id: int = Field(gt=0)


class WorkbenchQueueSnapshot(BaseModel):
    id: int = Field(gt=0)
    sort_order: int = Field(gt=0)
    priority: str


class WorkbenchReorderRequest(BaseModel):
    ids: list[int] = Field(min_length=2)
    moved_id: int = Field(gt=0)
    expected_rows: list[WorkbenchQueueSnapshot] = Field(min_length=2)


def _actor_name(user: SysUser) -> str:
    return (user.display_name or user.username or "").strip()


def _require_edit_scopes(
    db: Session,
    user: SysUser,
    allowed_scopes: set[str],
) -> frozenset[str]:
    context = build_user_context(db, user)
    permission_scopes = {
        WORKBENCH_EDIT_PERMISSION: "full",
        WORKBENCH_DRAFT_EDIT_PERMISSION: "draft",
        WORKBENCH_SUPPORT_EDIT_PERMISSION: "support",
    }
    scopes = frozenset(
        scope
        for permission, scope in permission_scopes.items()
        if context.is_superuser or permission in context.permissions
    )
    if not scopes.intersection(allowed_scopes):
        raise HTTPException(status_code=403, detail="没有权限执行该工作台操作")
    return scopes


def _run_write(db: Session, fn):
    try:
        return success(fn())
    except HTTPException:
        raise
    except PermissionError as exc:
        db.rollback()
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        db.rollback()
        message = str(exc)
        if message == "工作台记录不存在":
            raise HTTPException(status_code=404, detail=message) from exc
        if (
            "不属于当前工作台" in message
            or "已被其他用户修改" in message
            or "队列已变化" in message
        ):
            raise HTTPException(status_code=409, detail=message) from exc
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
    return success(service.get_list(db, data.model_dump() if data else {}))


@router.post("/export_list")
def export_workbench_list(
    data: WorkbenchListRequest | None = None,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
) -> Response:
    from utils.excel import xlsx_response

    require_permission(db, current_user, WORKBENCH_VIEW_PERMISSION)
    output, filename = service.export_list_workbook(
        db,
        data.model_dump() if data else {},
    )
    return xlsx_response(output, filename)


@router.get("/options")
def workbench_options(
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
) -> dict:
    require_permission(db, current_user, WORKBENCH_VIEW_PERMISSION)
    return success(service.get_options(db))


@router.get("/detail")
def workbench_detail(
    id: int = Query(...),
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
) -> dict:
    require_permission(db, current_user, WORKBENCH_VIEW_PERMISSION)
    data = service.get_detail(db, id)
    if data is None:
        raise HTTPException(status_code=404, detail="工作台记录不存在")
    return success(data)


@router.post("/save")
def save_workbench(
    data: WorkbenchSaveRequest,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
) -> dict:
    edit_scopes = _require_edit_scopes(db, current_user, {"full", "draft", "support"})
    payload = data.model_dump()
    return _run_write(
        db,
        lambda: service.save(
            db,
            payload,
            created_by=_actor_name(current_user),
            edit_scopes=edit_scopes,
        ),
    )


@router.post("/save_batch")
def save_workbench_batch(
    data: WorkbenchBatchSaveRequest,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
) -> dict:
    edit_scopes = _require_edit_scopes(db, current_user, {"full", "draft", "support"})
    payload = data.model_dump()
    return _run_write(
        db,
        lambda: service.save_batch(
            db,
            payload,
            created_by=_actor_name(current_user),
            edit_scopes=edit_scopes,
        ),
    )


@router.post("/save_scheme")
def save_workbench_scheme(
    data: WorkbenchSchemeSaveRequest,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
) -> dict:
    edit_scopes = _require_edit_scopes(db, current_user, {"full", "draft"})
    payload = data.model_dump()
    return _run_write(
        db,
        lambda: service.save_scheme(
            db,
            payload,
            created_by=_actor_name(current_user),
            edit_scopes=edit_scopes,
        ),
    )


@router.post("/delete")
def delete_workbench(
    data: WorkbenchIdRequest,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
) -> dict:
    edit_scopes = _require_edit_scopes(db, current_user, {"full", "draft"})

    def _delete():
        service.delete(db, data.id, edit_scopes=edit_scopes)
        return {"message": "删除成功"}

    return _run_write(db, _delete)


@router.post("/start")
def start_workbench(
    data: WorkbenchIdRequest,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
) -> dict:
    _require_edit_scopes(db, current_user, {"full"})
    require_serum_project_edit_permission(db, current_user)

    def _start():
        return service.start(db, data.id)

    return _run_write(db, _start)


@router.post("/unlist")
def unlist_workbench(
    data: WorkbenchIdRequest,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
) -> dict:
    _require_edit_scopes(db, current_user, {"full"})

    def _unlist():
        return service.unlist(db, data.id)

    return _run_write(db, _unlist)


@router.post("/copy")
def copy_workbench(
    data: WorkbenchIdRequest,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
) -> dict:
    edit_scopes = _require_edit_scopes(db, current_user, {"full", "draft"})

    def _copy():
        return service.copy_row(
            db,
            data.id,
            created_by=_actor_name(current_user),
            edit_scopes=edit_scopes,
        )

    return _run_write(db, _copy)


@router.post("/reorder")
def reorder_workbench(
    data: WorkbenchReorderRequest,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
) -> dict:
    edit_scopes = _require_edit_scopes(db, current_user, {"full"})

    def _reorder():
        return service.reorder(
            db,
            data.ids,
            moved_id=data.moved_id,
            expected_rows=[item.model_dump() for item in data.expected_rows],
            edit_scopes=edit_scopes,
        )

    return _run_write(db, _reorder)
