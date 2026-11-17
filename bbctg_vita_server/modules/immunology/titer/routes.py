from urllib.parse import quote

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    Query,
    UploadFile,
)
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from core.errors import NotFoundError
from core.response import success
from db.session import get_db
from integrations.drm_service import prepare_office_download_file, remove_temp_file
from models.immunology import (
    SerumElisaPlate,
    SerumFacsPlate,
    SerumFile,
    SerumImmProject,
    SerumTiterOrder,
)
from models.system import SysUser
from modules.auth.dependencies import actor_name, get_current_user
from modules.auth.permissions import (
    UserContext,
    get_user_context,
    permission_denied,
    require,
)
from modules.immunology.project_access import is_project_member, owner_aliases
from modules.immunology.titer import service
from modules.system.audit_routes import audit, permission_action
from utils.filter_values import DEFAULT_RECORDED_TARGET_LIMIT, MAX_RECORDED_TARGET_LIMIT

router = APIRouter()

TITER_READ = require("serum.page.detail", "serum.page.titer")
TITER_ORDER_FORM = require("serum.titer_order.edit")


@router.post("/file/list", dependencies=[TITER_READ])
def file_list(
    data: dict,
    db: Session = Depends(get_db),
) -> dict:
    return success({"items": service.get_file_list(db, data.get("experiment_id"))})


@router.post("/file/save", dependencies=[require("serum.file.manage", audit="上传效价文件")])
def file_save(
    file: UploadFile = File(...),
    experiment_id: str = Form(...),
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
    context: UserContext = Depends(get_user_context),
) -> dict:
    _require_project_owner_or_edit_all(db, current_user, context, experiment_id=experiment_id)
    return success(service.save_file(db, file, experiment_id, actor_name(current_user)))


@router.post("/file/delete", dependencies=[require("serum.file.manage", audit="删除效价文件")])
def file_delete(
    data: dict,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
    context: UserContext = Depends(get_user_context),
) -> dict:
    _require_project_owner_or_edit_all(db, current_user, context, file_id=int(data.get("id")))
    service.delete_file(db, int(data.get("id")))
    return success({"message": "删除成功"})


@router.post("/file/rename", dependencies=[require("serum.file.manage", audit="重命名效价文件")])
def file_rename(
    data: dict,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
    context: UserContext = Depends(get_user_context),
) -> dict:
    _require_project_owner_or_edit_all(db, current_user, context, file_id=int(data.get("id")))
    service.rename_file(db, int(data.get("id")), data.get("new_name"))
    return success({"message": "重命名成功"})


@router.post("/file/replace", dependencies=[require("serum.file.manage", audit="替换效价文件")])
def file_replace(
    file: UploadFile = File(...),
    id: int = Form(...),
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
    context: UserContext = Depends(get_user_context),
) -> dict:
    _require_project_owner_or_edit_all(db, current_user, context, file_id=id)
    return success(service.replace_file(db, id, file, actor_name(current_user)))


@router.get("/file/download", dependencies=[TITER_READ])
def file_download(
    background_tasks: BackgroundTasks,
    id: int = Query(...),
    preview: str | None = None,
    thumb: str | None = None,
    w: int = 400,
    h: int = 400,
    db: Session = Depends(get_db),
):
    record, file_path = service.get_download_record(db, id)
    if thumb and thumb.lower() in {"1", "true"}:
        thumbnail = service.create_thumbnail(file_path, w, h)
        if thumbnail:
            output, media_type = thumbnail
            return StreamingResponse(output, media_type=media_type)

    is_inline_preview = preview == "true"
    serve_path = file_path
    temp_path = None
    if not is_inline_preview:
        serve_path, temp_path = prepare_office_download_file(db, file_path, record.file_name)
        if temp_path is not None:
            background_tasks.add_task(remove_temp_file, temp_path)

    return FileResponse(
        serve_path,
        filename=record.file_name,
        media_type=None,
        headers={"Content-Disposition": f"{'inline' if is_inline_preview else 'attachment'}; filename*=UTF-8''{quote(record.file_name)}"},
    )


@router.post("/target/save", dependencies=[require("serum.titer.edit", audit="保存效价标靶")])
def target_save(
    data: dict,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
    context: UserContext = Depends(get_user_context),
) -> dict:
    _require_project_owner_or_edit_all(db, current_user, context, experiment_id=data.get("experiment_id"))
    return success({"items": service.save_targets(db, data.get("experiment_id"), data.get("targets", []))})


@router.post("/pc/save", dependencies=[require("serum.titer.edit", audit="保存效价阳性对照")])
def pc_save(
    data: dict,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
    context: UserContext = Depends(get_user_context),
) -> dict:
    _require_project_owner_or_edit_all(db, current_user, context, experiment_id=data.get("experiment_id"))
    return success({"items": service.save_pcs(db, data.get("experiment_id"), data.get("pcs", []))})


@router.post("/plate/list", dependencies=[TITER_READ])
def plate_list(
    data: dict,
    db: Session = Depends(get_db),
) -> dict:
    return success({"items": service.get_facs_plates(db, data.get("experiment_id"))})


@router.post("/plate/save", dependencies=[require("serum.titer.edit", audit="保存FACS板")])
def plate_save(
    data: dict,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
    context: UserContext = Depends(get_user_context),
) -> dict:
    _require_project_owner_or_edit_all(db, current_user, context, experiment_id=(data or {}).get("experiment_id"))
    return success(service.save_facs_plate(db, data or {}))


@router.post("/plate/delete", dependencies=[require("serum.titer.edit", audit="删除FACS板")])
def plate_delete(
    data: dict,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
    context: UserContext = Depends(get_user_context),
) -> dict:
    _require_project_owner_or_edit_all(db, current_user, context, plate_id=int(data.get("id")))
    service.delete_facs_plate(db, int(data.get("id")))
    return success({"message": "删除成功"})


@router.post("/elisa/plate/list", dependencies=[TITER_READ])
def elisa_plate_list(
    data: dict,
    db: Session = Depends(get_db),
) -> dict:
    return success({"items": service.get_elisa_plates(db, data.get("experiment_id"))})


@router.post("/elisa/plate/save", dependencies=[require("serum.titer.edit", audit="保存ELISA板")])
def elisa_plate_save(
    data: dict,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
    context: UserContext = Depends(get_user_context),
) -> dict:
    _require_project_owner_or_edit_all(db, current_user, context, experiment_id=(data or {}).get("experiment_id"))
    return success(service.save_elisa_plate(db, data or {}))


@router.post("/elisa/plate/delete", dependencies=[require("serum.titer.edit", audit="删除ELISA板")])
def elisa_plate_delete(
    data: dict,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
    context: UserContext = Depends(get_user_context),
) -> dict:
    _require_project_owner_or_edit_all(db, current_user, context, elisa_plate_id=int(data.get("id")))
    service.delete_elisa_plate(db, int(data.get("id")))
    return success({"message": "删除成功"})


_TITER_ORDER_BATCH_FIELD_KEYS = (
    "cage_position",
    "blood_collection_date",
    "blood_collection_seq",
    "mouse_count",
    "assay_method",
    "facs_plate_count",
    "elisa_plate_count",
)
_TITER_ORDER_RECORD_FIELD_KEYS = ("test_dates", "remark", "summary", "lab_notebook")
_TITER_ORDER_RECORD_OPEN_FIELD_KEYS = ("serum_status", "priority")


@router.get("/order/meta", dependencies=[require("serum.page.titer_order")])
def titer_order_meta(
    db: Session = Depends(get_db),
) -> dict:
    return success(service.get_titer_order_page_meta(db))


@router.get("/order/recorded_targets", dependencies=[require("serum.page.titer_order")])
def titer_order_recorded_targets(
    keyword: str = Query(default="", max_length=128),
    limit: int = Query(default=DEFAULT_RECORDED_TARGET_LIMIT, ge=1, le=MAX_RECORDED_TARGET_LIMIT),
    db: Session = Depends(get_db),
) -> dict:
    return success({"items": service.search_titer_order_targets(db, keyword, limit)})


@router.post("/order/stats", dependencies=[require("serum.page.titer_order")])
def titer_order_stats(
    data: dict | None = None,
    db: Session = Depends(get_db),
) -> dict:
    return success(service.get_titer_order_stats(db, data or {}))


@router.post("/order/column_values", dependencies=[require("serum.page.titer_order")])
def titer_order_column_values(
    data: dict | None = None,
    db: Session = Depends(get_db),
) -> dict:
    return success(service.get_titer_order_column_values(db, data or {}))


@router.get("/order/owner_stats", dependencies=[require("serum.page.titer_order")])
def titer_order_owner_stats(
    month_start: str = "",
    month_end: str = "",
    db: Session = Depends(get_db),
) -> dict:
    return success(
        service.get_titer_owner_workload_stats(
            db,
            month_start or None,
            month_end or None,
        )
    )


@router.get("/order/project_options", dependencies=[TITER_ORDER_FORM])
def titer_order_project_options(
    keyword: str = "",
    limit: int = 20,
    db: Session = Depends(get_db),
) -> dict:
    return success({"items": service.get_project_options(db, keyword, limit)})


@router.get("/order/batch_preview", dependencies=[TITER_ORDER_FORM])
def titer_order_batch_preview(
    experiment_id: str = "",
    db: Session = Depends(get_db),
) -> dict:
    return success(service.get_titer_order_batch_preview(db, experiment_id))


@router.post("/order/list", dependencies=[require("serum.page.titer_order")])
def titer_order_list(
    data: dict,
    db: Session = Depends(get_db),
) -> dict:
    return success(service.get_titer_order_list(db, data or {}))


@router.post("/order/export", dependencies=[require("serum.page.titer_order")])
def titer_order_export(
    data: dict,
    db: Session = Depends(get_db),
):
    from utils.excel import xlsx_response

    output, filename = service.export_titer_order_list_workbook(db, data or {})
    return xlsx_response(output, filename)


@router.post("/order/save", dependencies=[audit(permission_action("serum.titer_order.edit", "保存效价工单"))])
def titer_order_save(
    data: dict,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
    context: UserContext = Depends(get_user_context),
) -> dict:
    _validate_titer_order_save(db, current_user, context, data or {})
    return success(service.save_titer_order(db, data or {}))


@router.post("/order/delete", dependencies=[require("serum.titer_order.delete", audit="删除效价工单")])
def titer_order_delete(
    data: dict,
    db: Session = Depends(get_db),
) -> dict:
    order_id = data.get("id")
    if order_id is None or str(order_id).strip() == "":
        raise ValueError("缺少工单 ID")
    service.delete_titer_order(db, int(order_id))
    return success({"message": "删除成功"})


def _require_project_owner_or_edit_all(
    db: Session,
    user: SysUser,
    context: UserContext,
    *,
    experiment_id: str | None = None,
    file_id: int | None = None,
    plate_id: int | None = None,
    elisa_plate_id: int | None = None,
) -> None:
    project = _resolve_project(
        db,
        experiment_id=experiment_id,
        file_id=file_id,
        plate_id=plate_id,
        elisa_plate_id=elisa_plate_id,
    )
    if not project:
        raise NotFoundError("项目不存在")
    if is_project_member(user, project):
        return
    exp_id = str(project.experiment_id or "").strip()
    if exp_id:
        for owners in db.scalars(
            select(SerumTiterOrder.titer_owners).where(SerumTiterOrder.experiment_id == exp_id)
        ).all():
            if _is_titer_owner(user, owners):
                return
    context.require("serum.titer.edit_all")


def _resolve_project(
    db: Session,
    *,
    experiment_id: str | None = None,
    file_id: int | None = None,
    plate_id: int | None = None,
    elisa_plate_id: int | None = None,
) -> SerumImmProject | None:
    target_experiment_id = experiment_id
    if file_id is not None:
        record = db.get(SerumFile, file_id)
        if not record:
            raise NotFoundError("文件不存在")
        target_experiment_id = record.experiment_id
    if plate_id is not None:
        plate = db.get(SerumFacsPlate, plate_id)
        if not plate:
            raise NotFoundError("板数据不存在")
        target_experiment_id = plate.experiment_id
    if elisa_plate_id is not None:
        plate = db.get(SerumElisaPlate, elisa_plate_id)
        if not plate:
            raise NotFoundError("板数据不存在")
        target_experiment_id = plate.experiment_id
    if not target_experiment_id:
        return None
    return db.scalar(select(SerumImmProject).where(SerumImmProject.experiment_id == target_experiment_id))


def _has_payload_keys(data: dict, keys: tuple[str, ...]) -> bool:
    return any(key in data for key in keys)


def _is_titer_owner(user: SysUser, owners: object) -> bool:
    aliases = owner_aliases(user)
    if not isinstance(owners, list):
        return False
    return any(str(owner or "").strip() in aliases for owner in owners)


def _require_titer_order_record_edit(
    user: SysUser,
    context: UserContext,
    order: SerumTiterOrder,
    project: SerumImmProject | None = None,
) -> None:
    context.require("serum.titer_order.record.edit")
    if context.allows("serum.titer_order.record.edit_all"):
        return
    if _is_titer_owner(user, order.titer_owners):
        return
    if project and is_project_member(user, project):
        return
    raise permission_denied("serum.titer_order.record.edit")


def _validate_titer_order_save(db: Session, user: SysUser, context: UserContext, data: dict) -> None:
    order_id = data.get("id")
    order: SerumTiterOrder | None = None
    project: SerumImmProject | None = None

    if order_id is not None and str(order_id).strip() != "":
        order = db.get(SerumTiterOrder, int(order_id))
        if not order:
            raise NotFoundError("效价工单不存在")
        project = db.scalar(
            select(SerumImmProject).where(SerumImmProject.experiment_id == order.experiment_id)
        )
    else:
        context.require("serum.titer_order.edit")

    if order is not None and _has_payload_keys(data, _TITER_ORDER_BATCH_FIELD_KEYS):
        context.require("serum.titer_order.edit")

    if "titer_owners" in data:
        if order is None:
            raise permission_denied("serum.titer_order.owner.edit")
        context.require("serum.titer_order.owner.edit")

    if _has_payload_keys(data, _TITER_ORDER_RECORD_FIELD_KEYS):
        if order is None:
            raise permission_denied("serum.titer_order.record.edit")
        _require_titer_order_record_edit(user, context, order, project)
    elif _has_payload_keys(data, _TITER_ORDER_RECORD_OPEN_FIELD_KEYS):
        context.require("serum.titer_order.record.edit")
