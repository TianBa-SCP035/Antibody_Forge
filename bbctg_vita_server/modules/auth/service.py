from datetime import datetime

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from core.config import get_settings
from integrations.yunzhijia import YunzhijiaClient
from models.user import BbctgUser


def init_user(db: Session, user_data: dict) -> dict:
    user = db.scalar(select(BbctgUser).where(BbctgUser.openid == user_data["openid"]))
    if user:
        return user.to_dict()

    user = BbctgUser(
        username=user_data.get("username"),
        jobNo=user_data.get("jobNo"),
        openid=user_data.get("openid"),
        appid=user_data.get("appid"),
        eid=user_data.get("eid"),
        role=user_data.get("role", "guest"),
        role_menu=user_data.get("role_menu", "0"),
        create_date=datetime.now(),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user.to_dict()


def login_with_yunzhijia_ticket(db: Session, ticket: str) -> dict:
    settings = get_settings()
    client = YunzhijiaClient(settings.yunzhijia_appid, settings.yunzhijia_appsecret)
    result = client.acquire_user_context(ticket)
    user_context = result["data"]
    return init_user(
        db,
        {
            "username": user_context["username"],
            "appid": user_context["appid"],
            "eid": user_context["eid"],
            "jobNo": user_context["jobNo"],
            "openid": user_context["openid"],
            "role": "guest",
        },
    )


def get_development_user(db: Session) -> dict:
    settings = get_settings()
    user = None
    if settings.dev_user_openid:
        user = db.scalar(select(BbctgUser).where(BbctgUser.openid == settings.dev_user_openid))
    if user is None and settings.dev_user_name:
        user = db.scalar(
            select(BbctgUser).where(
                or_(
                    BbctgUser.username == settings.dev_user_name,
                    BbctgUser.username.like(f"%{settings.dev_user_name}%"),
                )
            )
        )
    if user:
        return user.to_dict()
    return {
        "role": ["ai", "DOGE"],
        "role_menu": ["0"],
        "username": settings.dev_user_name,
    }


def build_user_info(user: dict | None = None) -> dict:
    if user is None:
        user = {"role": ["ai", "DOGE"], "role_menu": ["0"], "username": "周科钢 Kegang Zhou"}
    return {
        "roles": user.get("role", ["admin"]),
        "roleMenu": user.get("role_menu", []),
        "avatar": "https://wpimg.wallstcn.com/f778738c-e4f8-4870-b634-56703b4acafe.gif",
        "realName": user.get("username") or user.get("name") or "开发用户",
        "username": user.get("username") or "dev",
        "homePath": "/serum/list",
        "token": "dev-token",
    }
