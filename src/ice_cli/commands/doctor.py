from __future__ import annotations

"""`ice doctor` – basic quality and CI helpers (lint, type-check, tests)."""

import platform
import shlex
import shutil
import subprocess
from dataclasses import dataclass

import typer  # type: ignore
from rich import print as rprint  # type: ignore

# ---------------------------------------------------------------------------
# Platform-safe icons (Windows CI consoles choke on emoji / unicode arrows) --
# ---------------------------------------------------------------------------

_SUPPORTS_UTF = platform.system() != "Windows"

_BULLET = "▶" if _SUPPORTS_UTF else ">"
_CHECKMARK = "✅" if _SUPPORTS_UTF else "OK"
_CROSS = "❌" if _SUPPORTS_UTF else "X"


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
    """Run MyPy in strict mode against *src/*."""

    _run(
        ["mypy", "--strict", "--config-file", "mypy.ini", "src/app", "src/ice_cli"]
    )  # strict only on modern packages


@doctor_app.command("test")
def doctor_test():
    """Run pytest quietly."""

    _run(["pytest", "-q"])


@dataclass(slots=True)
class _Check:  # noqa: D401 – internal container
    label: str
    command: str
    perf_only: bool = False  # include only when --perf flag passed

    def run(self) -> int:  # noqa: D401 – helper
        rprint(f"\n{_BULLET} {self.label}\n[cyan]$ {self.command}[/]")
        result = subprocess.run(shlex.split(self.command), check=False)
        if result.returncode == 0:
            rprint(f"{_CHECKMARK} PASSED")
        else:
            rprint(f"{_CROSS} FAILED (exit={result.returncode})")
        return result.returncode


# NOTE: Keep in sync with project HEALTHCHECKS.md ---------------------------
_CHECKS: list[_Check] = [
    _Check("Linting (ruff)", "ruff check src"),
    _Check("Typing (mypy strict: app)", "mypy --strict --config-file mypy.ini src/app"),
    _Check("Unit & integration tests", "pytest -q"),
    _Check(
        "Coverage threshold",
        ("pytest --cov=ice_sdk --cov=ice_orchestrator --cov-fail-under=60 -q"),
    ),
    *([_Check("Security audit", "pip-audit")] if shutil.which("pip-audit") else []),
    _Check("Import-linter rules", "lint-imports --config config/.importlinter"),
    _Check("isort check", "isort --check-only src"),
    _Check("JSON/YAML validity", "python -m scripts.cli.check_json_yaml"),
    _Check("FlowSpec examples schema", "python scripts/check_flow_spec.py"),
    _Check("Performance smoke", "pytest --benchmark-only -q", perf_only=True),
]


@doctor_app.command("all")
def doctor_all(
    perf: bool = typer.Option(
        False, "--perf", help="Include performance-heavy checks (benchmarks)"
    ),
    keep_going: bool = typer.Option(
        False,
        "--keep-going",
        help="Run all checks even if earlier ones fail",
    ),
):
    """Run the full health-check suite.

    By default stops at first failure.  Pass ``--keep-going`` to run the whole
    list and aggregate the exit status.  Use ``--perf`` to include the extra
    performance smoke benchmarks.
    """

    failed = False

    for chk in _CHECKS:
        if chk.perf_only and not perf:
            continue
        exit_code = chk.run()
        if exit_code != 0:
            failed = True
            if not keep_going:
                raise typer.Exit(exit_code)

    if failed:
        raise typer.Exit(1)

    rprint(f"[bold green]\nAll checks passed {_CHECKMARK}[/]")
