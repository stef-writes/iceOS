# pragma: no cover
from __future__ import annotations

# ruff: noqa: E402

"""`ice node` – additional node-level utilities.

Currently provides a *set-llm* command for quick parameter tweaks without
opening YAML.

Excluded from strict coverage – behaviour will be covered via high-level CLI
tests once added.
"""

import json
from pathlib import Path
from typing import Any, Dict

import typer
import yaml
from rich import print as rprint

node_app = typer.Typer(help="Node utilities (patch parameters, etc.)")

# ---------------------------------------------------------------------------
# Helper --------------------------------------------------------------------
# ---------------------------------------------------------------------------


def _load_yaml(path: Path) -> Dict[str, Any]:  # noqa: D401 – helper
    if not path.exists():
        raise FileNotFoundError(path)
    return yaml.safe_load(path.read_text())


def _save_yaml(path: Path, data: Dict[str, Any]) -> None:  # noqa: D401 – helper
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def _pretty(path: Path) -> str:  # noqa: D401 – helper
    try:
        return str(path.relative_to(Path.cwd()))
    except ValueError:
        return str(path)


# ---------------------------------------------------------------------------
# set-llm --------------------------------------------------------------------
# ---------------------------------------------------------------------------


@node_app.command("set-llm", help="Patch llm_config fields of a YAML AiNode")
def set_llm(
    node_file: Path = typer.Argument(
        ...,
        exists=True,
        readable=True,
        dir_okay=False,
        file_okay=True,
        help="Path to *.ainode.yaml",
    ),
    max_tokens: int | None = typer.Option(None, "--max-tokens"),
    temperature: float | None = typer.Option(None, "--temperature"),
    top_p: float | None = typer.Option(None, "--top-p"),
    provider: str | None = typer.Option(None, "--provider"),
    model: str | None = typer.Option(None, "--model"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show diff but do not write"),
):
    """Quickly change common LLM parameters in-place."""

    data = _load_yaml(node_file)
    if data.get("type") != "ai":
        rprint(f"[red]Error:[/] {node_file} is not an ai node.")
        raise typer.Exit(1)

    llm_conf: Dict[str, Any] = data.get("llm_config", {})

    if max_tokens is not None:
        llm_conf["max_tokens"] = max_tokens
    if temperature is not None:
        llm_conf["temperature"] = temperature
    if top_p is not None:
        llm_conf["top_p"] = top_p
    if provider is not None:
        llm_conf["provider"] = provider
    if model is not None:
        llm_conf["model"] = model

    data["llm_config"] = llm_conf

    if dry_run:
        rprint(json.dumps(data, indent=2))
    else:
        _save_yaml(node_file, data)
        rprint(f"[green]✔ Patched[/] {_pretty(node_file)}")
