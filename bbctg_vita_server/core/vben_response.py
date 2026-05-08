from typing import Any


def vben_success(data: Any = None) -> dict[str, Any]:
    return {"code": 0, "data": data}


def vben_error(message: str, code: int = 1) -> dict[str, Any]:
    return {"code": code, "message": message, "data": None}
