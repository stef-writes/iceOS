"""Generate protocols doc fragment."""
from __future__ import annotations

import inspect
from pathlib import Path
from types import ModuleType
from typing import List

from ice_core import protocols as protocols_pkg

ROOT = Path(__file__).resolve().parents[2]
DOC_OUT = ROOT / "docs" / "generated"
DOC_OUT.mkdir(parents=True, exist_ok=True)


def _collect_protocols() -> List[str]:
    names: list[str] = []
    for attr in dir(protocols_pkg):
        obj = getattr(protocols_pkg, attr)
        if isinstance(obj, ModuleType):
            for name, member in obj.__dict__.items():
                if inspect.isclass(member) and name.startswith("I"):
                    names.append(name)
    return sorted(set(names))


def build() -> None:
    names = _collect_protocols()
    content = "<!-- AUTO-GENERATED protocol list -->\n\n" + "\n".join(f"- `{n}`" for n in names) + "\n"
    out_file = DOC_OUT / "protocols_auto.md"
    out_file.write_text(content, encoding="utf-8")
    print(f"[gen-docs] Wrote {out_file.relative_to(ROOT)}")

if __name__ == "__main__":
    build()
