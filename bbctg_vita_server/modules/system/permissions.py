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
    "serum.page.titer_order",
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
    "serum.titer_order.edit",
    "serum.titer_order.delete",
    "serum.titer_order.owner.edit",
    "serum.titer_order.record.edit",
    "serum.titer_order.record.edit_all",
}

MEGA_PERMISSION_CODES = {
    "mega.page.flow_work_order",
    "mega.flow_work_order.edit",
    "mega.flow_work_order.dispatch",
}

DISCOVERY_PERMISSION_CODES = {
    "discovery.page.target_library",
}

DEFAULT_PERMISSION_MESSAGE = "没有权限执行此操作"

PERMISSION_MESSAGES: dict[str, str] = {
    "serum.page.list": "没有权限查看血清项目列表",
    "serum.page.detail": "没有权限查看项目详情",
    "serum.page.edit": "没有权限编辑血清项目",
    "serum.page.titer": "没有权限查看效价数据",
    "serum.page.titer_order": "没有权限查看效价实验列表",
    "serum.page.cell": "没有权限查看细胞库存",
    "serum.project.create": "没有权限新建血清项目",
    "serum.project.edit": "没有权限编辑此项目",
    "serum.project.edit_all": "没有权限编辑他人项目",
    "serum.project.delete": "没有权限删除血清项目",
    "serum.status.update": "没有权限修改项目状态",
    "serum.status.auto_update": "没有权限自动更新项目状态",
    "serum.mouse.export": "没有权限导出小鼠免疫数据",
    "serum.cage.update": "没有权限更新笼位",
    "serum.titer.edit": "没有权限编辑效价数据",
    "serum.titer.edit_all": "没有权限编辑他人效价数据",
    "serum.file.manage": "没有权限管理效价附件",
    "serum.cell.view": "没有权限查看细胞库存",
    "serum.cell.prep_status.update": "没有权限更新制备状态",
    "serum.titer_order.edit": "没有权限编辑效价工单",
    "serum.titer_order.delete": "没有权限删除效价工单",
    "serum.titer_order.owner.edit": "没有权限编辑效价负责人",
    "serum.titer_order.record.edit": "没有权限编辑效价工单检测记录",
    "serum.titer_order.record.edit_all": "没有权限编辑他人效价工单检测记录",
    "mega.page.flow_work_order": "没有权限查看流式工单总览",
    "mega.flow_work_order.edit": "没有权限编辑流式工单",
    "mega.flow_work_order.dispatch": "没有权限发送流式工单",
    "discovery.page.target_library": "没有权限查看靶点库",
    "system.page.user": "没有权限访问用户管理",
    "system.page.role": "没有权限访问角色管理",
    "system.page.permission": "没有权限访问权限管理",
    "system.page.operation_log": "没有权限查看操作日志",
    "system.page.feature": "没有权限访问功能开关",
    "system.user.manage": "没有权限管理用户",
    "system.role.manage": "没有权限管理角色",
    "system.permission.manage": "没有权限管理权限",
    "system.operation_log.view": "没有权限查看操作日志",
    "system.feature.manage": "没有权限管理功能开关",
}

ALL_FALLBACK_CODES = sorted(
    SERUM_PERMISSION_CODES
    | MEGA_PERMISSION_CODES
    | DISCOVERY_PERMISSION_CODES
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
        raise HTTPException(
            status_code=403,
            detail=PERMISSION_MESSAGES.get(code, DEFAULT_PERMISSION_MESSAGE),
        )


def _build_sys_user_context(db: Session, user: SysUser) -> UserContext:
    # Organization/profile fields on sys_user are only for display and filtering.
    # Effective permissions must stay limited to roles, permission bundles, and user overrides.
    roles = _get_user_role_codes(db, user.id)
    if user.is_superuser:
        permissions = sorted(set(_get_all_permission_codes(db)) | set(ALL_FALLBACK_CODES))
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
