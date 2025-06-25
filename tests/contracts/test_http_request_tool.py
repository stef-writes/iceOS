from __future__ import annotations

import shutil
from typing import Any

import pytest  # type: ignore

try:
    from testcontainers.core.generic import GenericContainer  # type: ignore
except ModuleNotFoundError:
    pytest.skip("testcontainers not installed", allow_module_level=True)

# Skip test entirely when Docker is not available ---------------------------
if shutil.which("docker") is None:
    pytest.skip("Docker is not available, skipping contract tests.", allow_module_level=True)

from ice_sdk.tools.builtins.deterministic import HttpRequestTool


@pytest.mark.contract
@pytest.mark.asyncio
async def test_http_request_tool_against_mockserver() -> None:
    """HttpRequestTool should successfully GET /get from httpbin in a container."""

    # Start lightweight httpbin container ------------------------------
    with GenericContainer("kennethreitz/httpbin").with_exposed_ports(80) as server:  # type: ignore[arg-type]
        host = f"http://{server.get_container_host_ip()}:{server.get_exposed_port(80)}"

        tool = HttpRequestTool()
        result: Any = await tool.run(url=f"{host}/get", method="GET")

        assert result["status_code"] == 200
        assert "body" in result 