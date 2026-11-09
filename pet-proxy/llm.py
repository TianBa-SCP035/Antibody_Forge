"""Upstream model endpoints, sampling presets and the raw chat-completions call."""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

QWEN = {
    "name": "qwen",
    "base": os.environ.get("PET_QWEN_BASE", "http://192.168.8.26:18081/v1"),
    "model": os.environ.get(
        "PET_QWEN_MODEL", "community-sc117-swift-1-5-qwen3-8-flash-next-gsq-rco-swift-iq3_xxs"
    ),
    "think_key": "enable_thinking",
}
DEEPSEEK = {
    "name": "deepseek",
    "base": os.environ.get("PET_DEEPSEEK_BASE", "http://10.88.1.2:11025/v1"),
    "model": os.environ.get("PET_DEEPSEEK_MODEL", "DeepSeek-V4.1-Flash"),
    "think_key": "thinking",
}

# Bench (model_bench/bench2.py): Qwen tool/structured work is more reliable at low temperature;
# vendor-recommended 0.7/0.8/20 is kept for free-form persona chat only.
SAMPLING = {
    "qwen_chat": {"temperature": 0.7, "top_p": 0.8, "top_k": 20, "min_p": 0},
    "qwen_low": {"temperature": 0.2},
    "deepseek_agent": {"temperature": 0.2},
}


def chat_completion(
    target: dict,
    messages: list,
    *,
    max_tokens: int,
    sampling: str,
    think: bool = False,
    tools: list | None = None,
    timeout: int = 120,
) -> tuple[int, dict]:
    payload = {
        "model": target["model"],
        "messages": messages,
        "max_tokens": max_tokens,
        "stream": False,
        "chat_template_kwargs": {target["think_key"]: think},
        **SAMPLING[sampling],
    }
    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = "auto"
        # llama.cpp keeps parallel tool calls off unless asked.
        payload["parallel_tool_calls"] = True
    req = urllib.request.Request(
        target["base"] + "/chat/completions",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", "replace")
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, {"error": raw[:500]}
    except Exception as e:
        return 502, {"error": str(e)}


def first_message(upstream: dict) -> dict:
    try:
        return (upstream.get("choices") or [{}])[0].get("message") or {}
    except Exception:
        return {}


def message_text(upstream: dict) -> str:
    content = first_message(upstream).get("content") or ""
    if "</think>" in content:
        content = content.split("</think>", 1)[1]
    return content.strip()
