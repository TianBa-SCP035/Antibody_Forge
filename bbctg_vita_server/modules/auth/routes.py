from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from core.vben_response import vben_success
from db.session import get_db
from modules.auth.service import build_user_info, get_development_user, login_with_yunzhijia_ticket

router = APIRouter()


@router.post("/login")
def login() -> dict:
    return vben_success({"accessToken": "dev-token"})


@router.post("/logout")
def logout() -> dict:
    return vben_success({"message": "ok"})


@router.post("/refresh")
def refresh_token() -> dict:
    return vben_success({"accessToken": "dev-token"})


@router.get("/codes")
def access_codes() -> dict:
    return vben_success(["*"])


@router.get("/user/info")
def user_info(db: Session = Depends(get_db)) -> dict:
    return vben_success(build_user_info(get_development_user(db)))


@router.get("/yunzhijia")
def yunzhijia_login(ticket: str = Query(...), db: Session = Depends(get_db)) -> dict:
    user = login_with_yunzhijia_ticket(db, ticket)
    return vben_success(build_user_info(user))
