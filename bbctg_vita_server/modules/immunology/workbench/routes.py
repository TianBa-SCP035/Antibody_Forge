from typing import Literal

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from core.errors import NotFoundError
from core.response import success
from db.session import get_db
from models.system import SysUser
from modules.auth.dependencies import actor_name, get_current_user
from modules.auth.permissions import UserContext, get_user_context, require
from modules.immunology.workbench import service
from utils.filter_values import DEFAULT_RECORDED_TARGET_LIMIT, MAX_RECORDED_TARGET_LIMIT
from utils.model_fields import fields_request_model

router = APIRouter()
WORKBENCH_VIEW_PERMISSION = "serum.page.workbench"
WORKBENCH_EDIT_PERMISSION = "serum.workbench.edit"
WORKBENCH_DRAFT_EDIT_PERMISSION = "serum.workbench.draft_edit"
WORKBENCH_SUPPORT_EDIT_PERMISSION = "serum.workbench.support_edit"
PERMISSION_SCOPES = {
    WORKBENCH_EDIT_PERMISSION: "full",
    WORKBENCH_DRAFT_EDIT_PERMISSION: "draft",
    WORKBENCH_SUPPORT_EDIT_PERMISSION: "support",
}
ROW_EDIT_PERMISSIONS = tuple(PERMISSION_SCOPES)
DRAFT_EDIT_PERMISSIONS = (WORKBENCH_EDIT_PERMISSION, WORKBENCH_DRAFT_EDIT_PERMISSION)


WorkbenchFields = fields_request_model("SerumWorkbenchFields", service.FIELDS)


class WorkbenchSaveRequest(WorkbenchFields):
    id: int | None = Field(default=None, gt=0)


class WorkbenchListRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    view_group: Literal["planned", "ongoing", "completed", "cancelled"] | None = None


class WorkbenchColumnValuesRequest(WorkbenchListRequest):
    field: str = Field(min_length=1, max_length=64)
    value_keyword: str = Field(default="", max_length=128)
    value_limit: int = Field(default=200, ge=1, le=1000)
    value_order: Literal["value", "value_desc", "recent"] = "value"


class WorkbenchBatchSaveRequest(BaseModel):
    items: list[WorkbenchFields] = Field(min_length=1)


class WorkbenchSchemeSaveRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: int = Field(gt=0)
    scheme_revision: str = Field(min_length=1)
    mouse_groups: list[dict]
    antigens: list[dict]
    steps: list[dict]
    titer_targets: list[dict]
    titer_pcs: list[dict]


class WorkbenchIdRequest(BaseModel):
    id: int = Field(gt=0)


class WorkbenchReorderRequest(BaseModel):
    moved_id: int = Field(gt=0)
    target_id: int = Field(gt=0)


def _edit_scopes(context: UserContext) -> frozenset[str]:
    return frozenset(scope for permission, scope in PERMISSION_SCOPES.items() if context.allows(permission))


@router.post("/list", dependencies=[require(WORKBENCH_VIEW_PERMISSION)])
def list_workbench(
    data: WorkbenchListRequest | None = None,
    db: Session = Depends(get_db),
) -> dict:
    return success(service.get_list(db, data.model_dump() if data else {}))


@router.post("/column_values", dependencies=[require(WORKBENCH_VIEW_PERMISSION)])
def workbench_column_values(
    data: WorkbenchColumnValuesRequest,
    db: Session = Depends(get_db),
) -> dict:
    return success(service.get_column_values(db, data.model_dump()))


@router.post("/export_list", dependencies=[require(WORKBENCH_VIEW_PERMISSION)])
def export_workbench_list(
    data: WorkbenchListRequest | None = None,
    db: Session = Depends(get_db),
) -> Response:
    from utils.excel import xlsx_response

    output, filename = service.export_list_workbook(
        db,
        data.model_dump() if data else {},
    )
    return xlsx_response(output, filename)


@router.get("/options", dependencies=[require(WORKBENCH_VIEW_PERMISSION)])
def workbench_options(
    db: Session = Depends(get_db),
) -> dict:
    return success(service.get_options(db))


@router.get("/recorded_targets", dependencies=[require(WORKBENCH_VIEW_PERMISSION)])
def workbench_recorded_targets(
    keyword: str = Query(default="", max_length=128),
    limit: int = Query(default=DEFAULT_RECORDED_TARGET_LIMIT, ge=1, le=MAX_RECORDED_TARGET_LIMIT),
    db: Session = Depends(get_db),
) -> dict:
    return success({"items": service.search_recorded_targets(db, keyword, limit)})


@router.get("/detail", dependencies=[require(WORKBENCH_VIEW_PERMISSION)])
def workbench_detail(
    id: int = Query(...),
    db: Session = Depends(get_db),
) -> dict:
    data = service.get_detail(db, id)
    if data is None:
        raise NotFoundError(service.MISSING_ROW)
    return success(data)


@router.post("/save", dependencies=[require(*ROW_EDIT_PERMISSIONS, audit="保存免疫工作台")])
def save_workbench(
    data: WorkbenchSaveRequest,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
    context: UserContext = Depends(get_user_context),
) -> dict:
    edit_scopes = _edit_scopes(context)
    return success(
        service.save(
            db,
            data.model_dump(exclude_unset=True),
            created_by=actor_name(current_user),
            edit_scopes=edit_scopes,
        )
    )


@router.post("/save_batch", dependencies=[require(*ROW_EDIT_PERMISSIONS, audit="批量保存免疫工作台")])
def save_workbench_batch(
    data: WorkbenchBatchSaveRequest,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
    context: UserContext = Depends(get_user_context),
) -> dict:
    edit_scopes = _edit_scopes(context)
    return success(
        service.save_batch(
            db,
            {"items": [item.model_dump(exclude_unset=True) for item in data.items]},
            created_by=actor_name(current_user),
            edit_scopes=edit_scopes,
        )
    )


@router.post("/save_scheme", dependencies=[require(*DRAFT_EDIT_PERMISSIONS, audit="保存免疫工作台方案草稿")])
def save_workbench_scheme(
    data: WorkbenchSchemeSaveRequest,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
    context: UserContext = Depends(get_user_context),
) -> dict:
    edit_scopes = _edit_scopes(context)
    return success(
        service.save_scheme(
            db,
            data.model_dump(),
            created_by=actor_name(current_user),
            edit_scopes=edit_scopes,
        )
    )


@router.post("/delete", dependencies=[require(*DRAFT_EDIT_PERMISSIONS, audit="删除免疫工作台")])
def delete_workbench(
    data: WorkbenchIdRequest,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
    context: UserContext = Depends(get_user_context),
) -> dict:
    service.delete(db, data.id, edit_scopes=_edit_scopes(context))
    return success({"message": "删除成功"})


@router.post(
    "/start",
    dependencies=[
        require(WORKBENCH_EDIT_PERMISSION, audit="免疫工作台记录开展为实验"),
        require("serum.project.edit", "serum.project.edit_all"),
    ],
)
def start_workbench(
    data: WorkbenchIdRequest,
    db: Session = Depends(get_db),
) -> dict:
    return success(service.start(db, data.id))


@router.post("/unlist", dependencies=[require(WORKBENCH_EDIT_PERMISSION, audit="免疫工作台记录下架撤回实验")])
def unlist_workbench(
    data: WorkbenchIdRequest,
    db: Session = Depends(get_db),
) -> dict:
    return success(service.unlist(db, data.id))


@router.post("/copy", dependencies=[require(*DRAFT_EDIT_PERMISSIONS, audit="复制免疫工作台记录")])
def copy_workbench(
    data: WorkbenchIdRequest,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
    context: UserContext = Depends(get_user_context),
) -> dict:
    return success(
        service.copy_row(
            db,
            data.id,
            created_by=actor_name(current_user),
            edit_scopes=_edit_scopes(context),
        )
    )


@router.post("/reorder", dependencies=[require(WORKBENCH_EDIT_PERMISSION, audit="免疫工作台同优先级排序")])
def reorder_workbench(
    data: WorkbenchReorderRequest,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
    context: UserContext = Depends(get_user_context),
) -> dict:
    return success(service.reorder(db, data.moved_id, data.target_id, edit_scopes=_edit_scopes(context)))
