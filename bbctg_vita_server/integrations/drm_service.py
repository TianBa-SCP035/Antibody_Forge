from __future__ import annotations

import importlib
import logging
import os
import shutil
import uuid
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from core.config import PROJECT_ROOT, get_settings
from modules.system.features import is_feature_enabled


DRM_FEATURE_CODE = "feature.drm_file_security"

OFFICE_DOWNLOAD_SUFFIXES = {
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
    ".xlsm",
    ".ppt",
    ".pptx",
}


def decrypt_upload_file_if_available(
    db: Session,
    file_path: str | Path,
    decrypt_user_id: str | None = None,
) -> bool:
    """DRM 模块启用且可用时解密上传文件。

    解密成功返回 True，跳过或失败返回 False；失败只记日志，不阻断上传。
    """

    runtime = _get_drm_runtime(db)
    if runtime is None:
        return False

    drm_module = _load_drm_module()
    if drm_module is None:
        return False

    applicant_id = (decrypt_user_id or "").strip() or runtime["sdk_kwargs"]["user_id"]

    try:
        return bool(
            drm_module.decrypt_file_if_needed(
                Path(file_path),
                decrypt_user_id=applicant_id,
                **runtime["sdk_kwargs"],
            )
        )
    except Exception:
        logging.exception("DRM upload decrypt failed, upload continues: %s", file_path)
        return False


def prepare_office_download_file(db: Session, source_path: Path, file_name: str) -> tuple[Path, Path | None]:
    """返回可供附件下载的文件路径。

    DRM 可用时在临时副本上加密 Word、Excel 和 PPT 文件；已加密文件直接发送，
    其他类型和预览使用原文件。第二个返回值是响应后需删除的临时文件。
    加密失败只记日志，并回退到原始明文文件。
    """

    if not is_office_download_name(file_name):
        return source_path, None

    runtime = _get_drm_runtime(db)
    if runtime is None:
        return source_path, None

    drm_module = _load_drm_module()
    if drm_module is None:
        return source_path, None

    settings = get_settings()
    sdk_kwargs = runtime["sdk_kwargs"]

    try:
        if drm_module.is_drm_encrypted_file(source_path, **sdk_kwargs):
            return source_path, None

        temp_dir = settings.repository_root / "tmp" / "drm_download"
        temp_dir.mkdir(parents=True, exist_ok=True)
        temp_path = temp_dir / f"{uuid.uuid4().hex}_{Path(file_name).name}"
        shutil.copy2(source_path, temp_path)

        owner_id = (settings.drm_encrypt_owner_id or "").strip() or settings.drm_user_id

        drm_module.encrypt_file_if_needed(
            temp_path,
            owner_id=owner_id,
            secret_level_id=settings.drm_encrypt_secret_level_id,
            **sdk_kwargs,
        )
        return temp_path, temp_path
    except Exception:
        if "temp_path" in locals() and temp_path.exists():
            temp_path.unlink()
        logging.exception(
            "DRM download encrypt failed, serving plaintext: %s",
            source_path,
        )
        return source_path, None


def is_office_download_name(file_name: str) -> bool:
    return Path(file_name or "").suffix.lower() in OFFICE_DOWNLOAD_SUFFIXES


def remove_temp_file(path: Path) -> None:
    try:
        if path.exists():
            path.unlink()
    except OSError:
        logging.warning("Failed to remove DRM temp file: %s", path)


def _get_drm_runtime(db: Session) -> dict[str, Any] | None:
    settings = get_settings()
    if not is_feature_enabled(db, DRM_FEATURE_CODE):
        return None
    if not settings.drm_enabled:
        return None

    lib_dir = _resolve_lib_dir(settings.drm_lib_dir)
    if not _has_native_library(lib_dir):
        logging.warning("DRM 功能已开启，但未找到动态库，跳过: %s", lib_dir)
        return None

    if not _has_server_config(settings):
        logging.warning(
            "DRM 功能已开启，但环境变量未配置完整（需 DRM_SERVER_HOST/PORT/USER_ID/PASSWORD）"
        )
        return None

    return {
        "sdk_kwargs": {
            "lib_dir": lib_dir,
            "server_ssl": settings.drm_server_ssl,
            "server_host": settings.drm_server_host,
            "server_port": settings.drm_server_port,
            "user_id": settings.drm_user_id,
            "password": settings.drm_password,
            "config_path": settings.drm_config_path,
        },
    }


def _load_drm_module() -> Any | None:
    try:
        return importlib.import_module("integrations.drm")
    except Exception as exc:
        logging.warning("DRM module is not available: %s", exc)
        return None


def _resolve_lib_dir(configured: str) -> Path:
    if configured:
        path = Path(os.path.expandvars(configured)).expanduser()
        return path if path.is_absolute() else (PROJECT_ROOT / path).resolve()
    return Path(__file__).resolve().parent / "drm" / "lib"


def _has_native_library(lib_dir: Path) -> bool:
    if not lib_dir.exists():
        return False
    if os.name == "nt":
        return (lib_dir / "DrmEdiC.dll").exists()
    return (lib_dir / "libdrmedi.so").exists() and (lib_dir / "libhttpcomm.so").exists()


def _has_server_config(settings: Any) -> bool:
    return bool(settings.drm_server_host and settings.drm_server_port and settings.drm_user_id and settings.drm_password)
