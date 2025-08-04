from __future__ import annotations

import subprocess
from pathlib import Path


def test_scaffold_tool(tmp_path: Path) -> None:
    """`ice new tool` should generate a valid tool file."""
    proj_dir = tmp_path / "proj"
    proj_dir.mkdir()

    cmd = [
        "python", "-m", "ice_cli.cli", "new", "tool", "demo_pricing_tool",
        "--description", "Compute price from cost.",
        "--output-dir", str(proj_dir),
    ]
    completed = subprocess.run(cmd, capture_output=True, text=True)
    assert completed.returncode == 0, completed.stderr

    gen_file = proj_dir / "src/ice_tools/generated/demo_pricing_tool.py"
    assert gen_file.is_file(), "Tool file not generated"

    # Quick sanity: file contains class with correct name
    content = gen_file.read_text()
    assert "class DemoPricingTool(" in content
    assert "name: str = \"demo_pricing_tool\"" in content
