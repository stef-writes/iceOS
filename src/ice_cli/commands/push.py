"""CLI command: ice push – upload blueprint to running iceOS API."""

from __future__ import annotations

import json
import pathlib
import sys

import click
import httpx

API_ENV_VAR = "ICEOS_API_URL"
DEFAULT_API = "http://localhost:8000"


@click.command("push")
@click.argument("blueprint_path", type=click.Path(exists=True, dir_okay=False))
@click.option(
    "--api",
    "api_url",
    envvar=API_ENV_VAR,
    default=DEFAULT_API,
    show_default=True,
    help="Base URL of iceOS API (env ICEOS_API_URL).",
)
@click.option(
    "--token", envvar="ICEOS_API_TOKEN", default="demo-token", help="Bearer token"
)
def cli_push(blueprint_path: str, api_url: str, token: str) -> None:  # noqa: D401
    """Upload *BLUEPRINT_PATH* to the server and return its id."""

    path = pathlib.Path(blueprint_path)
    payload = json.loads(path.read_text(encoding="utf-8"))

    url = f"{api_url.rstrip('/')}/api/v1/blueprints"

    try:
        response = httpx.post(
            url,
            json=payload,
            timeout=30.0,
            headers={"Authorization": f"Bearer {token}"},
        )
        response.raise_for_status()
    except Exception as exc:  # noqa: BLE001
        click.echo(f"Error uploading blueprint: {exc}", err=True)
        sys.exit(1)

    blueprint_id = response.json().get("id")
    click.echo(f"Blueprint ID: {blueprint_id}")

    # Store for convenience
    try:
        cache_dir = pathlib.Path.home() / ".iceos"
        cache_dir.mkdir(exist_ok=True)
        (cache_dir / "last_blueprint").write_text(str(blueprint_id), encoding="utf-8")
    except Exception:
        pass
