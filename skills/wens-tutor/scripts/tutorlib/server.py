# skills/wens-tutor/scripts/tutorlib/server.py
"""One process, two static roots, JSON API."""

import json
import mimetypes
import os
import posixpath
import threading
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from . import api, state

WEB = Path(__file__).resolve().parents[2] / "web"
PAGES = {"/": "index.html", "/reader": "reader.html", "/exam": "exam.html", "/stats": "stats.html"}


def safe_material_path(root, relpath: str):
    root = Path(root).resolve()
    rel = urllib.parse.unquote(relpath or "")
    if rel.startswith("/") or not rel.endswith(".md"):
        return None
    candidate = (root / rel)
    if candidate.is_symlink():
        return None
    try:
        resolved = candidate.resolve(strict=True)
    except OSError:
        return None
    if os.path.commonpath([str(resolved), str(root)]) != str(root):
        return None
    if resolved != candidate.absolute() and not str(candidate.absolute()).startswith(str(root)):
        return None
    return resolved if resolved.is_file() else None


def safe_web_path(relpath: str):
    clean = posixpath.normpath("/" + (relpath or "")).lstrip("/")
    p = (WEB / clean).resolve()
    if os.path.commonpath([str(p), str(WEB.resolve())]) != str(WEB.resolve()):
        return None
    return p if p.is_file() else None


def make_handler(root, conn, lock):
    class Handler(BaseHTTPRequestHandler):
        server_version = "wens-tutor"

        def log_message(self, *a):
            pass  # ui-design-principles 21: never pollute the surface

        def _send(self, code, body: bytes, ctype: str):
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(body)

        def _json(self, code, obj):
            self._send(code, json.dumps(obj, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")

        def _dispatch(self):
            parsed = urllib.parse.urlparse(self.path)
            path, query = parsed.path, urllib.parse.parse_qs(parsed.query)

            if path.startswith("/api/"):
                length = int(self.headers.get("Content-Length") or 0)
                body = json.loads(self.rfile.read(length) or "null") if length else None
                with lock:
                    code, payload = api.handle(conn, self.command, path, query, body)
                return self._json(code, payload)

            if path.startswith("/raw/"):
                p = safe_material_path(root, path[len("/raw/"):])
                if not p:
                    return self._send(404, b"not found", "text/plain; charset=utf-8")
                return self._send(200, p.read_bytes(), "text/markdown; charset=utf-8")

            name = PAGES.get(path)
            p = safe_web_path(name) if name else safe_web_path(path.lstrip("/"))
            if not p:
                return self._send(404, b"not found", "text/plain; charset=utf-8")
            ctype = mimetypes.guess_type(str(p))[0] or "application/octet-stream"
            if ctype.startswith("text/") or ctype in ("application/javascript", "application/json"):
                ctype += "; charset=utf-8"
            return self._send(200, p.read_bytes(), ctype)

        do_GET = do_PUT = do_POST = do_PATCH = do_DELETE = do_HEAD = _dispatch

    return Handler


def serve(root, port=8765, bind="0.0.0.0", open_browser=False) -> None:
    root = Path(root)
    conn = state.open_root(root)
    report = state.reconcile(conn, root)
    if report["relinked_questions"] or report["unresolved"]:
        print("reconciled:", json.dumps(report, ensure_ascii=False))
    lock = threading.Lock()
    httpd = ThreadingHTTPServer((bind, port), make_handler(root, conn, lock))
    shown = "127.0.0.1" if bind in ("0.0.0.0", "::") else bind
    print("http://%s:%d/" % (shown, port))
    if open_browser:
        webbrowser.open("http://%s:%d/" % (shown, port))
    httpd.serve_forever()
