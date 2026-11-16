from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.routing import APIRoute

from modules.system.audit_config import WRITE_METHODS, is_readonly_post
from modules.system.audit_routes import route_audit

logger = logging.getLogger(__name__)


def unclassified_write_routes(app: FastAPI) -> set[tuple[str, str]]:
    """没有审计声明、也不是标准只读后缀的写接口。"""
    return {
        (method, route.path)
        for route in app.routes
        if isinstance(route, APIRoute) and route.path.startswith("/api/") and route_audit(route) is None
        for method in route.methods & WRITE_METHODS
        if not is_readonly_post(method, route.path)
    }


def warn_unclassified_write_routes(app: FastAPI) -> None:
    unknown = sorted(unclassified_write_routes(app))
    if unknown:
        logger.warning("Unclassified write routes for audit: %s", unknown)
