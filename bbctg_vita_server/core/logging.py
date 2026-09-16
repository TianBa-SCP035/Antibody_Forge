import json
import logging
import re
import time
import uuid
from logging.handlers import RotatingFileHandler
from pathlib import Path

from fastapi import FastAPI, Request

from core.config import get_settings

REDACTED = "[REDACTED]"
SENSITIVE_FIELD_NAMES = {
    "access_token",
    "api_key",
    "appsecret",
    "authorization",
    "cookie",
    "new_password",
    "old_password",
    "passwd",
    "password",
    "password_hash",
    "private_key",
    "refresh_token",
    "secret",
    "session",
    "session_id",
    "ticket",
    "token",
}


def is_sensitive_key(key: object) -> bool:
    normalized = re.sub(r"(?<!^)(?=[A-Z])", "_", str(key)).lower().replace("-", "_")
    return (
        normalized in SENSITIVE_FIELD_NAMES
        or normalized.endswith(("_password", "_password_hash", "_private_key", "_secret", "_token"))
    )


_is_sensitive_key = is_sensitive_key


def _redact_sensitive_values(value):
    if isinstance(value, dict):
        return {key: REDACTED if _is_sensitive_key(key) else _redact_sensitive_values(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_redact_sensitive_values(item) for item in value]
    return value


def _sanitize_body_for_log(raw: bytes, content_type: str):
    if not raw:
        return None
    if "application/json" not in content_type:
        return {"note": "non-json body skipped", "bytes": len(raw)}
    try:
        data = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return {"note": "invalid json body skipped", "bytes": len(raw)}
    summary = {"bytes": len(raw), "json_type": type(data).__name__}
    if isinstance(data, dict):
        summary["fields"] = sorted(str(key) for key in data)
    elif isinstance(data, list):
        summary["items"] = len(data)
        if data and isinstance(data[0], dict):
            summary["item_fields"] = sorted(str(key) for key in data[0])
    return summary


def setup_logging(app: FastAPI) -> None:
    settings = get_settings()
    log_dir = Path(settings.repository_root) / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    handler = RotatingFileHandler(
        log_dir / "app.log",
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    if not any(isinstance(item, RotatingFileHandler) for item in root_logger.handlers):
        root_logger.addHandler(handler)

    @app.middleware("http")
    async def request_logging_middleware(request: Request, call_next):
        request_id = getattr(request.state, "request_id", None) or uuid.uuid4().hex
        request.state.request_id = request_id
        start_time = time.time()

        body_info = None
        if request.method not in {"GET", "HEAD", "OPTIONS"}:
            content_type = request.headers.get("content-type", "")
            if "multipart/form-data" in content_type:
                body_info = {"note": "files uploaded, body skipped"}
            else:
                raw = await request.body()
                if raw:
                    body_info = _sanitize_body_for_log(raw, content_type)

                body_replayed = False

                async def receive():
                    nonlocal body_replayed
                    if body_replayed:
                        return {"type": "http.disconnect"}
                    body_replayed = True
                    return {"type": "http.request", "body": raw, "more_body": False}

                request = Request(request.scope, receive)

        logging.info(
            "REQ %s",
            json.dumps(
                {
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "query": _redact_sensitive_values(dict(request.query_params)),
                    "remote_addr": request.client.host if request.client else None,
                    "content_type": request.headers.get("content-type"),
                    "body": body_info,
                },
                ensure_ascii=False,
            ),
        )

        response = await call_next(request)
        cost_ms = int((time.time() - start_time) * 1000)
        response.headers["X-Request-ID"] = request_id
        logging.info(
            "RESP %s",
            json.dumps(
                {
                    "request_id": request_id,
                    "status_code": response.status_code,
                    "cost_ms": cost_ms,
                },
                ensure_ascii=False,
            ),
        )
        return response
