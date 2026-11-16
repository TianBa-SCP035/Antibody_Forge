from __future__ import annotations

import json
import logging
import re
import uuid
from typing import Any

from fastapi.routing import APIRoute
from starlette.concurrency import run_in_threadpool
from starlette.routing import Match

from db.session import SessionLocal
from modules.auth.security import decode_access_token
from modules.system.audit import write_operation_log
from modules.system.audit_config import WRITE_METHODS, is_readonly_post
from modules.system.audit_context import (
    AuditContext,
    reset_audit_context,
    set_audit_context,
)
from modules.system.audit_routes import route_audit
from modules.system.audit_session import all_label_fields

logger = logging.getLogger(__name__)
MAX_RESPONSE_CAPTURE = 64 * 1024
_BUSINESS_CODE_PREFIX = re.compile(
    rb'^\s*\{\s*"code"\s*:\s*(-?\d+)',
)


class AuditMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope: dict, receive, send) -> None:
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return
        method = str(scope.get("method") or "").upper()
        path = str(scope.get("path") or "")
        if method not in WRITE_METHODS or not path.startswith("/api/"):
            await self.app(scope, receive, send)
            return

        context = _build_context(method, path, _headers(scope), scope)
        scope.setdefault("state", {})["request_id"] = context.request_id
        token = set_audit_context(context)
        status_code = 500
        response_is_json = False
        response_truncated = False
        captured = bytearray()
        finalized = False

        async def send_wrapper(message: dict) -> None:
            nonlocal status_code, response_is_json, response_truncated, finalized
            if message["type"] == "http.response.start":
                status_code = int(message.get("status") or 200)
                response_headers = {
                    key.decode("latin-1").lower(): value.decode("latin-1")
                    for key, value in message.get("headers", [])
                }
                response_is_json = "application/json" in response_headers.get("content-type", "")
            elif message["type"] == "http.response.body" and response_is_json:
                chunk = message.get("body") or b""
                remaining = MAX_RESPONSE_CAPTURE - len(captured)
                if remaining > 0:
                    captured.extend(chunk[:remaining])
                if len(chunk) > remaining:
                    response_truncated = True
            await send(message)
            if message["type"] == "http.response.body" and not message.get("more_body") and not finalized:
                finalized = True
                await run_in_threadpool(
                    _finalize_attempt,
                    context,
                    status_code,
                    bytes(captured),
                    response_truncated,
                )

        try:
            await self.app(scope, receive, send_wrapper)
        except Exception as exc:
            if not finalized and not context.has_committed_result("failed"):
                await run_in_threadpool(
                    _write_attempt_log,
                    context,
                    "failed",
                    str(exc) or "Unhandled server error",
                )
            raise
        finally:
            reset_audit_context(token)


def _headers(scope: dict) -> dict[str, str]:
    return {
        key.decode("latin-1").lower(): value.decode("latin-1")
        for key, value in scope.get("headers", [])
    }


def _build_context(method: str, path: str, headers: dict[str, str], scope: dict) -> AuditContext:
    route = _match_route(scope)
    spec = route_audit(route) if route else None
    suppress_noop = is_readonly_post(method, path) or bool(spec and spec.quiet)
    actions = spec.actions if spec and not suppress_noop else ()

    token = headers.get("authorization", "").removeprefix("Bearer ").strip()
    payload = decode_access_token(token) if token else None
    try:
        user_id = int(payload.get("sub")) if payload else None
    except (TypeError, ValueError):
        user_id = None
    username = str(payload.get("username") or "")[:64] if payload else None
    source = _source_for_path(path, bool(payload))
    client = scope.get("client")
    ip_address = str(client[0])[:64] if client else None
    return AuditContext(
        request_id=scope.get("state", {}).get("request_id") or uuid.uuid4().hex,
        source=source,
        method=method,
        path=path,
        actions=actions,
        user_id=user_id,
        username=username or None,
        ip_address=ip_address,
        fallback_action=f"{method} {path}",
        fallback_name=(spec and spec.fallback_name) or f"{method} {path}",
        fallback_resource=spec.fallback_resource if spec else None,
        suppress_noop=suppress_noop,
    )


def _match_route(scope: dict) -> APIRoute | None:
    app = scope.get("app")
    for route in getattr(app, "routes", ()):
        if isinstance(route, APIRoute) and route.matches(scope)[0] == Match.FULL:
            return route
    return None


def _source_for_path(path: str, has_user_token: bool) -> str:
    if path.startswith("/api/order-experiment/") or path == "/api/mega-automation/labillion/callback":
        return "device"
    return "user" if has_user_token else "system"


def _finalize_attempt(
    context: AuditContext,
    status_code: int,
    body: bytes,
    response_truncated: bool = False,
) -> None:
    result, error_message = _parse_result(
        status_code,
        body,
        response_truncated=response_truncated,
    )
    if context.has_committed_result(result):
        return
    if result == "failed" or context.explicitly_audited:
        _write_attempt_log(context, result, error_message, body)


def _parse_result(
    status_code: int,
    body: bytes,
    *,
    response_truncated: bool = False,
) -> tuple[str, str | None]:
    if status_code >= 400:
        fallback = f"HTTP {status_code}"
    else:
        fallback = None
    if not body:
        return ("failed", fallback) if fallback else ("success", None)
    try:
        data = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        if response_truncated:
            if fallback:
                return "failed", fallback
            match = _BUSINESS_CODE_PREFIX.match(body)
            if match and int(match.group(1)) != 0:
                code = match.group(1).decode("ascii")
                return "failed", code
            return "success", None
        return ("failed", fallback) if fallback else ("success", None)
    if status_code >= 400:
        return "failed", _error_message(data) or fallback
    if isinstance(data, dict) and data.get("code") not in (None, 0):
        return "failed", _error_message(data) or str(data.get("code"))
    return "success", None


def _error_message(data: Any) -> str | None:
    if not isinstance(data, dict):
        return None
    nested = data.get("data") if isinstance(data.get("data"), dict) else {}
    value = data.get("message") or data.get("detail") or nested.get("message")
    return str(value)[:2000] if value else None


def _target_from_response(body: bytes) -> tuple[str | None, str | None]:
    try:
        data = json.loads(body.decode("utf-8")).get("data")
    except (UnicodeDecodeError, json.JSONDecodeError, AttributeError):
        return None, None
    if not isinstance(data, dict):
        return None, None
    entity_id = data.get("id")
    label = next((data[key] for key in all_label_fields() if data.get(key) not in (None, "")), None)
    return (
        str(entity_id)[:64] if entity_id not in (None, "") else None,
        str(label)[:255] if label not in (None, "") else None,
    )


def _write_attempt_log(
    context: AuditContext,
    result: str,
    error_message: str | None,
    body: bytes = b"",
) -> None:
    action = context.select_action("update")
    target_id, target_label = (
        _target_from_response(body) if result == "success" else (None, None)
    )
    try:
        with SessionLocal() as db:
            write_operation_log(
                db,
                action.code,
                username=context.username,
                operator_name=context.operator_name,
                operation_name=(action.name or action.code)[:128],
                operation_type=_normalized_operation_type(action.operation_type),
                target_type=action.resource,
                target_id=target_id,
                target_label=target_label,
                result=result,
                detail={
                    "changed": False,
                    "method": context.method,
                    "path": context.path,
                },
                error_message=error_message,
            )
            db.commit()
    except Exception:
        logger.exception("Failed to write audit attempt log")


def _normalized_operation_type(value: str | None) -> str:
    if value == "create":
        return "create"
    if value == "delete":
        return "delete"
    return "update"
