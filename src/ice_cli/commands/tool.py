from __future__ import annotations

import asyncio
import json
import re
from pathlib import Path
from typing import Any

import typer
from rich import print as rprint
from rich.table import Table

from ice_cli.context import get_ctx  # access global CLIContext
from ice_cli.events import _emit_event
from ice_sdk.events.models import CLICommandEvent
from ice_sdk.tools.base import ToolContext
from ice_sdk.tools.service import ToolService

# ---------------------------------------------------------------------------
# Helper utilities ----------------------------------------------------------
# ---------------------------------------------------------------------------

def _snake_case(name: str) -> str:
    """Convert *PascalCase* or *camelCase* to ``snake_case``."""

    name = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", name)
    name = re.sub(r"([a-z\d])([A-Z])", r"\1_\2", name)
    return name.replace("-", "_").lower()


def _create_tool_template(tool_name: str) -> str:
    """Return a ready-to-write Python template for a new Tool class."""

    snake = _snake_case(tool_name)
    class_name = tool_name if tool_name.endswith("Tool") else f"{tool_name}Tool"

    return f"""from __future__ import annotations

from typing import Any

from ice_sdk.tools.base import BaseTool, ToolContext


class {class_name}(BaseTool):
    \"\"\"{class_name} – describe what the tool does.\"\"\"

    name = \"{snake}\"
    description = "Describe what the tool does"

    async def run(self, ctx: ToolContext, **kwargs: Any) -> Any:  # noqa: D401
        \"\"\"Execute the tool.

        Args:
            ctx: Execution context injected by the orchestrator.
            **kwargs: Parameters defined by the agent/node.
        \"\"\"
        # IMPLEMENT YOUR TOOL LOGIC HERE -----------------------------------
        return {{"echo": kwargs}}
"""


# ---------------------------------------------------------------------------
# Typer app -----------------------------------------------------------------
# ---------------------------------------------------------------------------

tool_app = typer.Typer(help="Commands related to tool development")

__all__ = ["tool_app", "get_tool_service"]

# ---------------------------------------------------------------------------
# Singleton `ToolService` instance -----------------------------------------
# ---------------------------------------------------------------------------

_tool_service: ToolService | None = None


def get_tool_service(refresh: bool = False) -> ToolService:
    """Return a memoised ToolService with auto-discovered project tools."""

    global _tool_service  # noqa: PLW0603 – module level cache is fine here

    if _tool_service is None or refresh:
        svc = ToolService()
        # Discover project-local tools relative to CWD ------------------
        svc.discover_and_register(Path.cwd())
        _tool_service = svc
    return _tool_service


# ---------------------------------------------------------------------------
# `tool new` ---------------------------------------------------------------
# ---------------------------------------------------------------------------

@tool_app.command("new", help="Scaffold a new tool module from a template")
def tool_new(
    name: str = typer.Argument(..., help="Class name for the tool (e.g. MyCool)"),
    directory: Path = typer.Option(
        Path.cwd(), "--dir", "-d", exists=True, file_okay=False, dir_okay=True, writable=True, help="Destination directory"
    ),
    force: bool = typer.Option(False, "--force", "-f", help="Overwrite if file already exists"),
):
    """Generate ``<snake_case>.tool.py`` with boilerplate code."""

    target_path = directory / f"{_snake_case(name)}.tool.py"

    # Emit started event -------------------------------------------------
    _emit_event(
        "cli.tool_new.started",
        CLICommandEvent(
            command="tool_new",
            status="started",
            params={"name": name, "directory": str(directory), "force": force},
        ),
    )

    def _pretty_path(p: Path) -> str:
        try:
            return str(p.relative_to(Path.cwd()))
        except ValueError:
            return str(p)

    # Honour --dry-run flag ---------------------------------------------------
    ctx = get_ctx()
    if getattr(ctx, "dry_run", False):
        rprint(f"[yellow]Dry-run:[/] Would create {_pretty_path(target_path)}")
        _emit_event(
            "cli.tool_new.completed",
            CLICommandEvent(command="tool_new", status="completed", params={"dry_run": True}),
        )
        raise typer.Exit()

    if target_path.exists() and not force:
        rprint(f"[red]Error:[/] File {target_path} already exists. Use --force to overwrite.")
        raise typer.Exit(code=1)

    try:
        target_path.write_text(_create_tool_template(name))
        rprint(f"[green]✔[/] Created {_pretty_path(target_path)}")
        _emit_event("cli.tool_new.completed", CLICommandEvent(command="tool_new", status="completed"))
    except Exception as exc:  # noqa: BLE001
        _emit_event(
            "cli.tool_new.failed",
            CLICommandEvent(command="tool_new", status="failed", params={"error": str(exc)}),
        )
        rprint(f"[red]✗ Failed to write template:[/] {exc}")
        raise typer.Exit(code=1)


# ---------------------------------------------------------------------------
# `tool ls` ------------------------------------------------------------------
# ---------------------------------------------------------------------------

@tool_app.command("ls", help="List all tools available in the current project")
def tool_ls(refresh: bool = typer.Option(False, "--refresh", "-r", help="Re-scan project directories")) -> None:
    """Print a table of registered tool names and their descriptions."""

    svc = get_tool_service(refresh)

    table = Table(title="Registered Tools")
    table.add_column("Name", style="cyan", no_wrap=True)
    table.add_column("Description", style="green")

    for name in sorted(svc.available_tools()):
        tool_obj = svc.get(name)
        table.add_row(name, getattr(tool_obj, "description", ""))

    rprint(table)


# ---------------------------------------------------------------------------
# `tool info` --------------------------------------------------------------
# ---------------------------------------------------------------------------

@tool_app.command("info", help="Show JSON schema & metadata for a tool")
def tool_info(name: str = typer.Argument(..., help="Tool name")) -> None:
    """Display detailed metadata for *name*."""

    svc = get_tool_service()
    try:
        tool_obj = svc.get(name)
    except KeyError:
        # May be stale cache – perform a one-off refresh and retry ----------
        svc = get_tool_service(refresh=True)
        try:
            tool_obj = svc.get(name)
        except KeyError:
            rprint(f"[red]Tool '{name}' not found.[/]")
            raise typer.Exit(code=1)

    from rich.json import JSON

    rprint(JSON.from_data(tool_obj.as_dict()))


# ---------------------------------------------------------------------------
# `tool test` --------------------------------------------------------------
# ---------------------------------------------------------------------------

@tool_app.command("test", help="Execute a tool in isolation with optional JSON args")
def tool_test(
    name: str = typer.Argument(..., help="Tool name"),
    args: str = typer.Option("{}", "--args", "-a", help="JSON string of arguments"),
) -> None:
    """Run *name* and pretty-print its output.

    Example::

        $ ice tool test calculator --args '{"a":1,"b":2}'
    """

    try:
        kwargs = json.loads(args)
        if not isinstance(kwargs, dict):  # pragma: no cover – edge-case
            raise ValueError
    except Exception:  # noqa: BLE001 – user input validation
        rprint("[red]--args must be a valid JSON object string.[/]")
        raise typer.Exit(code=1)

    svc = get_tool_service()
    try:
        tool_obj = svc.get(name)
    except KeyError:
        svc = get_tool_service(refresh=True)
        try:
            tool_obj = svc.get(name)
        except KeyError:
            rprint(f"[red]Tool '{name}' not found.[/]")
            raise typer.Exit(code=1)

    async def _run_tool() -> Any:  # type: ignore[override]
        return await tool_obj.run(ctx=ToolContext(agent_id="cli", session_id="cli"), **kwargs)

    result = asyncio.run(_run_tool())  # noqa: S609 – top-level call OK in CLI
    from rich.json import JSON

    rprint(JSON.from_data(result)) 