from typing import Literal
from urllib.parse import quote

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
)
from fastapi.responses import FileResponse, Response, StreamingResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from core.response import success
from db.session import get_db
from integrations.drm_service import prepare_office_download_file, remove_temp_file
from models.system import SysUser
from modules.auth.dependencies import actor_name, get_current_user
from modules.auth.permissions import (
    UserContext,
    get_user_context,
    permission_denied,
    require,
)
from modules.molecular_cell.library_orders import cell_checkout, service
from modules.molecular_cell.library_orders.result_upload import (
    TRACE_EXTENSIONS,
    preview_extension,
)
from modules.molecular_cell.permissions import library_type_scope
from modules.system.audit_context import use_audit_action
from modules.system.audit_routes import audit, audit_quiet, permission_action
from utils.filter_values import DEFAULT_RECORDED_TARGET_LIMIT, MAX_RECORDED_TARGET_LIMIT
from utils.model_fields import fields_request_model

router = APIRouter()
PAGE_PERMISSION = "molecular.page.library"
EDIT_PERMISSION = "molecular.library.edit"
DETAIL_PERMISSION = "molecular.page.library_detail"
FILE_PERMISSION = "molecular.library.file.manage"
QC_CONCLUSION_FIELDS = {"qc_result", "qc_owner", "qc_on", "qc_note"}
HANDOFF_PERMISSIONS = (EDIT_PERMISSION, "discovery.workbench.edit")
CHECKOUT_REVIEW_PERMISSION = "molecular.library.cell_checkout.review"


def _type_scope(context: UserContext = Depends(get_user_context)) -> service.TypeScope:
    return library_type_scope(context.permissions, context.is_superuser)


OrderFields = fields_request_model("LibraryOrderFields", service.FIELDS)


class OrderSaveRequest(OrderFields):
    id: int | None = Field(default=None, gt=0)


class OrderUpdateItem(OrderFields):
    id: int = Field(gt=0)


class OrderBatchSaveRequest(BaseModel):
    items: list[OrderUpdateItem] = Field(min_length=1, max_length=service.MAX_BATCH_SAVE_ITEMS)


class OrderListRequest(BaseModel):
    model_config = ConfigDict(extra="allow")


class OrderColumnValuesRequest(OrderListRequest):
    field: str = Field(min_length=1, max_length=64)
    value_keyword: str = Field(default="", max_length=128)
    value_limit: int = Field(default=200, ge=1, le=1000)
    value_order: Literal["value", "value_desc", "recent"] = "value"


class OrderIdRequest(BaseModel):
    id: int = Field(gt=0)


class HandoffRequest(BaseModel):
    discovery_workbench_id: int | None = Field(default=None, gt=0)
    discovery_id: str | None = None
    items: list[dict] = Field(min_length=1)


class CellCheckoutSelection(BaseModel):
    order_ids: list[int] = Field(default_factory=list, max_length=cell_checkout.MAX_ORDERS)
    filters: dict | None = None


class CellCheckoutSubmitRequest(CellCheckoutSelection):
    cell_bank_ids: list[int] = Field(min_length=1, max_length=5000)


class CellCheckoutListRequest(BaseModel):
    status: str | None = Field(default=None, max_length=16)


class CellCheckoutReviewRequest(BaseModel):
    id: int = Field(gt=0)
    approve: bool
    note: str | None = Field(default=None, max_length=500)


class FileListRequest(BaseModel):
    order_id: int = Field(gt=0)


class FilePreflightRequest(BaseModel):
    paths: list[str] = Field(min_length=1, max_length=service.MAX_UPLOAD_FILES)


class FileDeleteRequest(BaseModel):
    link_id: int | None = Field(default=None, gt=0)
    file_id: int | None = Field(default=None, gt=0)
    order_id: int | None = Field(default=None, gt=0)
    package_id: int | None = Field(default=None, gt=0)


class FileUpdateRequest(BaseModel):
    link_id: int = Field(gt=0)
    order_id: int = Field(gt=0)
    original_name: str | None = Field(default=None, max_length=255)
    is_final_qc: bool | None = None
    qc_regions: list[dict[str, float | str]] | None = None


def _is_qc_conclusion_only(payload: dict) -> bool:
    changed = set(payload) - {"id", "_expected"}
    return bool(changed) and changed <= QC_CONCLUSION_FIELDS


def _require_save(context: UserContext, qc_conclusion_only: bool) -> None:
    """只改已有工单的质检结论时，文库编辑或质检管理任一即可，日志记为质检操作；其余改动要文库编辑权限。"""
    if qc_conclusion_only:
        use_audit_action(FILE_PERMISSION)
        if not context.allows(EDIT_PERMISSION, FILE_PERMISSION):
            raise permission_denied(EDIT_PERMISSION)
    else:
        use_audit_action(EDIT_PERMISSION)
        context.require(EDIT_PERMISSION)


@router.get("/options", dependencies=[require(PAGE_PERMISSION, DETAIL_PERMISSION)])
def order_options(
    db: Session = Depends(get_db),
    scope: service.TypeScope = Depends(_type_scope),
) -> dict:
    return success(service.get_options(db, scope))


@router.get("/recorded_targets", dependencies=[require(PAGE_PERMISSION)])
def recorded_targets(
    keyword: str = Query(default="", max_length=128),
    limit: int = Query(default=DEFAULT_RECORDED_TARGET_LIMIT, ge=1, le=MAX_RECORDED_TARGET_LIMIT),
    db: Session = Depends(get_db),
    scope: service.TypeScope = Depends(_type_scope),
) -> dict:
    return success({"items": service.search_recorded_targets(db, keyword, limit, scope)})


@router.post("/list", dependencies=[require(PAGE_PERMISSION)])
def list_orders(
    data: OrderListRequest | None = None,
    db: Session = Depends(get_db),
    scope: service.TypeScope = Depends(_type_scope),
) -> dict:
    return success(service.get_list(db, data.model_dump() if data else {}, scope))


@router.post("/column_values", dependencies=[require(PAGE_PERMISSION)])
def order_column_values(
    data: OrderColumnValuesRequest,
    db: Session = Depends(get_db),
    scope: service.TypeScope = Depends(_type_scope),
) -> dict:
    return success(service.get_column_values(db, data.model_dump(), scope))


@router.get("/by-discovery", dependencies=[require(*HANDOFF_PERMISSIONS)])
def by_discovery(
    discovery_workbench_id: int | None = Query(default=None),
    discovery_id: str | None = Query(default=None),
    db: Session = Depends(get_db),
    scope: service.TypeScope = Depends(_type_scope),
) -> dict:
    return success(
        service.list_by_discovery(
            db,
            discovery_id=discovery_id,
            discovery_workbench_id=discovery_workbench_id,
            scope=scope,
        )
    )


@router.post(
    "/save",
    dependencies=[
        audit(
            permission_action(EDIT_PERMISSION, "保存文库构建工单"),
            permission_action(FILE_PERMISSION, "保存文库质检结论"),
        ),
    ],
)
def save_order(
    data: OrderSaveRequest,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
    context: UserContext = Depends(get_user_context),
    scope: service.TypeScope = Depends(_type_scope),
) -> dict:
    payload = data.model_dump(exclude_unset=True)
    _require_save(context, data.id is not None and _is_qc_conclusion_only(payload))
    return success(service.save(db, payload, created_by=actor_name(current_user), scope=scope))


@router.post(
    "/batch_save",
    dependencies=[
        audit(
            permission_action(EDIT_PERMISSION, "批量保存文库构建工单"),
            permission_action(FILE_PERMISSION, "批量保存文库质检结论"),
        ),
    ],
)
def batch_save_orders(
    data: OrderBatchSaveRequest,
    db: Session = Depends(get_db),
    context: UserContext = Depends(get_user_context),
    scope: service.TypeScope = Depends(_type_scope),
) -> dict:
    payloads = [item.model_dump(exclude_unset=True) for item in data.items]
    _require_save(context, all(_is_qc_conclusion_only(payload) for payload in payloads))
    return success(service.batch_save(db, payloads, scope))


@router.post("/export_list", dependencies=[require(PAGE_PERMISSION)])
def export_orders(
    data: OrderListRequest | None = None,
    db: Session = Depends(get_db),
    scope: service.TypeScope = Depends(_type_scope),
) -> Response:
    from utils.excel import xlsx_response

    output, filename = service.export_list_workbook(db, data.model_dump() if data else {}, scope)
    return xlsx_response(output, filename)


@router.post("/handoff", dependencies=[require(*HANDOFF_PERMISSIONS, audit="交接发现安排至文库构建")])
def handoff(
    data: HandoffRequest,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
    scope: service.TypeScope = Depends(_type_scope),
) -> dict:
    return success(service.handoff(db, data.model_dump(), created_by=actor_name(current_user), scope=scope))


@router.post("/delete", dependencies=[require(EDIT_PERMISSION, audit="删除文库构建工单")])
def delete_order(
    data: OrderIdRequest,
    db: Session = Depends(get_db),
    scope: service.TypeScope = Depends(_type_scope),
) -> dict:
    return success(service.delete_order(db, data.id, scope))


@router.post(
    "/cell_checkout/candidates",
    dependencies=[require(EDIT_PERMISSION), audit_quiet("查询可出库冻存细胞", "library_checkout")],
)
def cell_checkout_candidates(
    data: CellCheckoutSelection,
    db: Session = Depends(get_db),
    scope: service.TypeScope = Depends(_type_scope),
) -> dict:
    return success(cell_checkout.candidates(db, data.model_dump(), scope))


@router.post("/cell_checkout/submit", dependencies=[require(EDIT_PERMISSION, audit="提交冻存细胞出库申请")])
def cell_checkout_submit(
    data: CellCheckoutSubmitRequest,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
    scope: service.TypeScope = Depends(_type_scope),
) -> dict:
    return success(cell_checkout.submit(db, data.model_dump(), actor_name(current_user), scope))


@router.post("/cell_checkout/list", dependencies=[require(PAGE_PERMISSION)])
def cell_checkout_list(
    data: CellCheckoutListRequest | None = None,
    db: Session = Depends(get_db),
    scope: service.TypeScope = Depends(_type_scope),
) -> dict:
    return success(cell_checkout.list_requests(db, data.model_dump() if data else {}, scope))


@router.post("/cell_checkout/review", dependencies=[require(CHECKOUT_REVIEW_PERMISSION, audit="审核冻存细胞出库")])
def cell_checkout_review(
    data: CellCheckoutReviewRequest,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
    scope: service.TypeScope = Depends(_type_scope),
) -> dict:
    return success(cell_checkout.review(db, data.id, data.approve, actor_name(current_user), data.note, scope))


@router.post("/files/list", dependencies=[require(DETAIL_PERMISSION), audit_quiet("刷新质检核对", "library_file")])
def file_list(
    data: FileListRequest,
    db: Session = Depends(get_db),
    scope: service.TypeScope = Depends(_type_scope),
) -> dict:
    return success(service.list_files(db, data.order_id, scope))


@router.post("/files/upload_batch", dependencies=[require(FILE_PERMISSION, audit="批量上传文库构建结果")])
def file_upload_batch(
    files: list[UploadFile] = File(...),
    paths: list[str] = Form(default=[]),
    order_id: int | None = Form(default=None),
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
    scope: service.TypeScope = Depends(_type_scope),
) -> dict:
    return success(
        service.upload_batch(
            db,
            files,
            paths,
            actor_name(current_user),
            order_id,
            scope,
        )
    )


@router.post(
    "/files/preflight",
    dependencies=[require(FILE_PERMISSION), audit_quiet("预检文库构建结果路径", "library_file")],
)
def file_preflight(
    data: FilePreflightRequest,
    db: Session = Depends(get_db),
    scope: service.TypeScope = Depends(_type_scope),
) -> dict:
    return success(service.preflight_upload(db, data.paths, scope))


@router.post("/files/delete", dependencies=[require(FILE_PERMISSION, audit="删除文库构建结果文件")])
def file_delete(
    data: FileDeleteRequest,
    db: Session = Depends(get_db),
    scope: service.TypeScope = Depends(_type_scope),
) -> dict:
    if (data.package_id or data.file_id) and not data.order_id:
        raise HTTPException(status_code=422, detail="请指定工单")
    if data.package_id:
        return success(
            service.delete_package(db, data.order_id, data.package_id, scope)
        )
    if data.file_id:
        return success(
            service.delete_stored_file(db, data.order_id, data.file_id, scope)
        )
    if not data.link_id:
        raise HTTPException(status_code=422, detail="请选择要删除的文件")
    return success(service.delete_file(db, data.link_id, data.order_id, scope))


@router.post("/files/update", dependencies=[require(FILE_PERMISSION, audit="更新文库构建结果文件标记")])
def file_update(
    data: FileUpdateRequest,
    db: Session = Depends(get_db),
    scope: service.TypeScope = Depends(_type_scope),
) -> dict:
    payload = data.model_dump(exclude_unset=True)
    return success(
        service.update_file_link(
            db,
            data.link_id,
            data.order_id,
            payload,
            scope,
        )
    )


@router.get("/files/download", dependencies=[require(DETAIL_PERMISSION)])
def file_download(
    background_tasks: BackgroundTasks,
    id: int | None = Query(default=None),
    file_id: int | None = Query(default=None),
    preview: bool = False,
    thumb: bool = False,
    w: int = Query(default=400, ge=32, le=1600),
    h: int = Query(default=400, ge=32, le=1600),
    db: Session = Depends(get_db),
    scope: service.TypeScope = Depends(_type_scope),
):
    if file_id:
        original_name, file_path = service.get_stored_file(db, file_id, scope)
    elif id:
        record, file_path = service.get_download_record(db, id, scope)
        original_name = record.original_name
    else:
        raise ValueError("缺少文件")
    if thumb:
        thumbnail = service.create_thumbnail(file_path, w, h)
        if thumbnail:
            output, media_type = thumbnail
            return StreamingResponse(output, media_type=media_type)
    recognized = TRACE_EXTENSIONS | service.INLINE_PREVIEW_EXTENSIONS
    suffix = preview_extension(file_path.name, original_name, recognized)
    if preview and suffix in TRACE_EXTENSIONS:
        return service.read_trace_preview(file_path)
    is_inline_preview = preview and suffix in service.INLINE_PREVIEW_EXTENSIONS
    serve_path = file_path
    temp_path = None
    if not is_inline_preview:
        serve_path, temp_path = prepare_office_download_file(db, file_path, original_name)
        if temp_path is not None:
            background_tasks.add_task(remove_temp_file, temp_path)
    return FileResponse(
        serve_path,
        filename=original_name,
        media_type=None,
        headers={
            "Content-Disposition": (
                f"{'inline' if is_inline_preview else 'attachment'}; "
                f"filename*=UTF-8''{quote(original_name)}"
            )
        },
    )
