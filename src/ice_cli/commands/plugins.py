"""CLI commands for plugins manifest operations."""

from __future__ import annotations

import json
import pathlib
from typing import List

import click

from ice_core.exceptions import RegistryError
from ice_core.models.enums import NodeType
from ice_core.models.plugins import ComponentEntry, PluginsManifest
from ice_core.registry import registry

# ---------------------------------------------------------------------------
# Helper --------------------------------------------------------------------
# ---------------------------------------------------------------------------


def _collect_components() -> List[ComponentEntry]:
    """Collect currently registered components and convert to manifest entries.

    NOTE: MVP exports only tools; agents & workflows can be added once the
    registry tracks them more explicitly at import-time.
    """
    entries: List[ComponentEntry] = []

    # Tools -----------------------------------------------------------------
    for name in registry.list_tools():
        tool = registry.get_instance(NodeType.TOOL, name)
        cls = tool.__class__
        import_path = f"{cls.__module__}:{cls.__name__}"
        entries.append(
            ComponentEntry(
                node_type="tool",
                name=name,
                import_path=import_path,  # type: ignore[arg-type]
            )
        )

    # Agents (metadata only) -------------------------------------------------
    for name, path in registry.available_agents():
        entries.append(
            ComponentEntry(
                node_type="agent",
                name=name,
                import_path=path,  # type: ignore[arg-type]
            )
        )

    # Workflows --------------------------------------------------------------
    for name, _ in registry.available_chains():
        # We cannot reliably resolve import path; skip in MVP
        continue

    return entries


# ---------------------------------------------------------------------------
# Commands ------------------------------------------------------------------
# ---------------------------------------------------------------------------


@click.group()
def plugins() -> None:
    """Plugin manifest operations."""


@plugins.command("export")
@click.argument("output", type=click.Path(dir_okay=False))
def export_manifest(output: str) -> None:
    """Export current registry to a plugins.v0 manifest JSON file."""
    out_path = pathlib.Path(output)
    entries = sorted(_collect_components(), key=lambda c: (c.node_type, c.name))
    manifest = PluginsManifest(components=entries)
    out_path.write_text(
        json.dumps(manifest.model_dump(mode="json", by_alias=True), indent=2)
    )
    click.echo(f"✅ Wrote manifest with {len(entries)} components → {out_path}")


@plugins.command("lint")
@click.argument("manifest_path", type=click.Path(exists=True, dir_okay=False))
def lint_manifest(manifest_path: str) -> None:
    """Lint a manifest – fails (exit 1) if invalid or components missing."""
    import sys

    try:
        count = registry.load_plugins(manifest_path, allow_dynamic=False)
        click.echo(f"✅ Manifest valid, {count} components registered (metadata only)")
    except (RegistryError, ValueError) as exc:
        click.echo(f"❌ Lint failed: {exc}", err=True)
        sys.exit(1)
