from fastapi import APIRouter, Depends
from sqlalchemy import delete, func, or_, select
from sqlalchemy.orm import Session

from core.vben_response import vben_success
from db.session import get_db
from models.system import (
    SysOperationLog,
    SysPermission,
    SysPermissionBundle,
    SysPermissionBundleItem,
    SysRole,
    SysRolePermissionBundle,
    SysUser,
    SysUserPermissionOverride,
    SysUserRole,
)
from modules.auth.dependencies import get_current_user
from modules.auth.security import hash_password
from modules.system.permissions import build_user_context, require_permission

router = APIRouter()


@router.get("/permissions/current")
def current_permissions(
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
) -> dict:
    context = build_user_context(db, current_user)
    return vben_success(
        {
            "roles": context.roles,
            "permissions": context.permissions,
            "isSuperuser": context.is_superuser,
        }
    )


@router.get("/users")
def list_users(
    keyword: str = "",
    department: str = "",
    group_name: str = "",
    gender: str = "",
    status: str = "",
    employment_status: str = "",
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
) -> dict:
    require_permission(db, current_user, "system.user.manage")
    stmt = select(SysUser).order_by(SysUser.id.desc())
    if keyword:
        pattern = f"%{keyword}%"
        stmt = stmt.where(
            (SysUser.username.like(pattern))
            | (SysUser.display_name.like(pattern))
            | (SysUser.openid.like(pattern))
            | (SysUser.job_no.like(pattern))
            | (SysUser.department.like(pattern))
            | (SysUser.group_name.like(pattern))
            | (SysUser.position_title.like(pattern))
        )
    if department:
        stmt = stmt.where(SysUser.department == department)
    if group_name:
        stmt = stmt.where(SysUser.group_name == group_name)
    if gender:
        stmt = stmt.where(SysUser.gender == gender)
    if status:
        stmt = stmt.where(SysUser.status == status)
    if employment_status:
        stmt = stmt.where(SysUser.employment_status == employment_status)
    users = db.scalars(stmt).all()
    role_map = _get_user_role_map(db, [user.id for user in users])
    return vben_success({"items": [_user_to_dict(user, role_map.get(user.id, [])) for user in users]})


@router.post("/users/save")
def save_user(
    data: dict,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
) -> dict:
    require_permission(db, current_user, "system.user.manage")
    user_id = data.get("id")
    if user_id:
        user = db.get(SysUser, int(user_id))
        if not user:
            raise ValueError("用户不存在")
    else:
        username = data.get("username", "").strip()
        if not username:
            raise ValueError("请输入账号")
        user = SysUser(username=username)
        password = str(data.get("password") or "")
        if len(password) < 6:
            raise ValueError("新增用户密码至少需要 6 位")
        user.password_hash = hash_password(password)
        db.add(user)

    if "is_superuser" in data:
        requested_superuser = bool(data.get("is_superuser"))
        if requested_superuser != bool(user.is_superuser) and not current_user.is_superuser:
            raise ValueError("只有超级管理员可以修改超级管理员开关")
        user.is_superuser = requested_superuser

    for field in [
        "display_name",
        "openid",
        "job_no",
        "department",
        "group_name",
        "position_title",
        "gender",
        "profile_signature",
        "employment_status",
        "email",
        "mobile",
        "status",
    ]:
        if field in data:
            setattr(user, field, data.get(field) or None)
    user.employment_status = data.get("employment_status") or user.employment_status or "active"
    db.flush()
    if "role_ids" in data:
        role_ids = _unique_ints(data.get("role_ids") or [])
        _ensure_role_ids_exist(db, role_ids)
        _replace_user_roles(db, user.id, role_ids)
    db.commit()
    return vben_success({"id": user.id})


@router.post("/users/delete")
def delete_user(
    data: dict,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
) -> dict:
    require_permission(db, current_user, "system.user.manage")
    user = db.get(SysUser, int(data.get("id") or 0))
    if not user:
        raise ValueError("用户不存在")
    if user.id == current_user.id:
        raise ValueError("不能删除当前登录账号")
    db.execute(delete(SysUserRole).where(SysUserRole.user_id == user.id))
    db.execute(delete(SysUserPermissionOverride).where(SysUserPermissionOverride.user_id == user.id))
    db.delete(user)
    db.commit()
    return vben_success({"message": "ok"})


@router.post("/users/batch_roles")
def batch_update_user_roles(
    data: dict,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
) -> dict:
    require_permission(db, current_user, "system.user.manage")
    user_ids = [int(user_id) for user_id in data.get("user_ids") or [] if user_id]
    role_ids = [int(role_id) for role_id in data.get("role_ids") or [] if role_id]
    mode = data.get("mode") or "replace"
    if not user_ids:
        raise ValueError("请选择用户")
    if mode not in {"append", "replace"}:
        raise ValueError("批量设置模式不正确")
    _ensure_user_ids_exist(db, user_ids)
    _ensure_role_ids_exist(db, role_ids)

    for user_id in user_ids:
        if mode == "replace":
            _replace_user_roles(db, user_id, role_ids)
        else:
            existing = set(_get_user_role_map(db, [user_id]).get(user_id, []))
            _replace_user_roles(db, user_id, sorted(existing | set(role_ids)))
    db.commit()
    return vben_success({"updated": len(user_ids)})


@router.post("/users/reset_password")
def reset_password(
    data: dict,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
) -> dict:
    require_permission(db, current_user, "system.user.manage")
    user = db.get(SysUser, int(data.get("id")))
    if not user:
        raise ValueError("用户不存在")
    password = str(data.get("password") or "")
    if len(password) < 6:
        raise ValueError("密码至少需要 6 位")
    user.password_hash = hash_password(password)
    db.commit()
    return vben_success({"message": "ok"})


@router.get("/users/{user_id}/permission_overrides")
def get_user_permission_overrides(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
) -> dict:
    require_permission(db, current_user, "system.permission.manage")
    user = db.get(SysUser, int(user_id))
    if not user:
        raise ValueError("用户不存在")

    context = build_user_context(db, user)
    role_permissions = _get_role_permissions_for_user(db, user.id)
    overrides = db.scalars(
        select(SysUserPermissionOverride).where(SysUserPermissionOverride.user_id == user.id)
    ).all()
    return vben_success(
        {
            "user": _user_to_dict(user, _get_user_role_map(db, [user.id]).get(user.id, [])),
            "role_permissions": role_permissions,
            "effective_permissions": context.permissions,
            "overrides": [_override_to_dict(override) for override in overrides],
        }
    )


@router.post("/users/{user_id}/permission_overrides")
def save_user_permission_overrides(
    user_id: int,
    data: dict,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
) -> dict:
    require_permission(db, current_user, "system.permission.manage")
    user = db.get(SysUser, int(user_id))
    if not user:
        raise ValueError("用户不存在")

    allow_codes = {str(code) for code in data.get("allow_codes") or [] if code}
    deny_codes = {str(code) for code in data.get("deny_codes") or [] if code}
    reason = (data.get("reason") or "").strip() or None
    _ensure_permission_codes_exist(db, sorted(allow_codes | deny_codes))

    db.execute(delete(SysUserPermissionOverride).where(SysUserPermissionOverride.user_id == user.id))
    for code in sorted(allow_codes - deny_codes):
        db.add(SysUserPermissionOverride(user_id=user.id, permission_code=code, effect="allow", reason=reason))
    for code in sorted(deny_codes):
        db.add(SysUserPermissionOverride(user_id=user.id, permission_code=code, effect="deny", reason=reason))
    db.commit()
    return vben_success({"message": "ok"})


@router.get("/roles")
def list_roles(
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
) -> dict:
    require_permission(db, current_user, "system.role.manage")
    roles = db.scalars(select(SysRole).order_by(SysRole.sort_order, SysRole.id)).all()
    bundle_map = _get_role_bundle_map(db, [role.id for role in roles])
    return vben_success(
        {"items": [_role_to_dict(role, bundle_map.get(role.id, [])) for role in roles]}
    )


@router.post("/roles/save")
def save_role(
    data: dict,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
) -> dict:
    require_permission(db, current_user, "system.role.manage")
    role_id = data.get("id")
    if role_id:
        role = db.get(SysRole, int(role_id))
        if not role:
            raise ValueError("角色不存在")
    else:
        code = data.get("code", "").strip()
        if not code:
            raise ValueError("请输入角色编码")
        role = SysRole(code=code)
        db.add(role)
    if not str(data.get("name") or "").strip():
        raise ValueError("请输入角色名称")
    for field in ["name", "description", "status", "sort_order"]:
        if field in data:
            setattr(role, field, data.get(field))
    db.flush()
    if "bundle_codes" in data:
        bundle_codes = _unique_strings(data.get("bundle_codes") or [])
        _ensure_bundle_codes_exist(db, bundle_codes)
        _replace_role_bundles(db, role.id, bundle_codes)
    db.commit()
    return vben_success({"id": role.id})


@router.post("/roles/delete")
def delete_role(
    data: dict,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
) -> dict:
    require_permission(db, current_user, "system.role.manage")
    role = db.get(SysRole, int(data.get("id") or 0))
    if not role:
        raise ValueError("角色不存在")
    db.execute(delete(SysUserRole).where(SysUserRole.role_id == role.id))
    db.execute(delete(SysRolePermissionBundle).where(SysRolePermissionBundle.role_id == role.id))
    db.delete(role)
    db.commit()
    return vben_success({"message": "ok"})


@router.get("/permissions")
def list_permissions(
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
) -> dict:
    require_permission(db, current_user, "system.permission.manage")
    permissions = db.scalars(select(SysPermission).order_by(SysPermission.sort_order, SysPermission.id)).all()
    return vben_success({"items": [_permission_to_dict(permission) for permission in permissions]})


@router.get("/permission_bundles")
def list_permission_bundles(
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
) -> dict:
    require_permission(db, current_user, "system.permission.manage")
    bundles = db.scalars(select(SysPermissionBundle).order_by(SysPermissionBundle.sort_order, SysPermissionBundle.id)).all()
    item_map = _get_bundle_item_map(db, [bundle.code for bundle in bundles])
    return vben_success(
        {"items": [_bundle_to_dict(bundle, item_map.get(bundle.code, [])) for bundle in bundles]}
    )


@router.post("/permission_bundles/save")
def save_permission_bundle(
    data: dict,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
) -> dict:
    require_permission(db, current_user, "system.permission.manage")
    bundle_id = data.get("id")
    if bundle_id:
        bundle = db.get(SysPermissionBundle, int(bundle_id))
        if not bundle:
            raise ValueError("权限包不存在")
    else:
        code = str(data.get("code") or "").strip()
        if not code:
            raise ValueError("请输入权限包编码")
        bundle = SysPermissionBundle(code=code)
        db.add(bundle)

    for field in ["name", "module", "description", "status", "sort_order"]:
        if field in data:
            setattr(bundle, field, data.get(field))
    if not bundle.name:
        raise ValueError("请输入权限包名称")
    if not bundle.module:
        raise ValueError("请选择所属模块")
    db.flush()

    permission_codes = [str(code) for code in data.get("permission_codes") or [] if code]
    _ensure_permission_codes_exist(db, permission_codes)
    _replace_bundle_permissions(db, bundle.code, permission_codes)
    db.commit()
    return vben_success({"id": bundle.id})


@router.post("/permission_bundles/delete")
def delete_permission_bundle(
    data: dict,
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
) -> dict:
    require_permission(db, current_user, "system.permission.manage")
    bundle_id = data.get("id")
    bundle = db.get(SysPermissionBundle, int(bundle_id)) if bundle_id else None
    if not bundle and data.get("code"):
        bundle = db.scalar(select(SysPermissionBundle).where(SysPermissionBundle.code == str(data.get("code"))))
    if not bundle:
        raise ValueError("权限包不存在")
    db.execute(delete(SysRolePermissionBundle).where(SysRolePermissionBundle.bundle_code == bundle.code))
    db.execute(delete(SysPermissionBundleItem).where(SysPermissionBundleItem.bundle_code == bundle.code))
    db.delete(bundle)
    db.commit()
    return vben_success({"message": "ok"})


@router.get("/operation_logs")
def list_operation_logs(
    limit: int = 100,
    page: int = 1,
    page_size: int = 50,
    keyword: str = "",
    username: str = "",
    action: str = "",
    result: str = "",
    db: Session = Depends(get_db),
    current_user: SysUser = Depends(get_current_user),
) -> dict:
    require_permission(db, current_user, "system.operation_log.view")
    page = max(int(page or 1), 1)
    page_size = min(max(int(page_size or limit or 50), 1), 500)
    stmt = select(SysOperationLog)
    if username:
        stmt = stmt.where(SysOperationLog.username.like(f"%{username}%"))
    if action:
        stmt = stmt.where(SysOperationLog.action.like(f"%{action}%"))
    if result:
        stmt = stmt.where(SysOperationLog.result == result)
    if keyword:
        pattern = f"%{keyword}%"
        stmt = stmt.where(
            or_(
                SysOperationLog.username.like(pattern),
                SysOperationLog.operator_name.like(pattern),
                SysOperationLog.action.like(pattern),
                SysOperationLog.operation_name.like(pattern),
                SysOperationLog.target_type.like(pattern),
                SysOperationLog.target_id.like(pattern),
                SysOperationLog.target_label.like(pattern),
                SysOperationLog.result.like(pattern),
            )
        )
    total = db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0
    logs = db.scalars(stmt.order_by(SysOperationLog.id.desc()).offset((page - 1) * page_size).limit(page_size)).all()
    return vben_success({"items": [_log_to_dict(log) for log in logs], "total": total, "page": page, "page_size": page_size})


def _get_user_role_map(db: Session, user_ids: list[int]) -> dict[int, list[int]]:
    if not user_ids:
        return {}
    rows = db.execute(select(SysUserRole.user_id, SysUserRole.role_id).where(SysUserRole.user_id.in_(user_ids))).all()
    result: dict[int, list[int]] = {}
    for user_id, role_id in rows:
        result.setdefault(user_id, []).append(role_id)
    return result


def _get_role_bundle_map(db: Session, role_ids: list[int]) -> dict[int, list[str]]:
    if not role_ids:
        return {}
    rows = db.execute(
        select(SysRolePermissionBundle.role_id, SysRolePermissionBundle.bundle_code).where(
            SysRolePermissionBundle.role_id.in_(role_ids)
        )
    ).all()
    result: dict[int, list[str]] = {}
    for role_id, bundle_code in rows:
        result.setdefault(role_id, []).append(bundle_code)
    return result


def _get_bundle_item_map(db: Session, bundle_codes: list[str]) -> dict[str, list[str]]:
    if not bundle_codes:
        return {}
    rows = db.execute(
        select(SysPermissionBundleItem.bundle_code, SysPermissionBundleItem.permission_code).where(
            SysPermissionBundleItem.bundle_code.in_(bundle_codes)
        )
    ).all()
    result: dict[str, list[str]] = {}
    for bundle_code, permission_code in rows:
        result.setdefault(bundle_code, []).append(permission_code)
    return result


def _get_role_permissions_for_user(db: Session, user_id: int) -> list[str]:
    bundle_rows = db.execute(
        select(SysPermissionBundleItem.permission_code)
        .join(SysRolePermissionBundle, SysRolePermissionBundle.bundle_code == SysPermissionBundleItem.bundle_code)
        .join(SysRole, SysRole.id == SysRolePermissionBundle.role_id)
        .join(SysPermissionBundle, SysPermissionBundle.code == SysPermissionBundleItem.bundle_code)
        .join(SysPermission, SysPermission.code == SysPermissionBundleItem.permission_code)
        .join(SysUserRole, SysUserRole.role_id == SysRolePermissionBundle.role_id)
        .where(
            SysUserRole.user_id == user_id,
            SysRole.status == "active",
            SysPermissionBundle.status == "active",
            SysPermission.status == "active",
        )
    ).all()
    return sorted({row[0] for row in bundle_rows})


def _replace_user_roles(db: Session, user_id: int, role_ids: list[int]) -> None:
    db.execute(delete(SysUserRole).where(SysUserRole.user_id == user_id))
    for role_id in role_ids:
        db.add(SysUserRole(user_id=user_id, role_id=role_id))


def _replace_role_bundles(db: Session, role_id: int, bundle_codes: list[str]) -> None:
    db.execute(delete(SysRolePermissionBundle).where(SysRolePermissionBundle.role_id == role_id))
    for bundle_code in bundle_codes:
        db.add(SysRolePermissionBundle(role_id=role_id, bundle_code=bundle_code))


def _replace_bundle_permissions(db: Session, bundle_code: str, permission_codes: list[str]) -> None:
    db.execute(delete(SysPermissionBundleItem).where(SysPermissionBundleItem.bundle_code == bundle_code))
    for permission_code in dict.fromkeys(permission_codes):
        db.add(SysPermissionBundleItem(bundle_code=bundle_code, permission_code=permission_code))


def _unique_ints(values: list) -> list[int]:
    return list(dict.fromkeys(int(value) for value in values if value))


def _unique_strings(values: list) -> list[str]:
    return list(dict.fromkeys(str(value) for value in values if value))


def _ensure_user_ids_exist(db: Session, user_ids: list[int]) -> None:
    if not user_ids:
        return
    existing = set(db.scalars(select(SysUser.id).where(SysUser.id.in_(user_ids))).all())
    missing = sorted(set(user_ids) - existing)
    if missing:
        raise ValueError(f"用户不存在: {', '.join(str(item) for item in missing)}")


def _ensure_role_ids_exist(db: Session, role_ids: list[int]) -> None:
    if not role_ids:
        return
    existing = set(db.scalars(select(SysRole.id).where(SysRole.id.in_(role_ids))).all())
    missing = sorted(set(role_ids) - existing)
    if missing:
        raise ValueError(f"角色不存在: {', '.join(str(item) for item in missing)}")


def _ensure_bundle_codes_exist(db: Session, bundle_codes: list[str]) -> None:
    if not bundle_codes:
        return
    existing = set(db.scalars(select(SysPermissionBundle.code).where(SysPermissionBundle.code.in_(bundle_codes))).all())
    missing = sorted(set(bundle_codes) - existing)
    if missing:
        raise ValueError(f"权限包不存在: {', '.join(missing)}")


def _ensure_permission_codes_exist(db: Session, permission_codes: list[str]) -> None:
    if not permission_codes:
        return
    existing = set(db.scalars(select(SysPermission.code).where(SysPermission.code.in_(permission_codes))).all())
    missing = sorted(set(permission_codes) - existing)
    if missing:
        raise ValueError(f"权限点不存在: {', '.join(missing)}")


def _user_to_dict(user: SysUser, role_ids: list[int]) -> dict:
    data = user.to_dict()
    data["role_ids"] = role_ids
    return data


def _role_to_dict(role: SysRole, bundle_codes: list[str]) -> dict:
    return {
        "id": role.id,
        "code": role.code,
        "name": role.name,
        "description": role.description,
        "status": role.status,
        "sort_order": role.sort_order,
        "bundle_codes": bundle_codes,
    }


def _bundle_to_dict(bundle: SysPermissionBundle, permission_codes: list[str]) -> dict:
    return {
        "id": bundle.id,
        "code": bundle.code,
        "name": bundle.name,
        "module": bundle.module,
        "description": bundle.description,
        "status": bundle.status,
        "sort_order": bundle.sort_order,
        "permission_codes": permission_codes,
    }


def _permission_to_dict(permission: SysPermission) -> dict:
    return {
        "id": permission.id,
        "code": permission.code,
        "name": permission.name,
        "type": permission.type,
        "module": permission.module,
        "resource": permission.resource,
        "action": permission.action,
        "route_path": permission.route_path,
        "ui_key": permission.ui_key,
        "parent_code": permission.parent_code,
        "description": permission.description,
        "sort_order": permission.sort_order,
        "status": permission.status,
    }


def _override_to_dict(override: SysUserPermissionOverride) -> dict:
    return {
        "id": override.id,
        "user_id": override.user_id,
        "permission_code": override.permission_code,
        "effect": override.effect,
        "reason": override.reason,
    }


def _log_to_dict(log: SysOperationLog) -> dict:
    return {
        "id": log.id,
        "user_id": log.user_id,
        "username": log.username,
        "operator_name": log.operator_name,
        "action": log.action,
        "operation_name": log.operation_name,
        "operation_type": log.operation_type,
        "target_type": log.target_type,
        "target_id": log.target_id,
        "target_label": log.target_label,
        "result": log.result,
        "detail": log.detail,
        "error_message": log.error_message,
        "created_at": log.created_at,
    }
