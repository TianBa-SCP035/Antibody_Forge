import json
import logging
import re
import time
from collections.abc import Callable
from types import SimpleNamespace
from typing import Any

from fastapi import FastAPI, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from db.session import SessionLocal
from models.discovery import DiscoveryWorkbench
from models.immunology import (
    SerumElisaPlate,
    SerumFacsPlate,
    SerumFile,
    SerumImmProject,
    SerumImmWorkbench,
    SerumTiterOrder,
)
from models.mega_automation import MegaFlowWorkOrder
from models.system import SysOperationLog, SysPermission, SysPermissionApi, SysPermissionBundle, SysRole, SysUser
from modules.auth.security import decode_access_token
from modules.system.features import DEFAULT_FEATURE_INDEX

WRITE_METHODS = {"DELETE", "PATCH", "POST", "PUT"}
SKIP_PATHS = {"/api/system/operation_logs"}
ROW_ID_KEYS = (
    "id",
    "order_id",
    "project_id",
    "moved_id",
    "file_id",
    "plate_id",
    "user_id",
    "role_id",
)
FALLBACK_ID_KEYS = (
    "experiment_id",
    "bundle_code",
    "job_code",
)
TARGET_LABEL_KEYS = (
    "target_label",
    "display_name",
    "name",
    "username",
    "code",
    "orderNum",
    "experiment_id",
    "project_code",
    "project_name",
    "file_name",
    "new_name",
)
PROJECT_LIKE_RESOURCES = {
    "project",
    "project_status",
    "cage",
    "mouse",
    "cell",
    "titer",
    "titer_order",
    "file",
    "serum_workbench",
    "discovery_workbench",
}
# 身份 / 批量容器，不算「本次改了哪个字段」
META_BODY_KEYS = {
    "id",
    "order_id",
    "project_id",
    "moved_id",
    "file_id",
    "plate_id",
    "user_id",
    "role_id",
    "user_ids",
    "role_ids",
    "items",
    "mode",
    "experiment_id",
    "project_code",
    "project_name",
    "job_code",
    "bundle_code",
    "orderNum",
    "target_id",
    "target_label",
}
# 和主字段一起提交时不单独算一次改动：companion → 主字段
COMPANION_BODY_KEYS = {
    "target_codes": "target_name",
    "reviewer": "review_status",
}
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
        # 仅记录写操作意图；page/view 权限挂在 POST list 上时不要进操作日志
        if permission.action in {"view", "page"} or permission.type == "page":
            return None
        user = _get_request_user(db, request)
        path_params = _extract_path_params(mapping.path_pattern, request.url.path)
        operation_name = _resolve_operation_name(mapping.description, permission.name, request.url.path, body_data)
        operation_type = _resolve_operation_type(request.url.path, permission.action, body_data)
        target = _resolve_request_target(
            db,
            permission.resource,
            body_data,
            dict(request.query_params),
            path_params,
            request.url.path,
        )
        detail = {
            "permission_name": permission.name,
            "module": permission.module,
            "resource": permission.resource,
            "action": permission.action,
            "permission_action": permission.action,
            "method": request.method.upper(),
            "path": request.url.path,
        }
        if target.get("change"):
            detail["change"] = target["change"]
        if target.get("count"):
            detail["count"] = target["count"]
        return {
            "action": permission.code,
            "operation_name": operation_name,
            "operation_type": operation_type,
            "target_type": permission.resource,
            "target_id": target.get("id"),
            "target_label": target.get("label"),
            "detail": detail,
            "user_id": user.id if user else None,
            "username": user.username if user else None,
            "operator_name": user.display_name if user else None,
        }


_API_CACHE: tuple[float, list[SimpleNamespace]] | None = None
_API_CACHE_TTL = 60.0


def _cached_api_rows(db: Session) -> list[SimpleNamespace]:
    global _API_CACHE
    now = time.monotonic()
    if _API_CACHE and _API_CACHE[0] > now:
        return _API_CACHE[1]
    rows = [
        SimpleNamespace(
            method=row.method,
            path_pattern=row.path_pattern,
            permission_code=row.permission_code,
            description=row.description,
        )
        for row in db.scalars(select(SysPermissionApi).where(SysPermissionApi.status == "active"))
    ]
    _API_CACHE = (now + _API_CACHE_TTL, rows)
    return rows


def _match_permission_api(db: Session, method: str, path: str) -> list[SimpleNamespace]:
    return [row for row in _cached_api_rows(db) if row.method == method and _path_matches(row.path_pattern, path)]


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


def _choose_mapping(mappings: list[SimpleNamespace], body_data: dict) -> SimpleNamespace:
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


def _first_present(sources: tuple[dict, ...], keys: tuple[str, ...]) -> str | None:
    for source in sources:
        for key in keys:
            value = source.get(key)
            if value not in (None, ""):
                return str(value)
    return None


def _extract_target_id(body_data: dict, query_data: dict, path_data: dict | None = None) -> str | None:
    sources = (body_data, query_data, path_data or {})
    return _first_present(sources, ROW_ID_KEYS) or _first_present(sources, FALLBACK_ID_KEYS)


def _extract_target_label(body_data: dict) -> str | None:
    for key in TARGET_LABEL_KEYS:
        value = body_data.get(key)
        if value not in (None, ""):
            return str(value)
    return None


def _pick_label(*parts: Any) -> str | None:
    for part in parts:
        text = str(part or "").strip()
        if text:
            return text
    return None


def _row_by_id(db: Session, model: Any, target_id: str | None):
    if target_id and str(target_id).isdigit():
        return db.get(model, int(target_id))
    return None


def _project_by_id_or_experiment(db: Session, target_id: str | None):
    row = _row_by_id(db, SerumImmProject, target_id)
    if row:
        return row
    if target_id:
        return db.scalar(select(SerumImmProject).where(SerumImmProject.experiment_id == str(target_id)))
    return None


def _business_label(experiment_id: Any = None, project_code: Any = None, project_name: Any = None, extra: Any = None) -> str | None:
    return _pick_label(experiment_id, project_code, project_name, extra)


def _format_change_snippet(value: Any) -> str | None:
    if isinstance(value, dict):
        return None
    if isinstance(value, list):
        if any(isinstance(item, (dict, list)) for item in value):
            return None
        text = "、".join(str(item).strip() for item in value if str(item).strip())
    else:
        text = str(value or "").strip()
    if not text:
        return None
    return text if len(text) <= 40 else f"{text[:40]}…"


def _merged_payload(body_data: dict, first_item: dict) -> dict:
    return {**first_item, **{key: value for key, value in body_data.items() if key != "items"}}


def _batch_count(body_data: dict) -> int:
    for key in ("items", "user_ids", "targets", "pcs"):
        value = body_data.get(key)
        if isinstance(value, list) and value:
            return len(value)
    return 0


def _first_user_id(body_data: dict) -> str | None:
    user_ids = body_data.get("user_ids")
    if isinstance(user_ids, list) and user_ids:
        value = user_ids[0]
        if value not in (None, ""):
            return str(value)
    return None


def _is_protocol_key(key: str) -> bool:
    return key.startswith("_") or key in META_BODY_KEYS


def _narrow_change(source: dict, label: str | None) -> str | None:
    present = {
        key
        for key, value in source.items()
        if not _is_protocol_key(str(key)) and value not in (None, "")
    }
    keys = [key for key in present if COMPANION_BODY_KEYS.get(key) not in present]
    if len(keys) != 1:
        return None
    text = _format_change_snippet(source.get(keys[0]))
    if text and text != label:
        return text
    return None


def _resolve_request_target(
    db: Session,
    resource: str | None,
    body_data: dict,
    query_data: dict,
    path_data: dict,
    path: str,
) -> dict[str, Any]:
    items = body_data.get("items") if isinstance(body_data.get("items"), list) else None
    first_item = items[0] if items and isinstance(items[0], dict) else {}
    target_id = (
        _extract_target_id(body_data, query_data, path_data)
        or _extract_target_id(first_item, {}, {})
        or _first_user_id(body_data)
    )
    count = _batch_count(body_data)
    if resource == "flow_work_order":
        fallback = str(body_data["orderNum"]) if body_data.get("orderNum") else None
    elif resource in PROJECT_LIKE_RESOURCES:
        fallback = _business_label(
            body_data.get("experiment_id") or first_item.get("experiment_id"),
            body_data.get("project_code") or first_item.get("project_code"),
            body_data.get("project_name") or first_item.get("project_name"),
        )
    elif count <= 1:
        fallback = _extract_target_label(body_data) or _extract_target_label(first_item)
    else:
        fallback = None
    label = _resolve_target_label(db, resource, target_id) or fallback
    change = None
    if path.endswith("/features/jobs/run"):
        job_code = str(body_data.get("job_code") or "").strip()
        if job_code:
            default = DEFAULT_FEATURE_INDEX.get(job_code)
            label = str((default or {}).get("name") or job_code)
    elif count <= 1:
        change = _narrow_change(_merged_payload(body_data, first_item), label)
    return {"id": target_id, "label": label, "change": change, "count": count if count > 1 else None}


def _resolve_target_label(db: Session, resource: str | None, target_id: str | None) -> str | None:
    if not target_id:
        return None
    if resource in {"user", "sys_user"}:
        user = _row_by_id(db, SysUser, target_id)
        return (user.display_name or f"账号 {user.username}") if user else None
    if resource == "role":
        role = _row_by_id(db, SysRole, target_id)
        return (role.name or role.code) if role else None
    if resource in {"bundle", "permission"}:
        bundle = _row_by_id(db, SysPermissionBundle, target_id)
        if not bundle:
            bundle = db.scalar(select(SysPermissionBundle).where(SysPermissionBundle.code == target_id))
        return (bundle.name or bundle.code) if bundle else None
    if resource == "flow_work_order":
        order = _row_by_id(db, MegaFlowWorkOrder, target_id)
        return order.orderNum if order else None
    if resource == "discovery_workbench":
        row = _row_by_id(db, DiscoveryWorkbench, target_id)
        return _business_label(row.experiment_id, row.project_code) if row else None
    if resource == "serum_workbench":
        row = _row_by_id(db, SerumImmWorkbench, target_id)
        return _business_label(row.experiment_id, row.project_code, row.project_name) if row else None
    if resource == "titer_order":
        order = _row_by_id(db, SerumTiterOrder, target_id)
        return _business_label(order.experiment_id, extra=order.titer_order_id) if order else None
    if resource == "file":
        stored = _row_by_id(db, SerumFile, target_id)
        return _business_label(stored.experiment_id, extra=stored.file_name) if stored else None
    if resource == "titer":
        plate = _row_by_id(db, SerumFacsPlate, target_id) or _row_by_id(db, SerumElisaPlate, target_id)
        if plate:
            return _business_label(plate.experiment_id)
        return target_id if not str(target_id).isdigit() else None
    if resource in {"project", "project_status", "cage", "mouse", "cell"}:
        project = _project_by_id_or_experiment(db, target_id)
        return _business_label(project.experiment_id, project.project_code, project.project_name) if project else None
    return None


def _resolve_operation_name(description: str | None, permission_name: str, path: str, body_data: dict) -> str:
    if path == "/api/discovery/workbench/save_batch":
        return "批量保存发现工作台"
    if path == "/api/discovery/workbench/reorder":
        return "调整发现工作台排序"
    if path == "/api/serum/workbench/save_batch":
        return "批量保存免疫工作台"
    if path == "/api/serum/workbench/reorder":
        return "调整免疫工作台排序"
    if path.endswith("/save"):
        is_edit = bool(body_data.get("id"))
        if "users/save" in path:
            return "编辑用户" if is_edit else "新增用户"
        if "roles/save" in path:
            return "编辑角色" if is_edit else "新增角色"
        if "permission_bundles/save" in path:
            return "编辑权限包" if is_edit else "新增权限包"
        if path == "/api/serum/workbench/save":
            return "编辑免疫工作台" if is_edit else "新建免疫工作台"
        if path == "/api/discovery/workbench/save":
            return "编辑发现工作台" if is_edit else "新建发现工作台"
        if path == "/api/serum/save":
            return "编辑免疫项目" if is_edit else "新建免疫项目"
        if path == "/api/serum/titer/order/save":
            if not is_edit:
                return "新建效价工单"
            if "summary" in body_data:
                return "保存效价小结"
            if "priority" in body_data:
                return "保存检测优先级"
            if "titer_owners" in body_data:
                return "保存效价负责人"
            if any(key in body_data for key in ("test_dates", "serum_status", "remark")):
                return "保存效价工单检测记录"
            return "保存效价工单批次信息"
        if path == "/api/mega-automation/flow-work-orders/save":
            return "编辑流式工单" if is_edit else "新建流式工单"
    return description or permission_name


def _resolve_operation_type(path: str, permission_action: str | None, body_data: dict) -> str:
    if path.endswith("/delete"):
        return "delete"
    if path.endswith("/cancel"):
        return "cancel"
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
    if isinstance(payload, list) and payload and isinstance(payload[0], dict):
        payload = payload[0]
    elif isinstance(payload, dict) and isinstance(payload.get("items"), list) and payload["items"]:
        first = payload["items"][0]
        if isinstance(first, dict):
            payload = first
    if not isinstance(payload, dict):
        return
    if not context.get("target_id"):
        value = payload.get("id")
        if value not in (None, ""):
            context["target_id"] = str(value)
    if context.get("target_label"):
        return
    if context.get("target_type") == "flow_work_order" and payload.get("orderNum") not in (None, ""):
        context["target_label"] = str(payload["orderNum"])
        return
    context["target_label"] = _business_label(
        payload.get("experiment_id"),
        payload.get("project_code"),
        payload.get("project_name"),
        payload.get("orderNum"),
    )


def _extract_error_message(data: dict) -> str | None:
    nested = data.get("data") if isinstance(data.get("data"), dict) else {}
    message = data.get("message") or nested.get("message") or data.get("detail")
    return str(message) if message else None


def _parse_result(status_code: int, response_body: bytes) -> tuple[str, str | None]:
    try:
        data = json.loads(response_body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        if status_code >= 400:
            return "failed", f"HTTP {status_code}"
        return "success", None

    if status_code >= 400:
        if isinstance(data, dict):
            message = _extract_error_message(data)
            if message:
                return "failed", message
        return "failed", f"HTTP {status_code}"

    code = data.get("code") if isinstance(data, dict) else None
    if code in (0, None):
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
