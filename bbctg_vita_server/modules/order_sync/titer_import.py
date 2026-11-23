"""核对通过的效价检测板导入效价模块：从 SMB 下载可视化图和热图，写文件、FACS 板卡、标靶、PC、检测日期。

每块板独立一个事务。镁伽只覆盖自己写入且没被人改过的板卡和文件：
人保存过的板卡、替换或重命名过的文件都已转为手工，不再覆盖。
"""

from __future__ import annotations

import logging
from pathlib import Path, PurePosixPath
import re
import tempfile
import threading
import time
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.config import get_settings
from db.session import SessionLocal
from integrations import fcs_smb
from models.immunology import (
    SOURCE_MEGA,
    SerumFacsPlate,
    SerumFile,
    SerumImmMouse,
    SerumTiterOrder,
    SerumTiterPc,
    SerumTiterTarget,
)
from models.order_sync import OrderSync, OrderSyncBoard
from modules.immunology.titer.service import write_mega_file
from modules.mega_automation.content import clean_text
from modules.order_sync.heatmap import parse_heatmap, read_rows
from modules.order_sync.verify import TiterPlan
from modules.system.audit_context import audit_scope
from utils.clock import now_local

logger = logging.getLogger(__name__)

IMPORT_NONE = "none"
IMPORT_PENDING = "pending"
IMPORT_RUNNING = "running"
IMPORT_DONE = "done"
IMPORT_SKIPPED = "skipped"
IMPORT_DOWNLOAD_FAILED = "download_failed"
IMPORT_FAILED = "failed"

DOWNLOAD_ATTEMPTS = 3
DOWNLOAD_RETRY_SECONDS = 2
FACS_INSTRUMENT_DOMESTIC = "国产"
TARGET_TYPE_CELL = "细胞"
_LEGACY_SEX_PREFIX = re.compile(r"^[FM]：(.+)$")
_LEGACY_SPLIT = re.compile(r"[，\n]+")

_running_syncs: set[int] = set()
_running_lock = threading.Lock()


def is_running(sync_id: int) -> bool:
    with _running_lock:
        return sync_id in _running_syncs


def _claim(sync_id: int) -> bool:
    with _running_lock:
        if sync_id in _running_syncs:
            return False
        _running_syncs.add(sync_id)
        return True


def _release(sync_id: int) -> None:
    with _running_lock:
        _running_syncs.discard(sync_id)


def run_import(sync_id: int, plans: list[TiterPlan]) -> None:
    """后台任务入口：自己开会话和审计上下文，请求的会话此时已关闭。"""
    if not _claim(sync_id):
        logger.warning("order sync import skipped: sync_id=%s already running", sync_id)
        return
    try:
        with audit_scope(
            "order.experiment.import",
            "镁伽回传导入效价",
            source="system",
            operation_type="update",
            resource="order_sync",
        ):
            db = SessionLocal()
            try:
                _run(db, sync_id, plans)
            finally:
                db.close()
    except Exception:
        logger.exception("order sync import failed: sync_id=%s", sync_id)
    finally:
        _release(sync_id)


def _run(db: Session, sync_id: int, plans: list[TiterPlan]) -> None:
    record = db.get(OrderSync, sync_id)
    if record is None:
        return
    record.import_status = IMPORT_RUNNING
    db.commit()
    for plan in plans:
        try:
            _import_board(db, plan)
        except Exception as exc:
            db.rollback()
            logger.exception("order sync board import failed: board_id=%s", plan.board_id)
            _mark_board(db, plan.board_id, IMPORT_FAILED, f"导入异常：{exc}")
    statuses = db.scalars(
        select(OrderSyncBoard.import_status).where(
            OrderSyncBoard.sync_id == sync_id,
            OrderSyncBoard.import_status != IMPORT_NONE,
        )
    ).all()
    failed = any(status in {IMPORT_FAILED, IMPORT_DOWNLOAD_FAILED} for status in statuses)
    record.import_status = IMPORT_FAILED if failed else IMPORT_DONE
    record.processed_at = now_local()
    db.commit()


def _mark_board(db: Session, board_id: int, status: str, message: str) -> None:
    board = db.get(OrderSyncBoard, board_id)
    if board is None:
        return
    board.import_status = status
    board.import_message = message
    db.commit()


def _previous_board(db: Session, plan: TiterPlan) -> OrderSyncBoard | None:
    """同一工单、同一样品板、同一细胞上次导入的检测板（含本行自己），用来找之前生成的板卡和文件。"""
    return db.scalars(
        select(OrderSyncBoard)
        .where(
            OrderSyncBoard.work_order_id == plan.work_order_id,
            OrderSyncBoard.sample_barcode == plan.sample_barcode,
            OrderSyncBoard.cell_name == plan.cell_name,
            OrderSyncBoard.facs_plate_id.is_not(None),
        )
        .order_by(OrderSyncBoard.id.desc())
        .limit(1)
    ).first()


def _download(relative_path: str, target: Path) -> None:
    max_bytes = get_settings().upload_max_bytes
    for attempt in range(1, DOWNLOAD_ATTEMPTS + 1):
        try:
            fcs_smb.download(relative_path, target, max_bytes)
            return
        except fcs_smb.FcsSmbError:
            raise
        except Exception:
            if attempt == DOWNLOAD_ATTEMPTS:
                raise
            time.sleep(DOWNLOAD_RETRY_SECONDS)


def _mega_file(db: Session, file_id: int | None, experiment_id: str) -> SerumFile | None:
    record = db.get(SerumFile, file_id) if file_id else None
    if record is None or record.source != SOURCE_MEGA or record.experiment_id != experiment_id:
        return None
    return record


def _ensure_target(db: Session, experiment_id: str, column: dict[str, Any]) -> int:
    name = clean_text(column.get("cell_name"))
    batch = clean_text(column.get("batch"))
    targets = db.scalars(select(SerumTiterTarget).where(SerumTiterTarget.experiment_id == experiment_id)).all()
    for target in targets:
        if clean_text(target.name).casefold() == name.casefold() and clean_text(target.batch_no) == batch:
            return target.id
    target = SerumTiterTarget(
        experiment_id=experiment_id,
        type=TARGET_TYPE_CELL,
        species=clean_text(column.get("species")),
        name=name,
        batch_no=batch,
        passage=clean_text(column.get("generation")),
        cell_count=clean_text(column.get("cell_count")),
        catalog_no=clean_text(column.get("catalog_no")),
        source=clean_text(column.get("source")),
    )
    db.add(target)
    db.flush()
    return target.id


def _ensure_pc(db: Session, experiment_id: str, info: dict[str, Any] | None) -> int | None:
    if not info:
        return None
    name = clean_text(info.get("pc_name"))
    batch = clean_text(info.get("catalog_batch"))
    if not name:
        return None
    pcs = db.scalars(select(SerumTiterPc).where(SerumTiterPc.experiment_id == experiment_id)).all()
    for pc in pcs:
        if clean_text(pc.pc_name).casefold() == name.casefold() and clean_text(pc.catalog_batch) == batch:
            return pc.id
    pc = SerumTiterPc(
        experiment_id=experiment_id,
        pc_name=name,
        catalog_batch=batch,
        source=clean_text(info.get("source")),
        concentration=clean_text(info.get("concentration")),
    )
    db.add(pc)
    db.flush()
    return pc.id


def _group_mice(group: SerumImmMouse) -> list[str]:
    registry = group.mouse_registry if isinstance(group.mouse_registry, dict) else {}
    mice = registry.get("mice")
    if isinstance(mice, list) and mice:
        return [clean_text(mouse.get("no")) for mouse in mice if isinstance(mouse, dict) and clean_text(mouse.get("no"))]
    numbers: list[str] = []
    for part in _LEGACY_SPLIT.split(clean_text(group.mouse_no_list)):
        matched = _LEGACY_SEX_PREFIX.match(part)
        body = matched.group(1) if matched else part
        numbers.extend(token.strip() for token in body.split("、") if token.strip())
    return numbers


def _group_labels(db: Session, experiment_id: str) -> dict[str, str]:
    """鼠号 → 组别标签（与效价页组别选项同一写法：组号-品系）；一只鼠出现在多个组里就不标。"""
    labels: dict[str, str] = {}
    ambiguous: set[str] = set()
    for group in db.scalars(select(SerumImmMouse).where(SerumImmMouse.experiment_id == experiment_id)).all():
        group_id = clean_text(group.group_id)
        if not group_id:
            continue
        strain = clean_text(group.mouse_strain)
        label = f"{group_id}-{strain}" if strain else group_id
        for number in _group_mice(group):
            if labels.get(number, label) != label:
                ambiguous.add(number)
            labels[number] = label
    for number in ambiguous:
        labels.pop(number, None)
    return labels


def _slot_groups(mouse_list: list[str], labels: dict[str, str]) -> list[dict[str, Any]]:
    groups: list[dict[str, Any]] = []
    for index in range(1, len(mouse_list) - 1):
        label = labels.get(mouse_list[index], "")
        if not label:
            continue
        if groups and groups[-1]["label"] == label and groups[-1]["end"] == index - 1:
            groups[-1]["end"] = index
        else:
            groups.append({"start": index, "end": index, "label": label})
    return groups


def _append_test_date(db: Session, titer_order_id: str, test_date: str) -> None:
    if not titer_order_id or not test_date:
        return
    order = db.scalar(select(SerumTiterOrder).where(SerumTiterOrder.titer_order_id == titer_order_id))
    if order is None:
        return
    dates = [str(item) for item in order.test_dates] if isinstance(order.test_dates, list) else []
    if test_date not in dates:
        order.test_dates = sorted([*dates, test_date])


def _import_board(db: Session, plan: TiterPlan) -> None:
    board = db.get(OrderSyncBoard, plan.board_id)
    if board is None:
        return
    previous = _previous_board(db, plan)
    plate = db.get(SerumFacsPlate, previous.facs_plate_id) if previous else None
    if plate is not None and plate.experiment_id != plan.experiment_id:
        plate = None
    if plate is not None and plate.source != SOURCE_MEGA:
        board.import_status = IMPORT_SKIPPED
        board.import_message = "板卡已人工修改，未覆盖"
        board.facs_plate_id = plate.id
        db.commit()
        return

    with tempfile.TemporaryDirectory(prefix="order_sync_") as temp_dir:
        image_name = PurePosixPath(plan.image_path).name
        csv_name = PurePosixPath(plan.csv_path).name
        image_temp = Path(temp_dir) / "image.png"
        csv_temp = Path(temp_dir) / "heatmap.csv"
        try:
            _download(plan.image_path, image_temp)
            _download(plan.csv_path, csv_temp)
        except Exception as exc:
            board.import_status = IMPORT_DOWNLOAD_FAILED
            board.import_message = f"下载失败：{exc}"
            db.commit()
            return

        warnings: list[str] = []
        heatmap = parse_heatmap(read_rows(csv_temp))
        if heatmap.error:
            warnings.append(f"{heatmap.error}，阳性孔未标注")
        elif plan.reported_positive_wells and set(plan.reported_positive_wells) != set(heatmap.positive_wells):
            warnings.append("热图阳性孔与回传 ppc 不一致，以热图为准")

        written: list[Path] = []
        replaced: list[Path] = []
        try:
            files: list[SerumFile] = []
            for name, temp, file_id in (
                (image_name, image_temp, previous.image_file_id if previous else None),
                (csv_name, csv_temp, previous.excel_file_id if previous else None),
            ):
                record, new_path, old_path = write_mega_file(
                    db, plan.experiment_id, name, temp, _mega_file(db, file_id, plan.experiment_id)
                )
                written.append(new_path)
                if old_path is not None:
                    replaced.append(old_path)
                files.append(record)
            db.flush()

            if plate is None:
                plate = SerumFacsPlate(experiment_id=plan.experiment_id, source=SOURCE_MEGA, immune_stage="")
                db.add(plate)
            labels = _group_labels(db, plan.experiment_id)
            plate.qr_code = plan.sample_barcode
            plate.image_file_id = files[0].id
            plate.excel_file_id = files[1].id
            plate.instrument_type = FACS_INSTRUMENT_DOMESTIC
            plate.x_axis = plan.x_axis
            plate.y_axis = plan.y_axis
            plate.cell_target_id = _ensure_target(db, plan.experiment_id, plan.cell_column)
            plate.pc_upper_id = _ensure_pc(db, plan.experiment_id, plan.upper_pc)
            plate.pc_lower_id = _ensure_pc(db, plan.experiment_id, plan.lower_pc)
            plate.upper_mouse_list = list(plan.upper_mouse_list)
            plate.lower_mouse_list = list(plan.lower_mouse_list)
            plate.upper_slot_groups = _slot_groups(plan.upper_mouse_list, labels)
            plate.lower_slot_groups = _slot_groups(plan.lower_mouse_list, labels)
            plate.positive_well_list = list(heatmap.positive_wells)
            _append_test_date(db, plan.titer_order_id, plan.experiment_date)
            db.flush()

            board.import_status = IMPORT_DONE
            board.import_message = "；".join(warnings) or None
            board.facs_plate_id = plate.id
            board.image_file_id = files[0].id
            board.excel_file_id = files[1].id
            db.commit()
        except Exception:
            db.rollback()
            for path in written:
                path.unlink(missing_ok=True)
            raise
    for path in replaced:
        try:
            path.unlink(missing_ok=True)
        except OSError:
            logger.warning("order sync import: old titer file not removed: %s", path)
