from __future__ import annotations

from pathlib import Path

import click

TOOL_TEMPLATE = '''from __future__ import annotations

from typing import Any, Dict

from pydantic import Field

from ice_core.base_tool import ToolBase
from ice_core.unified_registry import register_tool_factory


class {class_name}(ToolBase):
    """{description}"""

    name: str = "{tool_name}"
    description: str = Field("{description}")

    async def _execute_impl(self, **kwargs: Any) -> Dict[str, Any]:
        # TODO: Implement tool logic using kwargs
        return {{"result": "{tool_name} executed"}}


def create_{tool_name}(**kwargs: Any) -> {class_name}:
    return {class_name}(**kwargs)


register_tool_factory("{tool_name}", "{module_path}:create_{tool_name}")
'''


def _to_snake(name: str) -> str:
    import re

    s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


@click.group()
def generate() -> None:
    """Code generators for tools and related components."""


@generate.command("tool")
@click.argument("name", type=str)
@click.option(
    "--out-dir",
    default="plugins/kits/tools/search",
    help="Output directory for the tool file (default CapabilityKit)",
)
@click.option("--description", default="Custom tool", help="Tool description")
def generate_tool(name: str, out_dir: str, description: str) -> None:  # noqa: D401
    """Scaffold a new ToolBase subclass and register its factory."""

    tool_name = _to_snake(name)
    class_name = "".join([p.capitalize() for p in tool_name.split("_")]) + "Tool"
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    module_rel = (
        f"plugins.kits.tools.search.{tool_name}"  # default kit; adjust per capability
    )
    file_path = out_path / f"{tool_name}.py"

    content = TOOL_TEMPLATE.format(
        class_name=class_name,
        tool_name=tool_name,
        description=description,
        module_path=module_rel,
    )
    file_path.write_text(content)
    click.echo(f"✅ Generated tool at {file_path}")
    click.echo("   Load via ICEOS_PLUGIN_MANIFESTS and plugins.v0 manifest.")
