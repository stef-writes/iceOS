"""CLI commands for creating and managing blueprints.

Keeps UX simple: scaffold a minimal valid blueprint JSON that passes server
validation and can be executed, with options to customize name and a single
tool node.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

import click

_MINIMAL_BLUEPRINT: Dict[str, Any] = {
    "schema_version": "1.2.0",
    "metadata": {"draft_name": "minimal_blueprint"},
    "nodes": [
        {
            "id": "n1",
            "type": "tool",
            "name": "echo_tool",
            "tool_name": "echo_tool",  # expects a trivial tool to exist or to be edited by user
            "dependencies": [],
            "input_schema": {
                "type": "object",
                "properties": {"text": {"type": "string"}},
            },
            "output_schema": {
                "type": "object",
                "properties": {"reply": {"type": "string"}},
            },
        }
    ],
}


@click.group(help="Blueprint utilities")
def blueprints() -> None:  # noqa: D401
    """CLI group registered under *ice* root."""


@blueprints.command("new")
@click.option(
    "--name", default="minimal_blueprint", help="Blueprint draft_name metadata"
)
@click.option(
    "--output",
    type=click.Path(dir_okay=False, path_type=Path),
    default=Path.cwd() / "Blueprint.min.json",
    show_default=True,
)
def blueprint_new(name: str, output: Path) -> None:  # noqa: D401
    """Create a minimal, valid blueprint JSON file."""
    bp = json.loads(json.dumps(_MINIMAL_BLUEPRINT))
    bp["metadata"]["draft_name"] = name
    output.write_text(json.dumps(bp, indent=2))
    click.echo(f"✅ Created {output}")
