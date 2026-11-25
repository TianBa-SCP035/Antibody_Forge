from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from core.response import success
from db.session import get_db
from models.system import SysUser
from modules.auth.dependencies import actor_name, get_current_user
from modules.auth.permissions import UserContext, get_user_context, require
from modules.discovery.synthesis_progress import order_files, service
from modules.system.audit_routes import audit_quiet
from utils.filter_values import DEFAULT_RECORDED_TARGET_LIMIT, MAX_RECORDED_TARGET_LIMIT
from utils.model_fields import fields_request_model

router = APIRouter()
SYNTHESIS_VIEW_PERMISSION = "discovery.page.synthesis_progress"
SYNTHESIS_EDIT_PERMISSION = "discovery.synthesis_progress.edit"
SYNTHESIS_PM_EDIT_PERMISSION = "discovery.synthesis_progress.pm_edit"
SYNTHESIS_ENG_EDIT_PERMISSION = "discovery.synthesis_progress.eng_edit"
SYNTHESIS_AFFINITY_EDIT_PERMISSION = "discovery.synthesis_progress.affinity_edit"
SYNTHESIS_FLOW_EDIT_PERMISSION = "discovery.synthesis_progress.flow_edit"
PERMISSION_SCOPES = {
    SYNTHESIS_EDIT_PERMISSION: "full",
    SYNTHESIS_PM_EDIT_PERMISSION: "pm",
    SYNTHESIS_ENG_EDIT_PERMISSION: "eng",
    SYNTHESIS_AFFINITY_EDIT_PERMISSION: "affinity",
    SYNTHESIS_FLOW_EDIT_PERMISSION: "flow",
}
ANY_EDIT_PERMISSIONS = tuple(PERMISSION_SCOPES)
CLAIM_PERMISSIONS = (SYNTHESIS_EDIT_PERMISSION, SYNTHESIS_PM_EDIT_PERMISSION)
ARRANGE_PERMISSIONS = (SYNTHESIS_EDIT_PERMISSION, SYNTHESIS_PM_EDIT_PERMISSION, SYNTHESIS_ENG_EDIT_PERMISSION)


SynthesisFields = fields_request_model("SynthesisOrderFields", service.FIELDS)


class SynthesisSaveRequest(SynthesisFields):
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
    items: list[SynthesisFields] = Field(min_length=1)
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


def _user_scopes(context: UserContext) -> frozenset[str]:
    return frozenset(scope for permission, scope in PERMISSION_SCOPES.items() if context.allows(permission))


def _visible(data, scopes: frozenset[str]):
    if "full" in scopes:
        return data
    return service.mask_synthetic_corp(data, keep_engineering_rows="eng" in scopes)


def _save_confirming(db: Session, fn, scopes: frozenset[str]) -> dict:
    """保存会让整单完成时先回滚，返回 needs_confirm 让前端弹确认，用户确认后带 confirm_complete 重提。"""
    try:
        return success(_visible(fn(), scopes))
    except service.CompletionConfirmRequired as exc:
        db.rollback()
        return success({"needs_confirm": True, "message": str(exc)})


@router.post("/list", dependencies=[require(SYNTHESIS_VIEW_PERMISSION)])
def list_synthesis_orders(
    data: SynthesisListRequest | None = None,
    db: Session = Depends(get_db),
    context: UserContext = Depends(get_user_context),
) -> dict:
    scopes = _user_scopes(context)
    payload = data.model_dump() if data else {}
    result = service.get_list(
        db,
        payload if "full" in scopes else service.without_corp_query(payload),
        include_cancelled=service.sees_cancelled(scopes),
    )
    return success(_visible(result, scopes))


@router.post("/column_values", dependencies=[require(SYNTHESIS_VIEW_PERMISSION)])
def synthesis_column_values(
    data: SynthesisColumnValuesRequest,
    db: Session = Depends(get_db),
    context: UserContext = Depends(get_user_context),
) -> dict:
    scopes = _user_scopes(context)
    payload = data.model_dump()
    if "full" not in scopes:
        if payload["field"] == "synthetic_corp":
            raise HTTPException(status_code=403, detail="没有权限查看合成公司")
        payload = service.without_corp_query(payload)
    return success(service.get_column_values(db, payload, include_cancelled=service.sees_cancelled(scopes)))


@router.get("/options", dependencies=[require(SYNTHESIS_VIEW_PERMISSION)])
def synthesis_options(
    db: Session = Depends(get_db),
    context: UserContext = Depends(get_user_context),
) -> dict:
    options = service.get_options(db)
    if not _user_scopes(context).intersection({"full", "eng"}):
        options["synthetic_corps"] = []
    return success(options)


@router.get("/recorded_targets", dependencies=[require(SYNTHESIS_VIEW_PERMISSION)])
def synthesis_recorded_targets(
    keyword: str = Query(default="", max_length=128),
    limit: int = Query(default=DEFAULT_RECORDED_TARGET_LIMIT, ge=1, le=MAX_RECORDED_TARGET_LIMIT),
    db: Session = Depends(get_db),
) -> dict:
    return success({"items": service.search_recorded_targets(db, keyword, limit)})


@router.post(
    "/check_remote",
    dependencies=[require(SYNTHESIS_VIEW_PERMISSION), audit_quiet("核对外部合成订单", "synthesis_progress")],
)
def check_remote_orders(
    data: SynthesisCheckRemoteRequest,
    db: Session = Depends(get_db),
    context: UserContext = Depends(get_user_context),
) -> dict:
    result = service.check_remote_for_local_rows(db, data.ids)
    return success(_visible(result, _user_scopes(context)))


@router.post("/save", dependencies=[require(*ANY_EDIT_PERMISSIONS, audit="保存合成与验证单")])
def save_synthesis_order(
    data: SynthesisSaveRequest,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
    context: UserContext = Depends(get_user_context),
) -> dict:
    scopes = _user_scopes(context)
    payload = data.model_dump(exclude_unset=True)
    confirm_complete = bool(payload.pop("confirm_complete", False))
    return _save_confirming(
        db,
        lambda: service.save(
            db,
            payload,
            created_by=actor_name(current_user),
            scopes=scopes,
            require_fields=True,
            confirm_complete=confirm_complete,
        ),
        scopes,
    )


@router.post("/save_batch", dependencies=[require(*ANY_EDIT_PERMISSIONS, audit="批量保存合成与验证单")])
def save_synthesis_order_batch(
    data: SynthesisBatchSaveRequest,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
    context: UserContext = Depends(get_user_context),
) -> dict:
    scopes = _user_scopes(context)
    payload = {"items": [item.model_dump(exclude_unset=True) for item in data.items]}
    return _save_confirming(
        db,
        lambda: service.save_batch(
            db,
            payload,
            created_by=actor_name(current_user),
            scopes=scopes,
            require_fields=True,
            confirm_complete=data.confirm_complete,
        ),
        scopes,
    )


@router.post("/claim", dependencies=[require(*CLAIM_PERMISSIONS, audit="认领合成与验证结果")])
def claim_synthesis_order(
    data: SynthesisIdRequest,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
    context: UserContext = Depends(get_user_context),
) -> dict:
    scopes = _user_scopes(context)
    return success(_visible(service.claim_order(db, data.id, actor_name(current_user), scopes=scopes), scopes))


@router.post("/reorder", dependencies=[require(*ARRANGE_PERMISSIONS, audit="调整合成与验证排序")])
def reorder_synthesis_orders(
    data: SynthesisReorderRequest,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
    context: UserContext = Depends(get_user_context),
) -> dict:
    scopes = _user_scopes(context)
    result = service.reorder(db, data.moved_id, data.target_id, scopes=scopes, actor_name=actor_name(current_user))
    return success(_visible(result, scopes))


@router.post("/delete", dependencies=[require(*ARRANGE_PERMISSIONS, audit="删除合成与验证单")])
def delete_synthesis_order(
    data: SynthesisIdRequest,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
    context: UserContext = Depends(get_user_context),
) -> dict:
    service.delete(db, data.id, scopes=_user_scopes(context), actor_name=actor_name(current_user))
    return success({"message": "删除成功"})


@router.post("/adopt_source", dependencies=[require(SYNTHESIS_EDIT_PERMISSION, audit="采用合成与验证外部来源变更")])
def adopt_synthesis_source(
    data: SynthesisAdoptRequest,
    db: Session = Depends(get_db),
) -> dict:
    return success(service.adopt_source(db, data.id, data.fields))


@router.post("/sync_now", dependencies=[require(SYNTHESIS_EDIT_PERMISSION, audit="同步外部合成订单")])
def sync_synthesis_orders_now(
    db: Session = Depends(get_db),
) -> dict:
    return success(service.sync_from_one(db))


@router.post("/export_list", dependencies=[require(SYNTHESIS_VIEW_PERMISSION)])
def export_synthesis_order_list(
    data: SynthesisListRequest | None = None,
    db: Session = Depends(get_db),
    context: UserContext = Depends(get_user_context),
) -> Response:
    from utils.excel import xlsx_response

    scopes = _user_scopes(context)
    hide_corp = "full" not in scopes
    payload = data.model_dump() if data else {}
    output, filename = service.export_list_workbook(
        db,
        service.without_corp_query(payload) if hide_corp else payload,
        hide_corp=hide_corp,
        keep_engineering_rows="eng" in scopes,
        include_cancelled=service.sees_cancelled(scopes),
    )
    return xlsx_response(output, filename)


@router.get("/transfection_pairs", dependencies=[require(SYNTHESIS_VIEW_PERMISSION)])
def synthesis_transfection_pairs(
    id: int = Query(gt=0),
    db: Session = Depends(get_db),
) -> dict:
    return success(order_files.transfection_pairs(db, id))


@router.get("/plate_layout", dependencies=[require(SYNTHESIS_VIEW_PERMISSION)])
def synthesis_plate_layout(
    id: int = Query(gt=0),
    db: Session = Depends(get_db),
) -> Response:
    from utils.excel import xlsx_response

    output, filename = order_files.export_plate_layout(db, id)
    return xlsx_response(output, filename)


@router.get("/plate_layout/preview", dependencies=[require(SYNTHESIS_VIEW_PERMISSION)])
def synthesis_plate_layout_preview(
    id: int = Query(gt=0),
    db: Session = Depends(get_db),
) -> dict:
    return success(order_files.plate_layout_preview(db, id))


@router.post(
    "/plate_layout/query",
    dependencies=[require(SYNTHESIS_VIEW_PERMISSION), audit_quiet("向合成公司查询上清板布局", "synthesis_progress")],
)
def synthesis_plate_layout_query(
    id: int = Query(gt=0),
    db: Session = Depends(get_db),
    context: UserContext = Depends(get_user_context),
) -> dict:
    return success(_visible(order_files.query_plate_layout(db, id), _user_scopes(context)))
