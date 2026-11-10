#!/usr/bin/env python3
"""Local FatFish pet chat proxy. Bind to 127.0.0.1 only; put /api/pet behind the app's login
(Vite / Nginx proxy). Do not expose this process on a public interface without auth.

HTTP surface only:
- POST /api/pet/agent    data tasks: one DeepSeek tool-calling step (agent.py); the browser runs
                         the tools with the user's own session and posts results back.
- POST /api/pet/chat     persona small talk / page comment (Qwen, chat.py).
- POST /api/pet/compress long-term memory compression (Qwen).
- POST /api/pet/lines    a small batch of fresh reaction lines in persona (Qwen, chat.py).
- POST /api/pet/labels   Chinese column headers for API fields no page column named (DeepSeek, agent.py).
Same-origin only (Vite / Nginx proxy /api/pet here): no CORS headers, JSON bodies up to 512 KB.
"""
from __future__ import annotations

import json
import os
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from agent import handle_agent, handle_labels
from chat import handle_chat, handle_compress, handle_lines

HOST = "127.0.0.1"
# Nginx points each site at its own port (start_dev.sh: prod 18765, test 18766); Vite dev uses 18765.
PORT = int(os.environ.get("PET_PORT", "18765"))
# A full agent turn (10 steps of tool results) stays well under this.
MAX_BODY = 512 * 1024


class Handler(BaseHTTPRequestHandler):
    """Same-origin only: the app reaches us through its own dev/Nginx proxy, so no CORS headers are sent
    and other web pages open in the browser can't call the models through localhost."""

    def log_message(self, fmt, *args):
        print("[pet-proxy]", fmt % args)

    def do_GET(self):
        if self.path.startswith("/api/pet/health"):
            self._json(200, {"ok": True, "service": "fatfish-pet-proxy"})
            return
        self._json(404, {"error": "not found"})

    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            length = -1
        if length < 0 or length > MAX_BODY:
            self.close_connection = True
            self._json(413, {"ok": False, "error": "request too large"})
            return
        # JSON content type makes a cross-site browser send a preflight, which this server never answers.
        if not (self.headers.get("Content-Type") or "").lower().startswith("application/json"):
            self.close_connection = True
            self._json(415, {"ok": False, "error": "application/json required"})
            return
        raw = self.rfile.read(length) if length else b"{}"
        try:
            data = json.loads(raw.decode("utf-8"))
        except Exception:
            self._json(400, {"error": "invalid json"})
            return

        try:
            if self.path.startswith("/api/pet/compress"):
                result = handle_compress(data)
                self._json(result["http"], result["body"])
                return
            if self.path.startswith("/api/pet/agent"):
                result = handle_agent(data)
                self._json(result["http"], result["body"])
                return
            if self.path.startswith("/api/pet/chat"):
                result = handle_chat(data)
                self._json(result["http"], result["body"])
                return
            if self.path.startswith("/api/pet/lines"):
                result = handle_lines(data)
                self._json(result["http"], result["body"])
                return
            if self.path.startswith("/api/pet/labels"):
                result = handle_labels(data)
                self._json(result["http"], result["body"])
                return
            self._json(404, {"error": "not found"})
        except Exception:
            # The exception text can echo request data; it goes to the local log, not back to the page.
            traceback.print_exc()
            self._json(500, {"ok": False, "error": "internal error", "reply": "咕噜…我晃了一下，再说一次好不好？"})

    def _json(self, code: int, obj: dict):
        raw = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)


def main():
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
    print(
        f"fatfish pet-proxy on http://{HOST}:{PORT}  "
        "(POST /api/pet/agent, /api/pet/chat, /api/pet/compress, /api/pet/lines, /api/pet/labels)"
    )
    httpd.serve_forever()


if __name__ == "__main__":
    main()
