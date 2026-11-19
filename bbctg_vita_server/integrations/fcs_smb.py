"""镁伽流式结果共享（SMB）只读下载。

回传 JSON 里的图片、CSV 路径都是相对共享根的路径，例如 images/<哈希>/可视化图_xxx.png。
共享按访客映射时服务端不签名，所以关闭签名和安全协商校验，只读不写。
"""

from __future__ import annotations

from pathlib import Path, PurePosixPath
import re

from core.config import get_settings

_CHUNK_SIZE = 1024 * 1024
_CONNECT_TIMEOUT_SECONDS = 15
_DRIVE_RE = re.compile(r"^[A-Za-z]:")


class FcsSmbError(Exception):
    pass


def normalize_relative_path(raw: str) -> str:
    """统一成 / 分隔的相对路径；绝对路径、带 .. 的路径不合法。"""
    text = str(raw or "").strip().replace("\\", "/")
    if not text:
        raise FcsSmbError("路径为空")
    if text.startswith("/") or _DRIVE_RE.match(text):
        raise FcsSmbError(f"路径必须是共享内的相对路径：{text}")
    parts = PurePosixPath(text).parts
    if any(part in {"", ".", ".."} for part in parts):
        raise FcsSmbError(f"路径不合法：{text}")
    return "/".join(parts)


def is_configured() -> bool:
    settings = get_settings()
    return bool(settings.fcs_smb_host.strip() and settings.fcs_smb_share.strip())


def download(relative_path: str, target: Path, max_bytes: int) -> None:
    if not is_configured():
        raise FcsSmbError("未配置 FCS_SMB_HOST / FCS_SMB_SHARE")
    import smbclient

    settings = get_settings()
    host = settings.fcs_smb_host.strip()
    share = settings.fcs_smb_share.strip().strip("\\/")
    credentials = {
        "port": settings.fcs_smb_port,
        "username": settings.fcs_smb_user or None,
        "password": settings.fcs_smb_password or None,
    }
    smbclient.ClientConfig(require_secure_negotiate=False)
    smbclient.register_session(
        host,
        require_signing=False,
        encrypt=False,
        connection_timeout=_CONNECT_TIMEOUT_SECONDS,
        **credentials,
    )
    windows_path = normalize_relative_path(relative_path).replace("/", "\\")
    unc_path = f"\\\\{host}\\{share}\\{windows_path}"
    copied = 0
    with smbclient.open_file(unc_path, mode="rb", **credentials) as source, target.open("wb") as output:
        while chunk := source.read(_CHUNK_SIZE):
            copied += len(chunk)
            if copied > max_bytes:
                raise FcsSmbError(f"文件超过 {max_bytes // (1024 * 1024)}MB：{relative_path}")
            output.write(chunk)
    if copied == 0:
        raise FcsSmbError(f"文件为空：{relative_path}")
