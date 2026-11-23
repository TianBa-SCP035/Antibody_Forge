"""用户有效权限的计算和接口权限检查。权限点本身在各模块 permissions.py 声明，由 modules/registry.py 汇总。"""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import Depends, HTTPException, params
from sqlalchemy import select
from sqlalchemy.orm import Session

from db.session import get_db
from models.system import (
    SysPermissionBundle,
    SysPermissionBundleItem,
    SysRole,
    SysRolePermissionBundle,
    SysUser,
    SysUserPermissionOverride,
    SysUserRole,
)
from modules.auth.dependencies import get_current_user
from modules.registry import PERMISSIONS

DEFAULT_PERMISSION_MESSAGE = "没有权限执行此操作"


@dataclass
class UserContext:
    id: int | None
    username: str
    display_name: str
    roles: list[str]
    permissions: list[str]
    is_superuser: bool = False

    def allows(self, *codes: str) -> bool:
        """有任一权限码即为真。"""
        return self.is_superuser or not set(codes).isdisjoint(self.permissions)

    def require(self, code: str) -> None:
        """按数据判断权限时在函数体里用；不依赖数据的检查写在路由上：dependencies=[require(...)]。"""
        if not self.allows(code):
            raise permission_denied(code)


def build_user_context(db: Session, user: SysUser) -> UserContext:
    # 用户表上的组织、资料字段只用于展示和筛选；有效权限只来自角色、权限包和个人覆盖。
    roles = _get_user_role_codes(db, user.id)
    if user.is_superuser:
        permissions = sorted(PERMISSIONS)
    else:
        allow_codes, deny_codes = _get_user_overrides(db, user.id)
        permissions = sorted((set(get_role_permissions(db, user.id)) | allow_codes) - deny_codes)
    return UserContext(
        id=user.id,
        username=user.username,
        display_name=user.display_name or user.username,
        roles=roles,
        permissions=permissions,
        is_superuser=user.is_superuser,
    )


def get_user_context(db: Session = Depends(get_db), user: SysUser = Depends(get_current_user)) -> UserContext:
    """当前用户的有效权限；同一请求里 require() 和接口函数共用一次计算。"""
    return build_user_context(db, user)


def permission_message(code: str) -> str:
    permission = PERMISSIONS.get(code)
    return permission.message if permission else DEFAULT_PERMISSION_MESSAGE


def permission_denied(code: str) -> HTTPException:
    return HTTPException(status_code=403, detail=permission_message(code))


@dataclass(frozen=True, eq=False)
class PermissionRequirement:
    """路由依赖：有任一权限码即放行，否则按第一个权限码的文案返回 403。

    audit 是这个接口的操作日志名称，记在第一个能产生日志的权限码上。
    """

    codes: tuple[str, ...]
    audit: str | None = None

    def __call__(self, context: UserContext = Depends(get_user_context)) -> None:
        if not context.allows(*self.codes):
            raise permission_denied(self.codes[0])


def require(*codes: str, audit: str | None = None) -> params.Depends:
    """路由权限声明，例如 dependencies=[require("discovery.workbench.edit", audit="保存抗体发现工作台")]。

    写了 audit 的接口算显式审计：成功但没有数据变化也记一条操作日志；操作类型、资源取自权限点。
    """
    if not codes:
        raise ValueError("require() 至少要一个权限码")
    unknown = [code for code in codes if code not in PERMISSIONS]
    if unknown:
        raise ValueError(f"未登记的权限码：{unknown}")
    if audit and not any(PERMISSIONS[code].auditable for code in codes):
        raise ValueError(f"页面、查看类权限不产生操作日志，不能写 audit：{codes}")
    return Depends(PermissionRequirement(tuple(codes), audit))


def _get_user_role_codes(db: Session, user_id: int) -> list[str]:
    rows = db.execute(
        select(SysRole.code)
        .join(SysUserRole, SysUserRole.role_id == SysRole.id)
        .where(SysUserRole.user_id == user_id, SysRole.status == "active")
        .order_by(SysRole.sort_order, SysRole.id)
    ).all()
    return [row[0] for row in rows]


def get_role_permissions(db: Session, user_id: int) -> list[str]:
    """角色经权限包得到的权限码；代码里已不登记的权限码不算。"""
    bundle_rows = db.execute(
        select(SysPermissionBundleItem.permission_code)
        .join(SysRolePermissionBundle, SysRolePermissionBundle.bundle_code == SysPermissionBundleItem.bundle_code)
        .join(SysRole, SysRole.id == SysRolePermissionBundle.role_id)
        .join(SysPermissionBundle, SysPermissionBundle.code == SysPermissionBundleItem.bundle_code)
        .join(SysUserRole, SysUserRole.role_id == SysRolePermissionBundle.role_id)
        .where(
            SysUserRole.user_id == user_id,
            SysRole.status == "active",
            SysPermissionBundle.status == "active",
        )
    ).all()
    return sorted({row[0] for row in bundle_rows if row[0] in PERMISSIONS})


def _get_user_overrides(db: Session, user_id: int) -> tuple[set[str], set[str]]:
    rows = db.execute(
        select(SysUserPermissionOverride.permission_code, SysUserPermissionOverride.effect).where(
            SysUserPermissionOverride.user_id == user_id
        )
    ).all()
    allow_codes = {code for code, effect in rows if effect == "allow" and code in PERMISSIONS}
    deny_codes = {code for code, effect in rows if effect == "deny"}
    return allow_codes, deny_codes
