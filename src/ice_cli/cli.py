"""iceOS command-line interface (pure *Click* implementation).

"""

from __future__ import annotations

"""iceOS command-line interface (pure *Click* implementation).

"""

import asyncio
import subprocess
import sys
from typing import List

import click

# ---------------------------------------------------------------------------
# Async helper ---------------------------------------------------------------
# ---------------------------------------------------------------------------

def _safe_run(coro):  # noqa: ANN001 – generic coroutine
    """Run *coro* regardless of whether an event loop is already running.

    If running inside an existing loop (e.g., Jupyter) we schedule the coroutine
    and block until completion using ``loop.run_until_complete`` after applying
    ``nest_asyncio`` to enable nested loops.
    """

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)

    # Already inside a loop ---------------------------------------------------
    try:
        import nest_asyncio  # type: ignore

        nest_asyncio.apply()
    except Exception:
        pass  # Optional dependency – if missing we still attempt but may error

    return loop.run_until_complete(coro)

# NOTE: All runtime execution now lives in *ice_orchestrator.cli* to respect
# clean layer boundaries.  We forward commands via *subprocess* instead of
# importing the orchestrator layer directly.

# ---------------------------------------------------------------------------
# Doctor implementation ------------------------------------------------------
# ---------------------------------------------------------------------------

_VALID_TARGETS: dict[str, List[str]] = {
    "lint": ["lint"],
    "type": ["type"],
    "test": ["test"],
    # *all* is expanded into individual targets so we capture granular
    # exit-codes and stop early on first failure.
    "all": ["lint", "type", "test"],
}

@click.group(context_settings={"help_option_names": ["-h", "--help"]})
def cli() -> None:  # – entrypoint
    """iceOS CLI utilities (run ``ice --help`` for details)."""

@cli.command()
@click.argument(
    "category",
    type=click.Choice(sorted(_VALID_TARGETS.keys()), case_sensitive=False),
    default="all",
    metavar="{lint|type|test|all}",
)
def doctor(category: str) -> None:  # – imperative mood
    """Run repository health-checks (lint, type, test).

    ``CATEGORY`` selects which subset of checks to perform.  The default
    **all** runs *lint*, *type* and *test* sequentially, failing fast on the
    first non-zero exit-status.
    """

    category = category.lower()
    for target in _VALID_TARGETS[category]:
        click.echo(f"[doctor] Running make {target} …")
        completed = subprocess.run(["make", target])
        if completed.returncode != 0:
            click.echo(f"[doctor] make {target} failed", err=True)
            sys.exit(completed.returncode)

    click.echo("[doctor] All checks passed ✔")

# ---------------------------------------------------------------------------
# Network commands -----------------------------------------------------------
# ---------------------------------------------------------------------------


@cli.group()
def network() -> None:
    """Convenience wrapper that forwards to *ice_orchestrator.cli*."""


@network.command("run")
@click.argument("manifest_path", type=click.Path(exists=True, dir_okay=False))
@click.option("--scheduled", is_flag=True, help="Respect cron schedules and watch forever.")
def network_run(manifest_path: str, scheduled: bool) -> None:  # noqa: D401
    """Execute *MANIFEST_PATH* via the runtime CLI without importing it."""

    cmd = [sys.executable, "-m", "ice_orchestrator.cli", "network", "run", manifest_path]
    if scheduled:
        cmd.append("--scheduled")

    subprocess.run(cmd, check=True)

# Alias for Poetry entrypoint -------------------------------------------------
app = cli  # For backward compatibility with pyproject.toml script entry

# ---------------------------------------------------------------------------
# Schema commands -----------------------------------------------------------
# ---------------------------------------------------------------------------

@cli.group()
def schemas() -> None:
    """Schema generation and validation commands."""

@schemas.command("export")
@click.option(
    "--output-dir",
    type=click.Path(file_okay=False, writable=True),
    default="schemas/generated",
    help="Directory to write JSON schema files (default: schemas/generated)"
)
@click.option(
    "--format",
    type=click.Choice(["json", "yaml"], case_sensitive=False),
    default="json",
    help="Output format for schema files"
)
def schemas_export(output_dir: str, format: str) -> None:
    """Export JSON schemas for all node types and MCP models."""
    from ice_cli.commands.export_schemas import export_all_schemas
    
    click.echo(f"🔧 Exporting schemas to {output_dir} in {format} format...")
    exported_count = export_all_schemas(output_dir, format)
    click.echo(f"✅ Exported {exported_count} schemas successfully!")

@schemas.command("import")
@click.argument("file_path", type=click.Path(exists=True, dir_okay=False))
@click.option(
    "--type",
    type=click.Choice(["blueprint", "component"], case_sensitive=False),
    default="blueprint",
    help="Type of file to import"
)
def schemas_import(file_path: str, type: str) -> None:
    """Import a Blueprint or ComponentDefinition JSON/YAML file for testing."""
    import json
    import pathlib

    import yaml
    from pydantic import ValidationError

    from ice_core.models.mcp import Blueprint, ComponentDefinition
    from ice_core.validation.schema_validator import validate_blueprint  # async

    click.echo(f"📥 Importing {type} file: {file_path}")

    path = pathlib.Path(file_path)
    try:
        raw_text = path.read_text()
        if path.suffix.lower() in {'.yaml', '.yml'}:
            data = yaml.safe_load(raw_text)
        else:
            data = json.loads(raw_text)

        if type == "blueprint":
            blueprint = Blueprint(**data)  # Pydantic validation

            # Design-time & runtime validation (same as MCP route)
            try:
                _safe_run(validate_blueprint(blueprint))  # uses existing validator
                blueprint.validate_runtime()
            except Exception as exc:
                raise ValueError(str(exc)) from exc

            click.echo(f"✅ Imported Blueprint with {len(blueprint.nodes)} nodes!")
            click.echo(f"   Blueprint ID: {blueprint.blueprint_id}")
            click.echo(f"   Schema Version: {blueprint.schema_version}")
            click.echo("\n💡 Next steps:")
            click.echo("   - POST /api/v1/mcp/blueprints to register")
            click.echo("   - POST /api/v1/mcp/runs to execute directly")
        else:  # component
            component = ComponentDefinition(**data)
            click.echo("✅ Imported ComponentDefinition!")
            click.echo(f"   Type: {component.type}")
            click.echo(f"   Name: {component.name}")
            click.echo("\n💡 Use the MCP API to register this component.")
    except (json.JSONDecodeError, yaml.YAMLError) as parse_err:
        click.echo(f"❌ Failed to parse file: {parse_err}", err=True)
        ctx = click.get_current_context()
        ctx.exit(1)
    except ValidationError as ve:
        click.echo("❌ Pydantic validation errors:", err=True)
        for err in ve.errors():
            click.echo(f"  {err['loc']}: {err['msg']}", err=True)
        ctx = click.get_current_context()
        ctx.exit(1)
    except Exception as exc:
        click.echo(f"❌ Import failed: {exc}", err=True)
        ctx = click.get_current_context()
        ctx.exit(1)

# Plugins group import (must come before cli.add_command)
from ice_cli.commands.plugins import plugins

cli.add_command(plugins)  # type: ignore[arg-type]

# Allow "python -m ice_cli.cli ..." invocation ------------------------------
if __name__ == "__main__":  # pragma: no cover
    cli()