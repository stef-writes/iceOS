from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Optional

import click

from ice_client import IceClient


@click.group()
def rag() -> None:
    """RAG agent demo helpers."""


@rag.command("demo")
@click.option("--api", "api_url", envvar="ICE_API_URL", default="http://localhost:8000")
@click.option("--token", envvar="ICE_API_TOKEN", default=None)
@click.option(
    "--files",
    default="",
    help="Comma-separated text files to ingest via memory_write_tool",
)
@click.option("--query", required=True)
@click.option("--scope", default="kb")
@click.option("--model", default="gpt-4o")
@click.option("--top-k", default=5, type=int)
@click.option("--with-citations", is_flag=True, default=False)
def rag_demo(
    api_url: str,
    token: Optional[str],
    files: str,
    query: str,
    scope: str,
    model: str,
    top_k: int,
    with_citations: bool,
) -> None:  # noqa: D401
    """Ingest files and run the rag_agent workflow end-to-end."""

    paths = [p.strip() for p in files.split(",") if p.strip()]

    async def _run() -> None:
        async with IceClient(api_url, auth_token=token) as client:
            # Ingest via memory_write_tool for each file
            for p in paths:
                text = Path(p).read_text(encoding="utf-8")
                payload = {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "tools/call",
                    "params": {
                        "name": "tool:memory_write_tool",
                        "arguments": {
                            "inputs": {
                                "key": Path(p).name,
                                "content": text,
                                "scope": scope,
                            }
                        },
                    },
                }
                resp = await client._client.post("/api/v1/mcp", json=payload)
                resp.raise_for_status()

            # Build rag_agent blueprint and run
            from importlib import import_module

            rag_mod = import_module("packs.first_party_agents.rag_agent")
            bp = getattr(rag_mod, "rag_chat_blueprint_agent")(
                model=model, scope=scope, top_k=top_k, with_citations=with_citations
            )
            exec_id = await client.run(blueprint=bp, inputs={"query": query})
            final = await client.poll_until_complete(exec_id, timeout=120)
            click.echo(json.dumps(final, indent=2))

    asyncio.run(_run())
