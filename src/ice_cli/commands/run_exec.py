"""CLI command: ice run – execute a blueprint via API and stream result."""

from __future__ import annotations

import json
import pathlib
import sys
from typing import Any, Dict, List, Optional

import click
import httpx

API_ENV_VAR = "ICEOS_API_URL"
DEFAULT_API = "http://localhost:8000"


def _load_last_blueprint() -> Optional[str]:
    try:
        return (pathlib.Path.home() / ".iceos/last_blueprint").read_text().strip()
    except Exception:
        return None


@click.command("run")
@click.argument("blueprint_id", required=False)
@click.option(
    "--input",
    "inputs",
    multiple=True,
    help="Key=value input pairs forwarded to workflow context.",
)
@click.option(
    "--api",
    "api_url",
    envvar=API_ENV_VAR,
    default=DEFAULT_API,
    show_default=True,
    help="Base URL of iceOS API (env ICEOS_API_URL).",
)
@click.option("--last", "use_last", is_flag=True, help="Run the last pushed blueprint.")
@click.option(
    "--token", envvar="ICEOS_API_TOKEN", default="demo-token", help="Bearer token"
)
def cli_run(
    blueprint_id: Optional[str],
    inputs: List[str],
    api_url: str,
    use_last: bool,
    token: str,
) -> None:  # noqa: D401
    """Execute a *blueprint_id* via API and stream status until completion."""

    if use_last and not blueprint_id:
        blueprint_id = _load_last_blueprint()
        if not blueprint_id:
            click.echo("No cached blueprint_id found", err=True)
            sys.exit(1)

    if not blueprint_id:
        click.echo("blueprint_id required (or --last)", err=True)
        sys.exit(1)

    # Parse inputs key=value
    input_dict = {}
    for pair in inputs:
        if "=" not in pair:
            click.echo(f"Invalid --input '{pair}', expected key=value", err=True)
            sys.exit(1)
        k, v = pair.split("=", 1)
        input_dict[k] = v

    # Start execution
    url = f"{api_url.rstrip('/')}/api/v1/executions"
    payload: Dict[str, Any] = {"blueprint_id": blueprint_id}
    if input_dict:
        payload["inputs"] = input_dict

    try:
        resp = httpx.post(
            url,
            json=payload,
            timeout=30.0,
            headers={"Authorization": f"Bearer {token}"},
        )
        resp.raise_for_status()
    except Exception as exc:  # noqa: BLE001
        click.echo(f"Failed to start execution: {exc}", err=True)
        sys.exit(1)

    execution_id = resp.json()["execution_id"]
    click.echo(f"Execution ID: {execution_id}")

    # Stream via simple polling loop (portable); WS support is optional via future flag
    click.echo("Streaming status (polling)…")
    import time

    while True:
        status_resp = httpx.get(
            f"{api_url.rstrip('/')}/api/v1/executions/{execution_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        status_data = status_resp.json()
        click.echo(json.dumps(status_data, indent=2))
        if status_data.get("status") in {"completed", "failed"}:
            if status_data.get("status") == "failed":
                sys.exit(1)
            break
        time.sleep(2)
