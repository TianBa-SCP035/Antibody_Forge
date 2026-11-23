from typing import Literal

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from core.response import success
from db.session import get_db
from models.system import SysUser
from modules.auth.dependencies import actor_name, get_current_user
from modules.auth.permissions import require
from modules.discovery.workbench import service
from utils.filter_values import DEFAULT_RECORDED_TARGET_LIMIT, MAX_RECORDED_TARGET_LIMIT
from utils.model_fields import fields_request_model

router = APIRouter()
WORKBENCH_VIEW_PERMISSION = "discovery.page.workbench"
WORKBENCH_EDIT_PERMISSION = "discovery.workbench.edit"


WorkbenchFields = fields_request_model("DiscoveryWorkbenchFields", service.FIELDS)


class WorkbenchSaveRequest(WorkbenchFields):
    id: int | None = Field(default=None, gt=0)


class WorkbenchListRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    view_group: Literal["harvest", "library", "sequencing", "cancelled"] | None = None
    boost_filter: Literal["boosting", "missing_date"] | None = None


class WorkbenchColumnValuesRequest(WorkbenchListRequest):
    field: str = Field(min_length=1, max_length=64)
    value_keyword: str = Field(default="", max_length=128)
    value_limit: int = Field(default=200, ge=1, le=1000)
    value_order: Literal["value", "value_desc", "recent"] = "value"


class WorkbenchBatchSaveRequest(BaseModel):
    items: list[WorkbenchFields] = Field(min_length=1)


class WorkbenchIdRequest(BaseModel):
    id: int = Field(gt=0)


class WorkbenchReorderRequest(BaseModel):
    moved_id: int = Field(gt=0)
    target_id: int = Field(gt=0)


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


@router.post("/save", dependencies=[require(WORKBENCH_EDIT_PERMISSION, audit="保存抗体发现工作台")])
def save_workbench(
    data: WorkbenchSaveRequest,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
) -> dict:
    return success(service.save(db, data.model_dump(exclude_unset=True), created_by=actor_name(current_user)))


@router.post("/export_list", dependencies=[require(WORKBENCH_VIEW_PERMISSION)])
def export_workbench_list(
    data: WorkbenchListRequest | None = None,
    db: Session = Depends(get_db),
) -> Response:
    from utils.excel import xlsx_response

    output, filename = service.export_list_workbook(db, data.model_dump() if data else {})
    return xlsx_response(output, filename)


@router.post("/save_batch", dependencies=[require(WORKBENCH_EDIT_PERMISSION, audit="批量保存抗体发现工作台")])
def save_workbench_batch(
    data: WorkbenchBatchSaveRequest,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
) -> dict:
    items = [item.model_dump(exclude_unset=True) for item in data.items]
    return success(service.save_batch(db, {"items": items}, created_by=actor_name(current_user)))


@router.post("/delete", dependencies=[require(WORKBENCH_EDIT_PERMISSION, audit="删除抗体发现工作台")])
def delete_workbench(
    data: WorkbenchIdRequest,
    db: Session = Depends(get_db),
) -> dict:
    service.delete(db, data.id)
    return success({"message": "删除成功"})


@router.post("/reorder", dependencies=[require(WORKBENCH_EDIT_PERMISSION, audit="调整抗体发现工作台排序")])
def reorder_workbench(
    data: WorkbenchReorderRequest,
    db: Session = Depends(get_db),
) -> dict:
    return success(service.reorder(db, data.moved_id, data.target_id))
