"""Export JSON schemas for public Pydantic models.

This CLI replaces the legacy :pyfile:`scripts/export_schemas.py` script.
It writes one `<ModelName>.json` file per model into the *schemas/* folder
at the repository root.

Key differences to the legacy implementation:

* Lives under ``scripts/cli/`` and can be executed via ``python -m scripts.cli.export_schemas``.
* Uses :pymod:`argparse` so that invalid flags fail fast with a helpful error message.
* Exports only *concrete* models – **not** the :pydata:`~ice_sdk.models.node_models.NodeConfig` ``Annotated``
  union alias (which intentionally has no :pyfunc:`~pydantic.BaseModel.model_json_schema` method).
* Gracefully supports both old and new Pydantic versions: if the
  ``mode`` parameter for :pyfunc:`~pydantic.BaseModel.model_json_schema` is not
  available (pre-v2.6) the call silently falls back to the legacy signature.
"""

from __future__ import annotations

import argparse
import json
import pathlib
from typing import Dict, Type

from pydantic import BaseModel  # type: ignore

from ice_sdk.models.config import AppConfig, LLMConfig, MessageTemplate
from ice_sdk.models.node_models import AiNodeConfig, ToolConfig, ToolNodeConfig

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent  # ../../
SCHEMA_DIR = REPO_ROOT / "schemas"
SCHEMA_DIR.mkdir(exist_ok=True, parents=True)

# Mapping of model name → concrete Pydantic model class
MODELS: Dict[str, Type[BaseModel]] = {
    "LLMConfig": LLMConfig,
    "MessageTemplate": MessageTemplate,
    "AppConfig": AppConfig,
    # Node related (export concrete models only!)
    "AiNodeConfig": AiNodeConfig,
    "ToolNodeConfig": ToolNodeConfig,
    "ToolConfig": ToolConfig,
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _dump_schema(model: Type[BaseModel], out_path: pathlib.Path) -> None:  # noqa: D401
    """Write the JSON schema of *model* to *out_path*."""

    # Pydantic ≥ 2.6 supports the ``mode`` kwarg. We detect support dynamically
    # to remain backwards-compatible with older versions.
    try:
        schema_dict = model.model_json_schema(mode="serialization")
    except TypeError:
        # Older Pydantic – fall back to original signature
        schema_dict = model.model_json_schema()

    out_path.write_text(json.dumps(schema_dict, indent=2), encoding="utf-8")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_arg_parser() -> argparse.ArgumentParser:  # noqa: D401
    parser = argparse.ArgumentParser(
        description="Export JSON schemas for public Pydantic models.",
    )
    parser.add_argument(
        "--output-dir",
        type=pathlib.Path,
        default=SCHEMA_DIR,
        help="Directory to write <Model>.json files to (default: ./schemas).",
    )
    return parser


def main() -> None:  # noqa: D401 (imperative mood)
    parser = build_arg_parser()
    args = parser.parse_args()

    output_dir: pathlib.Path = args.output_dir.expanduser().resolve()
    output_dir.mkdir(exist_ok=True, parents=True)

    for name, model in MODELS.items():
        schema_path = output_dir / f"{name}.json"
        _dump_schema(model, schema_path)
        rel = schema_path.relative_to(REPO_ROOT)
        print(f"[export_schemas] Wrote {rel}")


if __name__ == "__main__":
    main()
