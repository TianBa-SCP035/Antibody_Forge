"""合成工单上查看转染配对，以及下载合成公司推送的板布局。"""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from core.errors import NotFoundError
from models.discovery import DiscoverySynthesisOrder
from models.molecular_cell import MolecularTransfectionOrder
from models.supernatant import SynthesisSupernatantWell
from modules.molecular_cell.transfection.proteins import order_proteins

MISSING_ROW = "合成与验证记录不存在"


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


def export_plate_layout(db: Session, row_id: int):
    from utils.excel import build_list_workbook

    row = _order(db, row_id)
    order_no = str(row.order_no or "").strip()
    if not order_no:
        raise ValueError("请先填写订单号")
    wells = db.scalars(
        select(SynthesisSupernatantWell)
        .where(func.lower(SynthesisSupernatantWell.order_no) == order_no.lower())
        .order_by(SynthesisSupernatantWell.plate_no, SynthesisSupernatantWell.well_no, SynthesisSupernatantWell.id)
    ).all()
    if not wells:
        raise NotFoundError("还没有收到这家合成公司的版布局")
    headers = ["订单号", "合成公司", "板号", "孔号", "蛋白名称", "浓度(ug/mL)", "规格(mL/支)", "体积(mL)", "质粒量(ug)"]
    rows = [
        [
            well.order_no,
            well.corp_name,
            well.plate_no,
            well.well_no,
            well.sample_name,
            None if well.potency is None else float(well.potency),
            None if well.specs is None else float(well.specs),
            float(well.volume),
            float(well.sample_enter_vol),
        ]
        for well in wells
    ]
    safe_no = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in order_no) or "order"
    return build_list_workbook(
        sheet_title="版布局",
        filename_prefix=f"版布局_{safe_no}",
        headers=headers,
        rows=rows,
    )
