"""冻存细胞出库申请：文库工单按来源发现安排取在库的留存细胞，一次提交为一张申请单，审核通过才写出库。"""

from __future__ import annotations

import secrets
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.errors import NotFoundError
from models.discovery import DiscoveryCellBank, DiscoveryWorkbench
from models.molecular_cell import MolecularCellCheckoutItem, MolecularCellCheckoutRequest, MolecularLibraryOrder
from modules.molecular_cell.library_orders import service
from utils.clock import now_local, today_local
from utils.normalize import parse_date

STATUS_PENDING = "待审核"
STATUS_APPROVED = "已通过"
STATUS_REJECTED = "已驳回"
STATUS_OPTIONS = (STATUS_PENDING, STATUS_APPROVED, STATUS_REJECTED)
MAX_ORDERS = 500
MAX_REQUESTS = 200
REQUEST_PREFIX = "CKO"
STALE_SELECTION = "部分冻存细胞已出库或在审核中，请刷新后重试"


def pending_cell_bank_ids(db: Session, cell_bank_ids: list[int] | None = None) -> dict[int, str]:
    """在待审核申请单里的留存细胞 → 申请单号。"""
    stmt = (
        select(MolecularCellCheckoutItem.cell_bank_id, MolecularCellCheckoutRequest.request_no)
        .join(MolecularCellCheckoutRequest, MolecularCellCheckoutRequest.id == MolecularCellCheckoutItem.request_id)
        .where(MolecularCellCheckoutRequest.status == STATUS_PENDING)
    )
    if cell_bank_ids is not None:
        stmt = stmt.where(MolecularCellCheckoutItem.cell_bank_id.in_(cell_bank_ids))
    return {int(bank_id): request_no for bank_id, request_no in db.execute(stmt).all()}


def _selected_orders(db: Session, data: dict[str, Any], scope: service.TypeScope) -> list[MolecularLibraryOrder]:
    order_ids = [int(value) for value in data.get("order_ids") or [] if int(value) > 0]
    if order_ids:
        rows = db.scalars(
            select(MolecularLibraryOrder).where(MolecularLibraryOrder.id.in_(order_ids), *service._scope_clauses(scope))
        ).all()
        position = {order_id: index for index, order_id in enumerate(order_ids)}
        return sorted(rows, key=lambda row: position[row.id])
    filters = dict(data.get("filters") or {})
    if not str(filters.get("library_code") or "").strip():
        raise ValueError("请先按建库编号筛选")
    stmt = service._apply_list_filters(select(MolecularLibraryOrder), filters, db=db, scope=scope)
    rows = db.scalars(stmt.order_by(*service._list_order(filters)).limit(MAX_ORDERS + 1)).all()
    if len(rows) > MAX_ORDERS:
        raise ValueError(f"一次最多出库 {MAX_ORDERS} 条工单，请缩小筛选范围")
    return list(rows)


def _candidate_rows(
    db: Session, data: dict[str, Any], scope: service.TypeScope
) -> tuple[list[MolecularLibraryOrder], list[dict[str, Any]], int]:
    orders = _selected_orders(db, data, scope)
    discovery_ids = {row.source_discovery_id for row in orders if row.source_discovery_id}
    banks: dict[str, list[DiscoveryCellBank]] = {}
    if discovery_ids:
        stmt = (
            select(DiscoveryWorkbench.discovery_id, DiscoveryCellBank)
            .join(DiscoveryWorkbench, DiscoveryWorkbench.id == DiscoveryCellBank.workbench_id)
            .where(DiscoveryWorkbench.discovery_id.in_(discovery_ids), DiscoveryCellBank.checked_out_on.is_(None))
            .order_by(DiscoveryCellBank.id)
        )
        for discovery_id, bank in db.execute(stmt).all():
            banks.setdefault(discovery_id, []).append(bank)
    all_bank_ids = [bank.id for rows in banks.values() for bank in rows]
    pending = pending_cell_bank_ids(db, all_bank_ids) if all_bank_ids else {}
    items: list[dict[str, Any]] = []
    seen: set[int] = set()
    for order in orders:
        for bank in banks.get(order.source_discovery_id or "", []):
            if bank.id in seen or bank.id in pending:
                continue
            seen.add(bank.id)
            items.append({
                "cell_bank_id": bank.id,
                "library_order_id": order.id,
                "library_code": order.library_code,
                "discovery_id": order.source_discovery_id,
                "target_name": order.target_name,
                "instrument_on": order.instrument_on.isoformat() if order.instrument_on else None,
                "mouse_strain": order.mouse_strain,
                "sample_source": service.SAMPLE_SOURCE_LABELS.get(order.sample_source or "", order.sample_source),
                "cell_kind": bank.cell_kind,
                "cell_count": bank.cell_count,
                "tube_count": bank.tube_count,
                "box_location": bank.box_location,
                "remark": bank.remark,
            })
    return orders, items, len(pending)


def candidates(db: Session, data: dict[str, Any], scope: service.TypeScope = None) -> dict[str, Any]:
    orders, items, pending_count = _candidate_rows(db, data, scope)
    return {
        "order_count": len(orders),
        "linked_count": sum(1 for row in orders if row.source_discovery_id),
        "pending_count": pending_count,
        "items": items,
    }


def _next_request_no(db: Session) -> str:
    stamp = now_local().strftime("%y%m%d")
    for _ in range(20):
        suffix = "".join(secrets.choice(service.LIBRARY_ID_ALPHABET) for _ in range(service.LIBRARY_ID_RANDOM_LEN))
        candidate = f"{REQUEST_PREFIX}-{stamp}-{suffix}"
        exists = db.scalar(
            select(MolecularCellCheckoutRequest.id).where(MolecularCellCheckoutRequest.request_no == candidate)
        )
        if not exists:
            return candidate
    raise ValueError("无法分配出库申请单号")


def _request_payload(request: MolecularCellCheckoutRequest, items: list[MolecularCellCheckoutItem]) -> dict[str, Any]:
    return {**request.to_dict(), "items": [item.to_dict() for item in items]}


def submit(
    db: Session, data: dict[str, Any], applicant: str | None, scope: service.TypeScope = None
) -> dict[str, Any]:
    wanted = [int(value) for value in data.get("cell_bank_ids") or []]
    if not wanted:
        raise ValueError("请选择要出库的冻存细胞")
    _, items, _ = _candidate_rows(db, data, scope)
    available = {item["cell_bank_id"]: item for item in items}
    if any(bank_id not in available for bank_id in wanted):
        raise ValueError(STALE_SELECTION)
    request = MolecularCellCheckoutRequest(
        request_no=_next_request_no(db),
        status=STATUS_PENDING,
        applicant=(applicant or "").strip() or None,
        applied_on=today_local(),
        item_count=len(set(wanted)),
    )
    db.add(request)
    db.flush()
    rows = []
    for bank_id in dict.fromkeys(wanted):
        item = available[bank_id]
        rows.append(MolecularCellCheckoutItem(
            request_id=request.id,
            cell_bank_id=bank_id,
            library_order_id=item["library_order_id"],
            library_code=item["library_code"],
            discovery_id=item["discovery_id"],
            target_name=item["target_name"],
            instrument_on=parse_date(item["instrument_on"]),
            mouse_strain=item["mouse_strain"],
            sample_source=item["sample_source"],
            cell_kind=item["cell_kind"],
            cell_count=item["cell_count"],
            tube_count=item["tube_count"],
            box_location=item["box_location"],
            remark=item["remark"],
        ))
    db.add_all(rows)
    db.commit()
    return _request_payload(request, rows)


def _scope_filters(scope: service.TypeScope) -> list:
    """含范围外建库类型工单的申请单按不存在处理。"""
    if scope is None:
        return []
    outside = (
        select(MolecularCellCheckoutItem.request_id)
        .join(MolecularLibraryOrder, MolecularLibraryOrder.id == MolecularCellCheckoutItem.library_order_id)
        .where(MolecularLibraryOrder.build_type.not_in(scope))
    )
    return [MolecularCellCheckoutRequest.id.not_in(outside)]


def list_requests(db: Session, data: dict[str, Any], scope: service.TypeScope = None) -> dict[str, Any]:
    stmt = select(MolecularCellCheckoutRequest).where(*_scope_filters(scope))
    status = str(data.get("status") or "").strip()
    if status:
        stmt = stmt.where(MolecularCellCheckoutRequest.status == status)
    requests = db.scalars(stmt.order_by(MolecularCellCheckoutRequest.id.desc()).limit(MAX_REQUESTS)).all()
    by_request: dict[int, list[MolecularCellCheckoutItem]] = {}
    if requests:
        items = db.scalars(
            select(MolecularCellCheckoutItem)
            .where(MolecularCellCheckoutItem.request_id.in_([row.id for row in requests]))
            .order_by(MolecularCellCheckoutItem.id)
        ).all()
        for item in items:
            by_request.setdefault(item.request_id, []).append(item)
    return {"items": [_request_payload(row, by_request.get(row.id, [])) for row in requests]}


def review(
    db: Session,
    request_id: int,
    approve: bool,
    reviewer: str | None,
    note: Any = None,
    scope: service.TypeScope = None,
) -> dict[str, Any]:
    request = db.scalar(
        select(MolecularCellCheckoutRequest).where(MolecularCellCheckoutRequest.id == request_id, *_scope_filters(scope))
    )
    if not request:
        raise NotFoundError("出库申请单不存在")
    if request.status != STATUS_PENDING:
        raise ValueError("申请单已审核")
    note_text = str(note or "").strip()
    if len(note_text) > 500:
        raise ValueError("审核意见不能超过 500 个字")
    items = db.scalars(
        select(MolecularCellCheckoutItem)
        .where(MolecularCellCheckoutItem.request_id == request.id)
        .order_by(MolecularCellCheckoutItem.id)
    ).all()
    if approve:
        banks = {
            bank.id: bank
            for bank in db.scalars(
                select(DiscoveryCellBank).where(DiscoveryCellBank.id.in_([item.cell_bank_id for item in items]))
            ).all()
        }
        today = today_local().isoformat()
        for item in items:
            bank = banks.get(item.cell_bank_id)
            if bank is None or bank.checked_out_on:
                continue
            bank.checked_out_by = request.applicant or reviewer
            bank.checked_out_on = today
    request.status = STATUS_APPROVED if approve else STATUS_REJECTED
    request.reviewer = (reviewer or "").strip() or None
    request.reviewed_at = now_local()
    request.review_note = note_text or None
    db.commit()
    return _request_payload(request, list(items))
