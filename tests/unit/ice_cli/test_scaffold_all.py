import subprocess
from pathlib import Path

COMMAND = ["python", "-m", "ice_cli.cli", "new"]


def _run(cmd: list[str], cwd: Path) -> int:
    cp = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    return cp.returncode


def test_scaffold_variants(tmp_path: Path) -> None:
    proj = tmp_path / "proj"
    proj.mkdir()

    assert (
        _run(
            COMMAND + ["agent", "sales_support_agent", "--output-dir", str(proj)],
            tmp_path,
        )
        == 0
    )
    assert (
        _run(
            COMMAND + ["agent-tool", "sales_support_agent", "--output-dir", str(proj)],
            tmp_path,
        )
        == 0
    )
    # Backward compatibility: alias changed to llm-node-tool in CLI implementation
    assert (
        _run(
            COMMAND + ["llm-node-tool", "summarize_text", "--output-dir", str(proj)],
            tmp_path,
        )
        == 0
    )
    # New scaffolds for workflow and llm factory helpers
    assert (
        _run(
            COMMAND + ["workflow", "demo_workflow", "--output-dir", str(proj)], tmp_path
        )
        == 0
    )
    assert _run(COMMAND + ["llm", "demo_llm", "--output-dir", str(proj)], tmp_path) == 0
    # Additional node scaffolds
    assert (
        _run(
            COMMAND + ["condition", "demo_condition", "--output-dir", str(proj)],
            tmp_path,
        )
        == 0
    )
    assert (
        _run(COMMAND + ["loop", "demo_loop", "--output-dir", str(proj)], tmp_path) == 0
    )
    assert (
        _run(
            COMMAND + ["parallel", "demo_parallel", "--output-dir", str(proj)], tmp_path
        )
        == 0
    )
    assert (
        _run(
            COMMAND + ["recursive", "demo_recursive", "--output-dir", str(proj)],
            tmp_path,
        )
        == 0
    )
    assert (
        _run(COMMAND + ["code", "demo_code", "--output-dir", str(proj)], tmp_path) == 0
    )
    assert (
        _run(COMMAND + ["human", "demo_human", "--output-dir", str(proj)], tmp_path)
        == 0
    )
    assert (
        _run(COMMAND + ["monitor", "demo_monitor", "--output-dir", str(proj)], tmp_path)
        == 0
    )
    assert (
        _run(COMMAND + ["swarm", "demo_swarm", "--output-dir", str(proj)], tmp_path)
        == 0
    )
