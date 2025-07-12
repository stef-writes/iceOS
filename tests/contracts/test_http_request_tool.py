# Re-implemented without Docker to avoid flaky CI dependencies.
# The test spins up an in-process HTTP server that mimics httpbin's /get endpoint.

from __future__ import annotations

import contextlib
import socket
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Generator

import pytest  # type: ignore

from ice_sdk.tools.web import HttpRequestTool


class _Handler(BaseHTTPRequestHandler):
    """Minimal HTTP handler that returns JSON for /get requests."""

    def log_message(
        self, format: str, *args
    ) -> None:  # noqa: D401,E133 pylint: disable=invalid-name
        """Silence default stdout logging during tests."""

    def do_GET(self) -> None:  # noqa: N802  # method name from BaseHTTPRequestHandler
        if self.path.startswith("/get"):
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"url": "/get"}')
        else:
            self.send_response(404)
            self.end_headers()


@pytest.fixture(scope="session")
def http_server() -> Generator[str, None, None]:
    """Launch a background HTTP server available for the duration of the session."""

    # Bind to an ephemeral port first so we can pass the free port to HTTPServer.
    with contextlib.closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
        sock.bind(("127.0.0.1", 0))
        host, port = sock.getsockname()

    server = HTTPServer((host, port), _Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        yield f"http://{host}:{port}"
    finally:
        server.shutdown()
        thread.join()


@pytest.mark.contract
@pytest.mark.asyncio
async def test_http_request_tool_against_local_server(http_server: str) -> None:
    """HttpRequestTool should successfully GET /get from the local test server."""

    tool = HttpRequestTool()
    result: Any = await tool.run(url=f"{http_server}/get", method="GET")

    assert result["status_code"] == 200
    assert '"url": "/get"' in result["body"]
