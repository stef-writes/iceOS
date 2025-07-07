from __future__ import annotations

"""`ice doctor` – basic quality and CI helpers (lint, type-check, tests)."""

import subprocess

import typer
from rich import print as rprint


def _run(cmd: list[str]):  # noqa: D401 – helper
    """Run *cmd* and stream output.  Never raises."""

    rprint(f"[cyan]$ {' '.join(cmd)}[/]")
    subprocess.run(cmd, check=False)


doctor_app = typer.Typer(add_completion=False, help="Quality checks")

__all__ = ["doctor_app"]


@doctor_app.command("lint")
def doctor_lint():
    """Run Ruff auto-fix."""

    _run(["ruff", "src", "--fix"])


@doctor_app.command("type")
def doctor_type():
    """Run Pyright (strict type-checking)."""

    _run(["pyright"])


@doctor_app.command("test")
def doctor_test():
    """Run pytest quietly."""

    _run(["pytest", "-q"])


@doctor_app.command("all")
def doctor_all():
    """Run lint + type + test in sequence."""

    doctor_lint()
    doctor_type()
    doctor_test()
