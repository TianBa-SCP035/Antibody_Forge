from fastapi import Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from db.session import get_db
from models.system import SysUser
from modules.auth.security import decode_access_token


def get_current_user(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> SysUser:
    token = _extract_bearer_token(authorization)
    payload = decode_access_token(token) if token else None
    if not payload:
        raise HTTPException(status_code=401, detail="登录已失效，请重新登录")

    user_id = payload.get("sub")
    user = db.scalar(select(SysUser).where(SysUser.id == int(user_id), SysUser.status == "active"))
    if not user:
        raise HTTPException(status_code=401, detail="用户不存在或已禁用")
    return user


def _extract_bearer_token(authorization: str | None) -> str | None:
    if not authorization:
        return None
    prefix = "Bearer "
    if authorization.startswith(prefix):
        return authorization[len(prefix) :].strip()
    return authorization.strip()
