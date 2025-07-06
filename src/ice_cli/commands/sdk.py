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

        # --------------------------------------------------------------
        # Auto-register alias in chains.toml ---------------------------
        # --------------------------------------------------------------
        try:
            from pathlib import Path as _Path

            manifest = _Path.cwd() / "chains.toml"
            alias = _snake_case(name)  # use snake_case filename as default alias

            # Compute path relative to manifest for portability
            rel_path = target_path.relative_to(manifest.parent)

            alias_line = f'{alias} = "{rel_path}"'

            if not manifest.exists():
                manifest.write_text("[ice.chains]\n" + alias_line)
            else:
                txt = manifest.read_text()
                if alias_line.strip() not in txt:
                    if "[ice.chains]" in txt:
                        lines = txt.splitlines(keepends=True)
                        idx = next(
                            i
                            for i, line in enumerate(lines)
                            if line.strip() == "[ice.chains]"
                        )
                        # find insertion point – before next header or EOF
                        insert = idx + 1
                        while insert < len(lines) and not lines[insert].startswith("["):
                            insert += 1
                        lines.insert(insert, alias_line)
                        manifest.write_text("".join(lines))
                    else:
                        manifest.write_text(txt + "\n[ice.chains]\n" + alias_line)

                # Inform user ------------------------------------------------
            rprint(
                f"[green]✔[/] Added alias '{alias}' to chains.toml – try: ice run {alias}"
            )
        except Exception as exc:  # noqa: BLE001 – non-fatal
            rprint(f"[yellow]⚠ Could not update chains.toml:[/] {exc}")
    except Exception as exc:
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

        # --------------------------------------------------------------
        # Auto-register alias in chains.toml ---------------------------
        # --------------------------------------------------------------
        try:
            from pathlib import Path as _Path

            manifest = _Path.cwd() / "chains.toml"
            alias = _snake_case(name)  # use snake_case filename as default alias

            # Compute path relative to manifest for portability
            rel_path = target_path.relative_to(manifest.parent)

            alias_line = f'{alias} = "{rel_path}"'

            if not manifest.exists():
                manifest.write_text("[ice.chains]\n" + alias_line)
            else:
                txt = manifest.read_text()
                if alias_line.strip() not in txt:
                    if "[ice.chains]" in txt:
                        lines = txt.splitlines(keepends=True)
                        idx = next(i for i, line in enumerate(lines) if line.strip() == "[ice.chains]")
                        # find insertion point – before next header or EOF
                        insert = idx + 1
                        while insert < len(lines) and not lines[insert].startswith("["):
                            insert += 1
                        lines.insert(insert, alias_line)
                        manifest.write_text("".join(lines))
                    else:
                        manifest.write_text(txt + "\n[ice.chains]\n" + alias_line)

                # Inform user ------------------------------------------------
            rprint(f"[green]✔[/] Added alias '{alias}' to chains.toml – try: ice run {alias}")
        except Exception as exc:  # noqa: BLE001 – non-fatal
            rprint(f"[yellow]⚠ Could not update chains.toml:[/] {exc}")
    except Exception as exc:
        rprint(f"[red]✗ Failed to write template:[/] {exc}")
        raise typer.Exit(code=1)


# ---------------------------------------------------------------------------
# Chain helpers -------------------------------------------------------------
# ---------------------------------------------------------------------------


def _load_chain_from_py(path: Path):  # noqa: D401 – utility
    """Import *path* and return first ScriptChain found (or *None*)."""

    import sys as _sys
    from importlib import import_module as _import_module
    from importlib import util as _util

    from ice_orchestrator.script_chain import ScriptChain  # noqa: E402 – local import

    if not path.exists():
        raise FileNotFoundError(path)

    module_name = path.stem.replace(".", "_")

    # Ensure idempotent reload ------------------------------------------------
    if module_name in _sys.modules:
        del _sys.modules[module_name]

    if str(path.parent) not in _sys.path:
        _sys.path.insert(0, str(path.parent))

    try:
        module = _import_module(module_name)
    except ModuleNotFoundError:
        spec = _util.spec_from_file_location(module_name, path)
        if spec and spec.loader:
            module = _util.module_from_spec(spec)
            _sys.modules[module_name] = module
            spec.loader.exec_module(module)  # type: ignore[arg-type]
        else:
            raise

    chain = None
    if hasattr(module, "chain") and isinstance(getattr(module, "chain"), ScriptChain):
        chain = getattr(module, "chain")
    elif hasattr(module, "get_chain") and callable(getattr(module, "get_chain")):
        maybe = getattr(module, "get_chain")()
        if isinstance(maybe, ScriptChain):
            chain = maybe

    return chain


# ---------------------------------------------------------------------------
# chain-validate ------------------------------------------------------------
# ---------------------------------------------------------------------------


@sdk_app.command("chain-validate", help="Validate a ScriptChain declared in a Python file")
def sdk_chain_validate(
    file: Path = typer.Argument(
        ..., exists=True, file_okay=True, dir_okay=False, readable=True
    ),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output JSON"),
):
    """Static validation for chain definitions.

    Returns exit code 0 when no errors found, otherwise prints errors and exits
    with code 1 so CI pipelines can fail on invalid chains.
    """

    from rich import print as _rprint

    chain = _load_chain_from_py(file)
    if chain is None:
        _rprint(f"[red]Error:[/] No ScriptChain found in {file}.")
        raise typer.Exit(code=1)

    errors = []
    if hasattr(chain, "validate_chain") and callable(chain.validate_chain):
        errors = chain.validate_chain()  # type: ignore[assignment]
    else:
        _rprint("[yellow]⚠ Chain has no validate_chain() method – skipping checks.[/]")

    if errors:
        if json_output:
            import json as _json

            _rprint(_json.dumps({"errors": errors}, indent=2))
        else:
            _rprint("[red]Validation errors:[/]")
            for err in errors:
                _rprint(f" • {err}")
        raise typer.Exit(code=1)

    _rprint("[green]✔ Chain is valid.[/]")
    raise typer.Exit(code=0) 
