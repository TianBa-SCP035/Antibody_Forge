"""合成公司推送的上清板布局：校验后一孔一行保存，同一「订单号 + 板号 + 孔号」再推时覆盖该孔。
未合成的样品按「订单号 + 样品名」记一行标记，样品后来上板时去掉标记。"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
import json
import re
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from models.discovery import DiscoverySynthesisOrder
from models.supernatant import SynthesisSupernatantWell
from modules.discovery.synthesis_progress.constants import STATUS_CANCELLED, STATUS_COMPLETED, SUPPLY_MODE_ARRIVAL
from modules.discovery.synthesis_progress.one_sync import sync_derived_statuses
from utils.clock import now_local

MAX_TEXT = 64
# 君跻旧板号形如「订单号-GSZB00159/20R246_RMBWB02B11_Protein Supernatant-A」，超过 64
MAX_PLATE_NO = 128
MAX_SAMPLE_NAME = 128
MAX_ERRORS = 10
# 对应 DECIMAL(16,4)
_SCALE = Decimal("0.0001")
_NUMBER_LIMIT = Decimal(10) ** 12
_WELL = re.compile(r"([A-H])0?([1-9]|1[0-2])")
# (小写键, 存储键, 报错时的字段名, 是否允许 '/' 表示不适用)
_NUMBER_FIELDS = (
    ("potency", "potency", "potency", True),
    ("specs", "specs", "specs", True),
    ("volume", "volume", "volume", False),
    ("sampleentervol", "sample_enter_vol", "sampleEnterVol", False),
)
_NOT_APPLICABLE = {"/", "／"}
# 没合成出来的样品也会推过来，样品不在板上：擎科孔号写这个，君跻板号写「未合成」、孔号写 0
_NOT_ON_PLATE = {"未合成", "noshipping"}


class SupernatantReceiveError(Exception):
    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


def _lower_keys(item: dict[str, Any]) -> dict[str, Any]:
    # 对方文档里同一字段有 samplename / sampleName / Samplename 几种写法
    return {str(key).strip().lower(): value for key, value in item.items()}


def _text(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _number(value: Any, label: str, *, optional: bool = False) -> tuple[Decimal | None, str | None]:
    if isinstance(value, bool):
        return None, f"{label} 必须是数字"
    text = _text(value)
    if optional and text in _NOT_APPLICABLE:
        return None, None
    if not text:
        return None, f"{label} 不能为空"
    try:
        number = Decimal(text)
    except InvalidOperation:
        return None, f"{label}「{text}」不是数字"
    if not number.is_finite() or number < 0:
        return None, f"{label}「{text}」必须是非负数"
    if number >= _NUMBER_LIMIT:
        return None, f"{label}「{text}」超出范围"
    return number.quantize(_SCALE, rounding=ROUND_HALF_UP), None


def _required_text(value: Any, label: str, limit: int, errors: list[str]) -> str:
    text = _text(value)
    if not text:
        errors.append(f"{label} 不能为空")
    elif len(text) > limit:
        errors.append(f"{label} 超过 {limit} 个字符")
    return text


def _fail(errors: list[str]) -> SupernatantReceiveError:
    message = "；".join(errors[:MAX_ERRORS])
    if len(errors) > MAX_ERRORS:
        message += f"；另有 {len(errors) - MAX_ERRORS} 处错误"
    return SupernatantReceiveError(message)


def parse_payload(raw: bytes) -> tuple[str, str, dict[str, dict[str, dict[str, Any]]], list[str]]:
    """返回 (订单号, 合成公司, {板号: {孔号: 孔位}}, 未合成样品名)；任一处不合格整次拒收。"""
    try:
        body = json.loads(raw.decode("utf-8"))
    except UnicodeDecodeError as exc:
        raise SupernatantReceiveError("请求体必须是 UTF-8 编码") from exc
    except json.JSONDecodeError as exc:
        raise SupernatantReceiveError(f"JSON 格式错误：{exc.msg}（第 {exc.lineno} 行第 {exc.colno} 列）") from exc
    if not isinstance(body, dict):
        raise SupernatantReceiveError("请求体必须是 JSON 对象")
    body = _lower_keys(body)

    errors: list[str] = []
    order_no = _required_text(body.get("orderno"), "orderNo", MAX_TEXT, errors)
    corp_name = _required_text(body.get("corpname"), "corpName", MAX_TEXT, errors)
    rows = body.get("data")
    if not isinstance(rows, list) or not rows:
        errors.append("data 必须是非空数组")
        raise _fail(errors)

    plates: dict[str, dict[str, dict[str, Any]]] = {}
    not_synthesized: dict[str, None] = {}
    for index, item in enumerate(rows, start=1):
        if not isinstance(item, dict):
            errors.append(f"data[{index}] 必须是对象")
            continue
        item = _lower_keys(item)
        row_errors: list[str] = []
        well_text = _text(item.get("wellno"))
        if well_text.lower() in _NOT_ON_PLATE or _text(item.get("plateno")).lower() in _NOT_ON_PLATE:
            # 未合成的行只认样品名，浓度、体积对方会填 M、0 之类，不校验
            sample_name = _required_text(item.get("samplename"), "sampleName", MAX_SAMPLE_NAME, row_errors)
            if row_errors:
                errors.append(f"data[{index}]：" + "，".join(row_errors))
            else:
                not_synthesized[sample_name] = None
            continue
        plate_no = _required_text(item.get("plateno"), "plateno", MAX_PLATE_NO, row_errors)
        well = _WELL.fullmatch(well_text.upper())
        if not well:
            row_errors.append(f"wellno「{well_text}」不是 96 孔板孔号（A1-H12）")
        sample_name = _required_text(item.get("samplename"), "sampleName", MAX_SAMPLE_NAME, row_errors)
        numbers: dict[str, Decimal | None] = {}
        for source_key, stored_key, label, optional in _NUMBER_FIELDS:
            value, problem = _number(item.get(source_key), label, optional=optional)
            if problem:
                row_errors.append(problem)
            numbers[stored_key] = value
        if row_errors:
            errors.append(f"data[{index}]：" + "，".join(row_errors))
            continue

        well_no = f"{well[1]}{int(well[2]):02d}"
        wells = plates.setdefault(plate_no, {})
        if well_no in wells:
            errors.append(f"data[{index}]：板 {plate_no} 的孔号 {well_no} 重复")
            continue
        wells[well_no] = {"well_no": well_no, "sample_name": sample_name, **numbers}

    if errors:
        raise _fail(errors)
    return order_no, corp_name, plates, list(not_synthesized)


def _mark_shipped(db: Session, order_no: str, ship_date: str, well_count: int, *, keep_date: bool = False) -> None:
    """合成与验证的发货日期、发货个数只取上清推送：首次推送当天、板上蛋白数。
    keep_date：补查到的布局不知道实际发货日，已有发货日期的工单不改日期。"""
    from modules.discovery.synthesis_progress.service import settle_queue_after_sync

    orders = db.scalars(
        select(DiscoverySynthesisOrder).where(
            func.lower(DiscoverySynthesisOrder.order_no) == order_no.lower(),
            DiscoverySynthesisOrder.supply_mode == SUPPLY_MODE_ARRIVAL,
            DiscoverySynthesisOrder.status.not_in((STATUS_COMPLETED, STATUS_CANCELLED)),
        )
    ).all()
    status_changed = False
    for row in orders:
        row.arrival_count = well_count
        if row.arrival_date == ship_date or (keep_date and row.arrival_date):
            continue
        before = row.status
        row.arrival_date = ship_date
        sync_derived_statuses(row, changed_fields={"arrival_date"})
        status_changed = status_changed or row.status != before
    if status_changed:
        settle_queue_after_sync(db)


def receive(db: Session, raw: bytes, *, pulled: bool = False) -> dict[str, Any]:
    # 对方一单会分几批推，同一块板可能拆在不同批里，所以只按孔位覆盖，不删整板
    order_no, corp_name, plates, not_synthesized = parse_payload(raw)
    rows = db.scalars(
        select(SynthesisSupernatantWell).where(SynthesisSupernatantWell.order_no == order_no)
    ).all()
    existing = {(row.plate_no, row.well_no): row for row in rows if not row.not_synthesized}
    now = now_local()
    first_received = min((row.received_at for row in existing.values() if row.received_at), default=now)
    ship_date = first_received.date().isoformat()
    pending = {row.sample_name: row for row in rows if row.not_synthesized}
    on_plate = {row.sample_name for row in rows if not row.not_synthesized}
    for plate_no, wells in plates.items():
        for well_no in sorted(wells):
            fields = wells[well_no]
            on_plate.add(fields["sample_name"])
            marker = pending.pop(fields["sample_name"], None)
            if marker is not None:
                db.delete(marker)
            row = existing.get((plate_no, well_no))
            if row is None:
                db.add(SynthesisSupernatantWell(
                    order_no=order_no, corp_name=corp_name, plate_no=plate_no, received_at=now, **fields
                ))
                continue
            row.corp_name = corp_name
            for key, value in fields.items():
                setattr(row, key, value)
    # 已经在板上的样品以板上为准，后来的「未合成」不覆盖
    for sample_name in not_synthesized:
        if sample_name in on_plate:
            continue
        marker = pending.get(sample_name)
        if marker is None:
            pending[sample_name] = marker = SynthesisSupernatantWell(
                order_no=order_no, sample_name=sample_name, not_synthesized=True
            )
            db.add(marker)
        marker.corp_name = corp_name
    if plates:
        # 发货个数按蛋白计：君跻有的单同一批蛋白挂在新旧两个板号下，按孔数会翻倍
        db.flush()
        proteins = db.scalar(
            select(func.count(func.distinct(SynthesisSupernatantWell.sample_name))).where(
                SynthesisSupernatantWell.order_no == order_no, SynthesisSupernatantWell.not_synthesized.is_(False)
            )
        )
        _mark_shipped(db, order_no, ship_date, proteins or 0, keep_date=pulled)
    db.commit()
    return {
        "order_no": order_no,
        "plates": len(plates),
        "wells": sum(len(wells) for wells in plates.values()),
        "not_synthesized": len(not_synthesized),
    }
