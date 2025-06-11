from __future__ import annotations

"""Check that all .py files contain a license header.

Currently looks for the string "MIT License" within first 10 lines.
This is a simple placeholder; replace with more sophisticated logic as needed.
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

LICENSE_STRING = "MIT License"
MAX_LINES = 10


def file_has_header(path: Path) -> bool:
    try:
        with path.open("r", encoding="utf-8") as f:
            for _ in range(MAX_LINES):
                line = f.readline()
                if not line:
                    break
                if LICENSE_STRING in line:
                    return True
    except Exception as exc:
        print(f"Failed to read {path}: {exc}")
    return False


def main() -> None:
    missing: list[Path] = []
    for py_file in REPO_ROOT.rglob("*.py"):
        if "__pycache__" in py_file.parts:
            continue
        if not file_has_header(py_file):
            missing.append(py_file)

    if missing:
        print("Files missing license header:")
        for path in missing:
            print(f" - {path.relative_to(REPO_ROOT)}")
        sys.exit(1)
    else:
        print("All files contain license header ✔️")
        sys.exit(0)


if __name__ == "__main__":
    main()
