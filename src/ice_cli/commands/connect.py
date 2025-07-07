from __future__ import annotations

"""`ice connect` – add or remove edges between nodes in a ScriptChain.

Extracted from the legacy inline implementation inside *ice_cli.cli* so the
root CLI can stay lightweight and avoid circular imports.
"""

import ast
from pathlib import Path
from typing import cast

import typer
from rich import print as rprint

connect_app = typer.Typer(
    add_completion=False, help="Add or remove edges between nodes in a ScriptChain"
)

__all__ = ["connect_app"]


# ---------------------------------------------------------------------------
# Helper utilities ----------------------------------------------------------
# ---------------------------------------------------------------------------


def _load_chain_module(chain_path: Path):  # noqa: D401 – helper
    """Import and return the Python module at *chain_path*."""

    import importlib.util as _util

    spec = _util.spec_from_file_location(chain_path.stem, chain_path)
    if spec is None or spec.loader is None:
        raise FileNotFoundError(chain_path)
    mod = _util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[arg-type]
    return mod


# ---------------------------------------------------------------------------
# Commands ------------------------------------------------------------------
# ---------------------------------------------------------------------------


@connect_app.command("add")
def connect_add(
    chain: Path = typer.Argument(..., exists=True, dir_okay=False, readable=True),
    src: str = typer.Argument(..., help="Source node id"),
    dst: str = typer.Argument(..., help="Destination node id"),
):
    """Append a call `chain.add_edge(src, dst)` to the end of *chain* file."""

    line = f'\n# edge added by CLI\nchain.add_edge("{src}", "{dst}")\n'
    with chain.open("a", encoding="utf-8") as f:
        f.write(line)
    rprint(f"[green]✔[/] Added edge {src} -> {dst} in {chain}")


@connect_app.command("ls")
def connect_ls(
    chain: Path = typer.Argument(..., exists=True, dir_okay=False, readable=True),
):
    """List all edges in *chain* by inspecting node dependencies."""

    mod = _load_chain_module(chain)
    chain_obj = getattr(mod, "chain", None)
    if chain_obj is None and hasattr(mod, "get_chain"):
        chain_obj = mod.get_chain()
    if chain_obj is None:
        rprint("[red]Chain object not found.[/]")
        raise typer.Exit(1)

    for node_id, node in chain_obj.nodes.items():  # type: ignore[attr-defined]
        for dep in getattr(node, "dependencies", []):
            rprint(f"{dep} --> {node_id}")


@connect_app.command("rm")
def connect_rm(
    chain: Path = typer.Argument(..., exists=True, dir_okay=False),
    src: str = typer.Argument(...),
    dst: str = typer.Argument(...),
):
    """Remove a previously added `chain.add_edge(src, dst)` call from file."""

    source = chain.read_text()
    tree = ast.parse(source)

    new_body = []
    removed = False
    for node in tree.body:
        # Keep everything except the exact call expression we injected
        if (
            isinstance(node, ast.Expr)
            and isinstance(node.value, ast.Call)
            and isinstance(node.value.func, ast.Attribute)
            and node.value.func.attr == "add_edge"
            and len(node.value.args) == 2
            and {cast(ast.Constant, arg).value for arg in node.value.args} == {src, dst}
        ):
            removed = True
            continue
        new_body.append(node)

    if not removed:
        rprint("[yellow]No matching edge found – nothing changed.[/]")
        raise typer.Exit()

    tree.body = new_body  # type: ignore[assignment]
    updated = ast.unparse(tree)
    chain.write_text(updated, encoding="utf-8")
    rprint(f"[green]✔[/] Removed edge {src} -> {dst} in {chain}")
