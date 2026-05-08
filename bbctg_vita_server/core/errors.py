from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from core.response import error


class BusinessError(Exception):
    def __init__(self, message: str, code: int = 50000) -> None:
        self.message = message
        self.code = code
        super().__init__(message)


def setup_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(BusinessError)
    async def handle_business_error(_request: Request, exc: BusinessError) -> JSONResponse:
        return JSONResponse(status_code=200, content=error(exc.message, exc.code))

    @app.exception_handler(Exception)
    async def handle_unexpected_error(_request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(status_code=500, content=error(str(exc)))
