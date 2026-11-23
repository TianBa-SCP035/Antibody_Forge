"""上传文件的公共校验：文件名、落盘路径、大小上限。"""

from pathlib import Path, PurePath
from typing import BinaryIO

from fastapi import UploadFile

from core.config import get_settings


def upload_filename(raw: str | None) -> str:
    """只取文件名本身，去掉客户端带来的目录。"""
    name = PurePath(str(raw or "").replace("\\", "/")).name.strip()
    if not name or name in {".", ".."} or len(name) > 255:
        raise ValueError("缺少文件名或文件名过长")
    return name


def safe_path_part(raw: str | None, label: str = "路径") -> str:
    """单层目录名：不能为空、不能含分隔符或 ..。"""
    text = str(raw or "").strip()
    if not text or text in {".", ".."} or "/" in text or "\\" in text or ":" in text:
        raise ValueError(f"{label}不合法")
    return text


def contained_path(root: Path, relative: str) -> Path:
    """把相对路径拼到 root 下；解析后必须仍在 root 里。"""
    base = root.resolve()
    target = (base / str(relative or "").replace("\\", "/").lstrip("/")).resolve()
    if target != base and base not in target.parents:
        raise ValueError("文件路径不合法")
    return target


def read_limited(file_obj: UploadFile | BinaryIO, max_bytes: int | None = None, label: str = "文件") -> bytes:
    limit = max_bytes or get_settings().upload_max_bytes
    stream = getattr(file_obj, "file", file_obj)
    content = stream.read(limit + 1)
    if len(content) > limit:
        raise ValueError(f"{label}不能超过 {limit // (1024 * 1024)}MB")
    return content
