from dataclasses import dataclass

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from models.system import (
    SysPermission,
    SysPermissionBundle,
    SysPermissionBundleItem,
    SysRole,
    SysRolePermissionBundle,
    SysUser,
    SysUserPermissionOverride,
    SysUserRole,
)


SERUM_PERMISSION_CODES = {
    "serum.page.list",
    "serum.page.detail",
    "serum.page.edit",
    "serum.page.titer",
    "serum.page.cell",
    "serum.project.create",
    "serum.project.edit",
    "serum.project.edit_all",
    "serum.project.delete",
    "serum.status.update",
    "serum.status.auto_update",
    "serum.mouse.export",
    "serum.cage.update",
    "serum.titer.edit",
    "serum.titer.edit_all",
    "serum.file.manage",
    "serum.cell.view",
    "serum.cell.prep_status.update",
}

ALL_FALLBACK_CODES = sorted(
    SERUM_PERMISSION_CODES
    | {
        "system.page.user",
        "system.page.role",
        "system.page.permission",
        "system.page.operation_log",
        "system.page.feature",
        "system.user.manage",
        "system.role.manage",
        "system.permission.manage",
        "system.operation_log.view",
        "system.feature.manage",
    }
)


@dataclass
class UserContext:
    id: int | None
    username: str
    display_name: str
    roles: list[str]
    permissions: list[str]
    is_superuser: bool = False


def build_user_context(db: Session, user: SysUser) -> UserContext:
    return _build_sys_user_context(db, user)


def get_permission_codes(db: Session, user: SysUser) -> list[str]:
    return build_user_context(db, user).permissions


def has_permission(db: Session, user: SysUser, code: str) -> bool:
    context = build_user_context(db, user)
    return context.is_superuser or "*" in context.permissions or code in context.permissions


def require_permission(db: Session, user: SysUser, code: str) -> None:
    if not has_permission(db, user, code):
        raise HTTPException(status_code=403, detail=f"Permission denied: {code}")


def _build_sys_user_context(db: Session, user: SysUser) -> UserContext:
    # Organization/profile fields on sys_user are only for display and filtering.
    # Effective permissions must stay limited to roles, permission bundles, and user overrides.
    roles = _get_user_role_codes(db, user.id)
    if user.is_superuser:
        permissions = _get_all_permission_codes(db) or ALL_FALLBACK_CODES
    else:
        permissions = _get_role_permissions(db, user.id)
        allow_codes, deny_codes = _get_user_overrides(db, user.id)
        permissions = sorted((set(permissions) | allow_codes) - deny_codes)
    return UserContext(
        id=user.id,
        username=user.username,
        display_name=user.display_name or user.username,
        roles=roles,
        permissions=permissions,
        is_superuser=user.is_superuser,
    )


def _get_user_role_codes(db: Session, user_id: int) -> list[str]:
    rows = db.execute(
        select(SysRole.code)
        .join(SysUserRole, SysUserRole.role_id == SysRole.id)
        .where(SysUserRole.user_id == user_id, SysRole.status == "active")
        .order_by(SysRole.sort_order, SysRole.id)
    ).all()
    return [row[0] for row in rows]


def _get_role_permissions(db: Session, user_id: int) -> list[str]:
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


def _get_user_overrides(db: Session, user_id: int) -> tuple[set[str], set[str]]:
    rows = db.execute(
        select(SysUserPermissionOverride.permission_code, SysUserPermissionOverride.effect).where(
            SysUserPermissionOverride.user_id == user_id
        )
    ).all()
    allow_codes = {code for code, effect in rows if effect == "allow"}
    deny_codes = {code for code, effect in rows if effect == "deny"}
    return allow_codes, deny_codes


def _get_all_permission_codes(db: Session) -> list[str]:
    rows = db.execute(select(SysPermission.code).where(SysPermission.status == "active")).all()
    return sorted({row[0] for row in rows})
