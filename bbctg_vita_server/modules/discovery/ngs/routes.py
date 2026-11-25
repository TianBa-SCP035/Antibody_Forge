from typing import Literal

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from core.response import success
from db.session import get_db
from models.system import SysUser
from modules.auth.dependencies import actor_name, get_current_user
from modules.auth.permissions import UserContext, get_user_context, require
from modules.discovery.ngs import service
from modules.molecular_cell.permissions import library_type_scope
from utils.excel import xlsx_response
from utils.filter_values import DEFAULT_RECORDED_TARGET_LIMIT, MAX_RECORDED_TARGET_LIMIT
from utils.model_fields import fields_request_model

router = APIRouter()
PAGE_PERMISSION = "discovery.page.ngs"
EDIT_PERMISSION = "discovery.ngs.edit"
LIBRARY_HANDOFF_PERMISSIONS = (EDIT_PERMISSION, "molecular.library.edit")


def _library_scope(context: UserContext = Depends(get_user_context)) -> service.TypeScope:
    return library_type_scope(context.permissions, context.is_superuser)


OrderFields = fields_request_model("NgsRunFields", service.FIELDS)


class RunSaveRequest(OrderFields):
    id: int | None = Field(default=None, gt=0)


class RunUpdateItem(OrderFields):
    id: int = Field(gt=0)


class RunBatchSaveRequest(BaseModel):
    items: list[RunUpdateItem] = Field(min_length=1, max_length=service.MAX_BATCH_SAVE_ITEMS)


class ListRequest(BaseModel):
    model_config = ConfigDict(extra="allow")


class ColumnValuesRequest(ListRequest):
    field: str = Field(min_length=1, max_length=64)
    value_keyword: str = Field(default="", max_length=128)
    value_limit: int = Field(default=200, ge=1, le=1000)
    value_order: Literal["value", "value_desc", "recent"] = "value"


class RunIdRequest(BaseModel):
    id: int = Field(gt=0)


class LibraryHandoffRequest(BaseModel):
    library_order_id: int = Field(gt=0)


@router.get("/options", dependencies=[require(PAGE_PERMISSION)])
def run_options(db: Session = Depends(get_db)) -> dict:
    return success(service.get_options(db))


@router.get("/recorded_targets", dependencies=[require(PAGE_PERMISSION)])
def recorded_targets(
    keyword: str = Query(default="", max_length=128),
    limit: int = Query(default=DEFAULT_RECORDED_TARGET_LIMIT, ge=1, le=MAX_RECORDED_TARGET_LIMIT),
    db: Session = Depends(get_db),
) -> dict:
    return success({"items": service.search_recorded_targets(db, keyword, limit)})


@router.post("/list", dependencies=[require(PAGE_PERMISSION)])
def list_runs(data: ListRequest | None = None, db: Session = Depends(get_db)) -> dict:
    return success(service.get_list(db, data.model_dump() if data else {}))


@router.post("/column_values", dependencies=[require(PAGE_PERMISSION)])
def run_column_values(data: ColumnValuesRequest, db: Session = Depends(get_db)) -> dict:
    return success(service.get_column_values(db, data.model_dump()))


@router.post("/export_list", dependencies=[require(PAGE_PERMISSION)])
def export_runs(data: ListRequest | None = None, db: Session = Depends(get_db)) -> Response:
    output, filename = service.export_list_workbook(db, data.model_dump() if data else {})
    return xlsx_response(output, filename)


@router.post("/save", dependencies=[require(EDIT_PERMISSION, audit="保存NGS测序单")])
def save_run(
    data: RunSaveRequest,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
) -> dict:
    return success(service.save(db, data.model_dump(exclude_unset=True), created_by=actor_name(current_user)))


@router.post("/batch_save", dependencies=[require(EDIT_PERMISSION, audit="批量保存NGS测序单")])
def batch_save_runs(data: RunBatchSaveRequest, db: Session = Depends(get_db)) -> dict:
    return success(service.batch_save(db, [item.model_dump(exclude_unset=True) for item in data.items]))


@router.post("/delete", dependencies=[require(EDIT_PERMISSION, audit="删除NGS测序单")])
def delete_run(data: RunIdRequest, db: Session = Depends(get_db)) -> dict:
    return success(service.delete_run(db, data.id))


@router.post(
    "/handoff_library",
    dependencies=[require(*LIBRARY_HANDOFF_PERMISSIONS, audit="交接文库工单至NGS")],
)
def handoff_library(
    data: LibraryHandoffRequest,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
    scope: service.TypeScope = Depends(_library_scope),
) -> dict:
    return success(
        service.handoff_from_library(db, data.library_order_id, created_by=actor_name(current_user), scope=scope)
    )


@router.post("/handoff_synthesis", dependencies=[require(EDIT_PERMISSION, audit="送NGS至合成与验证")])
def handoff_synthesis(
    data: RunIdRequest,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
) -> dict:
    return success(service.handoff_to_synthesis(db, data.id, created_by=actor_name(current_user)))
