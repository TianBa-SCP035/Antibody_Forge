import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from db.session import get_db
from modules.auth.external import require_supernatant_caller
from modules.supernatant_receive import service
from modules.system.audit_context import AuditAction
from modules.system.audit_routes import audit

router = APIRouter()
logger = logging.getLogger(__name__)


# 按合成公司的约定 code 1 成功、0 失败，和本系统统一响应相反，所以错误不交给全局异常处理。
def partner_reply(status_code: int, code: int, msg: str) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"code": code, "msg": msg, "data": None})


async def raw_body(request: Request) -> bytes:
    return await request.body()


@router.post(
    "/receive",
    dependencies=[audit(AuditAction("supernatant.plate.receive", "接收上清板布局", "update", "supernatant_plate"))],
)
def receive_supernatant_plates(
    request: Request,
    raw: bytes = Depends(raw_body),
    db: Session = Depends(get_db),
) -> JSONResponse:
    try:
        require_supernatant_caller(request)
    except HTTPException as exc:
        return partner_reply(exc.status_code, 0, str(exc.detail))
    try:
        service.receive(db, raw)
    except service.SupernatantReceiveError as exc:
        return partner_reply(400, 0, exc.message)
    except Exception:
        db.rollback()
        logger.exception("supernatant plate receive failed")
        return partner_reply(500, 0, "服务端异常，请稍后重试")
    return partner_reply(200, 1, "success")
