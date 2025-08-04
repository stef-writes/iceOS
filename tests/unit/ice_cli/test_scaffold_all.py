from pathlib import Path
import subprocess

COMMAND = ["python", "-m", "ice_cli.cli", "new"]

def _run(cmd: list[str], cwd: Path) -> int:
    cp = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    return cp.returncode

def test_scaffold_variants(tmp_path: Path) -> None:
    proj = tmp_path / "proj"
    proj.mkdir()

    assert _run(COMMAND + ["agent", "sales_support_agent", "--output-dir", str(proj)], tmp_path) == 0
    assert _run(COMMAND + ["agent-tool", "sales_support_agent", "--output-dir", str(proj)], tmp_path) == 0
    assert _run(COMMAND + ["llm-operator", "summarize_text", "--output-dir", str(proj)], tmp_path) == 0
