"""镁伽结果回传核对：对照工单当时下发的 payload 快照，逐单、逐检测板、逐孔核对。

只查库、不碰 SMB，结果同步回复给镁伽；核对通过的效价板由 titer_import 在后台导入。
"""

from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from integrations.fcs_smb import FcsSmbError, normalize_relative_path
from models.immunology import SerumImmProject, SerumTiterOrder
from models.mega_automation import MegaFlowWorkOrder, MegaFlowWorkOrderDispatch
from modules.mega_automation.content import cell_plate_display_barcode, clean_text, safe_dict, safe_list
from modules.order_sync.heatmap import POSITIVE_RATE_THRESHOLD
from utils.normalize import normalize_date

ORDER_TYPE_TITER = "TITER"
ORDER_STATUS_CANCELLED = "cancelled"
ORDER_STATUS_COMPLETED = "completed"
DISPATCH_STATUS_VOIDED = "voided"

BOARD_PASSED = "passed"
BOARD_REJECTED = "rejected"
BOARD_ARCHIVED = "archived"
ORDER_ACCEPTED = "accepted"
ORDER_PARTIAL = "partial"
ORDER_REJECTED = "rejected"

# 效价布局：第 1 列 NC、第 12 列 PC，样本在 A02–A11（上半板）和 E02–E11（下半板）。
UPPER_ROW = "A"
LOWER_ROW = "E"
PC_COLUMN = 12
SAMPLE_COLUMNS = range(2, 12)
MAX_LISTED_WELLS = 8
_WELL_NO_RE = re.compile(r"^([A-H])0?([1-9]|1[0-2])$")
_COMPACT_DATE_RE = re.compile(r"^(\d{4})(\d{2})(\d{2})$")


@dataclass
class TiterPlan:
    """一块核对通过的效价检测板导入效价模块所需的全部信息。"""

    board_id: int = 0
    experiment_id: str = ""
    titer_order_id: str = ""
    work_order_id: int = 0
    sample_barcode: str = ""
    cell_name: str = ""
    image_path: str = ""
    csv_path: str = ""
    experiment_date: str = ""
    x_axis: str = ""
    y_axis: str = ""
    cell_column: dict[str, Any] = field(default_factory=dict)
    upper_mouse_list: list[str] = field(default_factory=list)
    lower_mouse_list: list[str] = field(default_factory=list)
    upper_pc: dict[str, Any] | None = None
    lower_pc: dict[str, Any] | None = None
    reported_positive_wells: list[str] = field(default_factory=list)


@dataclass
class BoardResult:
    seq: int
    order_no: str
    data_type: str
    detect_barcode: str
    cell_name: str
    image_path: str
    csv_path: str
    experiment_date: str
    status: str = BOARD_REJECTED
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    work_order_id: int | None = None
    dispatch_id: str = ""
    experiment_id: str = ""
    sample_barcode: str = ""
    plan: TiterPlan | None = None

    @property
    def message(self) -> str:
        return "；".join([*self.errors, *self.warnings])


@dataclass
class OrderResult:
    order_no: str
    status: str = ORDER_REJECTED
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    boards: list[BoardResult] = field(default_factory=list)

    @property
    def message(self) -> str:
        return "；".join([*self.errors, *self.warnings])


@dataclass
class _OrderContext:
    work_order: MegaFlowWorkOrder
    dispatch: MegaFlowWorkOrderDispatch
    sample_plates: list[dict[str, Any]]
    cell_columns: dict[tuple[str, int], dict[str, Any]]
    pc_infos: dict[str, dict[str, Any]]
    titer_order_id: str
    experiment_id: str


def normalize_well_no(value: Any) -> str:
    matched = _WELL_NO_RE.match(clean_text(value).upper())
    return f"{matched.group(1)}{int(matched.group(2)):02d}" if matched else ""


def normalize_experiment_date(value: Any) -> str:
    text = clean_text(value)
    compact = _COMPACT_DATE_RE.match(text)
    if compact:
        text = "-".join(compact.groups())
    try:
        return normalize_date(text) or ""
    except ValueError:
        return ""


def _listed(items: list[str]) -> str:
    shown = "、".join(items[:MAX_LISTED_WELLS])
    return f"{shown} 等 {len(items)} 处" if len(items) > MAX_LISTED_WELLS else shown


def _resolve_work_order(db: Session, order_no: str) -> tuple[MegaFlowWorkOrder | None, str]:
    orders = db.scalars(
        select(MegaFlowWorkOrder).where(MegaFlowWorkOrder.orderNum == order_no).order_by(MegaFlowWorkOrder.id.desc())
    ).all()
    if not orders:
        return None, "订单不存在"
    candidates = [order for order in orders if order.status != ORDER_STATUS_CANCELLED and order.sent_at]
    if len(candidates) > 1:
        return None, "订单号对应多张工单"
    if candidates:
        return candidates[0], ""
    if all(order.status == ORDER_STATUS_CANCELLED for order in orders):
        return None, "工单已作废"
    return None, "工单未下发"


def _latest_dispatch(db: Session, work_order_id: int) -> MegaFlowWorkOrderDispatch | None:
    return db.scalars(
        select(MegaFlowWorkOrderDispatch)
        .where(
            MegaFlowWorkOrderDispatch.work_order_id == work_order_id,
            MegaFlowWorkOrderDispatch.status != DISPATCH_STATUS_VOIDED,
        )
        .order_by(MegaFlowWorkOrderDispatch.id.desc())
        .limit(1)
    ).first()


def _cell_columns(cell_plates: list[Any]) -> dict[tuple[str, int], dict[str, Any]]:
    columns: dict[tuple[str, int], dict[str, Any]] = {}
    for index, plate in enumerate(cell_plates):
        if not isinstance(plate, dict):
            continue
        barcode = cell_plate_display_barcode(plate, index)
        for column in safe_list(plate.get("columns")):
            if not isinstance(column, dict):
                continue
            try:
                column_no = int(column.get("column_no"))
            except (TypeError, ValueError):
                continue
            columns[(barcode, column_no)] = column
    return columns


def _build_context(db: Session, work_order: MegaFlowWorkOrder, dispatch: MegaFlowWorkOrderDispatch) -> _OrderContext:
    detail = safe_dict(safe_dict(dispatch.payload).get("orderDetail"))
    pc_infos = {
        clean_text(item.get("pc_id")): item
        for item in safe_list(detail.get("pc_infos"))
        if isinstance(item, dict) and clean_text(item.get("pc_id"))
    }
    titer_order_id = ""
    experiment_id = ""
    source_id = clean_text(work_order.source_id)
    if source_id:
        titer_order = db.scalar(select(SerumTiterOrder).where(SerumTiterOrder.titer_order_id == source_id))
        if titer_order:
            titer_order_id = titer_order.titer_order_id
            experiment_id = clean_text(titer_order.experiment_id)
    return _OrderContext(
        work_order=work_order,
        dispatch=dispatch,
        sample_plates=[plate for plate in safe_list(detail.get("sample_plates")) if isinstance(plate, dict)],
        cell_columns=_cell_columns(safe_list(detail.get("cell_plates"))),
        pc_infos=pc_infos,
        titer_order_id=titer_order_id,
        experiment_id=experiment_id,
    )


def _wells_by_no(items: Any) -> dict[str, dict[str, Any]]:
    wells: dict[str, dict[str, Any]] = {}
    for well in safe_list(items):
        if isinstance(well, dict):
            well_no = normalize_well_no(well.get("well_no"))
            if well_no:
                wells[well_no] = well
    return wells


def _plate_wells(plate: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return _wells_by_no(plate.get("wells"))


def _reported_wells(detect: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return _wells_by_no(detect.get("well_infos"))


def _compare_wells(
    plate: dict[str, Any],
    reported: dict[str, dict[str, Any]],
) -> tuple[list[str], list[str]]:
    """只核对 SAMPLE 孔：返回（不一致的孔、回传缺的孔）。"""
    mismatched: list[str] = []
    missing: list[str] = []
    for well_no, well in sorted(_plate_wells(plate).items()):
        if clean_text(well.get("content_type")).upper() != "SAMPLE":
            continue
        expected = clean_text(well.get("sample_code"))
        if not expected:
            continue
        if well_no not in reported:
            missing.append(well_no)
            continue
        actual = clean_text(reported[well_no].get("sample_name"))
        if actual != expected:
            mismatched.append(f"{well_no} 应为 {expected}，回传 {actual or '空'}")
    return mismatched, missing


def _sample_plate(plates: list[dict[str, Any]], sample_code: str) -> dict[str, Any] | None:
    """镁伽协议里 sample_code 是样本板条码，须与下发的样品板条码一致；barcode 是镁伽检测板条码，不参与对应。"""
    for plate in plates:
        if clean_text(plate.get("barcode")) == sample_code:
            return plate
    return None


def _match_cell_column(
    context: _OrderContext,
    plate: dict[str, Any],
    cell_name: str,
) -> tuple[dict[str, Any] | None, list[str]]:
    selected: list[dict[str, Any]] = []
    for key in safe_list(plate.get("cell_keys")):
        if not isinstance(key, dict):
            continue
        try:
            column = context.cell_columns.get((clean_text(key.get("barcode")), int(key.get("column_no"))))
        except (TypeError, ValueError):
            continue
        if column and clean_text(column.get("cell_name")):
            selected.append(column)
    names = [clean_text(column.get("cell_name")) for column in selected]
    wanted = cell_name.casefold()
    for column in selected:
        if clean_text(column.get("cell_name")).casefold() == wanted:
            return column, names
    return None, names


def _mouse_list(plate: dict[str, Any], row: str) -> list[str]:
    wells = _plate_wells(plate)
    middle = []
    for column in SAMPLE_COLUMNS:
        well = wells.get(f"{row}{column:02d}") or {}
        is_sample = clean_text(well.get("content_type")).upper() == "SAMPLE"
        middle.append(clean_text(well.get("sample_code")) if is_sample else "")
    return ["NC", *middle, "PC"]


def _pc_info(context: _OrderContext, plate: dict[str, Any], row: str) -> dict[str, Any] | None:
    well = _plate_wells(plate).get(f"{row}{PC_COLUMN:02d}") or {}
    pc_id = clean_text(well.get("pc_id"))
    return context.pc_infos.get(pc_id) if pc_id else None


def _reported_positive_wells(reported: dict[str, dict[str, Any]]) -> list[str]:
    wells = []
    for well_no, well in sorted(reported.items()):
        try:
            ppc = float(well.get("ppc"))
        except (TypeError, ValueError):
            continue
        if ppc > POSITIVE_RATE_THRESHOLD:
            wells.append(f"{well_no[0]}{int(well_no[1:])}")
    return wells


def _check_path(board: BoardResult, value: Any, suffix: str, label: str) -> str:
    try:
        path = normalize_relative_path(value)
    except FcsSmbError as exc:
        board.errors.append(f"{label}{exc}")
        return clean_text(value)
    if not path.lower().endswith(suffix):
        board.errors.append(f"{label}必须是 {suffix} 文件")
    return path


def _resolve_experiment(db: Session, context: _OrderContext, plate: dict[str, Any]) -> str:
    if context.experiment_id:
        return context.experiment_id
    project_no = clean_text(plate.get("project_no"))
    if project_no and db.scalar(select(SerumImmProject.id).where(SerumImmProject.experiment_id == project_no)):
        return project_no
    return ""


def _verify_titer_board(
    db: Session,
    context: _OrderContext,
    board: BoardResult,
    project: dict[str, Any],
    detect: dict[str, Any],
    seen: set[tuple[str, str]],
) -> None:
    board.image_path = _check_path(board, detect.get("whole_board_img"), ".png", "可视化图")
    board.csv_path = _check_path(board, detect.get("heatmap_csv"), ".csv", "热图")

    if not board.sample_barcode:
        board.errors.append("sample_code 为空")
        return
    plate = _sample_plate(context.sample_plates, board.sample_barcode)
    if plate is None:
        board.errors.append(f"样本板 {board.sample_barcode} 不在下发的样品板中")
        return
    reported = _reported_wells(detect)

    column, names = _match_cell_column(context, plate, board.cell_name)
    if column is None:
        options = "、".join(names) if names else "无"
        board.errors.append(f"细胞 {board.cell_name or '（空）'} 不在样品板所选细胞中（可选：{options}）")
    else:
        board.cell_name = clean_text(column.get("cell_name"))

    mismatched, missing = _compare_wells(plate, reported)
    if mismatched:
        board.errors.append(f"鼠号不一致：{_listed(mismatched)}")
    if missing:
        board.warnings.append(f"回传缺孔：{_listed(missing)}")

    board.experiment_id = _resolve_experiment(db, context, plate)
    if not board.experiment_id:
        board.errors.append("找不到效价实验")

    target = clean_text(project.get("target"))
    plate_target = clean_text(plate.get("target"))
    if target and plate_target and target.casefold() != plate_target.casefold():
        board.warnings.append(f"靶点与样品板不一致（回传 {target}，样品板 {plate_target}）")
    if not board.experiment_date:
        board.warnings.append("实验日期无法识别，不写入检测日期")
    x_axis = clean_text(detect.get("x_axis"))
    y_axis = clean_text(detect.get("y_axis"))
    if not x_axis or not y_axis:
        board.warnings.append("x_axis / y_axis 未填，板卡坐标留空")

    identity = (board.sample_barcode, board.cell_name.casefold())
    if identity in seen:
        board.warnings.append("本次推送中重复出现，后面的板会覆盖前面的导入")
    seen.add(identity)

    if board.errors or column is None:
        return
    board.status = BOARD_PASSED
    board.plan = TiterPlan(
        experiment_id=board.experiment_id,
        titer_order_id=context.titer_order_id,
        work_order_id=context.work_order.id,
        sample_barcode=board.sample_barcode,
        cell_name=board.cell_name,
        image_path=board.image_path,
        csv_path=board.csv_path,
        experiment_date=board.experiment_date,
        x_axis=x_axis,
        y_axis=y_axis,
        cell_column=dict(column),
        upper_mouse_list=_mouse_list(plate, UPPER_ROW),
        lower_mouse_list=_mouse_list(plate, LOWER_ROW),
        upper_pc=_pc_info(context, plate, UPPER_ROW),
        lower_pc=_pc_info(context, plate, LOWER_ROW),
        reported_positive_wells=_reported_positive_wells(reported),
    )


def _iter_detect_boards(order_info: dict[str, Any]):
    for project in safe_list(order_info.get("project_infos")):
        if not isinstance(project, dict):
            continue
        for cell_board in safe_list(project.get("cell_board_infos")):
            if not isinstance(cell_board, dict):
                continue
            for detect in safe_list(cell_board.get("detect_board_infos")):
                if isinstance(detect, dict):
                    yield project, cell_board, detect


def _order_status(order: OrderResult) -> str:
    if order.errors:
        return ORDER_REJECTED
    if not order.boards:
        return ORDER_ACCEPTED
    passed = sum(1 for board in order.boards if board.status != BOARD_REJECTED)
    if passed == len(order.boards):
        return ORDER_ACCEPTED
    return ORDER_PARTIAL if passed else ORDER_REJECTED


def verify_order(db: Session, order_info: dict[str, Any], next_seq: int) -> OrderResult:
    order_no = clean_text(order_info.get("order_no"))
    result = OrderResult(order_no=order_no)

    context: _OrderContext | None = None
    work_order, reason = _resolve_work_order(db, order_no)
    if work_order is None:
        result.errors.append(reason)
    else:
        dispatch = _latest_dispatch(db, work_order.id)
        if dispatch is None:
            result.errors.append("工单未下发")
        else:
            context = _build_context(db, work_order, dispatch)
            if work_order.status != ORDER_STATUS_COMPLETED:
                result.warnings.append("工单尚未完成")

    is_titer = context is not None and clean_text(context.work_order.orderType).upper() == ORDER_TYPE_TITER
    seen: set[tuple[str, str]] = set()
    for project, cell_board, detect in _iter_detect_boards(order_info):
        board = BoardResult(
            seq=next_seq + len(result.boards),
            order_no=order_no,
            data_type=clean_text(project.get("data_type")).upper(),
            detect_barcode=clean_text(detect.get("barcode")),
            sample_barcode=clean_text(detect.get("sample_code")),
            cell_name=clean_text(cell_board.get("cell_name")),
            image_path=clean_text(detect.get("whole_board_img")),
            csv_path=clean_text(detect.get("heatmap_csv")),
            experiment_date=normalize_experiment_date(project.get("experiment_date")),
        )
        result.boards.append(board)
        if context is None:
            board.errors.append(f"整单未通过：{'；'.join(result.errors)}")
            continue
        board.work_order_id = context.work_order.id
        board.dispatch_id = context.dispatch.dispatchId
        if not is_titer:
            board.status = BOARD_ARCHIVED
            board.warnings.append("非效价工单，仅存档")
            continue
        _verify_titer_board(db, context, board, project, detect, seen)

    if context is not None and is_titer and not result.boards:
        result.errors.append("没有检测板数据")
    if context is not None and not is_titer:
        result.warnings.append("非效价工单，仅存档")
    result.status = _order_status(result)
    return result
