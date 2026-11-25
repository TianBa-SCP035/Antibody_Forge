"""蛋白基因名接口（李宗强）：按蛋白名称查重、轻链名称。地址和密钥留空即不查。

返回体：{"code": 20000, "data": {"beacon": {"heavy_chain_names": [...], "light_chain_names": [...], "matched": bool},
"ngs": {"gene_names": [...], "matched": bool}, "protein_name": ...}}。名称不区分大小写、整名匹配。
只用 beacon 的重轻链；NGS 只给基因名、分不出重轻链，查到时报给用户手填。
"""

from __future__ import annotations

import logging
from collections.abc import Iterable
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout, as_completed
from typing import Any

import requests

from core.config import get_settings

logger = logging.getLogger(__name__)

TIMEOUT_SECONDS = 5
# 整批查询的总时长要留在前端导入请求的超时（120 秒）以内。
TOTAL_SECONDS = 60
WORKERS = 8
SUCCESS_CODES = {0, 200, 20000}
AUTH_CODES = {401, 403, 40100, 40300}

Chains = tuple[str, str | None]


class ProteinGeneUnavailable(Exception):
    """接口没配、连不上、密钥不对或超时：这一批查不了，不等于查不到。"""


def configured() -> bool:
    settings = get_settings()
    return bool(str(settings.protein_gene_api_url or "").strip() and str(settings.protein_gene_api_key or "").strip())


def _names(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return list(dict.fromkeys(str(item).strip() for item in value if str(item or "").strip()))


def _result(data: Any) -> Chains | str | None:
    """查到返回 (重链, 轻链)；查到但用不了返回原因；没查到返回 None。"""
    if not isinstance(data, dict):
        return None
    beacon = data.get("beacon") if isinstance(data.get("beacon"), dict) else {}
    heavy = _names(beacon.get("heavy_chain_names"))
    light = _names(beacon.get("light_chain_names"))
    if beacon.get("matched") and heavy:
        if len(heavy) > 1:
            return f"接口查到多条重链（{'、'.join(heavy)}）"
        if len(light) > 1:
            return f"接口查到多条轻链（{'、'.join(light)}）"
        return heavy[0], (light[0] if light else None)
    ngs = data.get("ngs") if isinstance(data.get("ngs"), dict) else {}
    genes = _names(ngs.get("gene_names"))
    if ngs.get("matched") and genes:
        return f"接口只在 NGS 查到基因名 {'、'.join(genes)}，分不出重轻链"
    return None


def _lookup_one(url: str, key: str, name: str) -> Chains | str | None:
    try:
        response = requests.get(
            url, params={"protein_name": name}, headers={"X-API-Key": key}, timeout=TIMEOUT_SECONDS
        )
    except requests.RequestException as exc:
        raise ProteinGeneUnavailable("基因名接口连不上") from exc
    if response.status_code in (401, 403):
        raise ProteinGeneUnavailable("基因名接口密钥无效")
    if response.status_code >= 400:
        raise ProteinGeneUnavailable(f"基因名接口返回 HTTP {response.status_code}")
    try:
        body = response.json()
    except ValueError as exc:
        raise ProteinGeneUnavailable("基因名接口返回的不是 JSON") from exc
    if not isinstance(body, dict):
        raise ProteinGeneUnavailable("基因名接口返回格式不对")
    code = body.get("code")
    if code in AUTH_CODES:
        raise ProteinGeneUnavailable("基因名接口密钥无效")
    if code not in SUCCESS_CODES:
        message = str(body.get("message") or "").strip()
        raise ProteinGeneUnavailable(f"基因名接口返回 {code}{f' {message}' if message else ''}")
    return _result(body.get("data"))


def lookup(names: Iterable[str]) -> tuple[dict[str, Chains], dict[str, str]]:
    """按名称查重轻链，返回（查到的「原名称 → (重链, 轻链)」，查到但用不了的「原名称 → 原因」）；没查到的两边都不在。

    整批查不了时抛 ProteinGeneUnavailable。
    """
    wanted = list(dict.fromkeys(name for name in names if name))
    if not wanted:
        return {}, {}
    if not configured():
        raise ProteinGeneUnavailable("没有配置基因名接口")
    settings = get_settings()
    url = str(settings.protein_gene_api_url).strip()
    key = str(settings.protein_gene_api_key).strip()
    found: dict[str, Chains] = {}
    issues: dict[str, str] = {}
    pool = ThreadPoolExecutor(max_workers=min(WORKERS, len(wanted)))
    try:
        futures = {pool.submit(_lookup_one, url, key, name): name for name in wanted}
        try:
            for future in as_completed(futures, timeout=TOTAL_SECONDS):
                result = future.result()
                if isinstance(result, tuple):
                    found[futures[future]] = result
                elif isinstance(result, str):
                    issues[futures[future]] = result
        except FutureTimeout as exc:
            raise ProteinGeneUnavailable(f"基因名接口 {TOTAL_SECONDS} 秒内没查完") from exc
    except ProteinGeneUnavailable as exc:
        logger.warning("蛋白基因名接口查询失败：%s", exc)
        raise
    finally:
        pool.shutdown(wait=False, cancel_futures=True)
    return found, issues
