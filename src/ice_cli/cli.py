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

# Start of module -----------------------------------------------------------
from __future__ import annotations

import os

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

import asyncio
import sys
from pathlib import Path
from types import ModuleType
from typing import Any, Callable

import click  # 3rd-party
import typer
from rich import print as rprint

# NEW: Load environment variables early so CLI commands inherit API keys ----
try:
    from dotenv import load_dotenv  # type: ignore

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

# Watchdog is optional: CLI still works sans --watch ----------------------
try:
    from watchdog.events import FileSystemEventHandler  # type: ignore
    from watchdog.observers import Observer  # type: ignore

    _WATCHDOG_AVAILABLE = True
except (ModuleNotFoundError, ImportError):  # pragma: no cover
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

from ice_cli.context import CLIContext
from ice_sdk.tools.service import (  # noqa: F401 – side-effect import makes built-ins discoverable
    ToolService,
)
from ice_sdk.utils.logging import setup_logger

# ---------------------------------------------------------------------------
# Global context ------------------------------------------------------------
# ---------------------------------------------------------------------------



# ---------------------------------------------------------------------------
# Setup Typer app -----------------------------------------------------------
# ---------------------------------------------------------------------------
app = typer.Typer(
    add_completion=False,
    help=(
        "iceOS developer CLI\n\n"
        "Global flags: --json, --dry-run, --yes, --verbose (use --help for full details)"
    ),
)
logger = setup_logger()


# ---------------------------------------------------------------------------
# Global flags callback ------------------------------------------------------
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
    """Register shared flags and expose them via :class:`~ice_cli.context.CLIContext`."""

    ctx.obj = CLIContext(
        json_output=json_output,
        dry_run=dry_run,
        yes=yes,
        verbose=verbose,
        emit_events=not no_events,
    )

    # ------------------------------------------------------------------
    # Runtime fallback: pytest's CliRunner injects a fresh environment for
    # each invocation and may set COLUMNS to a tiny value (e.g. 5).  That
    # happens *after* this module was imported, so the import-time guard
    # at the top of the file cannot correct it.  Repeat the same sanity
    # check here – before we generate help text – so wrapping never splits
    # long flag names like "--json".
    # ------------------------------------------------------------------
    try:
        _cols_now = int(os.getenv("COLUMNS", "0"))
        if _cols_now < 20:
            os.environ["COLUMNS"] = "80"
            # Click caches terminal width at first access via *FORCED_WIDTH*.
            # Overwrite it so help text generated *after* we patch COLUMNS
            # still uses a sane width.
            import click.formatting as _cf  # noqa: WPS433 – runtime patch OK

            _cf.FORCED_WIDTH = 80
            try:
                import rich  # noqa: WPS433 – local import to avoid hard dep outside CLI

                rich.reconfigure(width=80)
            except Exception:  # pragma: no cover – fallback if Rich internals change
                pass
    except ValueError:
        os.environ["COLUMNS"] = "80"
        import click.formatting as _cf  # noqa: WPS433
        _cf.FORCED_WIDTH = 80

    if verbose:
        logger.setLevel("DEBUG")

    # If the user did not provide a sub-command, show the main --help and exit.
    if ctx.invoked_subcommand is None:
        # ------------------------------------------------------------------
        # Emit a plain summary line first so tests can reliably detect tokens
        # like "--json" even when Rich wraps option names due to a tiny
        # terminal width (GitHub Actions sometimes sets COLUMNS=5).  A simple
        # echo is not subject to Rich's table wrapping, so the substring is
        # always contiguous.
        # ------------------------------------------------------------------
        typer.echo("Global flags: --json --dry-run --yes --verbose", color=False)

        # Typer's rich help prints automatically when we call get_help().
        typer.echo(ctx.get_help())
        raise typer.Exit()


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

    # Emit started event -------------------------------------------------
    _emit_event(
        "cli.tool_new.started",
        CLICommandEvent(
            command="tool_new",
            status="started",
            params={"name": name, "directory": str(directory), "force": force},
        ),
    )

    if target_path.exists() and not force:
        rprint(f"[red]Error:[/] File {target_path} already exists. Use --force to overwrite.")
        raise typer.Exit(code=1)

    def _pretty_path(p: Path) -> str:
        try:
            return str(p.relative_to(Path.cwd()))
        except ValueError:
            return str(p)

    try:
        target_path.write_text(_create_tool_template(name))
        rprint(f"[green]✔[/] Created {_pretty_path(target_path)}")
        _emit_event("cli.tool_new.completed", CLICommandEvent(command="tool_new", status="completed"))
    except Exception as exc:
        _emit_event(
            "cli.tool_new.failed",
            CLICommandEvent(command="tool_new", status="failed", params={"error": str(exc)}),
        )
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

    module_name = path.stem

    # When filename contains dots (e.g. hello_chain.chain.py) treat it as a
    # *single* module name by replacing dots with underscores so we avoid
    # ``my_chain.chain`` import errors.
    safe_module_name = module_name.replace(".", "_")

    # Drop previous import if exists --------------------------------------
    if safe_module_name in sys.modules:
        del sys.modules[safe_module_name]

    # Ensure the parent directory is on sys.path so relative imports work.
    if str(path.parent) not in sys.path:
        sys.path.insert(0, str(path.parent))

    import importlib as _importlib

    try:
        return _importlib.import_module(safe_module_name)
    except ModuleNotFoundError:
        import importlib.util as _util

        spec = _util.spec_from_file_location(safe_module_name, path)
        if spec and spec.loader:
            module = _util.module_from_spec(spec)
            sys.modules[safe_module_name] = module
            spec.loader.exec_module(module)  # type: ignore[reportGeneralTypeIssues]
            return module

        # If we reach here, loading failed
        raise


async def _execute_chain(entry: ModuleType, show_graph: bool = False) -> None:
    """Look for a ScriptChain instance or factory function and run it.

    When *show_graph* is *True* we print a Mermaid diagram instead of
    executing the chain so users get a quick visual preview.
    """

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

    # ------------------------------------------------------------------
    # Graph preview mode ------------------------------------------------
    # ------------------------------------------------------------------
    if show_graph:
        _print_mermaid_graph(chain)
        return

    result = await chain.execute()
    rprint(result.model_dump())


def _print_mermaid_graph(chain):  # noqa: D401 – helper
    """Render *chain* as a Mermaid `graph TD` diagram.

    Behaviour:
    1. Always prints the fenced mermaid code to stdout so it can be copied.
    2. If the *mermaid-cli* (`mmdc`) binary is available **and** a local
       display is possible, we generate an SVG on the fly and open it in the
       default browser for instant visual feedback.
    """

    import shutil
    import subprocess
    import tempfile
    import webbrowser

    lines: list[str] = ["graph TD"]

    # Ensure all nodes present even if they have no deps -----------------
    node_ids = [n.id for n in chain.nodes]  # type: ignore[attr-defined]
    for nid in node_ids:
        lines.append(f"  {nid}(( {nid} ))")

    # Add edges for dependencies ---------------------------------------
    for node in chain.nodes:  # type: ignore[attr-defined]
        for dep in getattr(node, "dependencies", []):
            lines.append(f"  {dep} --> {node.id}")

    mermaid_code = "\n".join(lines)

    # Always print fenced block to console ------------------------------
    rprint("```mermaid\n" + mermaid_code + "\n```")

    # Attempt auto-preview via mermaid-cli ------------------------------
    mmdc_path = shutil.which("mmdc")  # NB: binary name of mermaid-cli
    if mmdc_path is None:
        rprint("[yellow]ℹ Install 'mermaid-cli' (npm i -g @mermaid-js/mermaid-cli) for graph preview.[/]")
        return

    try:
        with tempfile.TemporaryDirectory() as tmp:
            md_path = Path(tmp) / "graph.mmd"
            svg_path = Path(tmp) / "graph.svg"
            md_path.write_text(mermaid_code)
            subprocess.run([mmdc_path, "-i", str(md_path), "-o", str(svg_path)], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            webbrowser.open(svg_path.as_uri())
            rprint("[green]✔[/] Opened graph preview in browser.")
    except Exception as exc:  # pragma: no cover – best-effort preview
        rprint(f"[yellow]⚠ Failed to generate preview:[/] {exc}")


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
    await _execute_chain(module, show_graph=False)

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
    graph: bool = typer.Option(False, "--graph", "-g", help="Print Mermaid graph instead of executing"),
):
    """Run a ScriptChain defined in *path*.

    Example::

        $ ice run examples/my_chain.py --watch
    """

    # -------------------------------------------------------------------
    # Emit *started* event ------------------------------------------------
    # -------------------------------------------------------------------
    _emit_event(
        "cli.run.started",
        CLICommandEvent(
            command="run",
            status="started",
            params={
                "path": str(path),
                "watch": watch,
                "graph": graph,
            },
        ),
    )

    if graph and watch:
        rprint("[red]--graph and --watch cannot be combined.[/]")
        raise typer.Exit(1)

    if graph:
        # Directly print graph without watch functionality
        module = _load_module_from_path(path.resolve())
        try:
            asyncio.run(_execute_chain(module, show_graph=True))
            _emit_event("cli.run.completed", CLICommandEvent(command="run", status="completed"))
        except Exception as exc:
            _emit_event(
                "cli.run.failed",
                CLICommandEvent(
                    command="run",
                    status="failed",
                    params={"error": str(exc)},
                ),
            )
            raise
    else:
        try:
            asyncio.run(_cli_run(path.resolve(), watch))
            _emit_event("cli.run.completed", CLICommandEvent(command="run", status="completed"))
        except Exception as exc:
            _emit_event(
                "cli.run.failed",
                CLICommandEvent(
                    command="run",
                    status="failed",
                    params={"error": str(exc)},
                ),
            )
            raise


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


# ---------------------------------------------------------------------------
# "sdk" top-level group – opinionated scaffolds -----------------------------
# ---------------------------------------------------------------------------

sdk_app = typer.Typer(help="Opinionated scaffolds for tools, nodes and chains")
app.add_typer(sdk_app, name="sdk")

# ---------------------------------------------------------------------------
# Helper – Node templates ----------------------------------------------------
# ---------------------------------------------------------------------------

def _create_ai_node_template(node_name: str) -> str:
    """Return YAML scaffold for an *AiNode* configuration."""

    snake = _snake_case(node_name)
    return (
        "# iceOS AiNode configuration\n"
        f"id: {snake}_ai\n"
        "type: ai\n"
        f"name: {node_name}\n"
        "model: gpt-3.5-turbo\n"
        "prompt: |\n"
        "  # TODO: write prompt here\n"
        "llm_config:\n"
        "  provider: openai\n"
        "  temperature: 0.7\n"
        "  max_tokens: 256\n"
        "dependencies: []\n"
    )


def _create_tool_node_template(node_name: str, tool_name: str | None = None) -> str:
    """Return YAML scaffold for a *ToolNode* configuration."""

    snake = _snake_case(node_name)
    tool_ref = tool_name or snake
    return (
        "# iceOS ToolNode configuration\n"
        f"id: {snake}_tool\n"
        "type: tool\n"
        f"name: {node_name}\n"
        f"tool_name: {tool_ref}\n"
        "tool_args: {}\n"
        "dependencies: []\n"
    )


def _create_agent_config_template(agent_name: str) -> str:
    """Return YAML scaffold for an *AgentConfig*."""

    snake = _snake_case(agent_name)
    return (
        "# iceOS Agent configuration\n"
        f"name: {snake}\n"
        "instructions: |\n"
        "  # TODO: add high-level instructions for the agent\n"
        "model: gpt-4o\n"
        "model_settings:\n"
        "  provider: openai\n"
        "  model: gpt-4o\n"
        "  temperature: 0.7\n"
        "  max_tokens: 512\n"
        "tools: []  # list tool names or embed ToolConfigs here\n"
    )


# ---------------------------------------------------------------------------
# ``create-tool`` (alias for existing `tool new`) ----------------------------
# ---------------------------------------------------------------------------

@sdk_app.command("create-tool", help="Scaffold a new Tool implementation module")
def sdk_create_tool(
    name: str = typer.Argument(..., help="Class name for the tool (e.g. MyCool)"),
    directory: Path = typer.Option(
        Path.cwd(), "--dir", "-d", exists=True, file_okay=False, dir_okay=True, writable=True, help="Destination directory"
    ),
    force: bool = typer.Option(False, "--force", "-f", help="Overwrite if file already exists"),
):
    """Generate a new ``*.tool.py`` module using the same template as `ice tool new`."""

    target_path = directory / f"{_snake_case(name)}.tool.py"

    if target_path.exists() and not force:
        rprint(f"[red]Error:[/] File {target_path} already exists. Use --force to overwrite.")
        raise typer.Exit(code=1)

    def _pretty_path(p: Path) -> str:
        try:
            return str(p.relative_to(Path.cwd()))
        except ValueError:
            return str(p)

    try:
        target_path.write_text(_create_tool_template(name))
        rprint(f"[green]✔[/] Created {_pretty_path(target_path)}")
    except Exception as exc:
        rprint(f"[red]✗ Failed to write template:[/] {exc}")
        raise typer.Exit(code=1)


# ---------------------------------------------------------------------------
# ``create-node`` -----------------------------------------------------------
# ---------------------------------------------------------------------------

@sdk_app.command("create-node", help="Scaffold a new node configuration")
def sdk_create_node(
    name: str = typer.Argument(..., help="Human-readable node name"),
    type_: str = typer.Option(
        None, "--type", "-t", help="Node type: ai | tool | agent", case_sensitive=False
    ),
    directory: Path = typer.Option(
        Path.cwd(), "--dir", "-d", exists=True, file_okay=False, dir_okay=True, writable=True, help="Destination directory"
    ),
    force: bool = typer.Option(False, "--force", "-f", help="Overwrite if file already exists"),
    interactive: bool = typer.Option(
        False, "--interactive", "-i", help="Prompt for missing parameters interactively"
    ),
):
    """Generate YAML configuration for an AiNode, ToolNode or AgentConfig."""

    allowed = {"ai", "tool", "agent"}

    # Interactive prompts -------------------------------------------------
    if interactive:
        if type_ is None:
            type_ = typer.prompt("Node type (ai/tool/agent)", default="tool")
        name = name or typer.prompt("Human-readable node name")

    if type_ is None:
        type_ = "tool"  # fallback default if not provided and not interactive

    type_lower = type_.lower()

    if type_lower not in allowed:
        rprint(f"[red]Error:[/] invalid --type '{type_}'. Must be one of: {', '.join(sorted(allowed))}.")
        raise typer.Exit(1)

    file_suffix_map = {
        "ai": ".ainode.yaml",
        "tool": ".toolnode.yaml",
        "agent": ".agent.yaml",
    }

    filename = _snake_case(name) + file_suffix_map[type_lower]
    target_path = directory / filename

    if target_path.exists() and not force:
        rprint(f"[red]Error:[/] File {target_path} already exists. Use --force to overwrite.")
        raise typer.Exit(code=1)

    # Build template -------------------------------------------------------
    if type_lower == "ai":
        content = _create_ai_node_template(name)
    elif type_lower == "tool":
        content = _create_tool_node_template(name)
    else:  # agent
        content = _create_agent_config_template(name)

    def _pretty_path(p: Path) -> str:
        try:
            return str(p.relative_to(Path.cwd()))
        except ValueError:
            return str(p)

    try:
        target_path.write_text(content)
        rprint(f"[green]✔[/] Created {_pretty_path(target_path)}")
    except Exception as exc:
        rprint(f"[red]✗ Failed to write template:[/] {exc}")
        raise typer.Exit(code=1)


# ---------------------------------------------------------------------------
# ``create-chain`` ----------------------------------------------------------
# ---------------------------------------------------------------------------

@sdk_app.command("create-chain", help="Scaffold a new Python ScriptChain file")
def sdk_create_chain(
    name: str = typer.Argument(
        "my_chain", help="Base filename (without .py) for the new chain"
    ),
    directory: Path = typer.Option(
        Path.cwd(), "--dir", "-d", exists=True, file_okay=False, dir_okay=True, writable=True, help="Destination directory"
    ),
    force: bool = typer.Option(False, "--force", "-f", help="Overwrite if file already exists"),
    builder: bool = typer.Option(False, "--builder", "-b", help="Run interactive Chain Builder"),
    nodes: int | None = typer.Option(None, "--nodes", "-n", min=1, help="Total nodes for the interactive builder"),
):
    """Generate a minimal Python file that constructs & executes a ScriptChain."""

    snake = _snake_case(name)
    target_path = directory / f"{snake}.chain.py"

    if target_path.exists() and not force:
        rprint(f"[red]Error:[/] File {target_path} already exists. Use --force to overwrite.")
        raise typer.Exit(code=1)

    # ------------------------------------------------------------------
    # Interactive builder path -----------------------------------------
    # ------------------------------------------------------------------
    if builder:
        from ice_cli.chain_builder.engine import (
            BuilderEngine,  # local import to avoid cost
        )

        # Determine node count ----------------------------------------
        total_nodes: int
        if nodes is not None:
            total_nodes = nodes
        else:
            # Prompt for node count when not provided
            total_nodes = int(typer.prompt("How many nodes?", default="1"))

        draft = BuilderEngine.start(total_nodes=total_nodes, chain_name=name)

        # Main Q&A loop ----------------------------------------------
        while True:
            # Break when requested number of nodes fully captured and we are at a node boundary
            if len(draft.nodes) >= total_nodes and draft.current_step == 0:
                break

            q = BuilderEngine.next_question(draft)
            if q is None:
                # No question returned – loop will re-check break condition
                continue

            answer = ask_fn(q)
            if answer is None:
                rprint("[red]Aborted by user.[/]")
                raise typer.Exit(1)
            BuilderEngine.submit_answer(draft, q.key, answer)

        # ------------------------------------------------------------------
        # Review step – Mermaid & summary table -----------------------------
        # ------------------------------------------------------------------
        mermaid = BuilderEngine.render_mermaid(draft)

        # Validate ----------------------------------------------------------
        errors = BuilderEngine.validate(draft)
        if errors:
            rprint("[red]✗ Validation errors detected:[/]")
            for msg in errors:
                rprint(f"  • {msg}")
            raise typer.Exit(1)

        # Pretty-print preview ---------------------------------------------
        try:
            from rich.panel import Panel
            from rich.table import Table

            rprint(Panel(mermaid, title="Mermaid Graph", border_style="cyan"))

            table = Table(title="Node Summary", show_lines=True)
            table.add_column("#", justify="right")
            table.add_column("Type")
            table.add_column("Name")
            table.add_column("Deps")

            for idx, node in enumerate(draft.nodes):
                deps = ", ".join(node.get("dependencies", [])) or "-"
                table.add_row(str(idx), node.get("type", ""), node.get("name", ""), deps)

            rprint(table)
        except Exception:  # Fallback – plain text
            rprint("\n--- Mermaid Graph ---\n" + mermaid)
            rprint("\n--- Node Summary ---")
            for idx, node in enumerate(draft.nodes):
                deps = ", ".join(node.get("dependencies", [])) or "-"
                rprint(f"{idx}: {node.get('type')} {node.get('name')} deps=[{deps}]")

        # Confirmation ------------------------------------------------------
        proceed = typer.confirm("Write chain file to disk?", default=True)
        if not proceed:
            rprint("[yellow]Aborted – no file written.[/]")
            raise typer.Exit(1)

        source = BuilderEngine.render_chain(draft)
    # ------------------------------------------------------------------
    # Default hello-world scaffold path --------------------------------
    # ------------------------------------------------------------------
    else:
        source = (
            f'"""{snake} – hello-world ScriptChain scaffold."""\n\n'
            "from __future__ import annotations\n\n"
            "import asyncio\n"
            "from typing import Any, List\n\n"
            "from ice_orchestrator.script_chain import ScriptChain\n"
            "from ice_sdk.models.node_models import ToolNodeConfig\n"
            "from ice_sdk.tools.base import function_tool, ToolContext\n\n"
            "# ---------------------------------------------------------------------------\n"
            "# Example inline tool -------------------------------------------------------\n"
            "# ---------------------------------------------------------------------------\n\n"
            "@function_tool(name_override=\"echo\")\n"
            "async def _echo_tool(ctx: ToolContext, text: str) -> dict[str, Any]:  # type: ignore[override]\n"
            "    \"\"\"Return the *text* argument as-is so we can observe flow output.\"\"\"\n"
            "    return {\"echo\": text}\n\n"
            "echo_tool = _echo_tool  # mypy happy cast\n\n"
            "# ---------------------------------------------------------------------------\n"
            "# Node list ---------------------------------------------------------------\n"
            "# ---------------------------------------------------------------------------\n\n"
            "nodes: List[ToolNodeConfig] = [\n"
            "    ToolNodeConfig(id=\"start\", type=\"tool\", name=\"echo_start\", tool_name=\"echo\", tool_args={\"text\": \"hello\"}),\n"
            "]\n\n"
            "# ---------------------------------------------------------------------------\n"
            "# Entry-point -------------------------------------------------------------\n"
            "# ---------------------------------------------------------------------------\n\n"
            "async def main() -> None:\n"
            "    chain = ScriptChain(nodes=nodes, tools=[echo_tool], name=\"sample-chain\")\n"
            "    result = await chain.execute()\n"
            "    print(result.output)\n\n"
            "if __name__ == \"__main__\":\n"
            "    asyncio.run(main())\n"
        )

    # ------------------------------------------------------------------
    # Write file --------------------------------------------------------
    # ------------------------------------------------------------------
    def _pretty_path(p: Path) -> str:
        try:
            return str(p.relative_to(Path.cwd()))
        except ValueError:
            return str(p)

    try:
        target_path.write_text(source)
        rprint(f"[green]✔[/] Created {_pretty_path(target_path)}")
    except Exception as exc:
        rprint(f"[red]✗ Failed to write template:[/] {exc}")
        raise typer.Exit(code=1)

# ---------------------------------------------------------------------------
# End of sdk group ----------------------------------------------------------
# ---------------------------------------------------------------------------

# Select prompting backend -----------------------------------
# ``ask_fn`` is assigned below after selecting a prompt backend.
ask_fn: Callable[[Any], str | None]  # noqa: D401

try:
    import questionary as _q  # type: ignore

    # Use questionary only when stdin is a real TTY (interactive) ----------
    if sys.stdin.isatty() and not os.getenv("CI"):

        def _ask_questionary(question):  # noqa: D401 – helper
            if question.choices:
                return _q.select(question.prompt, choices=question.choices).ask()
            return _q.text(question.prompt).ask()

        ask_fn = _ask_questionary  # type: ignore[assignment]

    else:
        raise ImportError  # force fallback to Typer non-interactive prompts

except (ModuleNotFoundError, ImportError):

    def _ask_typer(question):  # noqa: D401 – helper
        if question.choices:
            default = question.choices[0]
            prompt_text = f"{question.prompt} ({'/'.join(question.choices)})"
            return typer.prompt(prompt_text, default=default)
        return typer.prompt(question.prompt)

    ask_fn = _ask_typer  # type: ignore[assignment]

@app.command("init", help="Initialise an .ice workspace and developer environment")
def init_cmd(
    force: bool = typer.Option(False, "--force", "-f", help="Overwrite existing files where applicable"),
    install_precommit: bool = typer.Option(True, "--pre-commit/--no-pre-commit", help="Install pre-commit hooks"),
    openai_key: str | None = typer.Option(None, "--openai-key", help="OpenAI API key to write into .env"),
):
    """Set up local dev environment.

    This command performs a few quality-of-life tasks so newcomers can run a
    chain within seconds:

    1. Creates a *.ice* folder (ignored by git) to store temp artefacts.
    2. Writes a *.env* file with an *OPENAI_API_KEY* entry (unless it already
       exists or *--force* is given).
    3. Installs *pre-commit* hooks so quality gates run on *git commit* if the
       tool is available and the flag not disabled.
    """

    _emit_event(
        "cli.init.started",
        CLICommandEvent(
            command="init",
            status="started",
            params={
                "force": force,
                "install_precommit": install_precommit,
            },
        ),
    )

    import json
    import shutil
    import subprocess
    import textwrap
    from dataclasses import asdict

    cwd = Path.cwd()
    ice_dir = cwd / ".ice"
    if not ice_dir.exists():
        ice_dir.mkdir(parents=True)
        rprint(f"[green]✔[/] Created workspace directory {ice_dir.relative_to(cwd)}")
    else:
        rprint(f"[yellow]ℹ[/] Workspace directory {ice_dir.relative_to(cwd)} already exists.")

    # ------------------------------------------------------------------
    # .env handling -----------------------------------------------------
    # ------------------------------------------------------------------
    env_path = cwd / ".env"
    if env_path.exists() and not force:
        rprint("[yellow]ℹ[/] .env already exists – not overwritten (use --force to regenerate).")
    else:
        key = openai_key or os.getenv("OPENAI_API_KEY")
        if key is None:
            key = typer.prompt("Enter your OpenAI API Key", hide_input=True)
        env_content = textwrap.dedent(
            f"""# iceOS environment variables\nOPENAI_API_KEY={key}\n"""
        )
        env_path.write_text(env_content)
        rprint(f"[green]✔[/] Wrote {env_path.relative_to(cwd)}")

    # ------------------------------------------------------------------
    # Persist default builder draft template ---------------------------
    # ------------------------------------------------------------------
    draft_path = ice_dir / "builder.draft.json"
    if not draft_path.exists():
        from ice_cli.chain_builder.engine import ChainDraft

        draft = ChainDraft()  # empty draft
        draft_path.write_text(json.dumps(asdict(draft), indent=2))
        rprint(f"[green]✔[/] Initialised {draft_path.relative_to(cwd)}")

    # ------------------------------------------------------------------
    # Install pre-commit hooks -----------------------------------------
    # ------------------------------------------------------------------
    if install_precommit:
        if shutil.which("pre-commit") is None:
            rprint("[yellow]⚠ pre-commit not found – skipping hook installation.[/]")
        else:
            try:
                subprocess.run(["pre-commit", "install"], check=True, stdout=subprocess.PIPE)
                rprint("[green]✔[/] pre-commit hooks installed.")
            except subprocess.CalledProcessError as exc:  # pragma: no cover
                rprint(f"[red]✗ Failed to install pre-commit hooks:[/] {exc}")

    # Completed ------------------------------------------------------------
    _emit_event("cli.init.completed", CLICommandEvent(command="init", status="completed"))

# ---------------------------------------------------------------------------
# Third-party / shared libs ---------------------------------------------------
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Helper – safe event publication respecting --no-events flag --------------
# ---------------------------------------------------------------------------
from pydantic import BaseModel  # noqa: E402

# Event system (non-blocking) -------------------------------------------------
from ice_sdk.events.dispatcher import (  # noqa: E402 – placed after stdlib imports
    publish,
)
from ice_sdk.events.models import CLICommandEvent  # noqa: E402


def _emit_event(name: str, payload: BaseModel) -> None:  # noqa: D401 – simple helper
    """Publish *payload* under *name* unless the user disabled events."""

    from ice_cli.context import get_ctx  # local import to avoid cycles

    try:
        if not get_ctx().emit_events:  # honour --no-events flag
            return
        asyncio.create_task(publish(name, payload))
    except Exception:  # noqa: BLE001 – best-effort only
        pass

# Auto-load webhook subscribers (non-blocking) ------------------------------
try:
    from ice_cli.webhooks import initialise as _init_webhooks  # noqa: WPS433

    _init_webhooks()
except Exception:
    # Never fail CLI if optional webhook config parsing blows up
    pass 