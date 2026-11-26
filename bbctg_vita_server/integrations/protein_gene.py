"""蛋白基因名接口（李宗强）：按蛋白名称查重、轻链名称。地址和密钥留空即不查。

POST {"protein_names": [...]}，返回 {"code": 20000, "data": {"items": [
{"input_protein_name": ..., "protein_name": ..., "beacon": {"heavy_chain_names": [...], "light_chain_names": [...], "matched": bool},
"ngs": {"gene_names": [...], "matched": bool}}]}}。名称不区分大小写、整名匹配。
Beacon 已把重链、轻链分开。NGS 只回一条链名称：RN 是重链，RL 的重轻链写在同一个名称里，整段记入重链，轻链留空。
"""

from __future__ import annotations

import logging
import time
from collections.abc import Iterable
from typing import Any

import requests

from core.config import get_settings

logger = logging.getLogger(__name__)

# 整批查询的总时长要留在前端导入请求的超时（120 秒）以内。
TOTAL_SECONDS = 60
BATCH_SIZE = 500
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


def _belongs_to_protein(gene: str, protein: str) -> bool:
    """基因名横线后的部分要和本次蛋白名称对上，避免把同项目的其他克隆算进来。"""
    stem = gene.split("-", 1)[1] if "-" in gene else gene
    left, right = stem.casefold(), protein.strip().casefold()
    if not left or not right:
        return False
    if left == right:
        return True
    return (
        left.startswith(right + "_")
        or left.startswith(right + ".")
        or right.startswith(left + "_")
        or right.startswith(left + ".")
    )


def _listed(names: list[str]) -> str:
    shown = names[:3]
    text = "、".join(shown)
    if len(names) > len(shown):
        text += f" 等 {len(names)} 条"
    return text


def _result(data: Any, protein: str = "") -> Chains | str | None:
    """查到返回 (重链, 轻链)；查到但用不了返回原因；没查到返回 None。"""
    if not isinstance(data, dict):
        return None
    protein = protein.strip() or str(data.get("protein_name") or "").strip()
    beacon = data.get("beacon") if isinstance(data.get("beacon"), dict) else {}
    heavy = _names(beacon.get("heavy_chain_names"))
    light = _names(beacon.get("light_chain_names"))
    if beacon.get("matched") and heavy:
        if len(heavy) > 1:
            return f"接口查到多条重链（{_listed(heavy)}）"
        if len(light) > 1:
            return f"接口查到多条轻链（{_listed(light)}）"
        return heavy[0], (light[0] if light else None)
    ngs = data.get("ngs") if isinstance(data.get("ngs"), dict) else {}
    genes = _names(ngs.get("gene_names"))
    if not (ngs.get("matched") and genes):
        return None
    owned = [gene for gene in genes if _belongs_to_protein(gene, protein)]
    if len(owned) == 1:
        return owned[0], None
    if owned:
        return f"接口在 NGS 查到多条基因名（{_listed(owned)}）"
    return f"接口在 NGS 查到 {len(genes)} 个基因名，没有和这个蛋白名称对上的重轻链"


def _response_body(response: requests.Response) -> dict[str, Any]:
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
    return body


def _post_batch(url: str, key: str, names: list[str], timeout: float) -> list[Any]:
    try:
        response = requests.post(
            url,
            json={"protein_names": names},
            headers={"X-API-Key": key},
            timeout=timeout,
        )
    except requests.Timeout as exc:
        raise ProteinGeneUnavailable(f"基因名接口 {TOTAL_SECONDS} 秒内没查完") from exc
    except requests.RequestException as exc:
        raise ProteinGeneUnavailable("基因名接口连不上") from exc
    data = _response_body(response).get("data")
    items = data.get("items") if isinstance(data, dict) else None
    if not isinstance(items, list):
        raise ProteinGeneUnavailable("基因名接口返回格式不对")
    return items


def lookup(names: Iterable[str]) -> tuple[dict[str, Chains], dict[str, str]]:
    """按名称查重轻链，返回（查到的「原名称 → (重链, 轻链)」，查到但用不了的「原名称 → 原因」）；没查到的两边都不在。

    整批查不了时抛 ProteinGeneUnavailable。一次最多提交 BATCH_SIZE 个名称。
    """
    wanted = list(dict.fromkeys(name for name in names if name))
    if not wanted:
        return {}, {}
    if not configured():
        raise ProteinGeneUnavailable("没有配置基因名接口")
    settings = get_settings()
    url = str(settings.protein_gene_api_url).strip()
    key = str(settings.protein_gene_api_key).strip()
    by_key = {name.casefold(): name for name in wanted}
    found: dict[str, Chains] = {}
    issues: dict[str, str] = {}
    started = time.monotonic()
    try:
        for offset in range(0, len(wanted), BATCH_SIZE):
            remaining = TOTAL_SECONDS - (time.monotonic() - started)
            if remaining <= 0:
                raise ProteinGeneUnavailable(f"基因名接口 {TOTAL_SECONDS} 秒内没查完")
            items = _post_batch(url, key, wanted[offset:offset + BATCH_SIZE], remaining)
            for item in items:
                if not isinstance(item, dict):
                    continue
                raw = str(item.get("input_protein_name") or item.get("protein_name") or "").strip()
                original = by_key.get(raw.casefold())
                if original is None:
                    continue
                result = _result(item, original)
                if isinstance(result, tuple):
                    found[original] = result
                elif isinstance(result, str):
                    issues[original] = result
    except ProteinGeneUnavailable as exc:
        logger.warning("蛋白基因名接口查询失败：%s", exc)
        raise
    return found, issues
