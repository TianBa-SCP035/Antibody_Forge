from __future__ import annotations

from fastapi import FastAPI
from sqlalchemy.orm import Session

from models.system import SysOperationLog, SysUser
from modules.system.audit_context import get_audit_context
from modules.system.audit_session import stage_audit_outcome


def write_operation_log(
    db: Session,
    action: str,
    *,
    target_type: str | None = None,
    target_id: str | None = None,
    detail: dict | None = None,
    user: SysUser | None = None,
    username: str | None = None,
    operator_name: str | None = None,
    operation_name: str | None = None,
    operation_type: str | None = None,
    target_label: str | None = None,
    result: str = "success",
    error_message: str | None = None,
) -> None:
    """Write explicit events such as authentication attempts.

    ORM entity changes are captured automatically by audit_session.
    """
    context = get_audit_context()
    source = context.source if context else "system"
    if source == "system" and (user or username):
        source = "user"
    user_id = user.id if user else context.user_id if context else None
    log_username = username or (user.username if user else None) or (
        context.username if context else None
    )
    log_operator_name = operator_name or (user.display_name if user else None) or (
        context.operator_name if context else None
    )
    log = SysOperationLog(
        request_id=context.request_id if context else None,
        user_id=user_id,
        username=log_username,
        operator_name=log_operator_name,
        source=source,
        ip_address=context.ip_address if context else None,
        action=action[:128],
        operation_name=operation_name,
        operation_type=operation_type,
        target_type=target_type,
        target_id=target_id,
        target_label=target_label,
        result=result,
        affected_count=1 if target_id else 0,
        detail=detail or {},
        error_message=error_message,
    )
    db.add(log)
    stage_audit_outcome(db, log, context, explicit=True)


def setup_audit_middleware(app: FastAPI) -> None:
    from modules.system.audit_middleware import AuditMiddleware
    from modules.system.audit_session import setup_session_audit

    setup_session_audit()
    app.add_middleware(AuditMiddleware)
