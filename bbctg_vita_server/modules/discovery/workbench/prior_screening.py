"""发现工作台既往筛选图片：文字走工单保存，图片单独上传。"""

from __future__ import annotations

import re
import secrets
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy.orm import Session

from core.config import get_settings
from core.errors import NotFoundError
from integrations.drm_service import decrypt_upload_file_if_available
from models.discovery import DiscoveryWorkbench
from utils.uploads import contained_path, read_limited, upload_filename

MAX_IMAGES = 12
_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"}
_STORED_NAME = re.compile(r"^[a-f0-9]{16}\.(?:png|jpg|jpeg|gif|webp|bmp)$")


def image_items(value) -> list[dict[str, str]]:
    if not isinstance(value, list):
        return []
    items = []
    for item in value:
        if not isinstance(item, dict):
            continue
        stored = str(item.get("file") or "")
        if not _STORED_NAME.fullmatch(stored):
            continue
        name = str(item.get("name") or stored).strip() or stored
        items.append({"file": stored, "name": name[:255]})
    return items


def _folder(workbench_id: int) -> Path:
    return Path(get_settings().repository_root) / "uploads" / "discovery_prior" / str(workbench_id)


def _row(db: Session, workbench_id: int) -> DiscoveryWorkbench:
    row = db.get(DiscoveryWorkbench, workbench_id)
    if not row:
        raise NotFoundError("发现安排不存在")
    return row


def add_image(db: Session, workbench_id: int, upload: UploadFile) -> list[dict[str, str]]:
    row = _row(db, workbench_id)
    items = image_items(row.prior_screening_images)
    if len(items) >= MAX_IMAGES:
        raise ValueError(f"最多 {MAX_IMAGES} 张图片")
    filename = upload_filename(upload.filename)
    suffix = Path(filename).suffix.lower()
    if suffix not in _IMAGE_SUFFIXES:
        raise ValueError("请上传图片")
    content = read_limited(upload, label="图片")
    if not content:
        raise ValueError("图片是空的")
    stored = f"{secrets.token_hex(8)}{suffix}"
    folder = _folder(row.id)
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / stored
    target.write_bytes(content)
    decrypt_upload_file_if_available(db, target)
    items.append({"file": stored, "name": filename})
    row.prior_screening_images = items
    db.commit()
    db.refresh(row)
    return image_items(row.prior_screening_images)


def remove_image(db: Session, workbench_id: int, stored_name: str) -> list[dict[str, str]]:
    row = _row(db, workbench_id)
    stored = str(stored_name or "")
    if not _STORED_NAME.fullmatch(stored):
        raise NotFoundError("图片不存在")
    items = image_items(row.prior_screening_images)
    if not any(item["file"] == stored for item in items):
        raise NotFoundError("图片不存在")
    path = contained_path(_folder(row.id), stored)
    if path.is_file():
        path.unlink()
    row.prior_screening_images = [item for item in items if item["file"] != stored]
    db.commit()
    db.refresh(row)
    return image_items(row.prior_screening_images)


def image_file(db: Session, workbench_id: int, stored_name: str) -> tuple[Path, str]:
    row = _row(db, workbench_id)
    stored = str(stored_name or "")
    item = next((one for one in image_items(row.prior_screening_images) if one["file"] == stored), None)
    if item is None:
        raise NotFoundError("图片不存在")
    path = contained_path(_folder(row.id), stored)
    if not path.is_file():
        raise NotFoundError("图片不存在")
    return path, item["name"]
