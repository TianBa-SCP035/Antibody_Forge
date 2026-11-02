"""外部系统（设备、第三方平台）调用的来源校验。

令牌和 IP 白名单都在配置里，留空表示不校验该项；两项都配了就都要满足。
令牌只认请求头：放在 URL 里会进 Nginx 访问日志。
"""

import hmac

from fastapi import HTTPException, Request

from core.config import get_settings

CALLBACK_TOKEN_HEADER = "X-Callback-Token"


def _ip_list(raw: str) -> set[str]:
    return {item.strip() for item in str(raw or "").split(",") if item.strip()}


def check_external_caller(request: Request, token: str, ips: str) -> None:
    expected = str(token or "").strip()
    if expected:
        supplied = request.headers.get(CALLBACK_TOKEN_HEADER) or ""
        if not hmac.compare_digest(supplied.strip().encode("utf-8"), expected.encode("utf-8")):
            raise HTTPException(status_code=401, detail="调用方校验失败")
    allowed = _ip_list(ips)
    if allowed:
        client_ip = request.client.host if request.client else ""
        if client_ip not in allowed:
            raise HTTPException(status_code=403, detail="调用方不在允许列表")


def require_labillion_caller(request: Request) -> None:
    settings = get_settings()
    check_external_caller(request, settings.labillion_callback_token, settings.labillion_callback_ips)


def require_order_sync_caller(request: Request) -> None:
    settings = get_settings()
    check_external_caller(request, settings.order_sync_token, settings.order_sync_ips)
