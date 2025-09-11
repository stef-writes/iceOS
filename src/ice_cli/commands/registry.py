from __future__ import annotations

import json
from typing import Any

import click
import httpx


@click.group()
def registry() -> None:
    """Inspect API registry and components."""


@registry.command("tools")
@click.option("--api", "api_url", envvar="ICE_API_URL", default="http://localhost")
def list_tools(api_url: str) -> None:  # noqa: D401
    """List registered tools from /api/v1/meta/registry/health."""

    resp = httpx.get(
        f"{api_url.rstrip('/')}/api/v1/meta/registry/health", timeout=httpx.Timeout(5.0)
    )
    resp.raise_for_status()
    data: dict[str, Any] = resp.json()
    tools = data.get("tools", [])
    for name in tools:
        click.echo(name)


@registry.command("agents")
@click.option("--api", "api_url", envvar="ICE_API_URL", default="http://localhost")
def list_agents(api_url: str) -> None:  # noqa: D401
    """List registered agents from /api/v1/meta/registry/health."""

    resp = httpx.get(
        f"{api_url.rstrip('/')}/api/v1/meta/registry/health", timeout=httpx.Timeout(5.0)
    )
    resp.raise_for_status()
    data: dict[str, Any] = resp.json()
    agents = data.get("agents", [])
    for name in agents:
        click.echo(name)


@registry.command("summary")
@click.option("--api", "api_url", envvar="ICE_API_URL", default="http://localhost")
def summary(api_url: str) -> None:  # noqa: D401
    """Print registry/health summary as JSON."""

    resp = httpx.get(
        f"{api_url.rstrip('/')}/api/v1/meta/registry/health", timeout=httpx.Timeout(5.0)
    )
    resp.raise_for_status()
    click.echo(json.dumps(resp.json(), indent=2))
