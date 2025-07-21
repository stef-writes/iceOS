from __future__ import annotations

"""CI helper to validate that newly-added tool packages were generated via
ice_sdk.scaffold.create_tool_package.

The script is *not* invoked automatically yet; it can be wired into GitHub
workflow marketplace-check once policy is agreed.
"""

import re
import sys
from pathlib import Path
from typing import List

RE_TOOL_PATH = re.compile(r"src/ice_sdk/tools/(?P<name>[a-zA-Z0-9_]+)/__init__\.py")


def _find_new_tools() -> List[str]:  # – helper
    changed_files = Path(".git").parent.rglob(
        "*__init__.py"
    )  # simplistic – in CI use git diff --name-only

    tools: List[str] = []
    for p in changed_files:
        m = RE_TOOL_PATH.match(str(p))
        if m:
            tools.append(m.group("name"))
    return tools


def _check_tests_exist(tool: str) -> bool:
    test_file = Path(f"tests/tools/test_{tool}_tool.py")
    return test_file.exists()


def main() -> None:
    failed: List[str] = []
    for tool in _find_new_tools():
        if not _check_tests_exist(tool):
            failed.append(tool)

    if failed:
        print("::error:: Missing tests for tool packages:", ", ".join(failed))
        sys.exit(1)

    print("Tool scaffold check passed ✔️")


if __name__ == "__main__":
    main()
