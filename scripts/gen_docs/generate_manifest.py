"""Generate manifest registry auto fragment."""
from __future__ import annotations

from pathlib import Path

from ice_core.models.enums import NodeType

ROOT = Path(__file__).resolve().parents[2]
DOC_OUT = ROOT / "docs" / "generated"
DOC_OUT.mkdir(parents=True, exist_ok=True)

FIELDS = [
    "node_type", "name", "import", "version", "schema", "cost_estimate",
]


def build() -> None:
    bullets = " ".join(f"`{f}`" for f in FIELDS)
    content = (
        "<!-- AUTO-GENERATED manifest schema summary -->\n\n"
        "### plugins.json Core Fields\n\n"
        f"{bullets}\n\n"
        "### Node types supported by manifest\n\n" +
        " ".join(f"`{nt.value}`" for nt in NodeType)
    )
    out_file = DOC_OUT / "manifest_auto.md"
    out_file.write_text(content + "\n", encoding="utf-8")
    print(f"[gen-docs] Wrote {out_file.relative_to(ROOT)}")

if __name__ == "__main__":
    build()
