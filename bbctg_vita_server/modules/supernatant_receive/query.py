"""向合成公司查询上清板布局：工单迟迟没收到推送时补查，查到的按推送同样入库。"""

from __future__ import annotations

from datetime import timedelta
import json
import logging
from typing import Any

import requests
from sqlalchemy import exists, func, select
from sqlalchemy.orm import Session

from core.config import get_settings
from models.discovery import DiscoverySynthesisOrder
from models.supernatant import SynthesisSupernatantWell
from modules.auth.external import CALLBACK_TOKEN_HEADER
from modules.discovery.synthesis_progress.constants import STATUS_CANCELLED, STATUS_COMPLETED, SUPPLY_MODE_ARRIVAL
from modules.supernatant_receive.service import SupernatantReceiveError, receive
from utils.clock import now_local, today_local

logger = logging.getLogger(__name__)

FOUND = "found"
MISSING = "missing"
FAILED = "failed"
UNSUPPORTED = "unsupported"
# 对方查一单要几秒、大单更久，一次只补查这么多单，按上次补查时间轮着来
PULL_LIMIT = 40
# 合成日期之后这么多天还没收到推送才去问
PULL_AFTER_DAYS = 7
_TIMEOUT = (5, 60)


def query_urls() -> dict[str, str]:
    urls: dict[str, str] = {}
    for item in str(get_settings().supernatant_query_urls or "").split(";"):
        corp, _, url = item.partition("=")
        if corp.strip() and url.strip():
            urls[corp.strip()] = url.strip()
    return urls


def _fetch(url: str, order_no: str) -> tuple[str, dict[str, Any] | None, str]:
    headers = {CALLBACK_TOKEN_HEADER: get_settings().supernatant_receive_token}
    try:
        response = requests.post(url, json={"orderNo": order_no}, headers=headers, timeout=_TIMEOUT)
        reply = response.json()
    except requests.Timeout:
        return FAILED, None, "合成公司查询接口超时，稍后再试"
    except (requests.RequestException, ValueError) as exc:
        logger.warning("supernatant query %s failed: %s", order_no, exc)
        return FAILED, None, "合成公司查询接口连不上，稍后再试"
    if not isinstance(reply, dict):
        return FAILED, None, "合成公司查询接口返回格式不对"
    if reply.get("code") == 1 and isinstance(reply.get("data"), dict):
        return FOUND, reply["data"], ""
    message = str(reply.get("msg") or "")
    if "不存在" in message:
        return MISSING, None, "合成公司还没有这单的上清板布局，应是还没发货"
    return FAILED, None, f"合成公司查询失败：{message[:100] or '未说明原因'}"


def pull_order(db: Session, corp: str, order_no: str) -> dict[str, Any]:
    """查一个订单号；查到就入库。不论结果都记下补查时间。"""
    url = query_urls().get(str(corp or "").strip())
    if not url:
        return {"state": UNSUPPORTED, "message": "这家合成公司还没有查询接口，只能等对方推送"}
    state, data, message = _fetch(url, order_no)
    result: dict[str, Any] = {"state": state, "message": message}
    if state == FOUND:
        try:
            saved = receive(db, json.dumps(data, ensure_ascii=False).encode("utf-8"), pulled=True)
        except SupernatantReceiveError as exc:
            db.rollback()
            result = {"state": FAILED, "message": f"合成公司返回的布局不合格：{exc}"}
        else:
            result.update(wells=saved["wells"], not_synthesized=saved["not_synthesized"])
            if not saved["wells"]:
                result["message"] = "合成公司回复这单的样品都没合成出来"
    now = now_local()
    for row in db.scalars(
        select(DiscoverySynthesisOrder).where(func.lower(DiscoverySynthesisOrder.order_no) == order_no.lower())
    ):
        row.supernatant_checked_at = now
    db.commit()
    return result


def pull_pending(db: Session) -> dict[str, Any]:
    urls = query_urls()
    if not urls or not get_settings().supernatant_receive_token:
        return {"skipped": True, "message": "未配置 SUPERNATANT_QUERY_URLS 或 SUPERNATANT_RECEIVE_TOKEN，已跳过"}
    received = exists().where(
        func.lower(SynthesisSupernatantWell.order_no) == func.lower(func.trim(DiscoverySynthesisOrder.order_no))
    )
    due = (today_local() - timedelta(days=PULL_AFTER_DAYS)).isoformat()
    rows = db.execute(
        select(DiscoverySynthesisOrder.synthetic_corp, func.upper(func.trim(DiscoverySynthesisOrder.order_no)))
        .where(
            DiscoverySynthesisOrder.supply_mode == SUPPLY_MODE_ARRIVAL,
            DiscoverySynthesisOrder.status.not_in((STATUS_COMPLETED, STATUS_CANCELLED)),
            func.trim(func.coalesce(DiscoverySynthesisOrder.order_no, "")) != "",
            DiscoverySynthesisOrder.synthetic_corp.in_(list(urls)),
            (DiscoverySynthesisOrder.synthetic_date.is_(None)) | (DiscoverySynthesisOrder.synthetic_date <= due),
            ~received,
        )
        .order_by(DiscoverySynthesisOrder.supernatant_checked_at, DiscoverySynthesisOrder.synthetic_date)
    ).all()
    targets: dict[str, str] = {}
    for corp, order_no in rows:
        targets.setdefault(order_no, corp)
        if len(targets) >= PULL_LIMIT:
            break
    counts = {FOUND: 0, MISSING: 0, FAILED: 0}
    found, failed = [], []
    for order_no, corp in targets.items():
        result = pull_order(db, corp, order_no)
        counts[result["state"]] = counts.get(result["state"], 0) + 1
        if result["state"] == FOUND:
            found.append(order_no)
        elif result["state"] == FAILED:
            failed.append(f"{order_no}：{result['message']}")
    return {
        "total": len(targets),
        "found": counts[FOUND],
        "missing": counts[MISSING],
        "failed": counts[FAILED],
        "found_orders": found,
        "failed_orders": failed[:20],
    }


def summarize(result: dict[str, Any]) -> str:
    return f"补查 {result['total']} 单：查到 {result['found']}，未发货 {result['missing']}，失败 {result['failed']}"
