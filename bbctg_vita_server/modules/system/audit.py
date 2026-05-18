import json
import logging
import re
from collections.abc import Callable
from typing import Any

from fastapi import FastAPI, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from db.session import SessionLocal
from models.system import SysOperationLog, SysPermission, SysPermissionApi, SysPermissionBundle, SysRole, SysUser
from modules.auth.security import decode_access_token

WRITE_METHODS = {"DELETE", "PATCH", "POST", "PUT"}
SKIP_PATHS = {"/api/system/operation_logs"}
TARGET_ID_KEYS = (
    "id",
    "project_id",
    "experiment_id",
    "file_id",
    "plate_id",
    "user_id",
    "role_id",
    "bundle_code",
)
TARGET_LABEL_KEYS = (
    "target_label",
    "display_name",
    "name",
    "username",
    "code",
    "project_name",
    "experiment_id",
    "file_name",
    "new_name",
)
logger = logging.getLogger(__name__)


def write_operation_log(
    db: Session,
    action: str,
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
    db.add(
        SysOperationLog(
            user_id=user.id if user else None,
            username=username or (user.username if user else None),
            operator_name=operator_name or (user.display_name if user else None),
            action=action,
            operation_name=operation_name,
            operation_type=operation_type,
            target_type=target_type,
            target_id=target_id,
            target_label=target_label,
            result=result,
            detail=detail or {},
            error_message=error_message,
        )
    )


def setup_audit_middleware(app: FastAPI) -> None:
    @app.middleware("http")
    async def audit_middleware(request: Request, call_next: Callable) -> Response:
        if not _should_audit(request):
            return await call_next(request)

        body = await _read_reusable_body(request)
        body_data = _parse_body(body, request.headers.get("content-type", ""))
        try:
            audit_context = _build_audit_context(request, body_data)
        except Exception:
            logger.exception("Failed to build audit context")
            audit_context = None
        if not audit_context:
            return await call_next(request)

        response = await call_next(request)
        response_body = b"".join([chunk async for chunk in response.body_iterator])
        result, error_message = _parse_result(response.status_code, response_body)
        _fill_target_from_response(audit_context, response_body)
        try:
            _write_audit_log(audit_context, result, error_message)
        except Exception:
            logger.exception("Failed to write audit log")
        return Response(
            content=response_body,
            status_code=response.status_code,
            headers=dict(response.headers),
            media_type=response.media_type,
        )


def _should_audit(request: Request) -> bool:
    return (
        request.method.upper() in WRITE_METHODS
        and request.url.path.startswith("/api/")
        and request.url.path not in SKIP_PATHS
    )


async def _read_reusable_body(request: Request) -> bytes:
    content_type = request.headers.get("content-type", "")
    if "multipart/form-data" in content_type:
        return b""
    body = await request.body()
    body_replayed = False

    async def receive() -> dict[str, Any]:
        nonlocal body_replayed
        if body_replayed:
            return {"type": "http.disconnect"}
        body_replayed = True
        return {"type": "http.request", "body": body, "more_body": False}

    request._receive = receive
    return body


_SENSITIVE_BODY_KEYS = frozenset(
    {
        "password",
        "oldPassword",
        "old_password",
        "newPassword",
        "new_password",
        "confirmPassword",
        "confirm_password",
    }
)


def _redact_sensitive_body(data: dict) -> dict:
    if not data:
        return data
    redacted = dict(data)
    for key in list(redacted):
        if key in _SENSITIVE_BODY_KEYS:
            redacted[key] = "***"
    return redacted


def _parse_body(body: bytes, content_type: str) -> dict:
    if not body or "application/json" not in content_type:
        return {}
    try:
        value = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return {}
    if not isinstance(value, dict):
        return {}
    return _redact_sensitive_body(value)


def _build_audit_context(request: Request, body_data: dict) -> dict | None:
    with SessionLocal() as db:
        mappings = _match_permission_api(db, request.method.upper(), request.url.path)
        if not mappings:
            return None
        mapping = _choose_mapping(mappings, body_data)
        permission = db.scalar(
            select(SysPermission).where(
                SysPermission.code == mapping.permission_code,
                SysPermission.status == "active",
            )
        )
        if not permission:
            return None
        user = _get_request_user(db, request)
        path_params = _extract_path_params(mapping.path_pattern, request.url.path)
        operation_name = _resolve_operation_name(mapping.description, permission.name, request.url.path, body_data)
        operation_type = _resolve_operation_type(request.url.path, permission.action, body_data)
        target_id = _extract_target_id(body_data, dict(request.query_params), path_params)
        target_label = _resolve_target_label(db, permission.resource, target_id, _extract_target_label(body_data))
        return {
            "action": permission.code,
            "operation_name": operation_name,
            "operation_type": operation_type,
            "target_type": permission.resource,
            "target_id": target_id,
            "target_label": target_label,
            "detail": {
                "permission_name": permission.name,
                "module": permission.module,
                "resource": permission.resource,
                "action": permission.action,
                "permission_action": permission.action,
                "method": request.method.upper(),
                "path": request.url.path,
            },
            "user_id": user.id if user else None,
            "username": user.username if user else None,
            "operator_name": user.display_name if user else None,
        }


def _match_permission_api(db: Session, method: str, path: str) -> list[SysPermissionApi]:
    rows = db.scalars(
        select(SysPermissionApi).where(SysPermissionApi.method == method, SysPermissionApi.status == "active")
    ).all()
    return [row for row in rows if _path_matches(row.path_pattern, path)]


def _path_matches(pattern: str, path: str) -> bool:
    regex = "^" + re.sub(r"\\\{[^/]+\\\}", r"[^/]+", re.escape(pattern)) + "$"
    return re.match(regex, path) is not None


def _extract_path_params(pattern: str, path: str) -> dict[str, str]:
    names = re.findall(r"\{([^/]+)\}", pattern)
    if not names:
        return {}
    regex = re.escape(pattern)
    for name in names:
        regex = regex.replace(r"\{" + name + r"\}", "([^/]+)")
    regex = "^" + regex + "$"
    match = re.match(regex, path)
    if not match:
        return {}
    return dict(zip(names, match.groups(), strict=False))


def _choose_mapping(mappings: list[SysPermissionApi], body_data: dict) -> SysPermissionApi:
    if len(mappings) == 1:
        return mappings[0]
    has_id = bool(body_data.get("id"))
    for mapping in mappings:
        if has_id and mapping.permission_code.endswith(".edit"):
            return mapping
        if not has_id and mapping.permission_code.endswith(".create"):
            return mapping
    return mappings[0]


def _get_request_user(db: Session, request: Request) -> SysUser | None:
    authorization = request.headers.get("authorization") or ""
    token = authorization.removeprefix("Bearer ").strip()
    payload = decode_access_token(token) if token else None
    if not payload:
        return None
    try:
        user_id = int(payload.get("sub"))
    except (TypeError, ValueError):
        return None
    return db.get(SysUser, user_id)


def _extract_target_id(body_data: dict, query_data: dict, path_data: dict | None = None) -> str | None:
    for source in (body_data, query_data, path_data or {}):
        for key in TARGET_ID_KEYS:
            value = source.get(key)
            if value not in (None, ""):
                return str(value)
    return None


def _extract_target_label(body_data: dict) -> str | None:
    for key in TARGET_LABEL_KEYS:
        value = body_data.get(key)
        if value not in (None, ""):
            return str(value)
    return None


def _resolve_target_label(db: Session, resource: str | None, target_id: str | None, fallback: str | None) -> str | None:
    if resource == "user" and target_id:
        user = db.get(SysUser, int(target_id)) if target_id.isdigit() else None
        if user:
            return user.display_name or f"账号 {user.username}"
    if resource == "role" and target_id:
        role = db.get(SysRole, int(target_id)) if target_id.isdigit() else None
        if role:
            return role.name or role.code
    if resource in {"bundle", "permission"} and target_id:
        bundle = db.get(SysPermissionBundle, int(target_id)) if target_id.isdigit() else None
        if not bundle:
            bundle = db.scalar(select(SysPermissionBundle).where(SysPermissionBundle.code == target_id))
        if bundle:
            return bundle.name or bundle.code
    return fallback


def _resolve_operation_name(description: str | None, permission_name: str, path: str, body_data: dict) -> str:
    if path.endswith("/save"):
        is_edit = bool(body_data.get("id"))
        if "users/save" in path:
            return "编辑用户" if is_edit else "新增用户"
        if "roles/save" in path:
            return "编辑角色" if is_edit else "新增角色"
        if "permission_bundles/save" in path:
            return "编辑权限包" if is_edit else "新增权限包"
        if path == "/api/serum/save":
            return "编辑血清项目" if is_edit else "新建血清项目"
    return description or permission_name


def _resolve_operation_type(path: str, permission_action: str | None, body_data: dict) -> str:
    if path.endswith("/delete"):
        return "delete"
    if path.endswith("/save"):
        return "update" if body_data.get("id") else "create"
    if "reset_password" in path:
        return "reset_password"
    if "batch_roles" in path:
        return "batch_update"
    if "permission_overrides" in path:
        return "update"
    if permission_action in {"create", "delete", "edit", "update"}:
        return "update" if permission_action == "edit" else permission_action
    return permission_action or "write"


def _fill_target_from_response(context: dict, response_body: bytes) -> None:
    try:
        data = json.loads(response_body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return
    payload = data.get("data") if isinstance(data, dict) else None
    if not isinstance(payload, dict):
        return
    if not context.get("target_id"):
        value = payload.get("id")
        if value not in (None, ""):
            context["target_id"] = str(value)
    if not context.get("target_label"):
        label = _extract_target_label(payload)
        if label:
            context["target_label"] = label


def _parse_result(status_code: int, response_body: bytes) -> tuple[str, str | None]:
    if status_code >= 400:
        return "failed", f"HTTP {status_code}"
    try:
        data = json.loads(response_body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return "success", None
    code = data.get("code") if isinstance(data, dict) else None
    if code in (0, 20000, None):
        return "success", None
    message = None
    if isinstance(data, dict):
        nested = data.get("data") if isinstance(data.get("data"), dict) else {}
        message = data.get("message") or nested.get("message")
    return "failed", str(message or code)


def _write_audit_log(context: dict, result: str, error_message: str | None) -> None:
    with SessionLocal() as db:
        db.add(
            SysOperationLog(
                user_id=context.get("user_id"),
                username=context.get("username"),
                operator_name=context.get("operator_name"),
                action=context["action"],
                operation_name=context.get("operation_name"),
                operation_type=context.get("operation_type"),
                target_type=context.get("target_type"),
                target_id=context.get("target_id"),
                target_label=context.get("target_label"),
                result=result,
                detail=context.get("detail") or {},
                error_message=error_message,
            )
        )
        db.commit()
