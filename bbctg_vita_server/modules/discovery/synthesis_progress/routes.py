from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from core.errors import route_error
from core.response import success
from db.session import get_db
from models.system import SysUser
from modules.auth.dependencies import get_current_user
from modules.discovery.synthesis_progress import service
from modules.system.permissions import build_user_context, require_permission
from utils.filter_values import DEFAULT_RECORDED_TARGET_LIMIT, MAX_RECORDED_TARGET_LIMIT

router = APIRouter()
SYNTHESIS_VIEW_PERMISSION = "discovery.page.synthesis_progress"
SYNTHESIS_EDIT_PERMISSION = "discovery.synthesis_progress.edit"
SYNTHESIS_PM_EDIT_PERMISSION = "discovery.synthesis_progress.pm_edit"
SYNTHESIS_ENG_EDIT_PERMISSION = "discovery.synthesis_progress.eng_edit"
SYNTHESIS_AFFINITY_EDIT_PERMISSION = "discovery.synthesis_progress.affinity_edit"
SYNTHESIS_FLOW_EDIT_PERMISSION = "discovery.synthesis_progress.flow_edit"
ALL_EDIT_SCOPES = {"full", "pm", "eng", "affinity", "flow"}
PERMISSION_SCOPES = {
    SYNTHESIS_EDIT_PERMISSION: "full",
    SYNTHESIS_PM_EDIT_PERMISSION: "pm",
    SYNTHESIS_ENG_EDIT_PERMISSION: "eng",
    SYNTHESIS_AFFINITY_EDIT_PERMISSION: "affinity",
    SYNTHESIS_FLOW_EDIT_PERMISSION: "flow",
}


class SynthesisSaveRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: int | None = Field(default=None, gt=0)


class SynthesisListRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    view_group: (
        Literal["wait_order", "synthesizing", "assay", "completed", "engineering", "cancelled"]
        | None
    ) = None
    quick_filter: Literal["unassigned", "has_drift"] | None = None


class SynthesisColumnValuesRequest(SynthesisListRequest):
    field: str = Field(min_length=1, max_length=64)
    value_keyword: str = Field(default="", max_length=128)
    value_limit: int = Field(default=200, ge=1, le=1000)
    value_order: Literal["value", "value_desc", "recent"] = "value"


class SynthesisBatchSaveRequest(BaseModel):
    items: list[dict] = Field(min_length=1)
    confirm_complete: bool = False


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


def _user_scopes(db: Session, user: SysUser) -> frozenset[str]:
    context = build_user_context(db, user)
    return frozenset(
        scope
        for permission, scope in PERMISSION_SCOPES.items()
        if context.is_superuser or permission in context.permissions
    )


def _require_edit_scopes(
    db: Session,
    user: SysUser,
    allowed_scopes: set[str] | None = None,
) -> frozenset[str]:
    scopes = _user_scopes(db, user)
    if not scopes.intersection(allowed_scopes or ALL_EDIT_SCOPES):
        raise HTTPException(status_code=403, detail="没有权限执行该合成与验证操作")
    return scopes


def _visible(data, scopes: frozenset[str]):
    if "full" in scopes:
        return data
    return service.mask_synthetic_corp(data, keep_engineering_rows="eng" in scopes)


def _run_write(db: Session, fn, *, scopes: frozenset[str] = frozenset({"full"})):
    try:
        return success(_visible(fn(), scopes))
    except HTTPException:
        raise
    except service.CompletionConfirmRequired as exc:
        db.rollback()
        return success({"needs_confirm": True, "message": str(exc)})
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
        return route_error(exc, db)


@router.post("/list")
def list_synthesis_orders(
    data: SynthesisListRequest | None = None,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
) -> dict:
    require_permission(db, current_user, SYNTHESIS_VIEW_PERMISSION)
    scopes = _user_scopes(db, current_user)
    payload = data.model_dump() if data else {}
    try:
        result = service.get_list(db, payload if "full" in scopes else service.without_corp_query(payload))
        return success(_visible(result, scopes))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/column_values")
def synthesis_column_values(
    data: SynthesisColumnValuesRequest,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
) -> dict:
    require_permission(db, current_user, SYNTHESIS_VIEW_PERMISSION)
    payload = data.model_dump()
    if "full" not in _user_scopes(db, current_user):
        if payload["field"] == "synthetic_corp":
            raise HTTPException(status_code=403, detail="没有权限查看合成公司")
        payload = service.without_corp_query(payload)
    try:
        return success(service.get_column_values(db, payload))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/options")
def synthesis_options(
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
) -> dict:
    require_permission(db, current_user, SYNTHESIS_VIEW_PERMISSION)
    options = service.get_options(db)
    if not _user_scopes(db, current_user).intersection({"full", "eng"}):
        options["synthetic_corps"] = []
    return success(options)


@router.get("/recorded_targets")
def synthesis_recorded_targets(
    keyword: str = Query(default="", max_length=128),
    limit: int = Query(default=DEFAULT_RECORDED_TARGET_LIMIT, ge=1, le=MAX_RECORDED_TARGET_LIMIT),
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
) -> dict:
    require_permission(db, current_user, SYNTHESIS_VIEW_PERMISSION)
    return success({"items": service.search_recorded_targets(db, keyword, limit)})


@router.post("/check_remote")
def check_remote_orders(
    data: SynthesisCheckRemoteRequest,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
) -> dict:
    require_permission(db, current_user, SYNTHESIS_VIEW_PERMISSION)
    result = service.check_remote_for_local_rows(db, data.ids)
    return success(_visible(result, _user_scopes(db, current_user)))


@router.post("/save")
def save_synthesis_order(
    data: SynthesisSaveRequest,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
) -> dict:
    scopes = _require_edit_scopes(db, current_user, ALL_EDIT_SCOPES)
    payload = data.model_dump(exclude_unset=True)
    confirm_complete = bool(payload.pop("confirm_complete", False))
    return _run_write(
        db,
        lambda: service.save(
            db,
            payload,
            created_by=_actor_name(current_user),
            scopes=scopes,
            require_fields=True,
            confirm_complete=confirm_complete,
        ),
        scopes=scopes,
    )


@router.post("/save_batch")
def save_synthesis_order_batch(
    data: SynthesisBatchSaveRequest,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
) -> dict:
    scopes = _require_edit_scopes(db, current_user, ALL_EDIT_SCOPES)
    payload = data.model_dump()
    return _run_write(
        db,
        lambda: service.save_batch(
            db,
            payload,
            created_by=_actor_name(current_user),
            scopes=scopes,
            require_fields=True,
            confirm_complete=data.confirm_complete,
        ),
        scopes=scopes,
    )


@router.post("/claim")
def claim_synthesis_order(
    data: SynthesisIdRequest,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
) -> dict:
    scopes = _require_edit_scopes(db, current_user, {"full", "pm"})
    return _run_write(
        db,
        lambda: service.claim_order(db, data.id, _actor_name(current_user), scopes=scopes),
        scopes=scopes,
    )


@router.post("/reorder")
def reorder_synthesis_orders(
    data: SynthesisReorderRequest,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
) -> dict:
    scopes = _require_edit_scopes(db, current_user, {"full", "pm", "eng"})
    return _run_write(
        db,
        lambda: service.reorder(
            db, data.moved_id, data.target_id, scopes=scopes, actor_name=_actor_name(current_user)
        ),
        scopes=scopes,
    )


@router.post("/delete")
def delete_synthesis_order(
    data: SynthesisIdRequest,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
) -> dict:
    scopes = _require_edit_scopes(db, current_user, {"full", "pm", "eng"})

    def _delete():
        service.delete(db, data.id, scopes=scopes, actor_name=_actor_name(current_user))
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
        lambda: service.sync_from_one(db),
    )


@router.post("/export_list")
def export_synthesis_order_list(
    data: SynthesisListRequest | None = None,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
) -> Response:
    from utils.excel import xlsx_response

    require_permission(db, current_user, SYNTHESIS_VIEW_PERMISSION)
    scopes = _user_scopes(db, current_user)
    hide_corp = "full" not in scopes
    payload = data.model_dump() if data else {}
    try:
        output, filename = service.export_list_workbook(
            db,
            service.without_corp_query(payload) if hide_corp else payload,
            hide_corp=hide_corp,
            keep_engineering_rows="eng" in scopes,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return xlsx_response(output, filename)
