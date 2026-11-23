"""业务模块登记表：新模块在这里加一行权限登记（ACCESS）和它的路由挂载（MOUNTS）。

权限文案、超级管理员兜底权限码、功能开关默认值、操作日志资源名都从这里汇总，不再各处分别维护。
"""

from __future__ import annotations

from typing import Any

from core.module_spec import ModuleAccess, Mount, Permission
from modules.atlas import permissions as atlas
from modules.discovery import permissions as discovery
from modules.immunology import permissions as immunology
from modules.mega_automation import permissions as mega_automation
from modules.molecular_cell import permissions as molecular_cell
from modules.order_sync import permissions as order_sync
from modules.supernatant_receive import permissions as supernatant_receive
from modules.system import permissions as system

ACCESS: tuple[ModuleAccess, ...] = (
    atlas.ACCESS,
    immunology.ACCESS,
    discovery.ACCESS,
    molecular_cell.ACCESS,
    mega_automation.ACCESS,
    order_sync.ACCESS,
    supernatant_receive.ACCESS,
    system.ACCESS,
)

MOUNTS: tuple[Mount, ...] = (
    Mount("modules.auth.routes:router", "/auth", "认证"),
    Mount("modules.atlas.routes:router", "/atlas", "千鼠万抗"),
    Mount("modules.discovery.workbench.routes:router", "/discovery/workbench", "抗体发现-项目工作台"),
    Mount("modules.discovery.synthesis_progress.routes:router", "/discovery/synthesis-progress", "抗体发现-合成进度"),
    Mount("modules.immunology.serum.routes:router", "/serum", "免疫部-血清"),
    Mount("modules.immunology.workbench.routes:router", "/serum/workbench", "免疫部-项目工作台"),
    Mount("modules.immunology.titer.routes:router", "/serum/titer", "免疫部-效价"),
    Mount("modules.immunology.cell.routes:router", "/serum/cell_inventory", "免疫部-细胞"),
    Mount("modules.mega_automation.routes:router", "/mega-automation", "镁伽自动化"),
    Mount("modules.molecular_cell.library_orders.routes:router", "/molecular-cell/library-orders", "分子与细胞-文库构建"),
    Mount("modules.molecular_cell.primer_catalog.routes:router", "/molecular-cell/library-orders/catalog",
          "分子与细胞-引物库"),
    Mount("modules.molecular_cell.transfection.routes:router", "/molecular-cell/transfection",
          "分子与细胞-转染与表达"),
    Mount("modules.order_sync.routes:router", "/order-experiment", "工单数据回传"),
    Mount("modules.order_sync.record_routes:router", "/mega-automation/order-sync", "镁伽自动化-回传记录"),
    Mount("modules.supernatant_receive.routes:router", "/protein-supernatant", "上清板布局接收"),
    Mount("modules.options.routes:router", "/options", "公共选项"),
    Mount("modules.home.routes:router", "/home", "首页"),
    Mount("modules.system.routes:router", "/system", "系统管理"),
)


def _index_permissions() -> dict[str, tuple[ModuleAccess, Permission]]:
    index: dict[str, tuple[ModuleAccess, Permission]] = {}
    for access in ACCESS:
        for permission in access.permissions:
            if permission.code in index:
                raise RuntimeError(f"权限码重复登记：{permission.code}")
            index[permission.code] = (access, permission)
    return index


def _index_features() -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for access in ACCESS:
        for flag in access.features:
            if flag["code"] in index:
                raise RuntimeError(f"功能开关重复登记：{flag['code']}")
            index[flag["code"]] = flag
    return index


def _merge_resources() -> dict[str, str]:
    labels: dict[str, str] = {}
    for access in ACCESS:
        for code, label in access.resources.items():
            if labels.get(code, label) != label:
                raise RuntimeError(f"资源码中文名冲突：{code}")
            labels[code] = label
    return labels


PERMISSION_INDEX = _index_permissions()
PERMISSIONS: dict[str, Permission] = {code: permission for code, (_access, permission) in PERMISSION_INDEX.items()}
# 业务模块（系统管理以外）的页面权限码；公共选项接口按“能打开任一业务页面”放行。
BUSINESS_PAGE_CODES: tuple[str, ...] = tuple(
    code for code, (access, permission) in PERMISSION_INDEX.items()
    if access.module != system.ACCESS.module and permission.type == "page"
)
FEATURE_INDEX = _index_features()
RESOURCE_LABELS = _merge_resources()
