from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import typer
from rich import print as rprint
from rich.table import Table

from ice_cli.context import get_ctx  # access global CLIContext
from ice_cli.events import _emit_event
from ice_cli.utils import snake_case as _snake_case  # centralised helper
from ice_sdk.events.models import CLICommandEvent
from ice_sdk.services import ServiceLocator  # new
from ice_sdk.tools.base import ToolContext
from ice_sdk.tools.service import ToolService

# ---------------------------------------------------------------------------
# Helper utilities ----------------------------------------------------------
# ---------------------------------------------------------------------------


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

# Expand help text with practical examples to improve discoverability.

tool_app = typer.Typer(
    help=(
        "Commands related to tool development.\n\n"
        "Examples:\n"
        "  ice tool create Echo --dir src/user_tools\n"
        "  ice tool ls\n"
        "  ice tool info echo\n"
    )
)

__all__ = ["tool_app", "get_tool_service"]

# ---------------------------------------------------------------------------
# Singleton `ToolService` instance -----------------------------------------
# ---------------------------------------------------------------------------

_tool_service: ToolService | None = None


def get_tool_service(refresh: bool = False) -> ToolService:
    """Return a memoised ToolService with auto-discovered project tools.

    The helper keeps a module-local cache for performance. However, test
    suites routinely wipe the :class:`~ice_sdk.services.ServiceLocator`
    registry via :py:meth:`ServiceLocator.clear`.  In that scenario the
    *cached* reference becomes *dangling* (no longer present in the global
    locator) which may cause stale data or missing tool registrations in
    subsequent calls.

    We therefore verify the cached instance is still registered and reset it
    if the locator was cleared.
    """

    global _tool_service  # noqa: PLW0603 – module level cache is fine here

    # Detect locator reset -------------------------------------------------
    if not refresh and _tool_service is not None:
        try:
            ServiceLocator.get("tool_service")
        except KeyError:
            # Global registry was cleared – drop stale cache so we rebuild.
            _tool_service = None

    # Build or refresh -----------------------------------------------------
    if _tool_service is None or refresh:
        try:
            _tool_service = ServiceLocator.get("tool_service")
        except KeyError:
            svc = ToolService()
            # Discover project-local tools relative to CWD ------------------
            svc.discover_and_register(Path.cwd())
            ServiceLocator.register("tool_service", svc)
            _tool_service = svc

    assert _tool_service is not None
    return _tool_service


# ---------------------------------------------------------------------------
# `tool new` ---------------------------------------------------------------
# ---------------------------------------------------------------------------


def _write_tool_file(*, name: str, directory: Path, force: bool) -> None:  # type: ignore[override]
    """Internal helper shared by *tool_new* and *tool_create*."""

    target_path = directory / f"{_snake_case(name)}.tool.py"

    # Emit started event -------------------------------------------------
    _emit_event(
        "cli.tool_create.started",
        CLICommandEvent(
            command="tool_create",
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
            "cli.tool_create.completed",
            CLICommandEvent(
                command="tool_create", status="completed", params={"dry_run": True}
            ),
        )
        raise typer.Exit()

    if target_path.exists() and not force:
        rprint(
            f"[red]Error:[/] File {target_path} already exists. Use --force to overwrite."
        )
        raise typer.Exit(code=1)

    try:
        target_path.write_text(_create_tool_template(name))
        rprint(f"[green]✔[/] Created {_pretty_path(target_path)}")
        _emit_event(
            "cli.tool_create.completed",
            CLICommandEvent(command="tool_create", status="completed"),
        )
    except Exception as exc:  # noqa: BLE001
        _emit_event(
            "cli.tool_create.failed",
            CLICommandEvent(
                command="tool_create", status="failed", params={"error": str(exc)}
            ),
        )
        rprint(f"[red]✗ Failed to write template:[/] {exc}")
        raise typer.Exit(code=1)


# ---------------------------------------------------------------------------
# `tool create` – preferred alias for legacy `tool new` ----------------------
# ---------------------------------------------------------------------------


@tool_app.command(
    "create",
    help="Scaffold a new tool module from a template (preferred).",
    rich_help_panel="Scaffolding",
)
def tool_create(
    name: str = typer.Argument(..., help="Class name for the tool (e.g. MyCool)"),
    directory: Path = typer.Option(
        Path.cwd(),
        "--dir",
        "-d",
        exists=True,
        file_okay=False,
        dir_okay=True,
        writable=True,
        help="Destination directory",
    ),
    force: bool = typer.Option(
        False, "--force", "-f", help="Overwrite if file already exists"
    ),
) -> None:
    """Preferred entry-point for scaffolding tools."""

    _write_tool_file(name=name, directory=directory, force=force)


# ---------------------------------------------------------------------------
# `tool ls` ------------------------------------------------------------------
# ---------------------------------------------------------------------------


@tool_app.command("ls", help="List all tools available in the current project")
def tool_ls(
    refresh: bool = typer.Option(
        False, "--refresh", "-r", help="Re-scan project directories"
    )
) -> None:
    """Print a table of registered tool names and their descriptions."""

    svc = get_tool_service(refresh)

    # Check if JSON output is requested via global flag
    ctx = get_ctx()
    if getattr(ctx, "json_output", False):
        import json

        tools = sorted(svc.available_tools())
        typer.echo(json.dumps(tools))
        return

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
        return await tool_obj.run(
            ctx=ToolContext(agent_id="cli", session_id="cli"), **kwargs
        )

    result = asyncio.run(_run_tool())  # noqa: S609 – top-level call OK in CLI
    from rich.json import JSON

    rprint(JSON.from_data(result))
