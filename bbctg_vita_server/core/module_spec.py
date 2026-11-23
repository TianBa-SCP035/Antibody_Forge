"""业务模块对外登记的数据结构：权限点、资源名、功能开关默认值、路由挂载。

各模块在自己的 permissions.py 里声明 ACCESS，modules/registry.py 汇总。这里只放纯数据，不依赖数据库和路由。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Permission:
    """一个权限点；权限管理页按这些字段展示和分组，message 是 403 提示。"""

    code: str
    name: str
    type: str
    resource: str
    action: str
    message: str
    sort_order: int
    route_path: str | None = None
    ui_key: str | None = None
    parent_code: str | None = None

    @property
    def auditable(self) -> bool:
        """页面、查看类权限不产生操作日志。"""
        return self.type != "page" and self.action not in {"page", "view"}


def page(code: str, name: str, *, resource: str, route_path: str, sort_order: int, message: str,
         action: str = "view", parent_code: str | None = None) -> Permission:
    return Permission(code, name, "page", resource, action, message, sort_order,
                      route_path=route_path, parent_code=parent_code)


def action(code: str, name: str, *, resource: str, action: str, parent_code: str, sort_order: int, message: str,
           ui_key: str | None = None) -> Permission:
    return Permission(code, name, "action", resource, action, message, sort_order,
                      ui_key=ui_key, parent_code=parent_code)


def data(code: str, name: str, *, resource: str, parent_code: str, sort_order: int, message: str) -> Permission:
    """数据范围：不放行接口，由模块按它收窄能看、能改的数据。"""
    return Permission(code, name, "data", resource, "view", message, sort_order, parent_code=parent_code)


@dataclass(frozen=True)
class ModuleAccess:
    """一个业务模块的权限登记：module 是权限管理页的模块分组；resources 是资源码到操作日志中文名。"""

    module: str
    permissions: tuple[Permission, ...] = ()
    resources: dict[str, str] = field(default_factory=dict)
    features: tuple[dict[str, Any], ...] = ()


@dataclass(frozen=True)
class Mount:
    """路由挂载：router 写成“模块路径:变量名”，由 api.py 导入，登记表本身不导入路由。"""

    router: str
    prefix: str
    tag: str


def menu(code: str, name: str, description: str, *, sort_order: int, path: str, icon: str,
         parent_code: str | None = None) -> dict[str, Any]:
    config: dict[str, Any] = {"path": path, "icon": icon}
    if parent_code:
        config["parent_code"] = parent_code
    return _flag(code, name, "menu", description, True, sort_order, config)


def feature(code: str, name: str, description: str, *, sort_order: int, enabled: bool) -> dict[str, Any]:
    return _flag(code, name, "feature", description, enabled, sort_order, {})


def job(code: str, name: str, description: str, *, sort_order: int, hour: int, minute: int,
        **schedule: Any) -> dict[str, Any]:
    config = {
        "schedule": "daily",
        "hour": hour,
        "minute": minute,
        "weekday": 0,
        "day": 1,
        "every": 1,
        "unit": "hour",
        **schedule,
    }
    return _flag(code, name, "job", description, True, sort_order, config)


def _flag(code: str, name: str, category: str, description: str, enabled: bool, sort_order: int,
          config: dict[str, Any]) -> dict[str, Any]:
    return {
        "code": code,
        "name": name,
        "category": category,
        "description": description,
        "enabled": enabled,
        "visible": True,
        "sort_order": sort_order,
        "config": config,
    }
