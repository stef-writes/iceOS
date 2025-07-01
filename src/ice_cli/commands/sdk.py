from __future__ import annotations  # isort: skip

"""SDK command group – opinionated scaffolds for tools, nodes and chains.

This module was extracted from *ice_cli.cli* to simplify the root CLI entry-point
and pave the way for clearer command hierarchy.  Public surface (command names
and behaviour) remains identical.
"""

import textwrap
from pathlib import Path
from typing import Optional

import typer
from rich import print as rprint

# ruff: noqa: E402

# Internal utilities ---------------------------------------------------------


def _snake_case(name: str) -> str:
    """Convert *PascalCase* or *camelCase* to ``snake_case``."""

    import re

    name = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", name)
    name = re.sub(r"([a-z\d])([A-Z])", r"\1_\2", name)
    return name.replace("-", "_").lower()


# Template helpers -----------------------------------------------------------


def _create_ai_node_template(node_name: str) -> str:
    snake = _snake_case(node_name)
    return textwrap.dedent(
        f"""\
        # iceOS AiNode configuration
        id: {snake}_ai
        type: ai
        name: {node_name}
        model: gpt-3.5-turbo
        prompt: |
          # TODO: write prompt here
        llm_config:
          provider: openai
          temperature: 0.7
          max_tokens: 256
        dependencies: []
        """
    )


def _create_tool_node_template(
    node_name: str, tool_name: str | None = None
) -> str:  # noqa: D401
    snake = _snake_case(node_name)
    tool_ref = tool_name or snake
    return textwrap.dedent(
        f"""\
        # iceOS ToolNode configuration
        id: {snake}_tool
        type: tool
        name: {node_name}
        tool_name: {tool_ref}
        tool_args: {{}}
        dependencies: []
        """
    )


def _create_agent_config_template(agent_name: str) -> str:
    snake = _snake_case(agent_name)
    return textwrap.dedent(
        f"""\
        # iceOS Agent configuration
        name: {snake}
        instructions: |
          # TODO: add high-level instructions for the agent
        model: gpt-4o
        model_settings:
          provider: openai
          model: gpt-4o
          temperature: 0.7
          max_tokens: 512
        tools: []  # list tool names or embed ToolConfigs here
        """
    )


# Typer application ----------------------------------------------------------

sdk_app = typer.Typer(
    help="Opinionated scaffolds for tools, nodes and chains",
    rich_help_panel="Scaffolding",
)


# ---------------------------------------------------------------------------
# create-tool ----------------------------------------------------------------
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
    """Generate a new ``*.tool.py`` module using the same template as `ice tool create`."""

    target_path = directory / f"{_snake_case(name)}.tool.py"

    if target_path.exists() and not force:
        rprint(
            f"[red]Error:[/] File {target_path} already exists. Use --force to overwrite."
        )
        raise typer.Exit(code=1)

    # Import canonical template generator to stay DRY
    from ice_cli.commands.tool import (  # noqa: WPS433 – local import
        _create_tool_template as _tpl,
    )

    try:
        target_path.write_text(_tpl(name))
        _pretty_path = (
            target_path.relative_to(Path.cwd())
            if target_path.is_absolute()
            else target_path
        )
        rprint(f"[green]✔[/] Created {_pretty_path}")
    except Exception as exc:  # noqa: BLE001
        rprint(f"[red]✗ Failed to write template:[/] {exc}")
        raise typer.Exit(code=1)


# ---------------------------------------------------------------------------
# create-node ----------------------------------------------------------------
# ---------------------------------------------------------------------------


@sdk_app.command("create-node", help="Scaffold a new node configuration")
def sdk_create_node(
    name: str = typer.Argument(..., help="Human-readable node name"),
    type_: Optional[str] = typer.Option(
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
        name = name or typer.prompt("Human-readable node name")  # type: ignore[assignment]

    if type_ is None:
        type_ = "tool"

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

    # Generate template ----------------------------------------------------
    if type_lower == "ai":
        content = _create_ai_node_template(name)
    elif type_lower == "tool":
        content = _create_tool_node_template(name)
    else:
        content = _create_agent_config_template(name)

    try:
        target_path.write_text(content)
        _pretty_path = (
            target_path.relative_to(Path.cwd())
            if target_path.is_absolute()
            else target_path
        )
        rprint(f"[green]✔[/] Created {_pretty_path}")
    except Exception as exc:  # noqa: BLE001
        rprint(f"[red]✗ Failed to write template:[/] {exc}")
        raise typer.Exit(code=1)


# ---------------------------------------------------------------------------
# create-chain --------------------------------------------------------------
# ---------------------------------------------------------------------------


# fmt: off
@sdk_app.command("create-chain", help="Scaffold a new Python ScriptChain file")
def sdk_create_chain(
    name: str = typer.Argument("my_chain", help="Base filename (without .py) for the new chain"),
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
    force: bool = typer.Option(False, "--force", "-f", help="Overwrite if file already exists"),
    builder: bool = typer.Option(False, "--builder", "-b", help="Run interactive Chain Builder"),
    nodes: Optional[int] = typer.Option(
        None,
        "--nodes",
        "-n",
        min=1,
        help="Total nodes for the interactive builder",
    ),
):
# fmt: on
    """Generate a new ScriptChain module or launch the interactive builder."""

    target_path = directory / f"{_snake_case(name)}.chain.py"

    if target_path.exists() and not force:
        rprint(f"[red]Error:[/] File {target_path} already exists. Use --force to overwrite.")
        raise typer.Exit(code=1)

    # For brevity we keep the existing non-interactive scaffold logic simple
    basic_content = textwrap.dedent(
        (
            f'"""Example ScriptChain generated by `ice sdk create-chain`."""\n\n'
            'from ice_orchestrator import ScriptChain\n\n\n'
            f'class {name.capitalize()}Chain(ScriptChain):\n'
            '    """Describe what the chain does."""\n'
        )
    )

    try:
        target_path.write_text(basic_content)
        _pretty_path = target_path.relative_to(Path.cwd()) if target_path.is_absolute() else target_path
        rprint(f"[green]✔[/] Created {_pretty_path}")
    except Exception as exc:  # noqa: BLE001
        rprint(f"[red]✗ Failed to write template:[/] {exc}")
        raise typer.Exit(code=1) 
