from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response, StreamingResponse
from sqlalchemy.orm import Session

from core.response import error, success
from db.session import get_db
from models.immunology import SerumImmProject
from models.system import SysUser
from modules.auth.dependencies import get_current_user
from modules.immunology.serum import service
from modules.system.permissions import has_permission, require_permission

router = APIRouter()


@router.get("/stats")
def stats(
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
) -> dict:
    require_permission(db, current_user, "serum.page.list")
    return success(service.get_stats(db))


@router.post("/list")
def list_serum(
    data: dict,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
) -> dict:
    require_permission(db, current_user, "serum.page.list")
    return success(service.get_list(db, data or {}))


@router.get("/detail")
def detail(
    id: int = Query(...),
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
) -> dict:
    require_permission(db, current_user, "serum.page.detail")
    data = service.get_detail(db, id)
    if data is None:
        return error("Project not found", 404)
    return success(data)


@router.get("/next_id")
def next_id(
    code: str = Query(...),
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
) -> dict:
    require_permission(db, current_user, "serum.project.create")
    return success({"next_id": service.generate_next_id(db, code)})


@router.post("/save")
def save(
    data: dict,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
) -> dict:
    try:
        save_data = dict(data or {})
        _require_project_save_permission(db, current_user, save_data)
        return success(service.save_serum(db, save_data))
    except HTTPException:
        raise
    except Exception as exc:
        db.rollback()
        return error(str(exc))


@router.post("/delete")
def delete(
    data: dict,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
) -> dict:
    try:
        require_permission(db, current_user, "serum.project.delete")
        service.delete_serum(db, int(data.get("id")))
        return success({"message": "Deleted successfully"})
    except HTTPException:
        raise
    except Exception as exc:
        db.rollback()
        return error(str(exc))


@router.get("/filter_options")
def filter_options(
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
) -> dict:
    require_permission(db, current_user, "serum.page.list")
    return success(service.get_filter_options(db))


@router.post("/update_status")
def update_status(
    data: dict,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
) -> dict:
    try:
        require_permission(db, current_user, "serum.status.update")
        _require_project_owner_or_edit_all(db, current_user, int(data.get("id")))
        service.update_status(db, int(data.get("id")), data.get("project_status"))
        return success({"message": "Status updated successfully"})
    except HTTPException:
        raise
    except Exception as exc:
        db.rollback()
        return error(str(exc))


@router.post("/update_cage_position")
def update_cage_position(
    data: dict,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
) -> dict:
    try:
        require_permission(db, current_user, "serum.cage.update")
        _require_project_owner_or_edit_all(db, current_user, int(data.get("id")))
        service.update_cage_position(db, int(data.get("id")), data.get("cage_position"))
        return success({"message": "笼位更新成功"})
    except HTTPException:
        raise
    except Exception as exc:
        db.rollback()
        return error(str(exc), 20001)


@router.post("/project/prep_status")
def update_prep_status(
    data: dict,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
) -> dict:
    try:
        require_permission(db, current_user, "serum.cell.prep_status.update")
        project = _get_project_by_experiment_id(db, data.get("experiment_id"))
        if project:
            _require_project_owner_or_edit_all(db, current_user, int(project.id))
        service.update_prep_status(db, data.get("experiment_id"), data.get("prep_status"))
        return success({"message": "Prep status updated successfully"})
    except HTTPException:
        raise
    except Exception as exc:
        db.rollback()
        return error(str(exc))


@router.post("/auto_update_status")
def auto_update_status(
    data: dict,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
) -> dict:
    try:
        require_permission(db, current_user, "serum.status.auto_update")
        require_permission(db, current_user, "serum.project.edit_all")
        return success(service.auto_update_status(db, data or {}))
    except HTTPException:
        raise
    except Exception as exc:
        db.rollback()
        return error(str(exc))


@router.post("/export_mouse")
def export_mouse(
    data: dict,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
) -> Response:
    require_permission(db, current_user, "serum.mouse.export")
    output, filename = service.export_mouse_workbook(db, data or {})
    return Response(
        content=output.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"},
    )


def _require_project_save_permission(db: Session, user: SysUser, data: dict) -> None:
    project_id = data.get("id")
    if not project_id:
        require_permission(db, user, "serum.project.create")
        owner = str(data.get("owner") or "").strip()
        if not owner:
            data["owner"] = _default_owner_name(user)
            return
        if not _is_owner_name(user, owner) and not has_permission(db, user, "serum.project.edit_all"):
            raise ValueError("普通用户只能将自己设为项目负责人")
        return

    project = db.get(SerumImmProject, int(project_id))
    if not project:
        raise ValueError("Project not found")

    target_owner = str(data.get("owner") or project.owner or "").strip()
    if not target_owner:
        data["owner"] = project.owner
        target_owner = str(project.owner or "").strip()

    is_current_owner = _is_owner_name(user, project.owner)
    keeps_own_owner = _is_owner_name(user, target_owner)
    if is_current_owner and keeps_own_owner:
        require_permission(db, user, "serum.project.edit")
        return

    require_permission(db, user, "serum.project.edit_all")


def _require_project_owner_or_edit_all(db: Session, user: SysUser, project_id: int) -> None:
    project = db.get(SerumImmProject, project_id)
    if not project:
        raise ValueError("Project not found")
    if _is_owner_name(user, project.owner):
        return
    require_permission(db, user, "serum.project.edit_all")


def _get_project_by_experiment_id(db: Session, experiment_id: str | None) -> SerumImmProject | None:
    if not experiment_id:
        return None
    return db.query(SerumImmProject).filter(SerumImmProject.experiment_id == experiment_id).first()


def _default_owner_name(user: SysUser) -> str:
    return (user.display_name or user.username or "").strip()


def _owner_aliases(user: SysUser) -> set[str]:
    values = {user.username, user.display_name, _default_owner_name(user)}
    aliases = {str(value).strip() for value in values if str(value or "").strip()}
    for value in list(aliases):
        aliases.add(value.split()[0])
    return aliases


def _is_owner_name(user: SysUser, owner: str | None) -> bool:
    owner_name = str(owner or "").strip()
    return bool(owner_name and owner_name in _owner_aliases(user))
