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


class DrmDecryptError(RuntimeError):
    """Raised when DRM is available but decrypting an encrypted file fails."""


class DrmEncryptError(RuntimeError):
    """Raised when DRM is available but encrypting a download file fails."""


def decrypt_upload_file_if_available(
    db: Session,
    file_path: str | Path,
    decrypt_user_id: str | None = None,
) -> bool:
    """Decrypt an uploaded file when the DRM module is enabled and available."""

    runtime = _get_drm_runtime(db)
    if runtime is None:
        return False

    drm_module = _load_drm_module()
    if drm_module is None:
        return False

    decrypt_func = getattr(drm_module, "decrypt_file_if_needed", None)
    if decrypt_func is None:
        logging.warning("DRM module exists but decrypt_file_if_needed is missing")
        return False

    applicant_id = (decrypt_user_id or "").strip() or runtime["settings"].drm_user_id

    try:
        return bool(decrypt_func(Path(file_path), decrypt_user_id=applicant_id, **runtime["sdk_kwargs"]))
    except Exception as exc:
        raise DrmDecryptError("DRM 文件解密失败") from exc


def prepare_office_download_file(db: Session, source_path: Path, file_name: str) -> tuple[Path, Path | None]:
    """Return a path suitable for attachment download.

    Office files (Word/Excel/PPT) are encrypted on a temp copy when DRM is available.
    Already-encrypted files are sent as-is. Other types and preview flows use the
    original path. Second value is a temp file to delete after response, if any.
    """

    if not is_office_download_name(file_name):
        return source_path, None

    runtime = _get_drm_runtime(db)
    if runtime is None:
        return source_path, None

    drm_module = _load_drm_module()
    if drm_module is None:
        return source_path, None

    is_encrypted = getattr(drm_module, "is_drm_encrypted_file", None)
    encrypt_func = getattr(drm_module, "encrypt_file_if_needed", None)
    if is_encrypted is None or encrypt_func is None:
        logging.warning("DRM module missing encrypt helpers, download uses plaintext")
        return source_path, None

    settings = runtime["settings"]
    sdk_kwargs = runtime["sdk_kwargs"]

    try:
        if is_encrypted(source_path, **sdk_kwargs):
            return source_path, None

        temp_dir = settings.repository_root / "tmp" / "drm_download"
        temp_dir.mkdir(parents=True, exist_ok=True)
        temp_path = temp_dir / f"{uuid.uuid4().hex}_{Path(file_name).name}"
        shutil.copy2(source_path, temp_path)

        owner_id = (settings.drm_encrypt_owner_id or "").strip() or settings.drm_user_id
        secret_level_id = settings.drm_encrypt_secret_level_id

        encrypt_func(
            temp_path,
            owner_id=owner_id,
            secret_level_id=secret_level_id,
            **sdk_kwargs,
        )
        return temp_path, temp_path
    except Exception as exc:
        if "temp_path" in locals() and temp_path.exists():
            temp_path.unlink()
        raise DrmEncryptError("DRM 文件加密失败") from exc


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
    if not is_feature_enabled(db, DRM_FEATURE_CODE, default=False):
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
        "settings": settings,
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
        logging.info("DRM module is not available: %s", exc)
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
