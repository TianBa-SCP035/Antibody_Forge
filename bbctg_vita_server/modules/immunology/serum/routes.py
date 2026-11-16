from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from core.errors import NotFoundError
from core.response import success
from db.session import get_db
from models.immunology import SerumImmProject
from models.system import SysUser
from modules.auth.dependencies import get_current_user
from modules.auth.permissions import (
    UserContext,
    get_user_context,
    permission_denied,
    require,
)
from modules.immunology import project_lifecycle
from modules.immunology.project_access import is_owner_name, is_project_member
from modules.immunology.serum import scheme_export, service
from modules.system.audit_routes import audit, audit_quiet, permission_action
from utils.filter_values import DEFAULT_RECORDED_TARGET_LIMIT, MAX_RECORDED_TARGET_LIMIT

router = APIRouter()
# 鼠号分组查询、鼠号明细保存：免疫方案编辑或效价编辑任一即可
MOUSE_REGISTRY_PERMISSIONS = ("serum.project.edit", "serum.project.edit_all", "serum.titer.edit", "serum.titer.edit_all")


def _parse_export_ids(data: dict) -> list:
    ids = data.get("ids") or []
    if not ids and data.get("id") is not None:
        ids = [data["id"]]
    return ids


def _attachment_response(content: bytes, filename: str, media_type: str) -> Response:
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"},
    )


@router.post("/stats", dependencies=[require("serum.page.list")])
def stats(
    data: dict | None = None,
    db: Session = Depends(get_db),
) -> dict:
    return success(service.get_stats(db, data or {}))


@router.post("/list", dependencies=[require("serum.page.list")])
def list_serum(
    data: dict,
    db: Session = Depends(get_db),
) -> dict:
    return success(service.get_list(db, data or {}))


@router.post("/column_values", dependencies=[require("serum.page.list")])
def serum_column_values(
    data: dict | None = None,
    db: Session = Depends(get_db),
) -> dict:
    return success(service.get_column_values(db, data or {}))


@router.get("/detail", dependencies=[require("serum.page.detail")])
def detail(
    id: int | None = Query(default=None),
    experiment_id: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> dict:
    if id is None and not str(experiment_id or "").strip():
        raise HTTPException(status_code=400, detail="id 或 experiment_id 必填")
    data = service.get_detail(db, project_id=id, experiment_id=experiment_id)
    if data is None:
        raise HTTPException(status_code=404, detail="项目不存在")
    return success(data)


@router.get("/mouse-groups", dependencies=[require(*MOUSE_REGISTRY_PERMISSIONS)])
def mouse_groups(
    experiment_id: str = Query(...),
    db: Session = Depends(get_db),
) -> dict:
    return success({"items": service.get_mouse_groups(db, experiment_id)})


@router.post("/mouse-registry/save", dependencies=[require(*MOUSE_REGISTRY_PERMISSIONS, audit="保存小鼠鼠号明细")])
def mouse_registry_save(
    data: dict,
    db: Session = Depends(get_db),
) -> dict:
    return success(service.save_mouse_registry(db, data or {}))


@router.post(
    "/save",
    dependencies=[
        audit(
            permission_action("serum.project.create", "新建免疫项目"),
            permission_action("serum.project.edit", "编辑免疫项目"),
        )
    ],
)
def save(
    data: dict,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
    context: UserContext = Depends(get_user_context),
) -> dict:
    save_data = dict(data or {})
    _require_project_save_permission(db, current_user, context, save_data)
    return success(service.save_serum(db, save_data))


@router.post("/delete", dependencies=[require("serum.project.delete", audit="删除免疫项目")])
def delete(
    data: dict,
    db: Session = Depends(get_db),
) -> dict:
    action = project_lifecycle.delete_or_revert_project(db, int(data.get("id")))
    message = "已撤回为工作台草稿" if action == "reverted" else "删除成功"
    return success({"action": action, "message": message})


@router.get("/filter_options", dependencies=[require("serum.page.list")])
def filter_options(
    db: Session = Depends(get_db),
) -> dict:
    return success(service.get_filter_options(db))


@router.get("/recorded_targets", dependencies=[require("serum.page.list")])
def recorded_targets(
    keyword: str = Query(default="", max_length=128),
    limit: int = Query(default=DEFAULT_RECORDED_TARGET_LIMIT, ge=1, le=MAX_RECORDED_TARGET_LIMIT),
    db: Session = Depends(get_db),
) -> dict:
    return success({"items": service.search_recorded_targets(db, keyword, limit)})


@router.post("/update_status", dependencies=[audit(permission_action("serum.status.update", "快速修改状态"))])
def update_status(
    data: dict,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
    context: UserContext = Depends(get_user_context),
) -> dict:
    _require_status_update_access(db, current_user, context, int(data.get("id")))
    service.update_status(db, int(data.get("id")), data.get("project_status"))
    return success({"message": "状态修改成功"})


@router.post("/update_lab_notebook", dependencies=[audit(permission_action("serum.project.edit", "更新实验记录本"))])
def update_lab_notebook(
    data: dict,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
    context: UserContext = Depends(get_user_context),
) -> dict:
    _require_project_scheme_edit(db, current_user, context, int(data.get("id")))
    value = service.update_lab_notebook(db, int(data.get("id")), data.get("lab_notebook"))
    return success({"message": "实验记录本更新成功", "lab_notebook": value})


@router.post("/update_reviewer", dependencies=[audit(permission_action("serum.project.edit", "更新免疫实验审核人"))])
def update_reviewer(
    data: dict,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
    context: UserContext = Depends(get_user_context),
) -> dict:
    _require_project_scheme_edit(db, current_user, context, int(data.get("id")))
    value = service.update_reviewer(db, int(data.get("id")), data.get("reviewer"))
    return success({"message": "审核人更新成功", "reviewer": value})


@router.post("/update_cage_position", dependencies=[require("serum.cage.update", audit="更新笼位信息")])
def update_cage_position(
    data: dict,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
    context: UserContext = Depends(get_user_context),
) -> dict:
    _require_project_owner_or_edit_all(db, current_user, context, int(data.get("id")))
    service.update_cage_position(db, int(data.get("id")), data.get("cage_position"))
    return success({"message": "笼位更新成功"})


@router.post("/project/prep_status", dependencies=[require("serum.cell.prep_status.update", audit="更新细胞制备状态")])
def update_prep_status(
    data: dict,
    db: Session = Depends(get_db),
) -> dict:
    service.update_prep_status(db, data.get("experiment_id"), data.get("prep_status"))
    return success({"message": "制备状态更新成功"})


@router.post("/auto_update_status", dependencies=[require("serum.status.auto_update", audit="自动更新状态")])
def auto_update_status(
    data: dict,
    db: Session = Depends(get_db),
) -> dict:
    return success(service.auto_update_status(db, data or {}))


@router.post("/export_list", dependencies=[require("serum.page.list")])
def export_list(
    data: dict,
    db: Session = Depends(get_db),
) -> Response:
    from utils.excel import xlsx_response

    output, filename = service.export_list_workbook(db, data or {})
    return xlsx_response(output, filename)


@router.post("/export_mouse", dependencies=[require("serum.mouse.export"), audit_quiet()])
def export_mouse(
    data: dict,
    db: Session = Depends(get_db),
) -> Response:
    output, filename = service.export_mouse_workbook(db, data or {})
    return Response(
        content=output.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"},
    )


@router.post("/export_scheme", dependencies=[require("serum.page.detail"), audit_quiet()])
def export_scheme(
    data: dict,
    db: Session = Depends(get_db),
) -> Response:
    ids = _parse_export_ids(data)
    if not ids:
        raise HTTPException(status_code=400, detail="请提供项目 ID")
    output, filename, export_type = scheme_export.export_scheme_response(db, ids)
    media_type = (
        "application/zip"
        if export_type == "zip"
        else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    return _attachment_response(output.getvalue(), filename, media_type)


@router.post("/export_scheme_pdf", dependencies=[require("serum.page.detail"), audit_quiet()])
def export_scheme_pdf(
    data: dict,
    db: Session = Depends(get_db),
) -> Response:
    ids = _parse_export_ids(data)
    if not ids:
        raise HTTPException(status_code=400, detail="请提供项目 ID")
    try:
        output, filename = scheme_export.export_scheme_pdf_response(db, ids)
    except RuntimeError as exc:
        detail = str(exc)
        status_code = 503 if "LibreOffice" in detail else 500
        raise HTTPException(status_code=status_code, detail=detail) from exc
    return _attachment_response(output.getvalue(), filename, "application/pdf")


def _require_project_save_permission(db: Session, user: SysUser, context: UserContext, data: dict) -> None:
    project_id = data.get("id")
    if not project_id:
        context.require("serum.project.create")
        owner = str(data.get("owner") or "").strip()
        if not owner:
            data["owner"] = _default_owner_name(user)
            return
        if not is_owner_name(user, owner) and not context.allows("serum.project.edit_all"):
            raise ValueError("普通用户只能将自己设为项目负责人")
        return

    project = db.get(SerumImmProject, int(project_id))
    if not project:
        raise NotFoundError("项目不存在")

    current_owner = str(project.owner or "").strip()
    target_owner = str(data.get("owner") or current_owner).strip()
    if not target_owner:
        data["owner"] = project.owner
        target_owner = current_owner

    keeps_owner = target_owner == current_owner or (
        is_owner_name(user, current_owner) and is_owner_name(user, target_owner)
    )
    if keeps_owner and is_project_member(user, project):
        context.require("serum.project.edit")
        return

    context.require("serum.project.edit_all")


def _require_project_scheme_edit(db: Session, user: SysUser, context: UserContext, project_id: int) -> None:
    project = db.get(SerumImmProject, project_id)
    if not project:
        raise NotFoundError("项目不存在")
    if context.allows("serum.project.edit_all"):
        return
    if context.allows("serum.project.edit") and is_project_member(user, project):
        return
    raise permission_denied("serum.project.edit")


def _require_project_owner_or_edit_all(db: Session, user: SysUser, context: UserContext, project_id: int) -> None:
    project = db.get(SerumImmProject, project_id)
    if not project:
        raise NotFoundError("项目不存在")
    if is_project_member(user, project):
        return
    context.require("serum.project.edit_all")


def _require_status_update_access(db: Session, user: SysUser, context: UserContext, project_id: int) -> None:
    project = db.get(SerumImmProject, project_id)
    if not project:
        raise NotFoundError("项目不存在")
    if is_project_member(user, project):
        if context.allows("serum.status.update", "serum.titer.edit"):
            return
        raise permission_denied("serum.status.update")
    if context.allows("serum.status.update") and context.allows("serum.project.edit_all"):
        return
    if context.allows("serum.titer.edit") and context.allows("serum.titer.edit_all"):
        return
    raise permission_denied("serum.status.update")


def _default_owner_name(user: SysUser) -> str:
    return (user.display_name or user.username or "").strip()
