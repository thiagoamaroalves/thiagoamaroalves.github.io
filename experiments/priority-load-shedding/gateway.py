#!/usr/bin/env python3
"""Local gateway proxy that assigns trusted priority from the workload route."""

from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen


ROUTES = {"essential", "standard", "deferrable"}
GATEWAY_HOST = os.environ.get("GATEWAY_HOST", "127.0.0.1")
GATEWAY_PORT = int(os.environ.get("GATEWAY_PORT", "8081"))
BACKEND_URL = os.environ.get("BACKEND_URL", "http://127.0.0.1:8080")
BACKEND_TIMEOUT_SECONDS = float(os.environ.get("BACKEND_TIMEOUT_SECONDS", "90"))


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args: object) -> None:
        return

    def send_json(self, status: int, payload: dict[str, object]) -> None:
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        route_id = urlparse(self.path).path.removeprefix("/")
        if route_id == "healthz":
            self.send_json(200, {"status": "ok", "role": "priority-classifying-gateway"})
            return
        if route_id not in ROUTES:
            self.send_json(404, {"error": "unknown workload route", "routes": sorted(ROUTES)})
            return

        # Deliberately forward no client-supplied priority header. The gateway
        # replaces it with a value derived from its trusted route mapping.
        request = Request(
            f"{BACKEND_URL.rstrip('/')}/{route_id}",
            headers={
                "User-Agent": "priority-gateway-lab/1.0",
                "X-Request-Priority": route_id,
            },
        )
        try:
            with urlopen(request, timeout=BACKEND_TIMEOUT_SECONDS) as response:
                status = response.status
                body = response.read()
                content_type = response.headers.get("Content-Type", "application/json")
        except HTTPError as error:
            status = error.code
            body = error.read()
            content_type = error.headers.get("Content-Type", "application/json")
        except (TimeoutError, URLError) as error:
            self.send_json(502, {"error": "backend request failed", "detail": str(error)})
            return

        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)


class LabHTTPServer(ThreadingHTTPServer):
    request_queue_size = 2048


def main() -> None:
    server = LabHTTPServer((GATEWAY_HOST, GATEWAY_PORT), Handler)
    server.daemon_threads = True
    print(
        f"gateway listening on {GATEWAY_HOST}:{GATEWAY_PORT}; backend={BACKEND_URL}",
        flush=True,
    )
    try:
        server.serve_forever(poll_interval=0.5)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
