import logging

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import StatementError

from core.response import error

logger = logging.getLogger("app.errors")
UNEXPECTED_MESSAGE = "服务器异常，请联系管理员"


class BusinessError(ValueError):
    """业务错误：消息原样交给前端，HTTP 状态取 status_code；code / error_code 供前端区分具体情形。

    继承 ValueError：service 里按 ValueError 捕获、加上行号等前缀再抛的写法照常适用。
    裸 ValueError 视为业务校验失败，与本类同样返回 422。
    """

    status_code = 422

    def __init__(self, message: str, code: int = 1, error_code: str | None = None) -> None:
        self.message = message
        self.code = code
        self.error_code = error_code
        super().__init__(message)


class ForbiddenError(BusinessError):
    """按记录、字段判断的业务权限不足（接口级权限由 require 依赖检查）。"""

    status_code = 403


class NotFoundError(BusinessError):
    status_code = 404


class ConflictError(BusinessError):
    """并发冲突或归属校验失败。"""

    status_code = 409


def _validation_error(exc: Exception) -> ValueError | None:
    """字段类型在写库时抛出的校验错误会被 SQLAlchemy 包一层，取出原始消息。"""
    if isinstance(exc, StatementError) and isinstance(exc.orig, ValueError):
        return exc.orig
    return None


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
    """路由不写 try/except：业务异常按状态码返回，数据库会话由 get_db 回滚。"""

    @app.exception_handler(BusinessError)
    async def handle_business_error(_request: Request, exc: BusinessError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content=error(exc.message, exc.code, exc.error_code))

    @app.exception_handler(ValueError)
    async def handle_value_error(_request: Request, exc: ValueError) -> JSONResponse:
        return JSONResponse(status_code=422, content=error(str(exc)))

    @app.exception_handler(StatementError)
    async def handle_statement_error(request: Request, exc: StatementError) -> JSONResponse:
        inner = _validation_error(exc)
        if inner is not None:
            return JSONResponse(status_code=422, content=error(str(inner)))
        logger.error("unhandled error %s %s", request.method, request.url.path, exc_info=exc)
        return JSONResponse(status_code=500, content=error(UNEXPECTED_MESSAGE))

    @app.exception_handler(HTTPException)
    async def handle_http_exception(_request: Request, exc: HTTPException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=error(_detail_to_message(exc.detail)),
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        logger.error("unhandled error %s %s", request.method, request.url.path, exc_info=exc)
        return JSONResponse(status_code=500, content=error(UNEXPECTED_MESSAGE))
