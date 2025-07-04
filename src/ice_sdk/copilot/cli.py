"""CLI entry-point for the **ICE Copilot** (Frosty).

This command group plugs into the main ``ice`` CLI and provides an interactive
chat session that uses the :class:`ice_sdk.agents.copilot.IceCopilot` agent
under the hood.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import typer
import yaml
from rich import print as rprint

from ice_sdk.copilot import IceCopilot

# Typer sub-application so the root CLI can mount it via *add_typer* ---------

copilot_app = typer.Typer(
    help="Interactive ICE Copilot – let Frosty co-design your flow"
)


@copilot_app.command("chat", help="Start an interactive Copilot chat session")
def chat(  # noqa: D401 – CLI callback
    goal: str | None = typer.Option(
        None,
        "--goal",
        "-g",
        help="Optional initial goal to seed the conversation",
    ),
):
    """Launch an interactive Socratic conversation in the terminal."""

    agent = IceCopilot()
    context_store = agent.context  # TestContextStore instance

    rprint("❄️  [bold cyan]ICE Copilot engaged[/] – type 'exit' to quit.")

    with context_store.new_session() as session:  # type: ignore[arg-type]
        if goal:
            session.add_message("user", goal)

        while True:
            # Generate assistant response -----------------------------------
            response = agent.generate_response(session)  # type: ignore[arg-type]
            rprint(f"[cyan]Copilot:[/] {response.text}")

            if not getattr(response, "requires_input", False):
                break

            # Prompt user ---------------------------------------------------
            user_input = typer.prompt("You")
            if user_input.lower() in {"exit", "quit", "q"}:
                rprint("[green]👋  Exiting Copilot chat.")
                break

            session.add_message("user", user_input)


@copilot_app.command("create-agent", help="Generate new agent spec via Copilot")
def create_agent(
    goal: str = typer.Argument(..., help="Agent's primary objective"),
    output: Path = typer.Option(
        Path.cwd() / "agent_spec.yaml",
        "--out",
        "-o",
        help="Where to save generated YAML",
    ),
):
    copilot = IceCopilot()
    spec = asyncio.run(copilot.generate_agent_spec(goal))  # New SDK method
    output.write_text(yaml.dump(spec))
