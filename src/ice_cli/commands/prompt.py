import json
import os
import subprocess
from pathlib import Path
from typing import Any, Dict, List

import typer
import yaml
from jinja2 import Template  # runtime dependency declared in pyproject
from jsonschema import Draft202012Validator, ValidationError  # type: ignore
from rich import print as rprint
from rich.table import Table

from ice_cli.utils import snake_case as _snake_case  # shared helper

# Everything is pure file I/O so we respect repo rule #2 (side-effects only
# inside CLI Tool implementations).

# ---------------------------------------------------------------------------
# Globals --------------------------------------------------------------------
# ---------------------------------------------------------------------------

prompt_app = typer.Typer(help="Manage prompt templates, few-shot examples and schemas")
example_app = typer.Typer(help="Manage few-shot examples for a prompt")
schema_app = typer.Typer(help="Manage output schemas for a prompt")

prompt_app.add_typer(example_app, name="example")
prompt_app.add_typer(schema_app, name="schema")

# Default storage folders ----------------------------------------------------
_PROMPT_DIR = Path.cwd() / "prompts"
_SCHEMA_DIR = Path.cwd() / "schemas" / "outputs"

# ---------------------------------------------------------------------------
# Internal helpers -----------------------------------------------------------
# ---------------------------------------------------------------------------


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _prompt_path(name: str, directory: Path | None = None) -> Path:
    directory = directory or _PROMPT_DIR
    _ensure_dir(directory)
    return directory / f"{_snake_case(name)}.prompt.yaml"


# _schema_path kept for future extension – currently unused but kept to avoid
# repeated helper creation if we add standalone schema files later.


def _schema_path(
    name: str, directory: Path | None = None
) -> Path:  # noqa: D401,F401 – helper placeholder
    directory = directory or _SCHEMA_DIR
    _ensure_dir(directory)
    return directory / f"{_snake_case(name)}.schema.json"


# ---------------------------------------------------------------------------
# Prompt commands ------------------------------------------------------------
# ---------------------------------------------------------------------------


@prompt_app.command("create", help="Scaffold a new prompt YAML file")
def prompt_create(
    name: str = typer.Argument(..., help="Prompt name (human readable)"),
    template: str | None = typer.Option(
        None,
        "--template",
        "-t",
        help="Inline template string. Use pipes for multiline.",
    ),
    directory: Path = typer.Option(
        _PROMPT_DIR,
        "--dir",
        exists=False,
        file_okay=False,
        dir_okay=True,
        writable=True,
    ),
    force: bool = typer.Option(False, "--force", "-f", help="Overwrite if file exists"),
):
    path = _prompt_path(name, directory)
    if path.exists() and not force:
        rprint(f"[red]File {path} already exists. Use --force to overwrite.[/]")
        raise typer.Exit(1)

    data: Dict[str, Any] = {
        "name": name,
        "template": template
        or "# TODO: write prompt here – use {variable} placeholders",
        "examples": [],
        "schema": None,
    }
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")

    def _pretty(p: Path) -> str:  # noqa: D401 – helper
        try:
            return str(p.relative_to(Path.cwd()))
        except ValueError:
            return str(p)

    rprint(f"[green]✔ Created[/] {_pretty(path)}")


@prompt_app.command("ls", help="List all prompt files")
def prompt_ls(directory: Path = typer.Option(_PROMPT_DIR, "--dir")):
    if not directory.exists():
        rprint("[yellow]No prompts found.[/]")
        return

    table = Table(title="Prompts")
    table.add_column("Name")
    table.add_column("Path")

    def _pretty(p: Path) -> str:  # noqa: D401 – helper
        try:
            return str(p.relative_to(Path.cwd()))
        except ValueError:
            return str(p)

    for f in sorted(directory.glob("*.prompt.yaml")):
        with open(f, "r", encoding="utf-8") as fp:
            meta = yaml.safe_load(fp)
        table.add_row(meta.get("name", f.stem), _pretty(f))
    rprint(table)


@prompt_app.command("edit", help="Open prompt file in $EDITOR")
def prompt_edit(
    name: str = typer.Argument(...),
    directory: Path = typer.Option(_PROMPT_DIR, "--dir"),
):
    path = _prompt_path(name, directory)
    if not path.exists():
        rprint(f"[red]Prompt {name} not found at {path}.[/]")
        raise typer.Exit(1)

    editor = os.getenv("EDITOR", "vi")
    subprocess.call([editor, str(path)])  # noqa: S603 – user-provided editor


@prompt_app.command("test", help="Render the prompt with input JSON and print result")
def prompt_test(
    name: str = typer.Argument(..., help="Prompt name"),
    input_json: str = typer.Option(
        "{}", "--input", "-i", help="JSON string passed as variables to the template"
    ),
    directory: Path = typer.Option(_PROMPT_DIR, "--dir"),
):
    path = _prompt_path(name, directory)
    if not path.exists():
        rprint(f"[red]Prompt {name} not found.[/]")
        raise typer.Exit(1)

    data = yaml.safe_load(path.read_text())
    template_str = data.get("template", "")
    try:
        variables = json.loads(input_json)
    except json.JSONDecodeError as exc:
        rprint(f"[red]Invalid JSON for --input:[/] {exc}")
        raise typer.Exit(1)

    # First try Jinja2 style ({{ var }}). If unchanged and template seems to
    # contain "{var}" placeholders, fall back to .format(**vars) for quick
    # ad-hoc testing convenience.
    rendered = Template(template_str).render(**variables)
    if rendered == template_str and "{" in template_str and "}" in template_str:
        try:
            rendered = template_str.format(**variables)
        except Exception:
            pass

    rprint("[bold cyan]Rendered Prompt:[/]")
    rprint(rendered)


# ---------------------------------------------------------------------------
# Few-shot example sub-commands ---------------------------------------------
# ---------------------------------------------------------------------------


@example_app.command("add", help="Append a new example to the prompt")
def example_add(
    prompt_name: str = typer.Argument(...),
    input_json: str = typer.Option(..., "--input", "-i", help="JSON of input vars"),
    output: str = typer.Option(
        ..., "--output", "-o", help="Expected LLM output / answer"
    ),
    directory: Path = typer.Option(_PROMPT_DIR, "--dir"),
):
    path = _prompt_path(prompt_name, directory)
    if not path.exists():
        rprint(f"[red]Prompt {prompt_name} not found.[/]")
        raise typer.Exit(1)

    data = yaml.safe_load(path.read_text())
    try:
        parsed_input = json.loads(input_json)
    except json.JSONDecodeError as exc:
        rprint(f"[red]Invalid JSON for --input:[/] {exc}")
        raise typer.Exit(1)

    ex_entry = {"input": parsed_input, "output": output}
    data.setdefault("examples", []).append(ex_entry)
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    rprint("[green]✔ Added example to prompt[/]")


@example_app.command("ls", help="List examples for a prompt")
def example_ls(
    prompt_name: str = typer.Argument(...),
    directory: Path = typer.Option(_PROMPT_DIR, "--dir"),
):
    path = _prompt_path(prompt_name, directory)
    if not path.exists():
        rprint(f"[red]Prompt {prompt_name} not found.[/]")
        raise typer.Exit(1)

    data = yaml.safe_load(path.read_text())
    examples: List[Dict[str, Any]] = data.get("examples", [])
    if not examples:
        rprint("[yellow]No examples found.[/]")
        return

    table = Table(title=f"Examples for {prompt_name}")
    table.add_column("#")
    table.add_column("Input (truncated)")
    table.add_column("Output (truncated)")
    for idx, ex in enumerate(examples, start=1):
        table.add_row(str(idx), json.dumps(ex["input"])[:40], ex["output"][:40])
    rprint(table)


# ---------------------------------------------------------------------------
# Schema sub-commands --------------------------------------------------------
# ---------------------------------------------------------------------------


@schema_app.command(
    "create", help="Attach / overwrite a JSON schema for the prompt output"
)
def schema_create(
    prompt_name: str = typer.Argument(...),
    schema_json: str = typer.Option(
        ..., "--schema", "-s", help="JSON string representing the schema"
    ),
    directory: Path = typer.Option(_PROMPT_DIR, "--dir"),
):
    path = _prompt_path(prompt_name, directory)
    if not path.exists():
        rprint(f"[red]Prompt {prompt_name} not found.[/]")
        raise typer.Exit(1)

    try:
        schema_obj = json.loads(schema_json)
    except json.JSONDecodeError as exc:
        rprint(f"[red]Invalid JSON for --schema:[/] {exc}")
        raise typer.Exit(1)

    data = yaml.safe_load(path.read_text())
    data["schema"] = schema_obj
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    rprint("[green]✔ Schema attached to prompt[/]")


@schema_app.command("test", help="Validate output JSON against the prompt schema")
def schema_test(
    prompt_name: str = typer.Argument(...),
    output_json: str = typer.Option(
        ..., "--output", "-o", help="Output JSON string to validate"
    ),
    directory: Path = typer.Option(_PROMPT_DIR, "--dir"),
):
    path = _prompt_path(prompt_name, directory)
    if not path.exists():
        rprint(f"[red]Prompt {prompt_name} not found.[/]")
        raise typer.Exit(1)

    data = yaml.safe_load(path.read_text())
    schema_obj = data.get("schema")
    if not schema_obj:
        rprint("[yellow]No schema attached to this prompt.[/]")
        raise typer.Exit(1)

    try:
        output_obj = json.loads(output_json)
    except json.JSONDecodeError as exc:
        rprint(f"[red]Invalid JSON for --output:[/] {exc}")
        raise typer.Exit(1)

    validator = Draft202012Validator(schema_obj)
    try:
        validator.validate(output_obj)
        rprint("[green]✔ Output is valid against schema.[/]")
    except ValidationError as exc:
        rprint(f"[red]✗ Validation failed:[/] {exc.message}")
        raise typer.Exit(1)


@schema_app.command("ls", help="Show schema (if any) attached to a prompt")
def schema_ls(
    prompt_name: str = typer.Argument(...),
    directory: Path = typer.Option(_PROMPT_DIR, "--dir"),
):
    path = _prompt_path(prompt_name, directory)
    if not path.exists():
        rprint(f"[red]Prompt {prompt_name} not found.[/]")
        raise typer.Exit(1)

    data = yaml.safe_load(path.read_text())
    schema_obj = data.get("schema")
    if not schema_obj:
        rprint("[yellow]No schema attached to this prompt.[/]")
        return

    rprint(json.dumps(schema_obj, indent=2))
