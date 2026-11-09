"""Summarize older turns into a durable memory note via Qwen (fast, thinking OFF)."""
from __future__ import annotations

from prompts import MEMORY_COMPRESS_SYSTEM

# The prompt asks for ≤400 characters; this is the hard cap everywhere a summary is stored or sent.
SUMMARY_MAX_CHARS = 800


def build_compress_messages(summary: str, older_turns: list) -> list:
    lines = []
    for h in older_turns[-40:]:
        role = h.get("role")
        content = str(h.get("content") or "").strip()
        if role not in ("user", "assistant") or not content:
            continue
        tag = "用户" if role == "user" else "大肥鱼"
        lines.append(f"{tag}: {content[:400]}")
    blob = "\n".join(lines) if lines else "(无)"
    user = (
        "既有摘要：\n"
        + ((summary or "").strip() or "(空)")
        + "\n\n待压缩的旧对话：\n"
        + blob
        + "\n\n请输出合并后的新摘要："
    )
    return [
        {"role": "system", "content": MEMORY_COMPRESS_SYSTEM},
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
