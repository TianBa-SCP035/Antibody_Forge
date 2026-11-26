"""合成工单上查看转染配对，以及下载合成公司推送的板布局。"""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from core.errors import NotFoundError
from models.discovery import DiscoverySynthesisOrder
from models.molecular_cell import MolecularTransfectionOrder
from models.supernatant import SynthesisSupernatantWell
from modules.discovery.synthesis_progress import service
from modules.discovery.synthesis_progress.constants import TRANSFECTION_ORDER_PREFIX
from modules.molecular_cell.transfection.proteins import order_proteins

MISSING_ROW = "合成与验证记录不存在"
LAYOUT_MISSING = "还没收到合成公司的上清板布局"
ALL_NOT_SYNTHESIZED = "合成公司回复这单的样品都没合成出来，没有上板"


def _order(db: Session, row_id: int) -> DiscoverySynthesisOrder:
    row = db.get(DiscoverySynthesisOrder, row_id)
    if not row:
        raise NotFoundError(MISSING_ROW)
    return row


def transfection_pairs(db: Session, row_id: int) -> dict:
    row = _order(db, row_id)
    code = str(row.order_no or "").strip()
    if not code.upper().startswith("TRF-"):
        return {"transfection_order_id": None, "items": [], "message": "这张工单不是转染交接单"}
    order = db.scalar(
        select(MolecularTransfectionOrder).where(MolecularTransfectionOrder.transfection_order_id == code)
    )
    if not order:
        raise NotFoundError("没有找到对应的转染工单")
    payload = order_proteins(db, order.id)
    return {
        "transfection_order_id": order.transfection_order_id,
        "transfection_id": order.id,
        "items": payload["items"],
    }


def _well_position(well: SynthesisSupernatantWell) -> tuple[str, int]:
    text = str(well.well_no or "")
    return text[:1], int(text[1:] or 0)


def _layout_file_name(row: DiscoverySynthesisOrder, order_no: str) -> str:
    target = str(row.target_name or "").strip()
    name = f"{order_no}孔板上清布局" + (f"-{target}" if target else "")
    return "".join("_" if ch in '\\/:*?"<>|' else ch for ch in name) + ".xlsx"


def _write_plate_grid(ws, order_no: str, target: str, plates: dict[str, list], missing: list[str]) -> None:
    """仿合成公司 COA 的「布局表」：每块板一个 8×12 网格，格子里写蛋白名称。"""
    from openpyxl.styles import Alignment, Font, PatternFill

    from utils.excel import BODY_FONT, FONT_NAME, HEADER_FONT, THIN_BORDER

    marker_fill = PatternFill(fill_type="solid", fgColor="FFFF00")
    center = Alignment(horizontal="center", vertical="center")
    ws["A1"] = order_no
    ws["A1"].font = Font(name=FONT_NAME, size=14, bold=True)
    if target:
        ws["B1"] = target
        ws["B1"].font = Font(name=FONT_NAME, size=12, color="606266")
    ws.row_dimensions[1].height = 42

    def header(cell, value):
        cell.value = value
        cell.font = HEADER_FONT
        cell.fill = marker_fill
        cell.alignment = center
        cell.border = THIN_BORDER

    width = 12.0
    line = 3
    for index, (plate_no, wells) in enumerate(plates.items(), 1):
        ws.cell(line, 1, "板号").font = BODY_FONT
        ws.cell(line, 2, plate_no).font = BODY_FONT
        line += 1
        header(ws.cell(line, 1), f"96孔板{index}")
        for col in range(1, 13):
            header(ws.cell(line, col + 1), col)
        ws.row_dimensions[line].height = 23
        names = {_well_position(well): well.sample_name for well in wells}
        for offset, letter in enumerate("ABCDEFGH", 1):
            header(ws.cell(line + offset, 1), letter)
            for col in range(1, 13):
                cell = ws.cell(line + offset, col + 1, names.get((letter, col)))
                cell.font = BODY_FONT
                cell.alignment = center
                cell.border = THIN_BORDER
                width = max(width, len(str(cell.value or "")) * 1.15 + 2)
            ws.row_dimensions[line + offset].height = 18.75
        line += 10
    if missing:
        for start in range(0, len(missing), 12):
            header(ws.cell(line, 1), "未合成")
            for col, name in enumerate(missing[start:start + 12], 2):
                cell = ws.cell(line, col, name)
                cell.font = BODY_FONT
                cell.alignment = center
                cell.border = THIN_BORDER
                width = max(width, len(name) * 1.15 + 2)
            line += 1
    ws.column_dimensions["A"].width = 12
    for col in range(2, 14):
        ws.column_dimensions[chr(ord("A") + col - 1)].width = min(width, 32)


def _write_well_detail(ws, plates: dict[str, list], missing: list[str]) -> None:
    from utils.excel import BODY_ALIGN, BODY_FONT, HEADER_ALIGN, HEADER_FILL, HEADER_FONT, THIN_BORDER
    from utils.excel import auto_fit_worksheet_columns

    def amount(value):
        return None if value is None else float(value)

    ws.append(["板号", "孔号", "蛋白名称", "浓度(ug/mL)", "规格(mL/支)", "体积(mL)", "质粒量(ug)"])
    for cell in ws[1]:
        cell.font, cell.fill, cell.alignment, cell.border = HEADER_FONT, HEADER_FILL, HEADER_ALIGN, THIN_BORDER
    for plate_no, wells in plates.items():
        for well in wells:
            ws.append([
                plate_no, well.well_no, well.sample_name, amount(well.potency), amount(well.specs),
                amount(well.volume), amount(well.sample_enter_vol),
            ])
    for name in missing:
        ws.append([None, "未合成", name, None, None, None, None])
    for row in ws.iter_rows(min_row=2, max_row=ws.max_row, max_col=ws.max_column):
        for cell in row:
            cell.font, cell.alignment, cell.border = BODY_FONT, BODY_ALIGN, THIN_BORDER
    ws.freeze_panes = "A2"
    auto_fit_worksheet_columns(ws)


def _load_layout(db: Session, row_id: int):
    row = _order(db, row_id)
    order_no = str(row.order_no or "").strip()
    if not order_no:
        raise ValueError("请先填写订单号")
    records = db.scalars(
        select(SynthesisSupernatantWell).where(func.lower(SynthesisSupernatantWell.order_no) == order_no.lower())
    ).all()
    wells = sorted(
        (item for item in records if not item.not_synthesized),
        key=lambda item: (item.plate_no or "", _well_position(item)[1], _well_position(item)[0]),
    )
    plates: dict[str, list] = {}
    for well in wells:
        plates.setdefault(well.plate_no or "", []).append(well)
    missing = sorted(item.sample_name for item in records if item.not_synthesized)
    return row, order_no, records, plates, missing


def plate_layout_preview(db: Session, row_id: int) -> dict:
    """抽屉里预览版布局：网格加孔位明细，没收到时给出原因而不报错。"""
    row, order_no, records, plates, missing = _load_layout(db, row_id)

    def amount(value):
        return None if value is None else float(value)

    def minute(value):
        return value.strftime("%Y-%m-%d %H:%M") if value else None

    message = ""
    if not records:
        message = LAYOUT_MISSING
    elif not plates:
        message = ALL_NOT_SYNTHESIZED
    return {
        "order_no": order_no,
        "target_name": row.target_name or "",
        "supernatant_checked_at": minute(row.supernatant_checked_at),
        "message": message,
        "missing": missing,
        "plates": [
            {
                "plate_no": plate_no,
                "wells": [
                    {
                        "well_no": well.well_no,
                        "sample_name": well.sample_name,
                        "potency": amount(well.potency),
                        "specs": amount(well.specs),
                        "volume": amount(well.volume),
                        "sample_enter_vol": amount(well.sample_enter_vol),
                        "received_at": minute(well.received_at),
                    }
                    for well in wells
                ],
            }
            for plate_no, wells in plates.items()
        ],
    }


def export_plate_layout(db: Session, row_id: int):
    from io import BytesIO

    from openpyxl import Workbook

    row, order_no, records, plates, missing = _load_layout(db, row_id)
    if not plates:
        raise NotFoundError(LAYOUT_MISSING if not records else ALL_NOT_SYNTHESIZED)

    wb = Workbook()
    grid = wb.active
    grid.title = f"{order_no}布局表"[:31]
    _write_plate_grid(grid, order_no, str(row.target_name or "").strip(), plates, missing)
    _write_well_detail(wb.create_sheet("孔位明细"), plates, missing)
    output = BytesIO()
    wb.save(output)
    output.seek(0)
    return output, _layout_file_name(row, order_no)


def query_plate_layout(db: Session, row_id: int) -> dict:
    """抽屉里点「版布局」但还没收到时，当场向合成公司查一次。"""
    from modules.supernatant_receive import query

    row = _order(db, row_id)
    order_no = str(row.order_no or "").strip()
    if not order_no:
        raise ValueError("请先填写订单号")
    if order_no.upper().startswith(TRANSFECTION_ORDER_PREFIX):
        result = {"state": query.UNSUPPORTED, "message": "转染交接单没有合成公司的上清板布局"}
    else:
        result = query.pull_order(db, row.synthetic_corp, order_no)
        db.refresh(row)
    return {**result, "row": service.serialize_order(row)}
