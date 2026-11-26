"""A loopback HTTP relay from the pane harness (a node process) to a TestClient.

The harness `ctx.rest` calls `fetch` on `base_url`. The relay forwards each request to the
real router through the client, under one lock, so a test sees the real route replies.
"""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from types import TracebackType
from typing import Any

from fastapi.testclient import TestClient

LOOPBACK = "127.0.0.1"


class RestRelay:
    """Context manager: serve one TestClient on 127.0.0.1 at a random port."""

    def __init__(self, client: TestClient) -> None:
        self._client = client
        self._lock = threading.Lock()
        self._server: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None

    @property
    def base_url(self) -> str:
        if self._server is None:
            raise RuntimeError("the relay is not running")
        return f"http://{LOOPBACK}:{self._server.server_address[1]}"

    def forward(self, method: str, path: str, body: Any) -> tuple[int, bytes]:
        with self._lock:
            reply = self._client.request(method, path, json=body)
        return reply.status_code, reply.content

    def __enter__(self) -> RestRelay:
        relay = self

        class Handler(BaseHTTPRequestHandler):
            def _serve(self) -> None:
                length = int(self.headers.get("Content-Length") or 0)
                raw = self.rfile.read(length) if length else b""
                body = json.loads(raw) if raw else None
                status, content = relay.forward(self.command, self.path, body)
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(content)))
                self.end_headers()
                self.wfile.write(content)

            do_GET = _serve
            do_POST = _serve

            def log_message(self, format: str, *args: Any) -> None:
                return None

        self._server = ThreadingHTTPServer((LOOPBACK, 0), Handler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        if self._server is not None:
            self._server.shutdown()
            self._server.server_close()
        if self._thread is not None:
            self._thread.join(timeout=5)
        self._server = None
        self._thread = None
