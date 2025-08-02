"""Frosty CLI – minimal generate command."""

from __future__ import annotations

import asyncio
import json
import sys
from typing import Optional

import click
import httpx

from ice_builder.public import create_partial_blueprint, append_tool_node
from ice_core.models.mcp import Blueprint

from frosty.core import get_provider, available_providers

API_ENV = "ICEOS_API_URL"
DEFAULT_API = "http://localhost:8000"


@click.group()
def cli() -> None:  # noqa: D401
    """Frosty – AI generator for iceOS workflows."""


@cli.command("generate")
@click.argument("spec", nargs=-1)
@click.option("--provider", "provider_name", default="o3", type=click.Choice(available_providers()))
@click.option("--api", envvar=API_ENV, default=DEFAULT_API, help="iceOS API base URL")
@click.option("--token", envvar="ICEOS_API_TOKEN", default="demo-token", help="Bearer token")
def generate_cmd(spec: tuple[str, ...], provider_name: str, api: str, token: str) -> None:  # noqa: D401
    """Generate a workflow from free-text *SPEC* and run it."""

    prompt = " ".join(spec)
    provider = get_provider(provider_name)

    async def _run() -> None:
        # 1. Call provider
        raw = await provider.complete(prompt)
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            click.echo("Provider returned non-JSON output", err=True)
            sys.exit(1)

        # 2. Build PartialBlueprint -> Blueprint (only tool nodes for now)
        pb = create_partial_blueprint("frosty_generated")
        for node in data.get("nodes", []):
            append_tool_node(pb, node_id=node["id"], tool_name=node["tool_name"])
        bp = Blueprint(**pb.model_dump())

        # 3. Push blueprint
        resp = httpx.post(f"{api.rstrip('/')}/api/v1/blueprints", json=bp.model_dump(), headers={"Authorization": f"Bearer {token}"})
        resp.raise_for_status()
        bp_id = resp.json()["id"]
        click.echo(f"Blueprint ID: {bp_id}")

        # 4. Run execution
        run_resp = httpx.post(f"{api.rstrip('/')}/api/v1/executions", json={"blueprint_id": bp_id}, headers={"Authorization": f"Bearer {token}"})
        run_resp.raise_for_status()
        exec_id = run_resp.json()["execution_id"]
        click.echo(f"Execution ID: {exec_id}")

        # Poll until done (simpler than WS for now)
        while True:
            status = httpx.get(f"{api.rstrip('/')}/api/v1/executions/{exec_id}").json()
            click.echo(json.dumps(status, indent=2))
            if status["status"] in {"completed", "failed"}:
                break
            await asyncio.sleep(1)

    asyncio.run(_run())


if __name__ == "__main__":  # pragma: no cover
    cli()