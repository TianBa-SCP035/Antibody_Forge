from typing import Any, Literal

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from core.response import success
from db.session import get_db
from models.system import SysUser
from modules.auth.dependencies import actor_name, get_current_user
from modules.auth.permissions import UserContext, get_user_context, require
from modules.molecular_cell.permissions import library_type_scope
from modules.molecular_cell.transfection import proteins, service
from utils.excel import xlsx_response
from utils.filter_values import DEFAULT_RECORDED_TARGET_LIMIT, MAX_RECORDED_TARGET_LIMIT
from utils.model_fields import fields_request_model

router = APIRouter()
PAGE_PERMISSION = "molecular.page.transfection"
EDIT_PERMISSION = "molecular.transfection.edit"
# 文库构建页面上把单细胞孔板交接过来：有任一权限即可
LIBRARY_HANDOFF_PERMISSIONS = (EDIT_PERMISSION, "molecular.library.edit")


def _library_scope(context: UserContext = Depends(get_user_context)) -> service.TypeScope:
    return library_type_scope(context.permissions, context.is_superuser)


OrderFields = fields_request_model("TransfectionOrderFields", service.FIELDS)


class OrderSaveRequest(OrderFields):
    id: int | None = Field(default=None, gt=0)


class OrderUpdateItem(OrderFields):
    id: int = Field(gt=0)


class OrderBatchSaveRequest(BaseModel):
    items: list[OrderUpdateItem] = Field(min_length=1, max_length=service.MAX_BATCH_SAVE_ITEMS)


class ListRequest(BaseModel):
    model_config = ConfigDict(extra="allow")


class ColumnValuesRequest(ListRequest):
    field: str = Field(min_length=1, max_length=64)
    value_keyword: str = Field(default="", max_length=128)
    value_limit: int = Field(default=200, ge=1, le=1000)
    value_order: Literal["value", "value_desc", "recent"] = "value"


class OrderIdRequest(BaseModel):
    id: int = Field(gt=0)


class LibraryHandoffRequest(BaseModel):
    library_order_id: int = Field(gt=0)


class ProteinImportItem(BaseModel):
    row: int | None = Field(default=None, ge=1)
    protein_name: Any = None
    heavy_chain: Any = None
    light_chain: Any = None


class ProteinImportRequest(BaseModel):
    order_id: int = Field(gt=0)
    items: list[ProteinImportItem] = Field(min_length=1, max_length=proteins.MAX_IMPORT_ROWS)



@router.get("/options", dependencies=[require(PAGE_PERMISSION)])
def order_options(db: Session = Depends(get_db)) -> dict:
    return success(service.get_options(db))


@router.get("/recorded_targets", dependencies=[require(PAGE_PERMISSION)])
def recorded_targets(
    keyword: str = Query(default="", max_length=128),
    limit: int = Query(default=DEFAULT_RECORDED_TARGET_LIMIT, ge=1, le=MAX_RECORDED_TARGET_LIMIT),
    db: Session = Depends(get_db),
) -> dict:
    return success({"items": service.search_recorded_targets(db, keyword, limit)})


@router.post("/list", dependencies=[require(PAGE_PERMISSION)])
def list_orders(data: ListRequest | None = None, db: Session = Depends(get_db)) -> dict:
    return success(service.get_list(db, data.model_dump() if data else {}))


@router.post("/column_values", dependencies=[require(PAGE_PERMISSION)])
def order_column_values(data: ColumnValuesRequest, db: Session = Depends(get_db)) -> dict:
    return success(service.get_column_values(db, data.model_dump()))


@router.post("/export_list", dependencies=[require(PAGE_PERMISSION)])
def export_orders(data: ListRequest | None = None, db: Session = Depends(get_db)) -> Response:
    output, filename = service.export_list_workbook(db, data.model_dump() if data else {})
    return xlsx_response(output, filename)


@router.post("/save", dependencies=[require(EDIT_PERMISSION, audit="保存转染工单")])
def save_order(
    data: OrderSaveRequest,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
) -> dict:
    return success(service.save(db, data.model_dump(exclude_unset=True), created_by=actor_name(current_user)))


@router.post("/batch_save", dependencies=[require(EDIT_PERMISSION, audit="批量保存转染工单")])
def batch_save_orders(data: OrderBatchSaveRequest, db: Session = Depends(get_db)) -> dict:
    return success(service.batch_save(db, [item.model_dump(exclude_unset=True) for item in data.items]))


@router.post("/delete", dependencies=[require(EDIT_PERMISSION, audit="删除转染工单")])
def delete_order(data: OrderIdRequest, db: Session = Depends(get_db)) -> dict:
    return success(service.delete_order(db, data.id))


@router.post(
    "/handoff_library",
    dependencies=[require(*LIBRARY_HANDOFF_PERMISSIONS, audit="交接文库工单至转染与表达")],
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


@router.post("/handoff_synthesis", dependencies=[require(EDIT_PERMISSION, audit="交接转染工单至合成与验证")])
def handoff_synthesis(
    data: OrderIdRequest,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
) -> dict:
    return success(service.handoff_to_synthesis(db, data.id, created_by=actor_name(current_user)))


@router.get("/order_proteins", dependencies=[require(PAGE_PERMISSION)])
def order_proteins(order_id: int = Query(gt=0), db: Session = Depends(get_db)) -> dict:
    return success(proteins.order_proteins(db, order_id))


@router.post("/proteins/import", dependencies=[require(EDIT_PERMISSION, audit="导入转染蛋白")])
def import_proteins(
    data: ProteinImportRequest,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
) -> dict:
    items = [item.model_dump() for item in data.items]
    return success(proteins.import_proteins(db, data.order_id, items, created_by=actor_name(current_user)))


@router.post("/proteins/clear", dependencies=[require(EDIT_PERMISSION, audit="整批删除转染蛋白")])
def clear_proteins(data: OrderIdRequest, db: Session = Depends(get_db)) -> dict:
    return success(proteins.clear_proteins(db, data.id))


@router.post("/proteins/list", dependencies=[require(PAGE_PERMISSION)])
def list_proteins(data: ListRequest | None = None, db: Session = Depends(get_db)) -> dict:
    return success(proteins.list_proteins(db, data.model_dump() if data else {}))


@router.post("/proteins/column_values", dependencies=[require(PAGE_PERMISSION)])
def protein_column_values(data: ColumnValuesRequest, db: Session = Depends(get_db)) -> dict:
    return success(proteins.get_column_values(db, data.model_dump()))


@router.post("/proteins/export", dependencies=[require(PAGE_PERMISSION)])
def export_proteins(data: ListRequest | None = None, db: Session = Depends(get_db)) -> Response:
    output, filename = proteins.export_workbook(db, data.model_dump() if data else {})
    return xlsx_response(output, filename)


@router.get("/order_proteins/export", dependencies=[require(PAGE_PERMISSION)])
def export_order_proteins(order_id: int = Query(gt=0), db: Session = Depends(get_db)) -> Response:
    output, filename = proteins.export_order_proteins(db, order_id)
    return xlsx_response(output, filename)
