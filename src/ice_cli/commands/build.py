"""CLI command: ice build – compile DSL/YAML to validated Blueprint JSON."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import click


@click.command("build")
@click.argument("source", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option(
    "--output",
    type=click.Path(dir_okay=False, path_type=Path),
    default=None,
    help="Output path for Blueprint JSON (defaults to <source>.json)",
)
def cli_build(source: Path, output: Optional[Path]) -> None:  # noqa: D401
    """Compile an authoring artifact (Python DSL or YAML) to Blueprint JSON.

    Supported inputs
    ----------------
    - Python module/file that constructs a Blueprint using ice_builder DSL.
      The file must expose a top-level `build()` function returning a
      `ice_core.models.mcp.Blueprint`.
    - YAML file (future). Currently not implemented.
    """

    # Resolve output path
    if output is None:
        output = source.with_suffix(source.suffix + ".json")

    # Python path: import and call build()
    if source.suffix in {".py"}:
        import importlib.util
        import sys

        spec = importlib.util.spec_from_file_location("_ice_build_module", str(source))
        if spec is None or spec.loader is None:  # pragma: no cover
            raise click.ClickException("Cannot import source module")
        module = importlib.util.module_from_spec(spec)
        sys.modules["_ice_build_module"] = module
        spec.loader.exec_module(module)  # type: ignore[assignment]

        if not hasattr(module, "build"):
            raise click.ClickException(
                "Source must define a build() function returning a Blueprint"
            )
        bp = module.build()  # type: ignore[no-any-return]
        try:
            payload = bp.model_dump(mode="json")  # pydantic
        except Exception as exc:  # noqa: BLE001
            raise click.ClickException(
                f"Invalid Blueprint returned by build(): {exc}"
            ) from exc
        output.write_text(json.dumps(payload, indent=2))
        click.echo(f"✅ Wrote {output}")
        return

    # YAML path: load minimal structure and validate as Blueprint
    if source.suffix in {".yaml", ".yml"}:
        import yaml

        from ice_core.models.mcp import Blueprint, NodeSpec

        try:
            data = yaml.safe_load(source.read_text())
        except Exception as exc:  # noqa: BLE001
            raise click.ClickException(f"Failed to parse YAML: {exc}") from exc

        if not isinstance(data, dict):
            raise click.ClickException("Top-level YAML must be a mapping")
        nodes = data.get("nodes")
        if not isinstance(nodes, list) or not nodes:
            raise click.ClickException("YAML must contain a non-empty 'nodes' list")

        try:
            node_specs = [NodeSpec.model_validate(n) for n in nodes]
            bp = Blueprint(
                nodes=node_specs,
                metadata=data.get("metadata", {}),
                schema_version=str(data.get("schema_version", "1.2.0")),
            )
        except Exception as exc:  # noqa: BLE001
            raise click.ClickException(f"Invalid YAML blueprint: {exc}") from exc

        output.write_text(json.dumps(bp.model_dump(mode="json"), indent=2))
        click.echo(f"✅ Wrote {output}")
        return

    raise click.ClickException(f"Unsupported source type: {source.suffix}")
