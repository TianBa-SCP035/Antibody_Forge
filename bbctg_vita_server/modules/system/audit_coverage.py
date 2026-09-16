from __future__ import annotations

import logging
from collections.abc import Iterable

from fastapi import FastAPI

from db.session import SessionLocal
from modules.system.audit_config import (
    INTENTIONALLY_IGNORED_ROUTES,
    SYSTEM_OR_MANUAL_AUDIT_ROUTES,
    WRITE_METHODS,
    audit_path_matches,
    load_audit_action_mappings,
)

logger = logging.getLogger(__name__)


def unclassified_write_routes(
    app: FastAPI,
    mappings: Iterable[tuple[str, str]] | None = None,
) -> set[tuple[str, str]]:
    routes = {
        (method, route.path)
        for route in app.routes
        for method in (getattr(route, "methods", None) or set())
        if method in WRITE_METHODS and route.path.startswith("/api/")
    }
    if mappings is None:
        with SessionLocal() as db:
            mappings = [
                (method, path)
                for method, path, _action in load_audit_action_mappings(db)
            ]
    mapping_list = list(mappings)
    mapped = {
        (method, path)
        for method, path in routes
        if any(method == mapped_method and audit_path_matches(pattern, path) for mapped_method, pattern in mapping_list)
    }
    known = (
        mapped
        | INTENTIONALLY_IGNORED_ROUTES
        | set(SYSTEM_OR_MANUAL_AUDIT_ROUTES)
    )
    return routes - known


def warn_unclassified_write_routes(app: FastAPI) -> None:
    try:
        unknown = sorted(unclassified_write_routes(app))
    except Exception:
        logger.exception("Failed to validate audit route coverage")
        return
    if unknown:
        logger.warning("Unclassified write routes for audit: %s", unknown)
