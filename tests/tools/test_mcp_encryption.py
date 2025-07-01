from shutil import which

import pytest

try:
    from cryptography.fernet import Fernet  # type: ignore
except ImportError:  # pragma: no cover
    Fernet = None  # type: ignore

from ice_sdk.tools.mcp import MCPServerStdio


@pytest.mark.asyncio
@pytest.mark.skipif(Fernet is None, reason="cryptography not installed")
async def test_mcp_encrypted_roundtrip():
    """Happy-path: encrypted payload travels through a simple echo server."""

    # Ensure a POSIX echo utility is available; fall back to Python echo server
    if which("cat"):
        cmd = "cat"
        args: list[str] = []
    else:
        # Portable Python one-liner that echoes stdin → stdout
        cmd = "python"
        args = [
            "-u",
            "-c",
            (
                "import sys, os;\n"
                "data = sys.stdin.buffer.readline();\n"
                "sys.stdout.buffer.write(data);\n"
            ),
        ]

    assert Fernet is not None  # for mypy/ruff
    key: bytes = Fernet.generate_key()

    async with MCPServerStdio({"command": cmd, "args": args, "encryption_key": key}) as server:
        # Send a simple ping-pong payload through the encrypted channel
        payload = {"ping": "pong"}
        response = await server._send_message(payload)  # type: ignore[attr-access]
        assert response == payload 