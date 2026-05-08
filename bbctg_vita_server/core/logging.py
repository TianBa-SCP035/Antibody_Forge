import json
import logging
import time
import uuid
from logging.handlers import RotatingFileHandler
from pathlib import Path

from fastapi import FastAPI, Request

from core.config import get_settings

MAX_BODY_LOG = 2000


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
        request_id = uuid.uuid4().hex[:12]
        start_time = time.time()
        request.state.request_id = request_id

        body_info = None
        if request.method not in {"GET", "HEAD", "OPTIONS"}:
            content_type = request.headers.get("content-type", "")
            if "multipart/form-data" in content_type:
                body_info = {"note": "files uploaded, body skipped"}
            else:
                raw = await request.body()
                if raw:
                    text = raw.decode("utf-8", errors="replace")
                    body_info = text[:MAX_BODY_LOG]

                async def receive():
                    return {"type": "http.request", "body": raw, "more_body": False}

                request = Request(request.scope, receive)

        logging.info(
            "REQ %s",
            json.dumps(
                {
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "query": dict(request.query_params),
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
