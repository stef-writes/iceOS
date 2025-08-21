"""iceOS command-line interface (pure *Click* implementation)."""

from __future__ import annotations

"""iceOS command-line interface (pure *Click* implementation).

"""

import asyncio
import subprocess
import sys
from typing import Any, Coroutine, List, TypeVar

import click

# ---------------------------------------------------------------------------
# Async helper ---------------------------------------------------------------
# ---------------------------------------------------------------------------


T = TypeVar("T")


def _safe_run(coro: "Coroutine[Any, Any, T]") -> T:
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
@click.option(
    "--scheduled", is_flag=True, help="Respect cron schedules and watch forever."
)
def network_run(manifest_path: str, scheduled: bool) -> None:  # noqa: D401
    """Execute *MANIFEST_PATH* via the runtime CLI without importing it."""

    cmd = [
        sys.executable,
        "-m",
        "ice_orchestrator.cli",
        "network",
        "run",
        manifest_path,
    ]
    if scheduled:
        cmd.append("--scheduled")

    subprocess.run(cmd, check=True)


# ---------------------------------------------------------------------------
# Remote API helpers (push/run) ---------------------------------------------
# ---------------------------------------------------------------------------

from ice_cli.commands.push import cli_push as _push_cmd
from ice_cli.commands.run_exec import cli_run as _run_cmd

cli.add_command(_push_cmd)
cli.add_command(_run_cmd)

# ---------------------------------------------------------------------------
# Scaffolder (new) -----------------------------------------------------------
# ---------------------------------------------------------------------------
from ice_cli.commands.scaffold import new as _new_cmd

cli.add_command(_new_cmd)

# ---------------------------------------------------------------------------
# Blueprint commands (legacy local execution) -------------------------------
# ---------------------------------------------------------------------------


@cli.command("run-blueprint")
@click.argument("blueprint_path", type=click.Path(exists=True, dir_okay=False))
@click.option(
    "--remote",
    "remote_url",
    metavar="URL",
    default=None,
    help="Execute via remote orchestrator REST API instead of local runtime.",
)
@click.option(
    "--max-parallel",
    type=int,
    default=5,
    help="Maximum node parallelism (forwarded to orchestrator).",
)
def run_blueprint(
    blueprint_path: str, remote_url: str | None, max_parallel: int
) -> None:  # noqa: D401
    """Execute *BLUEPRINT_PATH* locally or against a remote orchestrator.

    Examples
    --------
    Local runtime (no orchestrator container needed)::

        ice run-blueprint my_bp.json

    Remote execution via REST API::

        ice run-blueprint my_bp.json --remote https://api.iceos.dev
    """

    import json
    import pathlib
    import sys

    import click
    from pydantic import ValidationError

    if remote_url:
        # --- Remote execution via IceClient ---------------------------------
        # Lazy import to avoid top-level layering violation
        from importlib import import_module

        from ice_core.models.mcp import Blueprint

        IceClient = getattr(import_module("ice_client"), "IceClient")

        path = pathlib.Path(blueprint_path)
        data = json.loads(path.read_text())
        try:
            bp = Blueprint(**data)
        except ValidationError as exc:
            click.echo(f"❌ Invalid blueprint: {exc}", err=True)
            sys.exit(1)

        async def _remote() -> None:  # noqa: D401
            async with IceClient(remote_url) as client:
                ack = await client.submit_blueprint(bp, max_parallel=max_parallel)
                click.echo(f"🏃‍♂️ Run ID: {ack.run_id} (submitted)")
                async for event in client.stream_events(ack.run_id):
                    click.echo(json.dumps(event))
                result = await client.wait_for_completion(ack.run_id)
                click.echo("✅ Execution finished – result:")
                click.echo(json.dumps(result.model_dump(mode="json"), indent=2))

        _safe_run(_remote())
    else:
        # --- Local execution via runtime CLI --------------------------------
        cmd = [
            sys.executable,
            "-m",
            "ice_orchestrator.cli",
            "blueprint",
            "run",
            blueprint_path,
            "--max-parallel",
            str(max_parallel),
        ]
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
    help="Directory to write JSON schema files (default: schemas/generated)",
)
@click.option(
    "--format",
    type=click.Choice(["json", "yaml"], case_sensitive=False),
    default="json",
    help="Output format for schema files",
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
    help="Type of file to import",
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
        if path.suffix.lower() in {".yaml", ".yml"}:
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
            click.echo("   - POST /api/mcp/blueprints to register")
            click.echo("   - POST /api/mcp/runs to execute directly")
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

# ---------------------------------------------------------------------------
# Blueprint helpers ----------------------------------------------------------
# ---------------------------------------------------------------------------
from ice_cli.commands.blueprints import blueprints as _blueprints_group

cli.add_command(_blueprints_group)

from ice_cli.commands.memory import memory as _memory_group
from ice_cli.commands.registry import registry as _registry_group

# Uploads group
from ice_cli.commands.uploads import uploads as _uploads_group

cli.add_command(_uploads_group)
cli.add_command(_memory_group)
cli.add_command(_registry_group)

# Build command (DSL/YAML → Blueprint JSON)
from ice_cli.commands.build import cli_build as _build_cmd

cli.add_command(_build_cmd)

# Generate group (tool scaffolding)
from ice_cli.commands.generate import generate as _generate_group

cli.add_command(_generate_group)

# Allow "python -m ice_cli.cli ..." invocation ------------------------------
if __name__ == "__main__":  # pragma: no cover
    cli()
