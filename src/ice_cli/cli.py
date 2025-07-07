"""`ice` – developer command-line interface for iceOS.

Usage (installed as console_script entry-point)::

    $ ice --help
    $ ice init my_project
    $ ice create chain my_workflow
    $ ice run my_workflow.chain.py

This module intentionally keeps **no** business logic.  It delegates heavy-lifting
(e.g. code-generation, file-watching, orchestrator execution) to helper
functions so it remains fast to import – an important property for file
watchers that may need to reload commands many times per second.
"""

# Start of module -----------------------------------------------------------
# from __future__ import annotations

import os
import re
import shutil
import subprocess
from typing import Any

from rich import print as rprint  # type: ignore

from ice_cli.context import CLIContext
from ice_sdk.utils.logging import setup_logger

# Ensure realistic terminal width *before* importing Rich/Click/Typer so any
# Consoles instantiated during import use a sane fallback (GitHub Actions
# can report COLUMNS=5 which causes option names like "--json" to be split).


try:
    _cols = int(os.getenv("COLUMNS", "0"))
    if _cols < 20:
        os.environ["COLUMNS"] = "80"
except ValueError:
    os.environ["COLUMNS"] = "80"

# -------------------------------------------------------------------------

import sys
from pathlib import Path

import click  # type: ignore  # 3rd-party
import click.formatting as _cf  # type: ignore # noqa: WPS433,F401 – ensure available after click import
import typer  # type: ignore

# NEW: Load environment variables early so CLI commands inherit API keys ----
try:
    from dotenv import load_dotenv  # type: ignore  # noqa: E402

    def _load_dotenv() -> None:  # noqa: D401 – helper
        """Mimic the FastAPI lifespan logic: search CWD for a .env file."""
        project_root = Path.cwd()
        for candidate in (".env.local", ".env", ".env.example"):
            env_path = project_root / candidate
            if env_path.exists():
                load_dotenv(dotenv_path=env_path)
                # Avoid repeated loading when CLI is re-imported by *watch* mode
                break

    _load_dotenv()
except ModuleNotFoundError:  # pragma: no cover – optional dependency
    # *python-dotenv* not installed – proceed without automatic env loading.
    pass


# ---------------------------------------------------------------------------
# Global context ------------------------------------------------------------
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Setup Typer app -----------------------------------------------------------
# ---------------------------------------------------------------------------
app = typer.Typer(
    add_completion=False,
    help=(
        "iceOS developer CLI – build, test and run everything iceOS.\n\n"
        "Common global flags:\n"
        "  --json       Emit machine-readable JSON where supported.\n"
        "  --dry-run    Log intended mutations without changing files.\n"
        "  --yes        Assume affirmative answers for all prompts.\n"
        "  --verbose    Enable verbose logging.\n\n"
        "Quick examples:\n"
        "  ice init my_project\n"
        "  ice create chain my_workflow\n"
        "  ice run my_workflow.chain.py\n"
        "  ice ls\n"
    ),
    context_settings={"max_content_width": 80},
)

logger = setup_logger()

# ---------------------------------------------------------------------------
# Global options callback ---------------------------------------------------
# ---------------------------------------------------------------------------


@app.callback(invoke_without_command=True)
def _global_options(
    ctx: typer.Context,
    json_output: bool = typer.Option(
        False,
        "--json",
        "-j",
        help="Default to JSON output where supported",
        rich_help_panel="Global",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Do not execute mutations; log intended actions instead",
        rich_help_panel="Global",
    ),
    yes: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="Assume 'yes' for all confirmation prompts",
        rich_help_panel="Global",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Enable verbose logging output",
        rich_help_panel="Global",
    ),
    no_events: bool = typer.Option(
        False,
        "--no-events",
        help="Do not emit telemetry events (e.g. CLICommandEvent)",
        rich_help_panel="Global",
    ),
):
    """Global options handler."""
    if ctx.invoked_subcommand is None:
        # Show help when no subcommand provided
        typer.echo(ctx.get_help())
        raise typer.Exit()

    # Store global options in context for subcommands to access
    ctx.obj = CLIContext(
        json_output=json_output,
        dry_run=dry_run,
        yes=yes,
        verbose=verbose,
        emit_events=not no_events,
    )


# ---------------------------------------------------------------------------
# Helper utilities ----------------------------------------------------------
# ---------------------------------------------------------------------------


def _snake_case(name: str) -> str:
    """Convert *PascalCase* or *camelCase* to ``snake_case``."""
    name = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", name)
    name = re.sub(r"([a-z\d])([A-Z])", r"\1_\2", name)
    return name.replace("-", "_").lower()


# ---------------------------------------------------------------------------
# Compatibility patch: Typer <-> Click metavar bug ---------------------------
# ---------------------------------------------------------------------------

# Some versions of Typer call ``click.Parameter.make_metavar()`` without the
# required *ctx* argument causing a ``TypeError`` when running ``--help`` via
# *CliRunner*.  Patch the method at import-time to accept an optional context.
try:
    if not getattr(click.Parameter.make_metavar, "_icepatched", False):  # type: ignore[attr-defined]
        _orig_make_metavar = click.Parameter.make_metavar  # type: ignore[assignment]

        def _patched_make_metavar(self: click.Parameter, ctx: click.Context | None = None):  # type: ignore[override]
            if ctx is None:
                # Create a minimal dummy Context when none was provided
                ctx = click.Context(click.Command(name="_dummy"))
            try:
                _fn: Any = _orig_make_metavar  # type: ignore[assignment]
                return _fn(self, ctx)  # type: ignore[reportCallIssue]
            except TypeError:
                # Older Click versions expect only *self*
                return _orig_make_metavar(self)  # type: ignore[reportCallIssue]

        _patched_make_metavar._icepatched = True  # type: ignore[attr-defined]
        click.Parameter.make_metavar = _patched_make_metavar  # type: ignore[assignment]
except Exception:
    # Silently fail if patch doesn't work - CLI will still function
    pass


# ---------------------------------------------------------------------------
# Core Commands ------------------------------------------------------------
# ---------------------------------------------------------------------------


@app.command("init", help="Initialize a new iceOS project")
def init_project(
    name: str = typer.Argument(
        "my_project",
        help="Project name (directory will be created)",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Overwrite if directory already exists",
    ),
):
    """Initialize a new iceOS project with proper structure."""
    # Minimal implementation: create directory and .env
    project_path = Path(name)
    if project_path.exists() and not force:
        rprint(
            f"[red]Error:[/] Directory '{name}' already exists. Use --force to overwrite."
        )
        raise typer.Exit(1)
    if project_path.exists() and force:
        shutil.rmtree(project_path)
    project_path.mkdir(parents=True, exist_ok=True)
    (project_path / "chains").mkdir(exist_ok=True)
    (project_path / "tools").mkdir(exist_ok=True)
    (project_path / "nodes").mkdir(exist_ok=True)
    env_path = project_path / ".env"
    if not env_path.exists():
        env_content = """# iceOS Environment Configuration
OPENAI_API_KEY=your_openai_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here
GOOGLE_API_KEY=your_google_api_key_here
"""
        env_path.write_text(env_content)
        rprint(f"[green]✔[/] Created {env_path}")
    rprint(f"[green]✔[/] Project '{name}' initialized successfully!")
    rprint("[blue]Next steps:[/]")
    rprint(f"  cd {name}")
    rprint("  ice create chain my_first_workflow")
    rprint("  ice run my_first_workflow.chain.py")


@app.command("create", help="Create a new resource")
def create_resource(
    resource_type: str = typer.Argument(
        ...,
        help="Resource type: chain, tool, node",
        case_sensitive=False,
    ),
    name: str = typer.Argument(
        ...,
        help="Resource name",
    ),
    directory: Path = typer.Option(
        Path.cwd(),
        "--dir",
        "-d",
        help="Destination directory",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Overwrite if file already exists",
    ),
    builder: bool = typer.Option(
        False,
        "--builder",
        "-b",
        help="Use interactive builder (for chains)",
    ),
):
    """Create a new resource (chain, tool, or node)."""
    resource_type_lower = resource_type.lower()

    if resource_type_lower == "chain":
        target_path = directory / f"{name}.chain.py"
        if target_path.exists() and not force:
            rprint(
                f"[red]Error:[/] File {target_path} already exists. Use --force to overwrite."
            )
            raise typer.Exit(1)

        content = (
            '"""Example ScriptChain generated by `ice create chain`."""\n\n'
            "from ice_orchestrator import ScriptChain\n\n"
            f"class {name.capitalize()}Chain(ScriptChain):\n"
            '    """Describe what the chain does."""\n    pass\n'
        )
        target_path.write_text(content)

    elif resource_type_lower == "tool":
        target_path = directory / f"{name}.tool.py"
        if target_path.exists() and not force:
            rprint(
                f"[red]Error:[/] File {target_path} already exists. Use --force to overwrite."
            )
            raise typer.Exit(1)

        content = (
            "from ice_sdk.tools.base import BaseTool\n\n"
            f"class {name}(BaseTool):\n"
            f'    name = "{name.lower()}"\n'
            '    description = "Describe what the tool does"\n\n'
            "    async def run(self, ctx, **kwargs):\n"
            "        return {}\n"
        )
        target_path.write_text(content)

    elif resource_type_lower == "network":
        target_path = directory / f"{name}.network.yaml"
        if target_path.exists() and not force:
            rprint(
                f"[red]Error:[/] File {target_path} already exists. Use --force to overwrite."
            )
            raise typer.Exit(1)

        content = (
            'api_version: "network.v1"\n'
            'metadata:\n  name: {name}\n  description: "Describe the network"\n'
            "nodes:\n  ai1:\n    type: ai\n    model: gpt-3.5-turbo\n    prompt: |\n      Your prompt here\n    llm_config:\n      provider: openai\n\n"
        )
        target_path.write_text(content)

    elif resource_type_lower == "node":
        target_path = directory / f"{name}.ainode.yaml"
        if target_path.exists() and not force:
            rprint(
                f"[red]Error:[/] File {target_path} already exists. Use --force to overwrite."
            )
            raise typer.Exit(1)

        content = (
            f"id: {name}_ai\n"
            "type: ai\n"
            f"name: {name}\n"
            "model: gpt-3.5-turbo\n"
            "prompt: |\n  # TODO: write prompt here\n"
            "llm_config:\n  provider: openai\n  temperature: 0.7\n  max_tokens: 256\n"
            "dependencies: []\n"
        )
        target_path.write_text(content)

    else:
        rprint(
            f"[red]Error:[/] Unknown resource type '{resource_type}'. Use: chain, tool, node, network"
        )
        raise typer.Exit(1)

    rprint(f"[green]✔[/] Created {target_path}")


@app.command("run", help="Execute a workflow")
def run_workflow(
    entry: str = typer.Argument(
        ...,
        help="Path to workflow file (.chain.py)",
    ),
    profile: bool = typer.Option(
        False,
        "--profile",
        "-p",
        help="Show performance metrics",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        "-j",
        help="Output JSON format",
    ),
):
    """Execute a workflow file."""
    chain_path = Path(entry)
    if not chain_path.exists():
        rprint(f"[red]Error:[/] Workflow file '{entry}' not found")
        raise typer.Exit(1)
    # Run the chain file as a script
    result = subprocess.run(
        [sys.executable, str(chain_path)], capture_output=True, text=True
    )
    success = result.returncode == 0
    if result.returncode != 0:
        rprint("[red]Error running workflow:[/]")
        rprint(result.stderr)
        raise typer.Exit(result.returncode)

    if json_output:
        import json as _json

        payload = {"success": success, "output": result.stdout.strip()}
        rprint(_json.dumps(payload))
    else:
        rprint(result.stdout)


@app.command("ls", help="List resources")
def list_resources(
    resource_type: str = typer.Option(
        "all",
        "--type",
        "-t",
        help="Resource type: all, chains, tools, nodes",
        case_sensitive=False,
    ),
):
    """List available resources."""
    resource_type = resource_type.lower()
    cwd = Path.cwd()
    if resource_type in ["all", "chains"]:
        rprint("[blue]Chains:[/]")
        for f in cwd.glob("*.chain.py"):
            rprint(f"• {f.name}")
        rprint()
    if resource_type in ["all", "tools"]:
        rprint("[blue]Tools:[/]")
        for f in cwd.glob("*.tool.py"):
            rprint(f"• {f.name}")
        rprint()
    if resource_type in ["all", "nodes"]:
        rprint("[blue]Nodes:[/]")
        for f in cwd.glob("*.ainode.yaml"):
            rprint(f"• {f.name}")
        rprint()


@app.command("edit", help="Edit a resource")
def edit_resource(
    resource: str = typer.Argument(
        ...,
        help="Resource to edit (filename or name)",
    ),
):
    """Edit a resource in your default editor."""
    resource_path = Path(resource)
    if not resource_path.exists():
        # Try common extensions
        for ext in [".chain.py", ".tool.py", ".ainode.yaml", ".toolnode.yaml"]:
            test_path = Path(f"{resource}{ext}")
            if test_path.exists():
                resource_path = test_path
                break
    if not resource_path.exists():
        rprint(f"[red]Error:[/] Resource '{resource}' not found")
        raise typer.Exit(1)
    editor = os.getenv("EDITOR", "code")
    subprocess.run([editor, str(resource_path)])
    rprint(f"[green]✔[/] Opened {resource_path} in {editor}")


@app.command("delete", help="Delete a resource")
def delete_resource(
    resource: str = typer.Argument(
        ...,
        help="Resource to delete",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Skip confirmation",
    ),
):
    """Delete a resource."""
    resource_path = Path(resource)
    if not resource_path.exists():
        # Try common extensions
        for ext in [".chain.py", ".tool.py", ".ainode.yaml", ".toolnode.yaml"]:
            test_path = Path(f"{resource}{ext}")
            if test_path.exists():
                resource_path = test_path
                break
    if not resource_path.exists():
        rprint(f"[red]Error:[/] Resource '{resource}' not found")
        raise typer.Exit(1)
    if not force:
        confirm = typer.confirm(f"Delete {resource_path}?")
        if not confirm:
            rprint("Cancelled.")
            raise typer.Exit()
    resource_path.unlink()
    rprint(f"[green]✔[/] Deleted {resource_path}")


# ---------------------------------------------------------------------------
# Auto-load webhook subscribers (non-blocking) ------------------------------
try:
    from ice_cli.webhooks import initialise as _init_webhooks  # noqa: WPS433

    _init_webhooks()
except Exception:
    # Never fail CLI if optional webhook config parsing blows up
    pass


# ---------------------------------------------------------------------------
# Copilot integration -------------------------------------------------------
# ---------------------------------------------------------------------------

from ice_sdk.copilot.cli import copilot_app

app.add_typer(copilot_app, name="copilot", help="AI-powered workflow assistant")


# ---------------------------------------------------------------------------
# Quality and maintenance commands ------------------------------------------
# ---------------------------------------------------------------------------

# Quality assurance helpers (lint/type/test)
from ice_cli.commands.doctor import doctor_app as quality_app  # noqa: E402

# Misc maintenance utilities ported from scripts/cli/*
from ice_cli.commands.maint import maint_app  # noqa: E402

update_app = typer.Typer(add_completion=False, help="Self-update helpers")


@update_app.command("templates")
def update_templates():
    """Update project templates."""
    rprint("[yellow]Template updates not yet implemented.[/]")


# Mount quality sub-app (lint/type/test)
app.add_typer(quality_app, name="doctor", rich_help_panel="Quality")

app.add_typer(update_app, name="update", rich_help_panel="Maintenance")

# New: maintenance helpers sub-app ----------------------------------------
app.add_typer(maint_app, name="maint", rich_help_panel="Maintenance")


# ---------------------------------------------------------------------------
# Run *network* YAML command -------------------------------------------------
# ---------------------------------------------------------------------------


@app.command("run-network", help="Execute a network YAML specification")
def run_network(
    spec_path: str = typer.Argument(..., help="Path to network.yaml"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output JSON"),
):
    """Load *spec_path*, build a ScriptChain via NetworkFactory and run it."""

    import asyncio

    from ice_orchestrator.core.network_factory import NetworkFactory

    async def _runner():  # noqa: D401 – inner helper
        chain = await NetworkFactory.from_yaml(spec_path)
        return await chain.execute()

    try:
        result = asyncio.run(_runner())
    except Exception as exc:  # pragma: no cover – surface errors
        rprint(f"[red]Execution failed:[/] {exc}")
        raise typer.Exit(1)

    if json_output:
        import json as _json

        rprint(_json.dumps(result.model_dump()))
    else:
        from rich import print as _print

        _print(result.model_dump())


# ---------------------------------------------------------------------------
# Main entry point ---------------------------------------------------------
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app()
