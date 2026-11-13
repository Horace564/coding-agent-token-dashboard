"""HTTP server: static frontend + JSON endpoints + SSE diff stream."""
from __future__ import annotations

import http.server
import json
import mimetypes
import queue
import threading
import time
from pathlib import Path
from urllib.parse import urlparse, parse_qs, unquote

from .db import (
    overview_totals, expensive_prompts, project_summary,
    tool_use_breakdown, recent_sessions, session_turns,
    daily_token_breakdown, model_breakdown, skill_breakdown,
)
from .scanner import scan_dir
from .codex_scanner import default_codex_sessions_dir, scan_codex_dir
from .skills import cached_catalog


WEB_ROOT = Path(__file__).resolve().parent.parent / "web"

EVENTS: "queue.Queue[dict]" = queue.Queue()
SERVER_INSTANCE = str(time.time_ns())

MAX_LIMIT = 1000


def _send_json(handler, obj, status: int = 200) -> None:
    body = json.dumps(obj, default=str).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Cache-Control", "no-store")
    handler.end_headers()
    handler.wfile.write(body)


def _send_error(handler, status: int, msg: str) -> None:
    _send_json(handler, {"error": msg}, status=status)


def _clamp_limit(raw, default: int) -> int:
    try:
        v = int(raw)
    except (TypeError, ValueError):
        return default
    return max(1, min(v, MAX_LIMIT))


def _serve_static(handler, rel: str) -> None:
    rel = rel.lstrip("/")
    p = (WEB_ROOT / rel).resolve()
    if not str(p).startswith(str(WEB_ROOT.resolve())) or not p.is_file():
        handler.send_response(404)
        handler.end_headers()
        return
    body = p.read_bytes()
    ctype, _ = mimetypes.guess_type(str(p))
    handler.send_response(200)
    handler.send_header("Content-Type", ctype or "application/octet-stream")
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Cache-Control", "no-store")
    handler.end_headers()
    handler.wfile.write(body)


def build_handler(db_path: str, projects_dir: str, codex_dir: str = None):
    codex_dir = codex_dir or str(default_codex_sessions_dir())

    class H(http.server.BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            pass

        def do_HEAD(self):
            return self.do_GET()

        def do_GET(self):
            url = urlparse(self.path)
            qs = parse_qs(url.query or "")
            path = url.path
            since = qs.get("since", [None])[0]
            until = qs.get("until", [None])[0]
            source = qs.get("source", ["all"])[0]
            if source not in ("all", "claude", "codex"):
                return _send_error(self, 400, "invalid source")
            source = None if source == "all" else source
            if path in ("/", "/index.html"):
                return _serve_static(self, "index.html")
            if path.startswith("/web/"):
                return _serve_static(self, path[5:])
            if path == "/api/overview":
                return _send_json(self, overview_totals(db_path, since, until, source))
            if path == "/api/prompts":
                limit = _clamp_limit(qs.get("limit", ["50"])[0], 50)
                sort = qs.get("sort", ["tokens"])[0]
                return _send_json(self, expensive_prompts(db_path, limit=limit, sort=sort, source=source))
            if path == "/api/projects":
                return _send_json(self, project_summary(db_path, since, until, source))
            if path == "/api/tools":
                return _send_json(self, tool_use_breakdown(db_path, since, until, source))
            if path == "/api/sessions":
                sort = qs.get("sort", ["recent"])[0]
                if sort not in ("recent", "tokens"):
                    return _send_error(self, 400, "invalid session sort")
                return _send_json(self, recent_sessions(
                    db_path, limit=_clamp_limit(qs.get("limit", ["20"])[0], 20),
                    since=since, until=until, source=source, sort=sort,
                ))
            if path == "/api/daily":
                return _send_json(self, daily_token_breakdown(db_path, since, until, source))
            if path == "/api/skills":
                rows = skill_breakdown(db_path, since, until, source)
                catalog = cached_catalog()
                for r in rows:
                    info = catalog.get(r["skill"])
                    r["tokens_per_call"] = info["tokens"] if info else None
                return _send_json(self, rows)
            if path == "/api/by-model":
                return _send_json(self, model_breakdown(db_path, since, until, source))
            if path.startswith("/api/sessions/"):
                sid = unquote(path.rsplit("/", 1)[1])
                return _send_json(self, session_turns(db_path, sid))
            if path == "/api/scan":
                claude = scan_dir(projects_dir, db_path)
                codex = scan_codex_dir(codex_dir, db_path)
                return _send_json(self, {**claude, "codex": codex})
            if path == "/api/stream":
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Connection", "keep-alive")
                self.end_headers()
                try:
                    self.wfile.write(f"data: {json.dumps({'type': 'server', 'instance': SERVER_INSTANCE})}\n\n".encode())
                    self.wfile.flush()
                except (BrokenPipeError, ConnectionResetError):
                    return
                while True:
                    try:
                        evt = EVENTS.get(timeout=15)
                        chunk = f"data: {json.dumps(evt, default=str)}\n\n".encode()
                    except queue.Empty:
                        chunk = b": ping\n\n"
                    try:
                        self.wfile.write(chunk)
                        self.wfile.flush()
                    except (BrokenPipeError, ConnectionResetError):
                        return
            self.send_response(404)
            self.end_headers()

    return H


def _scan_loop(db_path: str, projects_dir: str, codex_dir: str, interval: float = 30.0):
    while True:
        try:
            n = scan_dir(projects_dir, db_path)
            codex = scan_codex_dir(codex_dir, db_path)
            if n["messages"] > 0 or codex["messages"] > 0:
                EVENTS.put({"type": "scan", "n": {**n, "codex": codex}, "ts": time.time()})
        except Exception as e:
            EVENTS.put({"type": "error", "message": str(e)})
        time.sleep(interval)


def run(host: str, port: int, db_path: str, projects_dir: str, codex_dir: str = None):
    codex_dir = codex_dir or str(default_codex_sessions_dir())
    threading.Thread(target=_scan_loop, args=(db_path, projects_dir, codex_dir), daemon=True).start()
    H = build_handler(db_path, projects_dir, codex_dir)
    httpd = http.server.ThreadingHTTPServer((host, port), H)
    httpd.serve_forever()
