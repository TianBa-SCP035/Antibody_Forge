"""合成公司推送的上清板布局：校验后一孔一行保存，同一「订单号 + 板号」整板覆盖。"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
import json
import re
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from models.supernatant import SynthesisSupernatantWell

MAX_TEXT = 64
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


def parse_payload(raw: bytes) -> tuple[str, str, dict[str, dict[str, dict[str, Any]]]]:
    """返回 (订单号, 合成公司, {板号: {孔号: 孔位}})；任一处不合格整次拒收。"""
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
    for index, item in enumerate(rows, start=1):
        if not isinstance(item, dict):
            errors.append(f"data[{index}] 必须是对象")
            continue
        item = _lower_keys(item)
        row_errors: list[str] = []
        plate_no = _required_text(item.get("plateno"), "plateno", MAX_TEXT, row_errors)
        well_text = _text(item.get("wellno"))
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
    return order_no, corp_name, plates


def receive(db: Session, raw: bytes) -> dict[str, Any]:
    order_no, corp_name, plates = parse_payload(raw)
    old_rows = db.scalars(
        select(SynthesisSupernatantWell).where(
            SynthesisSupernatantWell.order_no == order_no,
            SynthesisSupernatantWell.plate_no.in_(list(plates)),
        )
    ).all()
    for row in old_rows:
        db.delete(row)
    # 同一工作单元里插入先于删除执行，不先落库会撞唯一键
    db.flush()
    for plate_no, wells in plates.items():
        for well_no in sorted(wells):
            db.add(SynthesisSupernatantWell(order_no=order_no, corp_name=corp_name, plate_no=plate_no, **wells[well_no]))
    db.commit()
    return {"order_no": order_no, "plates": len(plates), "wells": sum(len(wells) for wells in plates.values())}
