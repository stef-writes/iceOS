from __future__ import annotations

import json
from typing import Any, Mapping, Optional, cast

import click
import httpx


@click.group()
def memory() -> None:
    """Semantic memory helpers via MCP tools."""


def _auth_headers(token: Optional[str]) -> dict[str, str]:
    if token:
        return {"Authorization": f"Bearer {token}"}
    return {}


def _mcp(
    api_url: str, payload: Mapping[str, Any], token: Optional[str]
) -> dict[str, Any]:
    resp = httpx.post(
        f"{api_url.rstrip('/')}/api/v1/mcp",
        json=payload,
        timeout=httpx.Timeout(connect=5.0, read=30.0, write=10.0),
        headers=_auth_headers(token),
    )
    resp.raise_for_status()
    return cast(dict[str, Any], resp.json())


@memory.command("write")
@click.option("--api", "api_url", envvar="ICE_API_URL", default="http://localhost:8000")
@click.option("--token", envvar="ICE_API_TOKEN", default=None)
@click.option("--scope", default="kb")
@click.option("--key", required=True)
@click.option("--content", required=True)
def write(
    api_url: str, token: Optional[str], scope: str, key: str, content: str
) -> None:  # noqa: D401
    """Write a document into semantic memory via memory_write_tool."""

    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "tool:memory_write_tool",
            "arguments": {"inputs": {"key": key, "content": content, "scope": scope}},
        },
    }
    data = _mcp(api_url, payload, token)
    click.echo(json.dumps(data, indent=2))


@memory.command("search")
@click.option("--api", "api_url", envvar="ICE_API_URL", default="http://localhost:8000")
@click.option("--token", envvar="ICE_API_TOKEN", default=None)
@click.option("--scope", default="kb")
@click.option("--query", required=True)
@click.option("--top-k", default=5, type=int)
def search(
    api_url: str, token: Optional[str], scope: str, query: str, top_k: int
) -> None:  # noqa: D401
    """Semantic search via memory_search_tool."""

    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "tool:memory_search_tool",
            "arguments": {"inputs": {"query": query, "scope": scope, "top_k": top_k}},
        },
    }
    data = _mcp(api_url, payload, token)
    click.echo(json.dumps(data, indent=2))
