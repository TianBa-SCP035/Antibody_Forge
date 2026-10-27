from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from core.response import error, success
from db.session import get_db
from models.system import SysUser
from modules.auth.dependencies import get_current_user
from modules.discovery.synthesis_progress import service
from modules.system.permissions import build_user_context, require_permission

router = APIRouter()
SYNTHESIS_VIEW_PERMISSION = "discovery.page.synthesis_progress"
SYNTHESIS_EDIT_PERMISSION = "discovery.synthesis_progress.edit"
SYNTHESIS_PM_EDIT_PERMISSION = "discovery.synthesis_progress.pm_edit"


class SynthesisSaveRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: int | None = Field(default=None, gt=0)


class SynthesisListRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    view_group: (
        Literal["wait_order", "synthesizing", "assay", "completed", "engineering", "cancelled"]
        | None
    ) = None
    quick_filter: Literal["unassigned", "has_issue"] | None = None


class SynthesisBatchSaveRequest(BaseModel):
    items: list[dict] = Field(min_length=1)


class SynthesisIdRequest(BaseModel):
    id: int = Field(gt=0)


class SynthesisReorderRequest(BaseModel):
    moved_id: int = Field(gt=0)
    target_id: int = Field(gt=0)


class SynthesisAdoptRequest(BaseModel):
    id: int = Field(gt=0)
    fields: list[str] | None = None


class SynthesisCheckRemoteRequest(BaseModel):
    ids: list[int] = Field(default_factory=list)


def _actor_name(user: SysUser) -> str:
    return (user.display_name or user.username or "").strip()


def _require_edit_scopes(
    db: Session,
    user: SysUser,
    allowed_scopes: set[str] | None = None,
) -> frozenset[str]:
    allowed = allowed_scopes or {"full", "pm"}
    context = build_user_context(db, user)
    permission_scopes = {
        SYNTHESIS_EDIT_PERMISSION: "full",
        SYNTHESIS_PM_EDIT_PERMISSION: "pm",
    }
    scopes = frozenset(
        scope
        for permission, scope in permission_scopes.items()
        if context.is_superuser or permission in context.permissions
    )
    if not scopes.intersection(allowed):
        raise HTTPException(status_code=403, detail="没有权限执行该合成与验证操作")
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
        if message == service.MISSING_ROW:
            raise HTTPException(status_code=404, detail=message) from exc
        raise HTTPException(status_code=422, detail=message) from exc
    except Exception as exc:
        db.rollback()
        return error(str(exc))


@router.post("/list")
def list_synthesis_orders(
    data: SynthesisListRequest | None = None,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
) -> dict:
    require_permission(db, current_user, SYNTHESIS_VIEW_PERMISSION)
    try:
        return success(service.get_list(db, data.model_dump() if data else {}))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/options")
def synthesis_options(
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
) -> dict:
    require_permission(db, current_user, SYNTHESIS_VIEW_PERMISSION)
    return success(service.get_options(db))


@router.post("/check_remote")
def check_remote_orders(
    data: SynthesisCheckRemoteRequest,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
) -> dict:
    require_permission(db, current_user, SYNTHESIS_VIEW_PERMISSION)
    return success(service.check_remote_for_local_rows(db, data.ids))


@router.post("/save")
def save_synthesis_order(
    data: SynthesisSaveRequest,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
) -> dict:
    scopes = _require_edit_scopes(db, current_user, {"full", "pm"})
    payload = data.model_dump(exclude_unset=True)
    return _run_write(
        db,
        lambda: service.save(
            db,
            payload,
            created_by=_actor_name(current_user),
            scopes=scopes,
        ),
    )


@router.post("/save_batch")
def save_synthesis_order_batch(
    data: SynthesisBatchSaveRequest,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
) -> dict:
    scopes = _require_edit_scopes(db, current_user, {"full", "pm"})
    payload = data.model_dump()
    return _run_write(
        db,
        lambda: service.save_batch(
            db,
            payload,
            created_by=_actor_name(current_user),
            scopes=scopes,
        ),
    )


@router.post("/claim")
def claim_synthesis_order(
    data: SynthesisIdRequest,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
) -> dict:
    _require_edit_scopes(db, current_user, {"full", "pm"})
    return _run_write(
        db,
        lambda: service.claim_order(db, data.id, _actor_name(current_user)),
    )


@router.post("/reorder")
def reorder_synthesis_orders(
    data: SynthesisReorderRequest,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
) -> dict:
    _require_edit_scopes(db, current_user, {"full", "pm"})
    return _run_write(
        db,
        lambda: service.reorder(db, data.moved_id, data.target_id),
    )


@router.post("/delete")
def delete_synthesis_order(
    data: SynthesisIdRequest,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
) -> dict:
    scopes = _require_edit_scopes(db, current_user, {"full", "pm"})

    def _delete():
        service.delete(db, data.id, scopes=scopes)
        return {"message": "删除成功"}

    return _run_write(db, _delete)


@router.post("/adopt_source")
def adopt_synthesis_source(
    data: SynthesisAdoptRequest,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
) -> dict:
    require_permission(db, current_user, SYNTHESIS_EDIT_PERMISSION)
    return _run_write(
        db,
        lambda: service.adopt_source(db, data.id, data.fields),
    )


@router.post("/sync_now")
def sync_synthesis_orders_now(
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
) -> dict:
    require_permission(db, current_user, SYNTHESIS_EDIT_PERMISSION)
    return _run_write(
        db,
        lambda: service.sync_from_one(db, created_by=_actor_name(current_user)),
    )


@router.post("/export_list")
def export_synthesis_order_list(
    data: SynthesisListRequest | None = None,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
) -> Response:
    from utils.excel import xlsx_response

    require_permission(db, current_user, SYNTHESIS_VIEW_PERMISSION)
    try:
        output, filename = service.export_list_workbook(
            db,
            data.model_dump() if data else {},
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return xlsx_response(output, filename)
