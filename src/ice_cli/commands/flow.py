from __future__ import annotations

"""`ice flow` – manage higher-level flows that group multiple ScriptChains."""

import json
from datetime import datetime
from pathlib import Path
from typing import List

import typer
from rich import print as rprint

flow_app = typer.Typer(
    add_completion=False, help="Organise chains into higher-level flows"
)

__all__ = ["flow_app"]

_FLOW_EXT = ".flow.json"


# ---------------------------------------------------------------------------
# Helper utilities -----------------------------------------------------------
# ---------------------------------------------------------------------------


def _flow_file(name: str) -> Path:
    p = Path(name)
    if p.suffix == _FLOW_EXT:
        return p
    return Path.cwd() / f"{name}{_FLOW_EXT}"


# ---------------------------------------------------------------------------
# Commands -------------------------------------------------------------------
# ---------------------------------------------------------------------------


@flow_app.command("create")
def flow_create(
    name: str = typer.Argument(..., help="Flow name"),
    description: str = typer.Option("", "--description", "-d"),
    chain: List[str] = typer.Option([], "--chain", "-c"),
    force: bool = typer.Option(False, "--force", "-f"),
):
    """Create a new flow manifest (JSON)."""

    path = _flow_file(name)
    if path.exists() and not force:
        rprint(f"[red]{path.name} exists – use --force to overwrite.[/]")
        raise typer.Exit(1)

    payload = {
        "name": Path(name).stem,
        "description": description,
        "chains": chain,
        "created": datetime.utcnow().isoformat(),
    }
    path.write_text(json.dumps(payload, indent=2))
    rprint(f"[green]✔[/] Created {path.relative_to(Path.cwd())}")


@flow_app.command("ls")
def flow_ls():
    flows = sorted(Path.cwd().glob(f"*{_FLOW_EXT}"))
    if not flows:
        rprint("[yellow]No flows found.[/]")
        return
    for f in flows:
        rprint(f"• {f.stem}")


@flow_app.command("describe")
def flow_describe(name: str = typer.Argument(...)):
    path = _flow_file(name)
    if not path.exists():
        rprint(f"[red]Flow {name} not found.[/]")
        raise typer.Exit(1)
    rprint(json.loads(path.read_text()))


@flow_app.command("run")
def flow_run(
    name: str = typer.Argument(...),
    json_output: bool = typer.Option(False, "--json", "-j"),
):
    """Execute all chains referenced in the flow manifest."""

    import asyncio as _asyncio
    import importlib.util as _util

    path = _flow_file(name)
    if not path.exists():
        rprint(f"[red]Flow {name} not found.[/]")
        raise typer.Exit(1)

    data = json.loads(path.read_text())
    results = {}
    for chain_path_str in data.get("chains", []):
        chain_path = Path(chain_path_str)
        if not chain_path.is_absolute():
            chain_path = Path.cwd() / chain_path
        if not chain_path.exists():
            rprint(f"[yellow]Missing chain {chain_path} – skipping.[/]")
            continue
        spec = _util.spec_from_file_location(chain_path.stem, chain_path)
        if spec is None or spec.loader is None:
            rprint(f"[red]Unable to import {chain_path}.[/]")
            continue
        mod = _util.module_from_spec(spec)
        spec.loader.exec_module(mod)  # type: ignore[arg-type]
        chain_obj = getattr(mod, "chain", None)
        if chain_obj is None and hasattr(mod, "get_chain"):
            chain_obj = mod.get_chain()
        if chain_obj is None:
            rprint(f"[yellow]No ScriptChain in {chain_path} – skipping.[/]")
            continue
        try:
            results[chain_path.name] = _asyncio.run(chain_obj.execute()).model_dump()
        except Exception as exc:  # noqa: BLE001
            rprint(f"[red]Execution of {chain_path} failed:[/] {exc}")

    if json_output:
        rprint(results)
    else:
        from rich.pretty import pprint as _pp

        _pp(results)


@flow_app.command("delete")
def flow_delete(
    name: str = typer.Argument(...),
    force: bool = typer.Option(False, "--force", "-f"),
):
    path = _flow_file(name)
    if not path.exists():
        rprint(f"[red]Flow {name} not found.[/]")
        raise typer.Exit(1)
    if not force and not typer.confirm(f"Delete {path}?", abort=True):
        return
    path.unlink()
    rprint(f"[green]✔[/] Deleted {path}")
