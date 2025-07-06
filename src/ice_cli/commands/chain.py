from __future__ import annotations

# ruff: noqa: E402

"""ice chain – high-level ScriptChain management commands.

This sub-command group offers ergonomic aliases that map directly onto
existing functionality inside *ice_cli.cli* and *ice_orchestrator.script_chain*.
The goal is to provide a beginner-friendly yet powerful entry-point for
"vibe coders" without touching low-level orchestration code.

Commands implemented (initial MVP):
    chain create   – thin alias around `ice sdk create-chain`
    chain graph    – print Mermaid graph of a ScriptChain file
    chain run      – execute a ScriptChain and pretty-print result
    chain validate – static validations; exit code !=0 on failures
    chain metrics  – run chain and show aggregated token / cost info
    chain export-run – run chain and write rich JSON to file/stdout

All heavy-lifting stays in existing helpers so we avoid duplication and
respect repo rule #4 (no *app.* imports inside *ice_sdk.*).
"""

import asyncio
import json
import os as _os
import sys
from pathlib import Path
from typing import List, Optional

import typer
from rich import print as rprint

from ice_cli.cli import _print_mermaid_graph  # local import

# Avoid circular import: import lazily inside *chain_create* command
from ice_orchestrator.script_chain import ScriptChain  # local import

# Local imports intentionally *inside* functions wherever possible to avoid
# circular import issues when the root CLI module imports *chain_app*.

chain_app = typer.Typer(help="Manage ScriptChain workflows")

# ---------------------------------------------------------------------------
# Helper utilities (kept minimal to avoid duplication) -----------------------
# ---------------------------------------------------------------------------


def _load_module(path: Path):
    """Import the module located at *path* (mirrors logic in ice_cli.cli)."""
    import importlib.util as _util

    if not path.exists():
        raise FileNotFoundError(path)

    spec = _util.spec_from_file_location(path.stem, path)
    if spec is None or spec.loader is None:  # pragma: no cover – safety net
        raise ImportError(f"Cannot import {path}")

    module = _util.module_from_spec(spec)
    sys.modules[path.stem] = module
    spec.loader.exec_module(module)  # type: ignore[arg-type]
    return module


def _resolve_chain(path_or_module: str):  # noqa: C901 – keep simple
    """Return a (*ScriptChain*, module) pair from path or module string."""
    # ------------------------------------------------------------------
    # 1) Treat as file path first --------------------------------------
    # ------------------------------------------------------------------
    p = Path(path_or_module)
    if p.suffix == ".py" and p.exists():
        mod = _load_module(p)
    else:
        # Attempt module import
        mod = __import__(path_or_module, fromlist=["__dummy__"])

    chain: Optional[ScriptChain] = None  # type: ignore[annotation-unchecked]

    if hasattr(mod, "chain") and isinstance(getattr(mod, "chain"), ScriptChain):
        chain = getattr(mod, "chain")
    elif hasattr(mod, "get_chain") and callable(getattr(mod, "get_chain")):
        maybe_chain = getattr(mod, "get_chain")()
        if isinstance(maybe_chain, ScriptChain):
            chain = maybe_chain
    else:
        # Fallback – scan globals
        for value in mod.__dict__.values():
            if isinstance(value, ScriptChain):
                chain = value
                break

    if chain is None:
        raise ValueError("No ScriptChain instance found in the given entry point")

    return chain, mod  # noqa: RET504 – clarity


# ---------------------------------------------------------------------------
# Commands -------------------------------------------------------------------
# ---------------------------------------------------------------------------


@chain_app.command(
    "create", help="Scaffold a new ScriptChain (alias for sdk create-chain)"
)
def chain_create(
    name: str = typer.Argument("my_chain", help="Base filename without .py"),
    directory: Path = typer.Option(
        Path.cwd(),
        "--dir",
        "-d",
        exists=True,
        file_okay=False,
        dir_okay=True,
        writable=True,
    ),
    force: bool = typer.Option(
        False, "--force", "-f", help="Overwrite existing file if present"
    ),
    builder: bool = typer.Option(
        False, "--wizard/--no-wizard", help="Run interactive chain builder"
    ),
    nodes: int | None = typer.Option(
        None, "--nodes", "-n", min=1, help="Pre-set number of nodes for the wizard"
    ),
):
    """Delegate to the existing *sdk create-chain* implementation."""
    # Re-use the function directly so we don't spawn a sub-process.
    # Avoid circular import: import lazily inside *chain_create* command
    from ice_cli.cli import sdk_create_chain  # type: ignore[call-arg]

    sdk_create_chain(  # type: ignore[call-arg]
        name=name,
        directory=directory,
        force=force,
        builder=builder,
        nodes=nodes,
    )


@chain_app.command("graph", help="Print Mermaid graph for a ScriptChain")
def chain_graph(
    entry: str = typer.Argument(
        ..., help="Path to .py file or importable module containing a ScriptChain"
    ),
    preview: bool = typer.Option(
        False,
        "--preview",
        "-p",
        help="Open SVG preview in browser (requires mermaid-cli)",
    ),
):
    """Pretty-print a DAG diagram so users can visualise dependencies."""
    chain, _ = _resolve_chain(entry)

    if preview:
        # Users can already set ICE_GRAPH_PREVIEW=1; we also toggle it here.
        _os.environ["ICE_GRAPH_PREVIEW"] = "1"
    _print_mermaid_graph(chain)


@chain_app.command("run", help="Execute a ScriptChain and print result")
def chain_run(
    entry: str = typer.Argument(..., help="Path or module containing ScriptChain"),
    profile: bool = typer.Option(
        False, "--profile", "-p", help="Show aggregated token/cost metrics after run"
    ),
    json_output: bool = typer.Option(
        False, "--json", "-j", help="Emit raw JSON result instead of Rich table"
    ),
    override: List[str] = typer.Option(
        None,
        "--override",
        "-o",
        help="Patch node param e.g. summariser_ai.max_tokens=512",
        show_default=False,
    ),
):
    """Simple synchronous wrapper around ScriptChain.execute()."""

    chain, _ = _resolve_chain(entry)

    # Apply in-memory overrides --------------------------------------
    if override:
        for item in override:
            try:
                k, v = item.split("=", 1)
                node_id, field = k.split(".", 1)
            except ValueError:
                rprint(
                    f"[red]Invalid --override '{item}'. Use nodeId.field=value format."
                )
                raise typer.Exit(1)

            node_cfg = chain.nodes.get(node_id)
            if node_cfg is None:
                rprint(f"[red]No node with id '{node_id}' found in chain.")
                raise typer.Exit(1)

            if node_cfg.type == "ai":
                # ensure llm_config exists
                llm_conf = getattr(node_cfg, "llm_config", {}) or {}
                # Try to parse value to int/float if possible
                if v.isdigit():
                    v_parsed = int(v)
                else:
                    try:
                        v_parsed = float(v)
                    except ValueError:
                        v_parsed = v
                llm_conf[field] = v_parsed
                setattr(node_cfg, "llm_config", llm_conf)
            else:
                setattr(node_cfg, field, v)

    # Execute ---------------------------------------------------------
    result = asyncio.run(chain.execute())

    if json_output:
        json.dump(result.model_dump(), sys.stdout, indent=2, default=str)
        sys.stdout.write("\n")
    else:
        rprint(result.model_dump())

    if profile:
        rprint("[bold cyan]\nExecution metrics[/]")
        rprint(chain.get_metrics())


@chain_app.command("validate", help="Perform static validations on a ScriptChain")
def chain_validate(
    entry: str = typer.Argument(..., help="Path or module containing ScriptChain"),
):
    """Run *ScriptChain.validate_chain()* and exit with non-zero code on errors."""
    chain, _ = _resolve_chain(entry)
    errors = chain.validate_chain()
    if errors:
        for err in errors:
            rprint(f"[red]• {err}[/]")
        raise typer.Exit(code=1)
    rprint("[green]✔ No validation errors found.")


@chain_app.command("metrics", help="Run a ScriptChain and show token/cost summary")
def chain_metrics(
    entry: str = typer.Argument(..., help="Path or module containing ScriptChain"),
):
    """Execute chain (de-duping cached runs) and print *chain.get_metrics()*."""
    chain, _ = _resolve_chain(entry)
    asyncio.run(chain.execute())
    rprint(chain.get_metrics())


@chain_app.command(
    "export-run", help="Run chain & write detailed JSON to file / stdout"
)
def chain_export(
    entry: Path = typer.Argument(
        ...,
        exists=True,
        readable=True,
        dir_okay=False,
        file_okay=True,
        help="Path to .py file with ScriptChain",
    ),
    out: Path | None = typer.Option(
        None,
        "--out",
        "-o",
        writable=True,
        help="Destination JSON file (stdout if omitted)",
    ),
):
    """Thin wrapper around *scripts/export_chain_run.py* functionality."""
    # We do a light re-implementation to avoid spawning a child process.
    from scripts.export_chain_run import _collect_run_data  # type: ignore

    _load_module(entry)  # ensure module side-effects executed
    chain, _ = _resolve_chain(entry.as_posix())  # reuse logic

    result = asyncio.run(chain.execute())
    payload = _collect_run_data(chain, result)

    serialized = json.dumps(payload, indent=2, default=str)

    if out is None:
        print(serialized)
    else:
        out.write_text(serialized, encoding="utf-8")
        rprint(f"[green]✔ Wrote results → {out}")
