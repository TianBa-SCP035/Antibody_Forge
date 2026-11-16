from __future__ import annotations

import logging
from collections.abc import Iterable

from fastapi.routing import APIRoute

from modules.system.audit_config import WRITE_METHODS, is_readonly_post
from modules.system.audit_routes import route_audit

logger = logging.getLogger(__name__)


def unclassified_write_routes(routes: Iterable[tuple[str, APIRoute]]) -> set[tuple[str, str]]:
    """没有审计声明、也不是标准只读后缀的写接口。routes 为（完整路径，路由）。"""
    return {
        (method, path)
        for path, route in routes
        if path.startswith("/api/") and route_audit(route) is None
        for method in route.methods & WRITE_METHODS
        if not is_readonly_post(method, path)
    }


def warn_unclassified_write_routes(routes: Iterable[tuple[str, APIRoute]]) -> None:
    unknown = sorted(unclassified_write_routes(routes))
    if unknown:
        logger.warning("Unclassified write routes for audit: %s", unknown)
