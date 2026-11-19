"""Summarize older turns into a durable memory note (prompt and parsing; the call is in chat.py)."""
from __future__ import annotations

from datetime import datetime

import clock
from prompts import MEMORY_COMPRESS_SYSTEM

# Hard cap everywhere a summary is stored or sent (the frontend's MEMORY_SUMMARY_MAX matches).
SUMMARY_MAX_CHARS = 800


def _stamp(at) -> str:
    try:
        d = datetime.fromtimestamp(float(at) / 1000, clock.TZ)
    except (TypeError, ValueError, OverflowError, OSError):
        return ""
    return f"[{d:%Y-%m-%d} {clock.weekday(d)}] "


def build_compress_messages(summary: str, older_turns: list) -> list:
    lines = []
    for h in older_turns[-40:]:
        role = h.get("role")
        content = str(h.get("content") or "").strip()
        if role not in ("user", "assistant") or not content:
            continue
        tag = "用户" if role == "user" else "大肥鱼"
        lines.append(f"{_stamp(h.get('at'))}{tag}: {content[:400]}")
    blob = "\n".join(lines) if lines else "(无)"
    user = (
        "既有摘要：\n"
        + ((summary or "").strip() or "(空)")
        + "\n\n待压缩的旧对话：\n"
        + blob
        + "\n\n请输出合并后的新摘要："
    )
    today, weekday = clock.today()
    return [
        {"role": "system", "content": MEMORY_COMPRESS_SYSTEM.format(today=today, weekday=weekday)},
        {"role": "user", "content": user},
    ]


def extract_summary(upstream: dict) -> str:
    try:
        content = (
            ((upstream.get("choices") or [{}])[0].get("message") or {}).get("content")
            or ""
        )
    except Exception:
        content = ""
    return str(content).strip()[:SUMMARY_MAX_CHARS]
