from __future__ import annotations

import logging
from typing import Any

import requests

from core.config import get_settings

logger = logging.getLogger(__name__)

LABILLION_LOGIN_PATH = "/api/automation/v1/login"
LABILLION_ORDERS_PATH = "/api/automation/v1/orders"
LABILLION_ORDERS_DELETE_PATH = "/api/automation/v1/orders/delete"
LABILLION_ORDER_STATUSES_PATH = "/api/automation/v1/orderstatuses"
LABILLION_CALLBACK_PATH = "/mega-automation/labillion/callback"
LABILLION_PLATFORM_ID = "c9e97cee-a00d-497e-8177-a8ae84c36510"
LABILLION_REQUEST_TIMEOUT = 5

PRIORITY_TO_LABILLION = {
    "high": "High",
    "normal": "Normal",
    "low": "Low",
}

_token_cache: str = ""


class LabillionError(Exception):
    pass


def _labillion_base_url() -> str:
    return str(get_settings().labillion_base_url or "").strip().rstrip("/")


def is_labillion_enabled() -> bool:
    return bool(_labillion_base_url())


def build_reply_address() -> str:
    base = str(get_settings().public_api_base_url or "").strip().rstrip("/")
    if not base:
        return ""
    return f"{base}{LABILLION_CALLBACK_PATH}"


def push_flow_work_order(payload: dict[str, Any]) -> None:
    base_url = _labillion_base_url()
    if not base_url:
        return

    reply_address = str(payload.get("replyAddress") or "").strip()
    if not reply_address:
        raise LabillionError("未配置 PUBLIC_API_BASE_URL，无法生成 replyAddress")

    body = _build_import_body(payload)
    settings = get_settings()
    client = LabillionClient(
        base_url=base_url,
        username=settings.labillion_username,
        password=settings.labillion_password,
    )
    client.import_order(body)


def delete_orders(dispatch_ids: list[str]) -> None:
    base_url = _labillion_base_url()
    if not base_url:
        return

    ids = [str(item or "").strip() for item in dispatch_ids if str(item or "").strip()]
    if not ids:
        raise LabillionError("缺少 dispatchId，无法删除订单")

    settings = get_settings()
    client = LabillionClient(
        base_url=base_url,
        username=settings.labillion_username,
        password=settings.labillion_password,
    )
    client.delete_orders(ids)


def query_order_statuses(dispatch_ids: list[str]) -> dict[str, dict[str, Any]]:
    base_url = _labillion_base_url()
    if not base_url:
        raise LabillionError("未配置 Labillion 服务地址")

    ids = [str(item or "").strip() for item in dispatch_ids if str(item or "").strip()]
    if not ids:
        return {}

    settings = get_settings()
    client = LabillionClient(
        base_url=base_url,
        username=settings.labillion_username,
        password=settings.labillion_password,
    )
    data = client.query_order_statuses(ids)
    return _normalize_status_query_result(data)


def _normalize_status_query_result(data: Any) -> dict[str, dict[str, Any]]:
    if not isinstance(data, dict):
        return {}
    result: dict[str, dict[str, Any]] = {}
    for dispatch_id, entry in data.items():
        key = str(dispatch_id or "").strip()
        if not key or not isinstance(entry, dict):
            continue
        result[key] = {
            "status": entry.get("status"),
            "progress": entry.get("progress"),
        }
    return result


def _build_import_body(payload: dict[str, Any]) -> dict[str, Any]:
    priority_key = str(payload.get("priority") or "normal").strip().lower()
    return {
        "orderName": payload.get("orderName") or "",
        "orderNum": payload.get("orderNum") or None,
        "priority": PRIORITY_TO_LABILLION.get(priority_key, "Normal"),
        "dispatchId": payload.get("dispatchId") or None,
        "orderType": payload.get("orderType") or "",
        "replyAddress": payload.get("replyAddress") or None,
        "orderDetail": payload.get("orderDetail"),
    }


class LabillionClient:
    def __init__(self, *, base_url: str, username: str, password: str) -> None:
        self.base_url = str(base_url or "").strip().rstrip("/")
        self.username = str(username or "").strip()
        self.password = str(password or "").strip()
        if not self.base_url:
            raise LabillionError("未配置 Labillion 服务地址")
        if not self.username or not self.password:
            raise LabillionError("未配置 Labillion 登录账号或密码")

    def import_order(self, body: dict[str, Any]) -> None:
        token = self._get_token()
        try:
            self._post(LABILLION_ORDERS_PATH, body, token=token)
        except LabillionError as exc:
            if "未授权" not in str(exc):
                raise
            global _token_cache
            _token_cache = ""
            token = self._get_token(force_refresh=True)
            self._post(LABILLION_ORDERS_PATH, body, token=token)

    def delete_orders(self, dispatch_ids: list[str]) -> None:
        token = self._get_token()
        try:
            self._post(LABILLION_ORDERS_DELETE_PATH, dispatch_ids, token=token)
        except LabillionError as exc:
            if "未授权" not in str(exc):
                raise
            global _token_cache
            _token_cache = ""
            token = self._get_token(force_refresh=True)
            self._post(LABILLION_ORDERS_DELETE_PATH, dispatch_ids, token=token)

    def query_order_statuses(self, dispatch_ids: list[str]) -> Any:
        token = self._get_token()
        try:
            return self._post(LABILLION_ORDER_STATUSES_PATH, dispatch_ids, token=token)
        except LabillionError as exc:
            if "未授权" not in str(exc):
                raise
            global _token_cache
            _token_cache = ""
            token = self._get_token(force_refresh=True)
            return self._post(LABILLION_ORDER_STATUSES_PATH, dispatch_ids, token=token)

    def _get_token(self, *, force_refresh: bool = False) -> str:
        global _token_cache
        if _token_cache and not force_refresh:
            return _token_cache

        response = self._request(
            "POST",
            LABILLION_LOGIN_PATH,
            json={
                "username": self.username,
                "password": self.password,
                "clientId": "web",
                "grantType": "password",
            },
            headers={"Accept-Language": "zh-CN"},
        )
        data = _parse_labillion_response(response)
        token = str(data or "").strip()
        if not token:
            raise LabillionError("Labillion 登录成功但未返回 Token")
        _token_cache = token
        return token

    def _post(self, path: str, body: Any, *, token: str) -> Any:
        response = self._request(
            "POST",
            path,
            json=body,
            headers={
                "Authorization": f"Bearer {token}",
                "Platform": LABILLION_PLATFORM_ID,
                "Accept-Language": "zh-CN",
            },
        )
        return _parse_labillion_response(response)

    def _request(self, method: str, path: str, **kwargs: Any) -> requests.Response:
        url = f"{self.base_url}{path}"
        try:
            response = requests.request(method, url, timeout=LABILLION_REQUEST_TIMEOUT, **kwargs)
        except requests.Timeout as exc:
            logger.exception("labillion request timed out: %s %s", method, url)
            raise LabillionError("连接 Labillion 服务超时") from exc
        except requests.RequestException as exc:
            logger.exception("labillion request failed: %s %s", method, url)
            raise LabillionError("无法连接 Labillion 服务") from exc

        if response.status_code == 401:
            raise LabillionError("Labillion 未授权，请检查账号或 Platform 配置")

        if response.status_code >= 400:
            message = _read_error_message(response)
            raise LabillionError(message or f"Labillion 请求失败（HTTP {response.status_code}）")

        return response


def _parse_labillion_response(response: requests.Response) -> Any:
    try:
        payload = response.json()
    except ValueError as exc:
        raise LabillionError("Labillion 响应不是合法 JSON") from exc

    if not isinstance(payload, dict):
        raise LabillionError("Labillion 响应格式异常")

    code = payload.get("code")
    if code != 200:
        message = str(payload.get("message") or "Labillion 业务处理失败").strip()
        raise LabillionError(message)

    return payload.get("data")


def _read_error_message(response: requests.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        return response.text.strip()
    if isinstance(payload, dict):
        return str(payload.get("message") or payload.get("detail") or "").strip()
    return ""
