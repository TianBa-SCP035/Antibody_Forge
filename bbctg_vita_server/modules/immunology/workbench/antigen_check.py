"""免疫抗原活性验证：每条方案抗原按验证项目记合格判定和结果图片。"""

from __future__ import annotations

import re
import secrets
from collections.abc import Iterable
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from core.config import get_settings
from core.errors import NotFoundError
from integrations.drm_service import decrypt_upload_file_if_available
from models.immunology import SerumAntigenCheck, SerumImmAntigen
from utils.uploads import contained_path, read_limited, upload_filename

ASSAYS = ("SEC-HPLC", "SDS-PAGE", "ELISA", "FACS", "荧光")
QUALIFIED_OPTIONS = ("是", "否")
MAX_IMAGES = 12
_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"}
_STORED_NAME = re.compile(r"^[a-f0-9]{16}\.(?:png|jpg|jpeg|gif|webp|bmp)$")


def _image_items(value) -> list[dict[str, str]]:
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


def _folder(antigen_row_id: int) -> Path:
    return Path(get_settings().repository_root) / "uploads" / "serum_antigen_check" / str(antigen_row_id)


def _antigen(db: Session, antigen_row_id: int) -> SerumImmAntigen:
    antigen = db.get(SerumImmAntigen, antigen_row_id)
    if not antigen:
        raise NotFoundError("抗原不存在，请先保存方案")
    return antigen


def _assay(value) -> str:
    assay = str(value or "").strip()
    if assay not in ASSAYS:
        raise ValueError("验证项目不正确")
    return assay


def _check(db: Session, antigen: SerumImmAntigen, assay: str, *, create: bool) -> SerumAntigenCheck | None:
    row = db.scalar(
        select(SerumAntigenCheck).where(
            SerumAntigenCheck.antigen_row_id == antigen.id,
            SerumAntigenCheck.assay == assay,
        )
    )
    if row is None and create:
        row = SerumAntigenCheck(experiment_id=antigen.experiment_id, antigen_row_id=antigen.id, assay=assay, images=[])
        db.add(row)
    return row


def _item(assay: str, row: SerumAntigenCheck | None) -> dict:
    return {
        "assay": assay,
        "qualified": row.qualified if row else None,
        "images": _image_items(row.images) if row else [],
        "updated_by": row.updated_by if row else None,
    }


def summarize(items: Iterable[dict]) -> dict:
    """抗原旁的判定：有一项不合格为「否」，已判的全合格为「是」，都没判为空。"""
    marks = [item.get("qualified") for item in items]
    judged = [mark for mark in marks if mark in QUALIFIED_OPTIONS]
    if "否" in judged:
        result = "否"
    elif judged:
        result = "是"
    else:
        result = None
    return {"result": result, "judged": len(judged), "total": len(ASSAYS)}


def detail(db: Session, antigen_row_id: int) -> dict:
    antigen = _antigen(db, antigen_row_id)
    rows = {
        row.assay: row
        for row in db.scalars(select(SerumAntigenCheck).where(SerumAntigenCheck.antigen_row_id == antigen.id)).all()
    }
    items = [_item(assay, rows.get(assay)) for assay in ASSAYS]
    return {"antigen": antigen.to_dict(), "items": items, "summary": summarize(items)}


def experiment_summaries(db: Session, experiment_id: str) -> list[dict]:
    """一个实验下每条抗原的判定，按抗原记录 ID 返回；页面按抗原行的 id 对上。"""
    ids = list(db.scalars(select(SerumImmAntigen.id).where(SerumImmAntigen.experiment_id == experiment_id)).all())
    if not ids:
        return []
    grouped: dict[int, list[dict]] = {item: [] for item in ids}
    for row in db.scalars(select(SerumAntigenCheck).where(SerumAntigenCheck.antigen_row_id.in_(ids))).all():
        grouped[row.antigen_row_id].append({"qualified": row.qualified})
    return [{"antigen_row_id": item, **summarize(rows)} for item, rows in grouped.items()]


def save_result(db: Session, antigen_row_id: int, assay: str, qualified, actor: str) -> dict:
    antigen = _antigen(db, antigen_row_id)
    key = _assay(assay)
    mark = str(qualified or "").strip() or None
    if mark is not None and mark not in QUALIFIED_OPTIONS:
        raise ValueError("判定只能选「是」或「否」")
    row = _check(db, antigen, key, create=True)
    row.qualified = mark
    row.updated_by = actor
    db.commit()
    return detail(db, antigen.id)


def add_image(db: Session, antigen_row_id: int, assay: str, upload: UploadFile, actor: str) -> dict:
    antigen = _antigen(db, antigen_row_id)
    key = _assay(assay)
    row = _check(db, antigen, key, create=True)
    items = _image_items(row.images)
    if len(items) >= MAX_IMAGES:
        raise ValueError(f"每项最多 {MAX_IMAGES} 张图片")
    filename = upload_filename(upload.filename)
    suffix = Path(filename).suffix.lower()
    if suffix not in _IMAGE_SUFFIXES:
        raise ValueError("请上传图片")
    content = read_limited(upload, label="图片")
    if not content:
        raise ValueError("图片是空的")
    stored = f"{secrets.token_hex(8)}{suffix}"
    folder = _folder(antigen.id)
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / stored
    target.write_bytes(content)
    decrypt_upload_file_if_available(db, target)
    row.images = [*items, {"file": stored, "name": filename}]
    row.updated_by = actor
    db.commit()
    return detail(db, antigen.id)


def remove_image(db: Session, antigen_row_id: int, assay: str, stored_name: str, actor: str) -> dict:
    antigen = _antigen(db, antigen_row_id)
    row = _check(db, antigen, _assay(assay), create=False)
    stored = str(stored_name or "")
    items = _image_items(row.images) if row else []
    if not _STORED_NAME.fullmatch(stored) or not any(item["file"] == stored for item in items):
        raise NotFoundError("图片不存在")
    path = contained_path(_folder(antigen.id), stored)
    if path.is_file():
        path.unlink()
    row.images = [item for item in items if item["file"] != stored]
    row.updated_by = actor
    db.commit()
    return detail(db, antigen.id)


def image_file(db: Session, antigen_row_id: int, stored_name: str) -> tuple[Path, str]:
    antigen = _antigen(db, antigen_row_id)
    stored = str(stored_name or "")
    if not _STORED_NAME.fullmatch(stored):
        raise NotFoundError("图片不存在")
    rows = db.scalars(select(SerumAntigenCheck).where(SerumAntigenCheck.antigen_row_id == antigen.id)).all()
    item = next((one for row in rows for one in _image_items(row.images) if one["file"] == stored), None)
    if item is None:
        raise NotFoundError("图片不存在")
    path = contained_path(_folder(antigen.id), stored)
    if not path.is_file():
        raise NotFoundError("图片不存在")
    return path, item["name"]
