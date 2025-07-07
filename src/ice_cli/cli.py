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

import json
import os
import re
import shutil
import subprocess

from rich import print as rprint

from ice_cli.apps import (
    chain_app,
    connect_app,
    flow_app,
    space_app,
    tool_app,
    update_app,
)
from ice_cli.commands.edit import edit_app as _edit_app
from ice_cli.commands.make import make_app as _make_app
from ice_cli.context import CLIContext
from ice_sdk.plugin_discovery import load_module_from_path
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

import asyncio
import sys
from pathlib import Path
from typing import Any, Callable

import click  # 3rd-party
import click.formatting as _cf  # noqa: WPS433,F401 – ensure available after click import
import typer

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
        "  ice tool create Echo --dir src/user_tools\n"
        "  ice run demo_chain.chain.py --watch\n"
        "  ice ls --json\n"
    ),
    context_settings={"max_content_width": 80},
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
            # (removed local re-import of _cf)
            try:
                import rich  # noqa: WPS433 – local import to avoid hard dep outside CLI

                rich.reconfigure(width=80)
            except Exception:  # pragma: no cover – fallback if Rich internals change
                pass
    except ValueError:
        os.environ["COLUMNS"] = "80"
        # (removed local re-import of _cf)
        _cf.FORCED_WIDTH = 80

    if verbose:
        logger.setLevel("DEBUG")
        import rich.traceback

        rich.traceback.install(show_locals=False)

    # If the user did not provide a sub-command, show the main --help and exit.
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())
        raise typer.Exit()


# ---------------------------------------------------------------------------
# Helper utilities ----------------------------------------------------------
# ---------------------------------------------------------------------------


def _snake_case(name: str) -> str:
    """Convert *PascalCase* or *camelCase* to ``snake_case``."""

    name = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", name)
    name = re.sub(r"([a-z\d])([A-Z])", r"\1_\2", name)
    return name.replace("-", "_").lower()


# ---------------------------------------------------------------------------
# Externalised sub-command groups -------------------------------------------
# ---------------------------------------------------------------------------

# The bulky *tool* command set now lives in a dedicated module under
# ``ice_cli.commands`` to keep this file lean and improve overall
# maintainability.  We import the Typer app _after_ instantiating the root
# application so the add_typer call can attach the group immediately.

# noqa comment to appease ruff E402 (import after app setup)

# Register the group under its original name – behaviour remains identical.
app.add_typer(tool_app, name="tool")
app.add_typer(_make_app, name="make", help="High-level scaffolding helpers")
app.add_typer(_edit_app, name="edit", help="Open nodes/tools in $EDITOR")


# ---------------------------------------------------------------------------
# Original in-file implementation removed – see ice_cli.commands.tool -------
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# ``run`` command -----------------------------------------------------------
# ---------------------------------------------------------------------------


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

    # ------------------------------------------------------------------
    # Iterate over ``chain.nodes`` which is a *dict[str, NodeConfig]* ---
    # ------------------------------------------------------------------
    # Earlier versions assumed ``chain.nodes`` was a list and attempted to
    # access ``n.id`` directly which raised ``AttributeError`` because the
    # iterator returned the *keys* (node IDs).  We now iterate over the
    # items ensuring we have access to both the ID and the node object.

    # Ensure all nodes are present even if they have no dependencies ----
    for node_id in chain.nodes.keys():  # type: ignore[attr-defined]
        lines.append(f"  {node_id}(( {node_id} ))")

    # Add edges for declared dependencies ------------------------------
    for node_id, node in chain.nodes.items():  # type: ignore[attr-defined]
        for dep in getattr(node, "dependencies", []):
            lines.append(f"  {dep} --> {node_id}")

    mermaid_code = "\n".join(lines)

    # Always print fenced block to console ------------------------------
    rprint("```mermaid\n" + mermaid_code + "\n```")

    # Respect environment flag: only launch preview when ICE_GRAPH_PREVIEW=1
    import os as _os  # local import to avoid module-level side effect

    if _os.getenv("ICE_GRAPH_PREVIEW", "0") != "1":
        return  # Do not open browser unless explicitly requested

    # Attempt auto-preview via mermaid-cli ------------------------------
    mmdc_path = shutil.which("mmdc")  # NB: binary name of mermaid-cli
    if mmdc_path is None:
        rprint(
            "[yellow]ℹ Install 'mermaid-cli' (npm i -g @mermaid-js/mermaid-cli) for graph preview.[/]"
        )
        return

    try:
        with tempfile.TemporaryDirectory() as tmp:
            md_path = Path(tmp) / "graph.mmd"
            svg_path = Path(tmp) / "graph.svg"
            md_path.write_text(mermaid_code)
            subprocess.run(
                [mmdc_path, "-i", str(md_path), "-o", str(svg_path)],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            webbrowser.open(svg_path.as_uri())
            rprint("[green]✔[/] Opened graph preview in browser.")
    except Exception as exc:  # pragma: no cover – best-effort preview
        rprint(f"[yellow]⚠ Failed to generate preview:[/] {exc}")


# ---------------------------------------------------------------------------
# ``ls`` – top-level alias (shortcut) ---------------------------------------
# ---------------------------------------------------------------------------


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
# SDK command group is now housed in *ice_cli.commands.sdk* to keep the
# root CLI lightweight.  We import and re-export it here for backwards
# compatibility with code/tests that might reference `ice_cli.cli.sdk_app`.
# ------------------------------------------------------------------

# Re-export for backwards compat -------------------------------------------------
from ice_cli.commands.sdk import sdk_app as sdk_app  # noqa: E402,F401

# Mount first-level sub-apps ------------------------------------------------------

app.add_typer(sdk_app, name="sdk")
app.add_typer(chain_app, name="chain", help="Manage ScriptChain workflows")

# Prompt engineering
try:
    from ice_cli.commands.prompt import prompt_app

    app.add_typer(prompt_app, name="prompt", help="Prompt engineering utilities")
except Exception as exc:  # pragma: no cover
    import logging as _logging

    _logging.getLogger(__name__).debug("Failed to load prompt commands: %s", exc)

# Node utilities
from ice_cli.apps import node_app as _node_app

app.add_typer(_node_app, name="node", help="Node utilities")

# Edge helpers
app.add_typer(connect_app, name="connect", help="Manage edges between nodes")

# ---------------------------------------------------------------------------
# Chain management commands (new) -------------------------------------------
# ---------------------------------------------------------------------------

try:
    from ice_cli.apps import chain_app

    app.add_typer(chain_app, name="chain", help="Manage ScriptChain workflows")

    # Prompt engineering commands ---------------------------------------------
    try:
        from ice_cli.commands.prompt import prompt_app

        app.add_typer(prompt_app, name="prompt", help="Prompt engineering utilities")

        # Node utilities
        from ice_cli.commands.node import node_app

        app.add_typer(node_app, name="node", help="Node utilities")
    except Exception as exc:  # pragma: no cover
        import logging as _logging

        _logging.getLogger(__name__).debug("Failed to load prompt commands: %s", exc)
except Exception as exc:  # pragma: no cover – safe fallback if optional deps missing
    # Do not fail import if chain_app has issues; simply warn in debug.
    import logging as _logging

    _logging.getLogger(__name__).debug("Failed to load chain commands: %s", exc)

# NOTE: The original inline implementation has been extracted; any residual
# helper functions below are retained only for historical reference and are
# wrapped in an `if False:` guard so they do not register duplicate commands.

# Dummy block to satisfy indentation for legacy guard
if False:  # pragma: no cover – legacy code path
    pass

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
):
    """Generate a new ``*.tool.py`` module using the same template as `ice tool new`."""

    target_path = directory / f"{_snake_case(name)}.tool.py"

    if target_path.exists() and not force:
        rprint(
            f"[red]Error:[/] File {target_path} already exists. Use --force to overwrite."
        )
        raise typer.Exit(code=1)

    # Import the canonical template generator from the *tool* command module
    from ice_cli.commands.tool import (
        _create_tool_template as _tpl,  # local import to avoid heavy dependency at module load
    )

    def _pretty_path(p: Path) -> str:
        try:
            return str(p.relative_to(Path.cwd()))
        except ValueError:
            return str(p)

    try:
        target_path.write_text(_tpl(name))
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
        rprint(
            f"[red]Error:[/] invalid --type '{type_}'. Must be one of: {', '.join(sorted(allowed))}."
        )
        raise typer.Exit(1)

    file_suffix_map = {
        "ai": ".ainode.yaml",
        "tool": ".toolnode.yaml",
        "agent": ".agent.yaml",
    }

    filename = _snake_case(name) + file_suffix_map[type_lower]
    target_path = directory / filename

    if target_path.exists() and not force:
        rprint(
            f"[red]Error:[/] File {target_path} already exists. Use --force to overwrite."
        )
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
    builder: bool = typer.Option(
        False, "--builder", "-b", help="Run interactive Chain Builder"
    ),
    nodes: int | None = typer.Option(
        None, "--nodes", "-n", min=1, help="Total nodes for the interactive builder"
    ),
):
    """Generate a minimal Python file that constructs & executes a ScriptChain."""

    snake = _snake_case(name)
    target_path = directory / f"{snake}.chain.py"

    if target_path.exists() and not force:
        rprint(
            f"[red]Error:[/] File {target_path} already exists. Use --force to overwrite."
        )
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

        # Show --graph preview (Mermaid) right after builder finishes
        try:
            import shutil
            import subprocess
            import tempfile
            import webbrowser

            from rich.panel import Panel
            from rich.table import Table

            rprint(Panel(mermaid, title="Mermaid Graph", border_style="cyan"))

            # Attempt auto-preview via mermaid-cli (mmdc)
            mmdc_path = shutil.which("mmdc")
            import os as _os  # local import to avoid module-level side effect

            if mmdc_path is not None:
                # Only open browser if ICE_GRAPH_PREVIEW=1
                if _os.getenv("ICE_GRAPH_PREVIEW", "0") == "1":
                    with tempfile.TemporaryDirectory() as tmp:
                        md_path = Path(tmp) / "graph.mmd"
                        svg_path = Path(tmp) / "graph.svg"
                        md_path.write_text(mermaid)
                        subprocess.run(
                            [mmdc_path, "-i", str(md_path), "-o", str(svg_path)],
                            check=True,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                        )
                        webbrowser.open(svg_path.as_uri())
                        rprint("[green]✔[/] Opened graph preview in browser.")
                else:
                    rprint(
                        "[yellow]ℹ Skipping browser preview (set ICE_GRAPH_PREVIEW=1 or use --preview to enable).[/]"
                    )
            else:
                rprint(
                    "[yellow]ℹ Install 'mermaid-cli' (npm i -g @mermaid-js/mermaid-cli) for graph preview.[/]"
                )

            table = Table(title="Node Summary", show_lines=True)
            table.add_column("#", justify="right")
            table.add_column("Type")
            table.add_column("Name")
            table.add_column("Deps")

            for idx, node in enumerate(draft.nodes):
                deps = ", ".join(node.get("dependencies", [])) or "-"
                table.add_row(
                    str(idx), node.get("type", ""), node.get("name", ""), deps
                )

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
            '@function_tool(name_override="echo")\n'
            "async def _echo_tool(ctx: ToolContext, text: str) -> dict[str, Any]:  # type: ignore[override]\n"
            '    """Return the *text* argument as-is so we can observe flow output."""\n'
            '    return {"echo": text}\n\n'
            "echo_tool = _echo_tool  # mypy happy cast\n\n"
            "# ---------------------------------------------------------------------------\n"
            "# Node list ---------------------------------------------------------------\n"
            "# ---------------------------------------------------------------------------\n\n"
            "nodes: List[ToolNodeConfig] = [\n"
            '    ToolNodeConfig(id="start", type="tool", name="echo_start", tool_name="echo", tool_args={"text": "hello"}),\n'
            "]\n\n"
            "# ---------------------------------------------------------------------------\n"
            "# Entry-point -------------------------------------------------------------\n"
            "# ---------------------------------------------------------------------------\n\n"
            "async def main() -> None:\n"
            '    chain = ScriptChain(nodes=nodes, tools=[echo_tool], name="sample-chain")\n'
            "    result = await chain.execute()\n"
            "    print(result.output)\n\n"
            'if __name__ == "__main__":\n'
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

# ---------------------------------------------------------------------------
# Demo – Google Search -------------------------------------------------------
# ---------------------------------------------------------------------------


from ice_sdk.copilot.cli import (  # noqa: E402 – imported late to avoid heavy deps
    copilot_app,
)

app.add_typer(copilot_app, name="copilot")

# ---------------------------------------------------------------------------
# New top-level user-friendly commands (PR-1 of CLI refactor) -----------------
# ---------------------------------------------------------------------------

# NOTE: These wrappers intentionally live **after** the original sdk_* helper
# functions are defined, so we can re-use them without duplication or circular
# imports. They provide a simpler noun-verb UX described in the roadmap:
#   ice space create <name>
#   ice chain create <name>
#   ice node  create <name>

import shutil
from pathlib import Path

# Workspace ("space") --------------------------------------------------------
space_app = typer.Typer(
    add_completion=False, help="Manage iceOS workspaces (aka 'spaces')"
)


@space_app.command(
    "create", help="Create a new workspace directory and initialise defaults"
)
def space_create(  # noqa: D401 – simple CLI
    name: str = typer.Argument(..., help="Directory name for the new space"),
    directory: Path = typer.Option(
        Path.cwd(),
        "--dir",
        "-d",
        dir_okay=True,
        file_okay=False,
        exists=True,
        writable=True,
        help="Parent directory in which to create the space",
    ),
    force: bool = typer.Option(
        False, "--force", "-f", help="Overwrite if directory already exists"
    ),
):
    """Scaffold a workspace folder with a default *chains.toml* manifest.

    The operation is intentionally minimalist – it only ensures a clean folder
    and an empty `chains.toml` so newcomers can immediately add chains.
    """

    dest = directory / name
    if dest.exists():
        if not force:
            rprint(
                f"[red]✗ Directory '{dest}' already exists – use --force to overwrite.[/]"
            )
            raise typer.Exit(code=1)
        shutil.rmtree(dest)

    dest.mkdir(parents=True, exist_ok=True)
    (dest / "chains.toml").write_text("# iceOS chains manifest\n\n")
    rprint(f"[green]✔[/] Created space at {dest}")


app.add_typer(space_app, name="space", rich_help_panel="Workspace")

# Chain wrappers -------------------------------------------------------------
chain_app = typer.Typer(add_completion=False, help="Create and manage ScriptChains")

chain_app.command("create")(sdk_create_chain)  # type: ignore[arg-type]


@chain_app.command("ls", help="List *.chain.py files in current directory")
def chain_ls():
    chains = sorted(Path.cwd().rglob("*.chain.py"))
    if not chains:
        rprint("[yellow]No chains found.[/]")
        return
    for c in chains:
        rprint(f"• {c.relative_to(Path.cwd())}")


@chain_app.command("delete", help="Delete a ScriptChain file")
def chain_delete(
    path: Path = typer.Argument(..., exists=True, dir_okay=False, readable=True),
    force: bool = typer.Option(False, "--force", "-f", help="Delete without prompt"),
):
    if not force and not typer.confirm(f"Delete {path}?", abort=True):
        return
    path.unlink()
    rprint(f"[green]✔[/] Deleted {path.relative_to(Path.cwd())}")


@chain_app.command("edit", help="Open a ScriptChain in $EDITOR")
def chain_edit(
    path: Path = typer.Argument(..., exists=True, dir_okay=False, readable=True),
):
    editor = os.getenv("EDITOR") or ("code" if shutil.which("code") else "nano")
    try:
        subprocess.run([editor, str(path)])
    except Exception as exc:
        rprint(f"[red]Failed to open editor:[/] {exc}")


@chain_app.command("diagram", help="Print Mermaid graph for a ScriptChain")
def chain_diagram(
    path: Path = typer.Argument(..., exists=True, dir_okay=False, readable=True),
    open_preview: bool = typer.Option(
        False, "--open", help="Open SVG preview if mermaid-cli is installed"
    ),
):
    try:
        module = load_module_from_path(path)
    except Exception as exc:
        rprint(f"[red]Unable to import {path}: {exc}[/]")
        raise typer.Exit(1)

    chain_obj = getattr(module, "chain", None)
    if chain_obj is None and hasattr(module, "get_chain"):
        chain_obj = module.get_chain()
    if chain_obj is None:
        rprint("[red]No ScriptChain object found in module.[/]")
        raise typer.Exit(1)

    if open_preview:
        os.environ["ICE_GRAPH_PREVIEW"] = "1"
    from ice_cli.utils import _print_mermaid_graph

    _print_mermaid_graph(chain_obj)


# Node edit/delete ----------------------------------------------------------


@node_app.command("edit", help="Open a node YAML in $EDITOR")
def node_edit(
    node_file: Path = typer.Argument(..., exists=True, dir_okay=False, readable=True),
):
    editor = os.getenv("EDITOR") or ("code" if shutil.which("code") else "nano")
    subprocess.run([editor, str(node_file)])


@node_app.command("delete", help="Delete a node YAML (and optional sibling .py)")
def node_delete(
    node_file: Path = typer.Argument(..., exists=True, dir_okay=False),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
    remove_py: bool = typer.Option(
        False, "--impl", help="Also remove sibling .py file"
    ),
):
    if not force and not typer.confirm(f"Delete {node_file}?", abort=True):
        return
    node_file.unlink()
    if remove_py:
        py_path = node_file.with_suffix(".py")
        if py_path.exists():
            py_path.unlink()
    rprint(f"[green]✔[/] Deleted {node_file}")


# ---------------------------------------------------------------------------
# Connect app ---------------------------------------------------------------
# ---------------------------------------------------------------------------
connect_app = typer.Typer(
    add_completion=False, help="Add or remove edges between nodes in a ScriptChain"
)


def _load_chain_module(chain_path: Path):  # helper
    return load_module_from_path(chain_path)


@connect_app.command("add")
def connect_add(
    chain: Path = typer.Argument(..., exists=True, dir_okay=False, readable=True),
    src: str = typer.Argument(..., help="Source node id"),
    dst: str = typer.Argument(..., help="Destination node id"),
):
    """Very naive: appends a python line 'chain.add_edge("src", "dst")' at EOF."""
    line = f'\n# edge added by CLI\nchain.add_edge("{src}", "{dst}")\n'
    with chain.open("a", encoding="utf-8") as f:
        f.write(line)
    rprint(f"[green]✔[/] Added edge {src} -> {dst} in {chain}")


@connect_app.command("ls")
def connect_ls(
    chain: Path = typer.Argument(..., exists=True, dir_okay=False, readable=True),
):
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
    """Remove a previously-added edge call `chain.add_edge(src, dst)` from file.

    Utilises *ast* parsing so we don't corrupt unrelated code.  It rewrites the
    file without the matching expression statement.
    """

    import ast
    from typing import cast

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
            and all(
                isinstance(a, ast.Constant) and isinstance(a.value, str)
                for a in node.value.args
            )
            and cast(ast.Constant, node.value.args[0]).value == src
            and cast(ast.Constant, node.value.args[1]).value == dst
        ):
            removed = True
            continue  # skip
        new_body.append(node)

    if not removed:
        rprint("[yellow]No matching edge found – nothing to remove.[/]")
        return

    tree.body = new_body  # type: ignore[attr-defined]
    new_source = ast.unparse(tree)
    chain.write_text(new_source)
    rprint(f"[green]✔[/] Removed edge {src} -> {dst} in {chain}")


# Flow diagram --------------------------------------------------------------

flow_app = typer.Typer(
    add_completion=False, help="Organise chains into higher-level flows"
)

import json
from datetime import datetime

_FLOW_EXT = ".flow.json"


def _flow_file(name: str) -> Path:  # helper
    p = Path(name)
    if p.suffix == _FLOW_EXT:
        return p
    return Path.cwd() / f"{name}{_FLOW_EXT}"


@flow_app.command("create")
def flow_create(
    name: str = typer.Argument(..., help="Flow name"),
    description: str = typer.Option("", "--description", "-d"),
    chain: list[str] = typer.Option([], "--chain", "-c"),
    force: bool = typer.Option(False, "--force", "-f"),
):
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
    import asyncio as _asyncio

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
        try:
            mod = load_module_from_path(chain_path)
        except Exception as exc:
            rprint(f"[red]Unable to import {chain_path}: {exc}[/]")
            continue
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
    name: str = typer.Argument(...), force: bool = typer.Option(False, "--force", "-f")
):
    path = _flow_file(name)
    if not path.exists():
        rprint(f"[red]Flow {name} not found.[/]")
        raise typer.Exit(1)
    if not force and not typer.confirm(f"Delete {path}?", abort=True):
        return
    path.unlink()
    rprint(f"[green]✔[/] Deleted {path}")


app.add_typer(flow_app, name="flow", rich_help_panel="Flows")

# ---------------------------------------------------------------------------
# Run alias fallback ---------------------------------------------------------
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Doctor & Update apps (restored) -------------------------------------------
# ---------------------------------------------------------------------------

quality_app = typer.Typer(add_completion=False, help="Quality checks")


@quality_app.command("lint")
def doctor_lint():
    subprocess.run(["ruff", "src", "--fix"], check=False)


@quality_app.command("type")
def doctor_type():
    subprocess.run(["pyright"], check=False)


@quality_app.command("test")
def doctor_test():
    subprocess.run(["pytest", "-q"], check=False)


@quality_app.command("all")
def doctor_all():
    doctor_lint()
    doctor_type()
    doctor_test()


app.add_typer(quality_app, name="doctor", rich_help_panel="Quality")

update_app = typer.Typer(add_completion=False, help="Self-update helpers")


@update_app.command("templates")
def update_templates():
    rprint("[yellow]TODO:[/] Download latest templates from remote repo.")


app.add_typer(update_app, name="update", rich_help_panel="Maintenance")
