import asyncio
from typing import Optional

import click


@click.group()
def uploads() -> None:
    """Upload and ingest documents into semantic memory."""


@uploads.command("files")
@click.option("--scope", default="kb", help="Memory scope key")
@click.option("--files", required=True, help="Comma-separated file paths")
@click.option("--chunk-size", default=1000, type=int)
@click.option("--overlap", default=200, type=int)
@click.option("--meta", default=None, help="JSON metadata string (category,tags,...)")
@click.option("--api", default=None, help="API base URL (defaults to ICE_API_URL)")
@click.option("--token", default=None, help="API token (defaults to ICE_API_TOKEN)")
def upload_files_cmd(
    scope: str,
    files: str,
    chunk_size: int,
    overlap: int,
    meta: Optional[str],
    api: Optional[str],
    token: Optional[str],
) -> None:
    """Upload multiple files for ingestion via the API."""
    import json

    from ice_client.client import IceClient

    paths = [p.strip() for p in files.split(",") if p.strip()]
    metadata = json.loads(meta) if meta else None

    async def _run() -> None:
        base = api or None
        tok = token or None
        async with IceClient(base_url=base, auth_token=tok) as client:
            resp = await client.upload_files(
                paths,
                scope=scope,
                chunk_size=chunk_size,
                overlap=overlap,
                metadata=metadata,
            )
            click.echo(json.dumps(resp, indent=2))

    asyncio.run(_run())
