from __future__ import annotations

from sqlalchemy import Engine, text

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

# 标准只读 POST 后缀（查询、导出、统计）：路由上不用声明审计，没有数据变化不记日志。
READ_ONLY_POST_SUFFIXES = (
    "/list",
    "/column_values",
    "/export_list",
    "/export",
    "/stats",
)


def is_readonly_post(method: str, path: str) -> bool:
    return method.upper() == "POST" and path.endswith(READ_ONLY_POST_SUFFIXES)


AUDIT_SET_LIKE_FIELDS: dict[str, frozenset[str]] = {
    "MolecularLibraryOrder": frozenset({"plate_nos", "target_codes"}),
    "DiscoveryWorkbench": frozenset({"target_codes"}),
    "DiscoverySynthesisOrder": frozenset({"target_codes"}),
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


def load_database_field_labels(engine: Engine) -> int:
    """启动时用一次查询加载字段名并校验审计 V2 表结构。"""
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
