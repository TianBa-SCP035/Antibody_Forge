"""写接口的审计声明：写在路由的 dependencies 上，审计中间件按请求匹配到的路由读取。

每个写接口（POST/PUT/PATCH/DELETE）必须有下面一种声明，标准只读后缀（/list、/export 等）除外：
- require(..., audit="操作名")：权限检查和操作名一起声明，操作类型、资源取自权限点；
- audit(...)：权限要按数据在函数体里判断，或者不走权限点（登录、设备回调）时单独声明操作；
- audit_quiet(...)：查询、核对类接口，没有数据变化不记日志；有变化时用给定名称。
"""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import Depends, params
from fastapi.routing import APIRoute

from modules.auth.permissions import PermissionRequirement
from modules.registry import PERMISSIONS
from modules.system.audit_context import AuditAction


@dataclass(frozen=True, eq=False)
class AuditSpec:
    actions: tuple[AuditAction, ...] = ()
    quiet: bool = False
    fallback_name: str | None = None
    fallback_resource: str | None = None

    def __call__(self) -> None:
        return None


def permission_action(code: str, name: str) -> AuditAction:
    permission = PERMISSIONS[code]
    if not permission.auditable:
        raise ValueError(f"页面、查看类权限不产生操作日志：{code}")
    return AuditAction(code=code, name=name, operation_type=permission.action, resource=permission.resource)


def audit(*actions: AuditAction) -> params.Depends:
    return Depends(AuditSpec(actions=actions))


def audit_quiet(name: str | None = None, resource: str | None = None) -> params.Depends:
    return Depends(AuditSpec(quiet=True, fallback_name=name, fallback_resource=resource))


def route_audit(route: APIRoute) -> AuditSpec | None:
    """汇总路由上的审计声明；没有声明返回 None。"""
    actions: list[AuditAction] = []
    quiet = False
    fallback_name = fallback_resource = None
    declared = False
    for dependency in route.dependencies:
        target = dependency.dependency
        if isinstance(target, PermissionRequirement) and target.audit:
            declared = True
            code = next(code for code in target.codes if PERMISSIONS[code].auditable)
            actions.append(permission_action(code, target.audit))
        elif isinstance(target, AuditSpec):
            declared = True
            actions.extend(target.actions)
            quiet = quiet or target.quiet
            fallback_name = target.fallback_name or fallback_name
            fallback_resource = target.fallback_resource or fallback_resource
    if not declared:
        return None
    return AuditSpec(tuple(actions), quiet, fallback_name, fallback_resource)
