"""`ice` – developer command-line interface for iceOS.

Usage (installed as console_script entry-point)::

    $ ice --help
    $ ice tool new MyCoolTool
    $ ice run path/to/chain.py --watch

This module intentionally keeps **no** business logic.  It delegates heavy-lifting
(e.g. code-generation, file-watching, orchestrator execution) to helper
functions so it remains fast to import – an important property for file
watchers that may need to reload commands many times per second.
"""

from __future__ import annotations

import asyncio
import importlib
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import typer
from rich import print as rprint
import click  # Added for patch

# Watchdog is optional: CLI still works sans --watch ----------------------
try:
    from watchdog.events import FileSystemEventHandler  # type: ignore
    from watchdog.observers import Observer  # type: ignore

    _WATCHDOG_AVAILABLE = True
except ModuleNotFoundError:  # pragma: no cover
    _WATCHDOG_AVAILABLE = False

    class FileSystemEventHandler:  # type: ignore
        """Fallback stub when *watchdog* is missing."""

        def __init__(self, *args, **kwargs):
            pass

    class Observer:  # type: ignore
        """Stubbed *watchdog.observers.Observer* when dependency absent."""

        def schedule(self, *args, **kwargs):
            pass

        def start(self):
            rprint("[yellow]Watch mode disabled – *watchdog* not installed.[/]")

        def stop(self):
            pass

        def join(self):
            pass

from ice_sdk.tools.service import (  # noqa: F401 – side-effect import makes built-ins discoverable
    ToolService,
)
from ice_sdk.utils.logging import setup_logger

# ---------------------------------------------------------------------------
# Setup Typer app -----------------------------------------------------------
# ---------------------------------------------------------------------------
app = typer.Typer(add_completion=False, help="iceOS developer CLI")
logger = setup_logger()


# ---------------------------------------------------------------------------
# Helper utilities ----------------------------------------------------------
# ---------------------------------------------------------------------------

def _snake_case(name: str) -> str:
    """Convert *PascalCase* or *camelCase* to ``snake_case``."""

    import re

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
# "tool" command group -----------------------------------------------------
# ---------------------------------------------------------------------------

tool_app = typer.Typer(help="Commands related to tool development")
app.add_typer(tool_app, name="tool")


# Keep a singleton ToolService to avoid repeated disk scans -------------
_tool_service: ToolService | None = None


def _get_tool_service(refresh: bool = False) -> ToolService:
    """Return a memoised ToolService with auto-discovered project tools."""

    global _tool_service  # noqa: PLW0603 – simple module-level cache

    if _tool_service is None or refresh:
        svc = ToolService()
        # Discover project-local tools relative to CWD ------------------
        svc.discover_and_register(Path.cwd())
        _tool_service = svc
    return _tool_service


@tool_app.command("new", help="Scaffold a new tool module from a template")
def tool_new(
    name: str = typer.Argument(..., help="Class name for the tool (e.g. MyCool)") ,
    directory: Path = typer.Option(
        Path.cwd(), "--dir", "-d", exists=True, file_okay=False, dir_okay=True, writable=True, help="Destination directory"
    ),
    force: bool = typer.Option(False, "--force", "-f", help="Overwrite if file already exists"),
):
    """Generate ``<snake_case>.tool.py`` with boilerplate code."""

    target_path = directory / f"{_snake_case(name)}.tool.py"

    if target_path.exists() and not force:
        rprint(f"[red]Error:[/] File {target_path} already exists. Use --force to overwrite.")
        raise typer.Exit(code=1)

    try:
        target_path.write_text(_create_tool_template(name))
        rprint(f"[green]✔[/] Created {target_path.relative_to(Path.cwd())}")
    except Exception as exc:
        rprint(f"[red]✗ Failed to write template:[/] {exc}")
        raise typer.Exit(code=1)


# ---------------------------------------------------------------------------
# ``ls`` – list available tools -------------------------------------------
# ---------------------------------------------------------------------------

@tool_app.command("ls", help="List all tools available in the current project")
def tool_ls(refresh: bool = typer.Option(False, "--refresh", "-r", help="Re-scan project directories")):
    """Print a table of registered tool names and their descriptions."""

    svc = _get_tool_service(refresh)
    from rich.table import Table

    table = Table(title="Registered Tools")
    table.add_column("Name", style="cyan", no_wrap=True)
    table.add_column("Description", style="green")

    for name in sorted(svc.available_tools()):
        tool_obj = svc.get(name)
        table.add_row(name, getattr(tool_obj, "description", ""))

    rprint(table)


# ---------------------------------------------------------------------------
# ``info`` – show details for a given tool ----------------------------------
# ---------------------------------------------------------------------------

@tool_app.command("info", help="Show JSON schema & metadata for a tool")
def tool_info(name: str = typer.Argument(..., help="Tool name")):
    """Display detailed metadata for *name*."""

    svc = _get_tool_service()
    try:
        tool_obj = svc.get(name)
    except KeyError:
        # May be stale cache – perform a one-off refresh and retry ----------
        svc = _get_tool_service(refresh=True)
        try:
            tool_obj = svc.get(name)
        except KeyError:
            rprint(f"[red]Tool '{name}' not found.[/]")
            raise typer.Exit(code=1)

    from rich.json import JSON
    rprint(JSON.from_data(tool_obj.as_dict()))


# ---------------------------------------------------------------------------
# ``test`` – execute tool standalone --------------------------------------
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

    import json

    from ice_sdk.tools.base import ToolContext

    try:
        kwargs = json.loads(args)
        if not isinstance(kwargs, dict):  # pragma: no cover – edge-case
            raise ValueError
    except Exception:
        rprint("[red]--args must be a valid JSON object string.[/]")
        raise typer.Exit(code=1)

    svc = _get_tool_service()
    try:
        tool_obj = svc.get(name)
    except KeyError:
        svc = _get_tool_service(refresh=True)
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


# ---------------------------------------------------------------------------
# ``run`` command -----------------------------------------------------------
# ---------------------------------------------------------------------------


def _load_module_from_path(path: Path) -> ModuleType:
    """Dynamically import Python module from *path* and return it."""

    if not path.exists():
        raise FileNotFoundError(path)

    # Add parent dir to sys.path so `import` works inside the module too.
    sys.path.insert(0, str(path.parent))
    module_name = path.stem

    # When reloading we need to drop previous import -----------------------
    if module_name in sys.modules:
        del sys.modules[module_name]

    return importlib.import_module(module_name)


async def _execute_chain(entry: ModuleType) -> None:
    """Look for a ScriptChain instance or factory function and run it."""

    from ice_orchestrator.script_chain import (
        ScriptChain,  # local import to avoid cycles
    )

    chain: Any | None = None

    # Common patterns: ``chain = ScriptChain(...)`` OR ``def get_chain()``
    if hasattr(entry, "chain") and isinstance(getattr(entry, "chain"), ScriptChain):
        chain = getattr(entry, "chain")
    elif hasattr(entry, "get_chain") and callable(getattr(entry, "get_chain")):
        maybe_chain = getattr(entry, "get_chain")()
        if isinstance(maybe_chain, ScriptChain):
            chain = maybe_chain

    if chain is None:
        rprint("[red]No ScriptChain found in the provided file.[/]")
        return

    result = await chain.execute()
    rprint(result.model_dump())


class _ReloadHandler(FileSystemEventHandler):  # type: ignore[misc]
    """Watchdog handler that re-executes the chain on file changes."""

    def __init__(self, entry_path: Path):
        super().__init__()
        self.entry_path = entry_path.resolve()

    def on_modified(self, event):  # type: ignore[override]
        if event.src_path.endswith(".py"):
            rprint("[yellow]🔄 Change detected. Re-running...[/]")
            asyncio.run(_cli_run(self.entry_path, watch=False))


async def _cli_run(entry: Path, watch: bool) -> None:
    module = _load_module_from_path(entry)
    await _execute_chain(module)

    if watch:
        observer = Observer()
        handler = _ReloadHandler(entry)
        observer.schedule(handler, str(entry.parent), recursive=True)
        observer.start()
        rprint("[green]Watching for changes (press Ctrl+C to quit)...[/]")
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            observer.stop()
        observer.join()


@app.command("run", help="Execute a ScriptChain declared in a Python file")
def run_cmd(
    path: Path = typer.Argument(..., exists=True, file_okay=True, dir_okay=False, readable=True),
    watch: bool = typer.Option(False, "--watch", "-w", help="Auto-reload when source files change"),
):
    """Run a ScriptChain defined in *path*.

    Example::

        $ ice run examples/my_chain.py --watch
    """

    asyncio.run(_cli_run(path.resolve(), watch))


# ---------------------------------------------------------------------------
# ``ls`` – top-level alias (shortcut) ---------------------------------------
# ---------------------------------------------------------------------------

@app.command("ls", help="List tools (shortcut for 'tool ls')")
def root_ls(
    json_format: bool = typer.Option(False, "--json", "-j", help="Return JSON instead of rich table"),
    refresh: bool = typer.Option(False, "--refresh", "-r", help="Re-scan project directories"),
):
    """Convenience wrapper around ``tool ls`` for quicker access.

    Example::
        $ ice ls --json
    """
    svc = _get_tool_service(refresh)
    if json_format:
        import json as _json

        typer.echo(_json.dumps(sorted(svc.available_tools())))
    else:
        # Reuse the internal ``tool_ls`` implementation -------------------
        from rich.table import Table

        table = Table(title="Registered Tools")
        table.add_column("Name", style="cyan", no_wrap=True)
        table.add_column("Description", style="green")
        for name in sorted(svc.available_tools()):
            tool_obj = svc.get(name)
            table.add_row(name, getattr(tool_obj, "description", ""))
        rprint(table)


# ---------------------------------------------------------------------------
# Compatibility patch: Typer <-> Click metavar bug ---------------------------
# ---------------------------------------------------------------------------

# Some versions of Typer call ``click.Parameter.make_metavar()`` without the
# required *ctx* argument causing a ``TypeError`` when running ``--help`` via
# *CliRunner*.  Patch the method at import-time to accept an optional context.
if not getattr(click.Parameter.make_metavar, "_icepatched", False):  # type: ignore[attr-defined]
    _orig_make_metavar = click.Parameter.make_metavar  # type: ignore[assignment]

    def _patched_make_metavar(self: click.Parameter, ctx: click.Context | None = None):  # type: ignore[override]
        if ctx is None:
            # Create a minimal dummy Context when none was provided
            ctx = click.Context(click.Command(name="_dummy"))
        return _orig_make_metavar(self, ctx)

    _patched_make_metavar._icepatched = True  # type: ignore[attr-defined]
    click.Parameter.make_metavar = _patched_make_metavar  # type: ignore[assignment] 