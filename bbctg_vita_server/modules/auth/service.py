import hashlib
import re
import secrets
from pathlib import Path

from fastapi import HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from core.config import get_settings
from core.errors import NotFoundError
from integrations.drm_service import decrypt_upload_file_if_available
from integrations.yunzhijia import YunzhijiaClient
from models.system import SysUser
from modules.auth.permissions import build_user_context
from modules.auth.security import create_access_token, hash_password, verify_password
from modules.system.audit import write_operation_log
from modules.system.features import is_feature_enabled
from utils.clock import now_local
from utils.uploads import contained_path, read_limited, upload_filename

YUNZHIJIA_AUTO_PROVISION_FEATURE = "feature.yunzhijia_auto_provision"
BUILTIN_AVATARS = [f"/avatars/avatar-{slot:02d}.gif" for slot in range(1, 16)]
AVATAR_TEXT = "text"
AVATAR_UPLOAD_PREFIX = "/api/auth/avatar/"
AVATAR_MAX_BYTES = 5 * 1024 * 1024
AVATAR_LINK_MAX_LENGTH = 500
_AVATAR_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"}
_AVATAR_FILE = re.compile(r"^(\d+)_[a-f0-9]{16}\.(?:png|jpg|jpeg|gif|webp|bmp)$")


def resolve_avatar(setting: str | None, user_id: int) -> str:
    """头像设置转展示地址：未设置时按用户和日期随机一张站内动图，当天不变；文字头像返回空串，由前端显示姓名。"""
    value = (setting or "").strip()
    if not value:
        seed = f"{user_id}:{now_local().date().isoformat()}".encode()
        return BUILTIN_AVATARS[int(hashlib.md5(seed).hexdigest(), 16) % len(BUILTIN_AVATARS)]
    if value == AVATAR_TEXT:
        return ""
    return value


def login_with_password(db: Session, username: str, password: str) -> dict:
    username = (username or "").strip()
    user = db.scalar(select(SysUser).where(SysUser.username == username))
    if not user or not verify_password(password, user.password_hash or ""):
        write_operation_log(
            db,
            "auth.password_login",
            target_type="sys_user",
            target_id=str(user.id) if user else None,
            detail={"username": username},
            user=user,
            username=username,
            operation_name="账号密码登录",
            operation_type="login",
            target_label=username,
            result="failed",
            error_message="用户名或密码错误",
        )
        db.commit()
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    if user.status != "active":
        write_operation_log(
            db,
            "auth.password_login",
            target_type="sys_user",
            target_id=str(user.id),
            detail={"username": username},
            user=user,
            username=username,
            operation_name="账号密码登录",
            operation_type="login",
            target_label=user.display_name or username,
            result="failed",
            error_message="账号已被禁用",
        )
        db.commit()
        raise HTTPException(status_code=401, detail="账号已被禁用，请联系管理员")
    write_operation_log(
        db,
        "auth.password_login",
        target_type="sys_user",
        target_id=str(user.id),
        detail={"username": user.username},
        user=user,
        operation_name="账号密码登录",
        operation_type="login",
        target_label=user.display_name or user.username,
    )
    _mark_login(db, user)
    return {"accessToken": create_access_token(user.id, user.username)}


def login_with_yunzhijia_ticket(db: Session, ticket: str) -> dict:
    settings = get_settings()
    client = YunzhijiaClient(settings.yunzhijia_appid, settings.yunzhijia_appsecret)
    result = client.acquire_user_context(ticket)
    user_context = result["data"]
    openid = user_context.get("openid")
    if not openid:
        write_operation_log(
            db,
            "auth.yunzhijia_login",
            target_type="sys_user",
            target_id=None,
            detail={},
            operation_name="云之家登录",
            operation_type="login",
            result="failed",
            error_message="云之家未返回用户 openid",
        )
        db.commit()
        raise HTTPException(status_code=401, detail="云之家未返回用户 openid")
    user = db.scalar(select(SysUser).where(SysUser.openid == openid))
    if not user:
        if is_feature_enabled(db, YUNZHIJIA_AUTO_PROVISION_FEATURE):
            user = _provision_yunzhijia_user(db, user_context)
            write_operation_log(
                db,
                "auth.yunzhijia_auto_provision",
                target_type="sys_user",
                target_id=str(user.id) if user.id else None,
                detail={"openid": openid, "job_no": user.job_no},
                user=user,
                operation_name="云之家自动创建用户",
                operation_type="create",
                target_label=user.display_name or user.username,
            )
        else:
            write_operation_log(
                db,
                "auth.yunzhijia_login",
                target_type="sys_user",
                target_id=None,
                detail={"openid": openid},
                username=openid,
                operation_name="云之家登录",
                operation_type="login",
                target_label=openid,
                result="failed",
                error_message="该云之家账号尚未绑定系统用户",
            )
            db.commit()
            raise HTTPException(status_code=403, detail="该云之家账号尚未绑定系统用户")
    if user.status != "active":
        write_operation_log(
            db,
            "auth.yunzhijia_login",
            target_type="sys_user",
            target_id=None,
            detail={"openid": openid},
            username=openid,
            operation_name="云之家登录",
            operation_type="login",
            target_label=openid,
            result="failed",
            error_message="该云之家账号未启用",
        )
        db.commit()
        raise HTTPException(status_code=403, detail="该云之家账号未启用")
    write_operation_log(
        db,
        "auth.yunzhijia_login",
        target_type="sys_user",
        target_id=str(user.id),
        detail={"openid": openid},
        user=user,
        operation_name="云之家登录",
        operation_type="login",
        target_label=user.display_name or user.username,
    )
    _mark_login(db, user)
    return {"accessToken": create_access_token(user.id, user.username)}


def build_user_info(db: Session, user: SysUser) -> dict:
    context = build_user_context(db, user)
    last_login_at = user.last_login_at.isoformat() if user.last_login_at else None
    return {
        "id": context.id,
        "roles": context.roles,
        "permissions": context.permissions,
        "accessCodes": context.permissions,
        "avatar": resolve_avatar(user.avatar, context.id),
        "avatarSetting": user.avatar or "",
        "builtinAvatars": BUILTIN_AVATARS,
        "realName": context.display_name,
        "username": context.username,
        "homePath": "/home",
        "isSuperuser": context.is_superuser,
        "department": user.department,
        "groupName": user.group_name,
        "jobNo": user.job_no,
        "positionTitle": user.position_title,
        "gender": user.gender,
        "email": user.email,
        "mobile": user.mobile,
        "profileSignature": user.profile_signature,
        "lastLoginAt": last_login_at,
        "hasPassword": bool(user.password_hash),
    }


def update_profile_signature(db: Session, user: SysUser, signature: str | None) -> dict:
    normalized = (signature or "").strip()
    if len(normalized) > 255:
        raise ValueError("个性名片不能超过 255 个字符")
    user.profile_signature = normalized or None
    db.commit()
    db.refresh(user)
    return build_user_info(db, user)


def update_avatar(db: Session, user: SysUser, value: str | None) -> dict:
    """空串为随机站内头像；text 为姓名文字；也可选站内动图、本人上传的图片或 http(s) 图片链接。"""
    normalized = (value or "").strip()
    if normalized and normalized != AVATAR_TEXT and normalized not in BUILTIN_AVATARS:
        if normalized.startswith(AVATAR_UPLOAD_PREFIX):
            matched = _AVATAR_FILE.fullmatch(normalized[len(AVATAR_UPLOAD_PREFIX):])
            if not matched or int(matched.group(1)) != user.id:
                raise ValueError("头像图片不存在")
        elif not re.fullmatch(r"https?://\S+", normalized, re.IGNORECASE):
            raise ValueError("请填写 http:// 或 https:// 开头的图片链接")
        if len(normalized) > AVATAR_LINK_MAX_LENGTH:
            raise ValueError(f"头像链接不能超过 {AVATAR_LINK_MAX_LENGTH} 个字符")
    _replace_avatar(db, user, normalized or None)
    return build_user_info(db, user)


def upload_avatar(db: Session, user: SysUser, upload: UploadFile) -> dict:
    filename = upload_filename(upload.filename)
    suffix = Path(filename).suffix.lower()
    if suffix not in _AVATAR_SUFFIXES:
        raise ValueError("请上传 png、jpg、gif、webp 或 bmp 图片")
    content = read_limited(upload, AVATAR_MAX_BYTES, "头像图片")
    if not content:
        raise ValueError("图片是空的")
    stored = f"{user.id}_{secrets.token_hex(8)}{suffix}"
    folder = _avatar_folder()
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / stored
    target.write_bytes(content)
    decrypt_upload_file_if_available(db, target)
    _replace_avatar(db, user, AVATAR_UPLOAD_PREFIX + stored)
    return build_user_info(db, user)


def avatar_file(name: str) -> Path:
    if not _AVATAR_FILE.fullmatch(name or ""):
        raise NotFoundError("头像不存在")
    path = contained_path(_avatar_folder(), name)
    if not path.is_file():
        raise NotFoundError("头像不存在")
    return path


def _avatar_folder() -> Path:
    return Path(get_settings().repository_root) / "uploads" / "avatars"


def _replace_avatar(db: Session, user: SysUser, value: str | None) -> None:
    old = user.avatar or ""
    user.avatar = value
    db.commit()
    db.refresh(user)
    if old != (value or "") and old.startswith(AVATAR_UPLOAD_PREFIX):
        name = old[len(AVATAR_UPLOAD_PREFIX):]
        if _AVATAR_FILE.fullmatch(name):
            contained_path(_avatar_folder(), name).unlink(missing_ok=True)


def change_user_password(db: Session, user: SysUser, new_password: str) -> None:
    password = (new_password or "").strip()
    if len(password) < 6:
        raise ValueError("密码至少需要 6 位")
    user.password_hash = hash_password(password)
    db.commit()


def _mark_login(db: Session, user: SysUser) -> None:
    user.last_login_at = now_local()
    db.commit()


def _provision_yunzhijia_user(db: Session, user_context: dict) -> SysUser:
    openid = str(user_context["openid"]).strip()
    job_no = _first_present(user_context, "jobNo", "job_no", "jobNumber", "employeeNo")
    display_name = _first_present(user_context, "displayName", "userName", "username", "name", "nickName") or openid
    username = _unique_username(db, job_no or openid)
    user = SysUser(
        username=username,
        display_name=display_name,
        openid=openid,
        job_no=job_no,
        email=_first_present(user_context, "email"),
        mobile=_first_present(user_context, "mobile", "phone", "mobilePhone"),
        status="active",
        employment_status="active",
        is_superuser=False,
    )
    db.add(user)
    db.flush()
    return user


def _first_present(data: dict, *keys: str) -> str | None:
    for key in keys:
        value = data.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return None


def _unique_username(db: Session, raw_value: str) -> str:
    base = re.sub(r"[^0-9A-Za-z_.-]+", "_", raw_value.strip())[:64].strip("._-")
    if not base:
        base = "yunzhijia_user"
    username = base
    suffix = 1
    while db.scalar(select(SysUser.id).where(SysUser.username == username)):
        suffix += 1
        suffix_text = f"_{suffix}"
        username = f"{base[: 64 - len(suffix_text)]}{suffix_text}"
    return username
