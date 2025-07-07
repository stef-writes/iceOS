from __future__ import annotations

"""`ice maint` – miscellaneous maintenance helpers used by CI.

These commands were previously stand-alone *argparse* scripts located in
`scripts/cli/` or `scripts/`.  Porting them to Typer means they share the
same UX surface, global flags and help text as the rest of our CLI.
"""

import importlib
import subprocess
import sys
from pathlib import Path
from typing import Any, Optional

import typer  # type: ignore
from rich import print as rprint  # type: ignore

__all__ = ["maint_app"]

# ---------------------------------------------------------------------------
# Helper utilities -----------------------------------------------------------
# ---------------------------------------------------------------------------


def _call_module(module_path: str, *extra_argv: str, capture: bool = False) -> None:  # noqa: D401
    """Execute *module_path* via :pymod:`python -m` so shebangs still work.

    This keeps the existing scripts untouched while enabling a unified
    interface.  Flags passed via Typer are forwarded verbatim.
    """

    cmd = [sys.executable, "-m", module_path, *extra_argv]
    rprint(f"[cyan]$ {' '.join(cmd)}[/]")
    subprocess.run(cmd, check=False, capture_output=capture)


# ---------------------------------------------------------------------------
# Typer sub-application ------------------------------------------------------
# ---------------------------------------------------------------------------

maint_app = typer.Typer(add_completion=False, help="Maintenance utilities")


# ---------------------------------------------------------------------------
# Commands -------------------------------------------------------------------
# ---------------------------------------------------------------------------


@maint_app.command("export-schemas", help="Export public Pydantic model schemas")
def export_schemas(
    output_dir: Optional[Path] = typer.Option(
        None,
        "--output-dir",
        "-o",
        help="Target directory (defaults to ./schemas)",
    ),
):
    args: list[str] = []
    if output_dir is not None:
        args.extend(["--output-dir", str(output_dir)])
    _call_module("scripts.cli.export_schemas", *args)


@maint_app.command("check-license", help="Verify source files carry the license header")
def check_license():  # noqa: D401 – CLI entry-point
    _call_module("scripts.cli.check_license")


@maint_app.command("check-json-yaml", help="Validate JSON / YAML syntax across repo")
def check_json_yaml():  # noqa: D401 – CLI entry-point
    _call_module("scripts.cli.check_json_yaml")


@maint_app.command("gen-catalog", help="Generate nodes & tools catalog (docs helper)")
def gen_catalog():  # noqa: D401 – CLI entry-point
    _call_module("scripts.cli.gen_catalog")


@maint_app.command("gen-overview", help="Generate high-level docs overview page")
def gen_overview():  # noqa: D401 – CLI entry-point
    _call_module("scripts.cli.gen_overview") 