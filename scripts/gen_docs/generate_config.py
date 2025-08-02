"""Generate config architecture auto fragment."""
from __future__ import annotations

import inspect
from pathlib import Path
from typing import Type

from ice_core.models import node_models

ROOT = Path(__file__).resolve().parents[2]
DOC_OUT = ROOT / "docs" / "generated"
DOC_OUT.mkdir(parents=True, exist_ok=True)

# Mapping provider vs node configs
PROVIDER_CONFIGS = [
    "LLMConfig",
]

NODE_CONFIGS = [
    cls.__name__
    for cls in node_models.__dict__.values()
    if inspect.isclass(cls) and cls.__name__.endswith("NodeConfig")
]


def build() -> None:
    lines: list[str] = ["<!-- AUTO-GENERATED: config architecture facts -->", "", "### Provider Configs (HOW)"]
    for pc in sorted(PROVIDER_CONFIGS):
        lines.append(f"- `{pc}`")

    lines.append("\n### Node Configs (WHAT)")
    for nc in sorted(NODE_CONFIGS):
        lines.append(f"- `{nc}`")

    out_file = DOC_OUT / "config_architecture_auto.md"
    out_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[gen-docs] Wrote {out_file.relative_to(ROOT)}")

if __name__ == "__main__":
    build()
