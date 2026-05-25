from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Any

from fastapi import UploadFile
from PIL import Image
from sqlalchemy import select
from sqlalchemy.orm import Session

from core.config import get_settings
from integrations import drm_service
from models.immunology import SerumElisaPlate, SerumFacsPlate, SerumFile, SerumTiterPc, SerumTiterTarget


def _upload_root() -> Path:
    root = Path(get_settings().repository_root) / "uploads" / "titer_files"
    root.mkdir(parents=True, exist_ok=True)
    return root


def get_full_path(relative_path: str) -> Path:
    path_parts = relative_path.lstrip("/")
    settings = get_settings()
    return Path(settings.repository_root) / "uploads" / path_parts


def get_file_list(db: Session, experiment_id: str) -> list[dict]:
    if not experiment_id:
        return []
    return [item.to_dict() for item in db.scalars(select(SerumFile).where(SerumFile.experiment_id == experiment_id)).all()]


def _save_upload_content(db: Session, file_obj: UploadFile, file_path: Path) -> None:
    with file_path.open("wb") as target:
        target.write(file_obj.file.read())
    drm_service.decrypt_upload_file_if_available(db, file_path)


def save_file(db: Session, file_obj: UploadFile, experiment_id: str, user_name: str = "unknown") -> dict:
    if not file_obj.filename or not experiment_id:
        raise ValueError("Missing file or experiment ID")

    exp_dir = _upload_root() / experiment_id
    exp_dir.mkdir(parents=True, exist_ok=True)
    save_name = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{Path(file_obj.filename).name}"
    file_path = exp_dir / save_name

    _save_upload_content(db, file_obj, file_path)

    record = SerumFile(
        experiment_id=experiment_id,
        upload_user=user_name,
        file_name=file_obj.filename,
        file_path=f"/titer_files/{experiment_id}/{save_name}",
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record.to_dict()


def delete_file(db: Session, file_id: int) -> None:
    record = db.get(SerumFile, file_id)
    if not record:
        raise ValueError("File not found")
    full_path = get_full_path(record.file_path)
    if full_path.exists():
        full_path.unlink()
    db.delete(record)
    db.commit()


def rename_file(db: Session, file_id: int, new_name: str) -> None:
    record = db.get(SerumFile, file_id)
    if not record:
        raise ValueError("File not found")
    record.file_name = new_name
    db.commit()


def replace_file(db: Session, file_id: int, file_obj: UploadFile, user_name: str = "unknown") -> dict:
    record = db.get(SerumFile, file_id)
    if not record:
        raise ValueError("File not found")

    old_path = get_full_path(record.file_path)
    exp_dir = old_path.parent
    exp_dir.mkdir(parents=True, exist_ok=True)
    save_name = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{Path(file_obj.filename or '').name}"
    new_path = exp_dir / save_name

    _save_upload_content(db, file_obj, new_path)
    if old_path != new_path and old_path.exists():
        old_path.unlink()

    record.file_name = file_obj.filename or save_name
    record.file_path = f"/titer_files/{record.experiment_id}/{save_name}"
    record.upload_user = user_name
    db.commit()
    db.refresh(record)
    return record.to_dict()


def get_download_record(db: Session, file_id: int) -> tuple[SerumFile, Path]:
    record = db.get(SerumFile, file_id)
    if not record:
        raise ValueError("File not found")
    full_path = get_full_path(record.file_path)
    if not full_path.exists():
        raise ValueError("File not found on disk")
    return record, full_path


def prepare_office_download_file(db: Session, source_path: Path, file_name: str) -> tuple[Path, Path | None]:
    """Attachment download: encrypt Office files on a temp copy; preview uses plaintext path."""
    return drm_service.prepare_office_download_file(db, source_path, file_name)


def create_thumbnail(file_path: Path, width: int, height: int) -> tuple[BytesIO, str] | None:
    suffix = file_path.suffix.lower()
    if suffix not in {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"}:
        return None
    image = Image.open(file_path)
    image.thumbnail((width, height), Image.Resampling.LANCZOS)
    output = BytesIO()
    image_format = image.format or "JPEG"
    image.save(output, format=image_format, quality=85)
    output.seek(0)
    return output, f"image/{image_format.lower()}"


def _replace_children(db: Session, model_class, experiment_id: str, items: list[dict], id_field: str = "id") -> list[dict]:
    submitted_ids = set()
    created_objs = []
    valid_fields = set(model_class.__table__.columns.keys())
    for item in items:
        item_id = item.get(id_field)
        if item_id:
            obj = db.get(model_class, int(item_id))
            if obj:
                for key, value in item.items():
                    if key != id_field and hasattr(obj, key):
                        setattr(obj, key, value)
                obj.experiment_id = experiment_id
                submitted_ids.add(int(item_id))
                continue
        data = {key: value for key, value in item.items() if key in valid_fields and key != id_field}
        data["experiment_id"] = experiment_id
        obj = model_class(**data)
        db.add(obj)
        created_objs.append(obj)

    db.flush()
    keep_ids = submitted_ids | {getattr(obj, id_field) for obj in created_objs if getattr(obj, id_field, None)}
    existing = db.scalars(select(model_class).where(model_class.experiment_id == experiment_id)).all()
    for obj in existing:
        if getattr(obj, id_field) not in keep_ids:
            db.delete(obj)
    db.commit()
    return [item.to_dict() for item in db.scalars(select(model_class).where(model_class.experiment_id == experiment_id)).all()]


def save_targets(db: Session, experiment_id: str, targets: list[dict]) -> list[dict]:
    return _replace_children(db, SerumTiterTarget, experiment_id, targets)


def save_pcs(db: Session, experiment_id: str, pcs: list[dict]) -> list[dict]:
    return _replace_children(db, SerumTiterPc, experiment_id, pcs)


def get_facs_plates(db: Session, experiment_id: str) -> list[dict]:
    return [item.to_dict() for item in db.scalars(select(SerumFacsPlate).where(SerumFacsPlate.experiment_id == experiment_id)).all()]


PLATE_FIELDS = [
    "qr_code",
    "image_file_id",
    "excel_file_id",
    "immune_stage",
    "x_axis",
    "y_axis",
    "cell_target_id",
    "pc_upper_id",
    "pc_lower_id",
    "upper_group",
    "lower_group",
    "upper_mouse_list",
    "lower_mouse_list",
    "upper_slot_groups",
    "lower_slot_groups",
    "positive_well_list",
    "instrument_type",
]


def save_facs_plate(db: Session, plate_data: dict[str, Any]) -> dict:
    experiment_id = plate_data.get("experiment_id")
    if not experiment_id:
        raise ValueError("Missing experiment_id")

    plate_id = plate_data.get("id")
    if plate_id:
        plate = db.get(SerumFacsPlate, int(plate_id))
        if not plate:
            raise ValueError("Plate not found")
        if plate.experiment_id != experiment_id:
            raise ValueError("Plate does not belong to this experiment")
    else:
        plate = SerumFacsPlate(experiment_id=experiment_id)
        db.add(plate)

    for field in PLATE_FIELDS:
        setattr(plate, field, plate_data.get(field))
    db.commit()
    db.refresh(plate)
    return plate.to_dict()


def delete_facs_plate(db: Session, plate_id: int) -> None:
    plate = db.get(SerumFacsPlate, plate_id)
    if not plate:
        raise ValueError("Plate not found")
    db.delete(plate)
    db.commit()


def get_elisa_plates(db: Session, experiment_id: str) -> list[dict]:
    return [item.to_dict() for item in db.scalars(select(SerumElisaPlate).where(SerumElisaPlate.experiment_id == experiment_id)).all()]


ELISA_PLATE_FIELDS = [
    "qr_code",
    "excel_file_id",
    "immune_stage",
    "protein_target_id",
    "pc_id",
    "mouse_group",
    "antigen_type",
    "slot_groups",
    "upper_slot_list",
    "lower_slot_list",
    "positive_well_list",
    "absorbance_1",
]


def save_elisa_plate(db: Session, plate_data: dict[str, Any]) -> dict:
    experiment_id = plate_data.get("experiment_id")
    if not experiment_id:
        raise ValueError("Missing experiment_id")

    plate_id = plate_data.get("id")
    if plate_id:
        plate = db.get(SerumElisaPlate, int(plate_id))
        if not plate:
            raise ValueError("Plate not found")
        if plate.experiment_id != experiment_id:
            raise ValueError("Plate does not belong to this experiment")
    else:
        plate = SerumElisaPlate(experiment_id=experiment_id, immune_stage="")
        db.add(plate)

    for field in ELISA_PLATE_FIELDS:
        setattr(plate, field, plate_data.get(field))
    if not plate.immune_stage:
        plate.immune_stage = ""
    db.commit()
    db.refresh(plate)
    return plate.to_dict()


def delete_elisa_plate(db: Session, plate_id: int) -> None:
    plate = db.get(SerumElisaPlate, plate_id)
    if not plate:
        raise ValueError("Plate not found")
    db.delete(plate)
    db.commit()
