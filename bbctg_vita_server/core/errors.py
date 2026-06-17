from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from core.response import error


class BusinessError(Exception):
    def __init__(self, message: str, code: int = 1, error_code: str | None = None) -> None:
        self.message = message
        self.code = code
        self.error_code = error_code
        super().__init__(message)


def _detail_to_message(detail: object) -> str:
    if isinstance(detail, str):
        return detail
    if isinstance(detail, list):
        parts = []
        for item in detail:
            if isinstance(item, dict):
                msg = item.get("msg")
                if msg:
                    parts.append(str(msg))
        if parts:
            return "；".join(parts)
    return str(detail)


def setup_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(BusinessError)
    async def handle_business_error(_request: Request, exc: BusinessError) -> JSONResponse:
        return JSONResponse(status_code=200, content=error(exc.message, exc.code, exc.error_code))

    @app.exception_handler(ValueError)
    async def handle_value_error(_request: Request, exc: ValueError) -> JSONResponse:
        return JSONResponse(status_code=200, content=error(str(exc)))

    @app.exception_handler(HTTPException)
    async def handle_http_exception(_request: Request, exc: HTTPException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=error(_detail_to_message(exc.detail)),
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(_request: Request, _exc: Exception) -> JSONResponse:
        return JSONResponse(status_code=500, content=error("服务器异常，请联系管理员"))
