from typing import Any


SUCCESS_CODE = 0
ERROR_CODE = 1


def success(data: Any = None, code: int = SUCCESS_CODE) -> dict[str, Any]:
    return {"code": code, "data": data}


def error(message: str, code: int = ERROR_CODE, error_code: str | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {"code": code, "message": message, "data": None}
    if error_code:
        payload["errorCode"] = error_code
    return payload
