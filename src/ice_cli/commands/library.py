from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

import click
import httpx


def _api_base(api_url: str) -> str:
    return api_url.rstrip("/")


def _headers(token: str) -> Dict[str, str]:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


@click.group("library")
def library_cmd() -> None:
    """Manage per-user library assets."""


@library_cmd.command("add")
@click.option("--api", "api_url", envvar="ICE_API_URL", default="http://localhost:8000")
@click.option("--token", envvar="ICE_API_TOKEN", required=True)
@click.option("--label", required=True, help="Asset label (unique per user)")
@click.option("--file", "file_path", type=click.Path(exists=True), required=True)
@click.option("--mime", default="text/plain")
@click.option("--org", "org_id", default=None)
@click.option("--user", "user_id", default=None)
def add_asset(
    api_url: str,
    token: str,
    label: str,
    file_path: str,
    mime: str,
    org_id: Optional[str],
    user_id: Optional[str],
) -> None:
    content = Path(file_path).read_text(encoding="utf-8")
    payload: Dict[str, Any] = {
        "label": label,
        "content": content,
        "mime": mime,
        "org_id": org_id,
        "user_id": user_id,
    }
    url = f"{_api_base(api_url)}/api/v1/library/assets"
    resp = httpx.post(url, headers=_headers(token), json=payload, timeout=30.0)
    resp.raise_for_status()
    click.echo(json.dumps(resp.json(), indent=2))


@library_cmd.command("list")
@click.option("--api", "api_url", envvar="ICE_API_URL", default="http://localhost:8000")
@click.option("--token", envvar="ICE_API_TOKEN", required=True)
@click.option("--org", "org_id", default=None)
@click.option("--user", "user_id", default=None)
@click.option("--prefix", default=None)
@click.option("--limit", default=20, type=int)
def list_assets(
    api_url: str,
    token: str,
    org_id: Optional[str],
    user_id: Optional[str],
    prefix: Optional[str],
    limit: int,
) -> None:
    params: Dict[str, Any] = {"limit": limit}
    if org_id is not None:
        params["org_id"] = org_id
    if user_id is not None:
        params["user_id"] = user_id
    if prefix is not None:
        params["prefix"] = prefix
    url = f"{_api_base(api_url)}/api/v1/library/assets"
    resp = httpx.get(url, headers=_headers(token), params=params, timeout=30.0)
    resp.raise_for_status()
    click.echo(json.dumps(resp.json(), indent=2))


@library_cmd.command("get")
@click.option("--api", "api_url", envvar="ICE_API_URL", default="http://localhost:8000")
@click.option("--token", envvar="ICE_API_TOKEN", required=True)
@click.option("--label", required=True)
@click.option("--org", "org_id", default=None)
@click.option("--user", "user_id", default=None)
def get_asset(
    api_url: str, token: str, label: str, org_id: Optional[str], user_id: Optional[str]
) -> None:
    params: Dict[str, Any] = {}
    if org_id is not None:
        params["org_id"] = org_id
    if user_id is not None:
        params["user_id"] = user_id
    url = f"{_api_base(api_url)}/api/v1/library/assets/{label}"
    resp = httpx.get(url, headers=_headers(token), params=params, timeout=30.0)
    resp.raise_for_status()
    click.echo(json.dumps(resp.json(), indent=2))


@library_cmd.command("rm")
@click.option("--api", "api_url", envvar="ICE_API_URL", default="http://localhost:8000")
@click.option("--token", envvar="ICE_API_TOKEN", required=True)
@click.option("--label", required=True)
@click.option("--org", "org_id", default=None)
@click.option("--user", "user_id", default=None)
def delete_asset(
    api_url: str, token: str, label: str, org_id: Optional[str], user_id: Optional[str]
) -> None:
    params: Dict[str, Any] = {}
    if org_id is not None:
        params["org_id"] = org_id
    if user_id is not None:
        params["user_id"] = user_id
    url = f"{_api_base(api_url)}/api/v1/library/assets/{label}"
    resp = httpx.delete(url, headers=_headers(token), params=params, timeout=30.0)
    resp.raise_for_status()
    click.echo(json.dumps(resp.json(), indent=2))
