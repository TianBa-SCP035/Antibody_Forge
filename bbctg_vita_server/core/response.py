from typing import Any


SUCCESS_CODE = 20000
ERROR_CODE = 50000


def success(data: Any = None, code: int = SUCCESS_CODE) -> dict[str, Any]:
    return {"code": code, "data": data}


def error(message: str, code: int = ERROR_CODE) -> dict[str, Any]:
    return {"code": code, "data": {"message": message}, "message": message}
