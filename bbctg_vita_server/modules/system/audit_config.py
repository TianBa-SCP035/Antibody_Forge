from __future__ import annotations

import re

from sqlalchemy import Engine, select, text
from sqlalchemy.orm import Session

from models.system import SysPermission, SysPermissionApi
from modules.system.audit_context import AuditAction

WRITE_METHODS = frozenset({"DELETE", "PATCH", "POST", "PUT"})
_DATABASE_FIELD_LABELS: dict[tuple[str, str], str] = {}
_REQUIRED_AUDIT_COLUMNS = {
    ("sys_operation_log", "request_id"),
    ("sys_operation_log", "source"),
    ("sys_operation_log", "ip_address"),
    ("sys_operation_log", "affected_count"),
    ("sys_operation_log", "detail"),
    ("sys_operation_log_item", "id"),
    ("sys_operation_log_item", "log_id"),
    ("sys_operation_log_item", "entity_type"),
    ("sys_operation_log_item", "table_name"),
    ("sys_operation_log_item", "entity_id"),
    ("sys_operation_log_item", "entity_label"),
    ("sys_operation_log_item", "change_type"),
    ("sys_operation_log_item", "change_count"),
    ("sys_operation_log_item", "changes"),
}

# 查询、普通导出和会话管理：不记录无变化日志。
INTENTIONALLY_IGNORED_ROUTES = frozenset(
    {
        ("POST", "/api/atlas/targets/list"),
        ("POST", "/api/auth/logout"),
        ("POST", "/api/auth/refresh"),
        ("POST", "/api/discovery/workbench/export_list"),
        ("POST", "/api/discovery/workbench/list"),
        ("POST", "/api/mega-automation/flow-work-orders/by-source"),
        ("POST", "/api/mega-automation/flow-work-orders/export"),
        ("POST", "/api/mega-automation/flow-work-orders/list"),
        ("POST", "/api/serum/export_list"),
        ("POST", "/api/serum/export_mouse"),
        ("POST", "/api/serum/export_scheme"),
        ("POST", "/api/serum/export_scheme_pdf"),
        ("POST", "/api/serum/list"),
        ("POST", "/api/serum/titer/elisa/plate/list"),
        ("POST", "/api/serum/titer/file/list"),
        ("POST", "/api/serum/titer/order/export"),
        ("POST", "/api/serum/titer/order/list"),
        ("POST", "/api/serum/titer/plate/list"),
        ("POST", "/api/serum/workbench/export_list"),
        ("POST", "/api/serum/workbench/list"),
    }
)

# 不依赖 sys_permission_api，由登录显式日志或 Session 捕获负责。
LABILLION_CALLBACK_AUDIT_ACTION = AuditAction(
    code="mega.labillion.callback",
    name="Labillion 状态回调",
    operation_type="update",
    resource="MegaFlowWorkOrderDispatch",
)
LABILLION_STATUS_SYNC_AUDIT_ACTION = AuditAction(
    code="mega.labillion.status_sync",
    name="同步镁伽工单状态",
    operation_type="update",
    resource="MegaFlowWorkOrder",
)
SYSTEM_OR_MANUAL_AUDIT_ROUTES: dict[
    tuple[str, str],
    AuditAction | None,
] = {
    ("POST", "/api/auth/login"): None,
    ("POST", "/api/auth/user/change_password"): None,
    ("PUT", "/api/auth/user/profile"): None,
    (
        "POST",
        "/api/mega-automation/flow-work-orders/{order_id}/sync-labillion-status",
    ): LABILLION_STATUS_SYNC_AUDIT_ACTION,
    (
        "POST",
        "/api/mega-automation/labillion/callback",
    ): LABILLION_CALLBACK_AUDIT_ACTION,
    ("POST", "/api/order-experiment/sync"): None,
}


AUDIT_SET_LIKE_FIELDS: dict[str, frozenset[str]] = {
    "DiscoveryWorkbench": frozenset({"target_codes"}),
    "SerumImmProject": frozenset({"target_codes"}),
    "SerumImmWorkbench": frozenset({"target_codes"}),
    "SerumTiterOrder": frozenset({"test_dates", "titer_owners"}),
}


def get_audit_set_like_fields(
    entity_type: str,
    table_name: str,
) -> frozenset[str]:
    return AUDIT_SET_LIKE_FIELDS.get(
        entity_type,
        AUDIT_SET_LIKE_FIELDS.get(table_name, frozenset()),
    )


def load_audit_action_mappings(
    db: Session,
) -> tuple[tuple[str, str, AuditAction], ...]:
    rows = db.execute(
        select(SysPermissionApi, SysPermission)
        .join(
            SysPermission,
            SysPermission.code == SysPermissionApi.permission_code,
        )
        .where(
            SysPermissionApi.status == "active",
            SysPermission.status == "active",
        )
    ).all()
    return tuple(
        (
            mapping.method.upper(),
            mapping.path_pattern,
            AuditAction(
                code=permission.code,
                name=mapping.description or permission.name,
                operation_type=permission.action,
                resource=permission.resource,
            ),
        )
        for mapping, permission in rows
        if permission.type != "page"
        and permission.action not in {"page", "view"}
    )


def load_database_field_labels(engine: Engine) -> int:
    """Load labels and validate audit V2 schema with one startup query."""
    if engine.dialect.name != "mysql":
        return 0
    try:
        with engine.connect() as connection:
            rows = connection.execute(
                text(
                    """
                    SELECT TABLE_NAME, COLUMN_NAME, COLUMN_COMMENT
                    FROM INFORMATION_SCHEMA.COLUMNS
                    WHERE TABLE_SCHEMA = DATABASE()
                    """
                )
            ).all()
    except Exception as exc:
        raise RuntimeError("Unable to validate audit V2 database schema") from exc

    available = {
        (str(table_name), str(column_name))
        for table_name, column_name, _comment in rows
    }
    missing = sorted(_REQUIRED_AUDIT_COLUMNS - available)
    if missing:
        names = ", ".join(f"{table}.{column}" for table, column in missing)
        raise RuntimeError(f"Audit V2 database schema is incomplete: {names}")

    labels = {
        (str(table_name), str(column_name)): str(comment).strip()
        for table_name, column_name, comment in rows
        if str(comment or "").strip()
    }
    _DATABASE_FIELD_LABELS.clear()
    _DATABASE_FIELD_LABELS.update(labels)
    return len(labels)


def get_audit_field_label(
    table_name: str,
    field_name: str,
    *,
    orm_comment: str | None = None,
) -> str:
    return (
        _DATABASE_FIELD_LABELS.get((table_name, field_name), "")
        or str(orm_comment or "").strip()
        or field_name
    )


def audit_path_matches(pattern: str, path: str) -> bool:
    regex = "^" + re.sub(r"\\\{[^/]+\\\}", r"[^/]+", re.escape(pattern)) + "$"
    return re.match(regex, path) is not None
