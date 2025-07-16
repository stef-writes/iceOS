from pathlib import Path

import pytest

from ice_sdk.exceptions import SecurityViolationError
from ice_sdk.tools.workflow.scaffolder import WorkflowScaffolder


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "resource_type, name, ext",
    [
        ("chain", "testchain", ".chain.py"),
        ("tool", "testtool", ".tool.py"),
        ("node", "testnode", ".ainode.yaml"),
    ],
)
async def test_scaffolder_creates_files(tmp_path, resource_type, name, ext):
    tool = WorkflowScaffolder()
    work_dir = Path.cwd() / "_scaffold_test_out"
    work_dir.mkdir(exist_ok=True)
    out = await tool.run(
        ctx=None,
        resource_type=resource_type,
        name=name,
        description="A test resource",
        directory=str(work_dir),
        generate_test=False,
    )
    file_path = Path(out["file_path"])
    assert file_path.exists()
    if resource_type == "node":
        assert file_path.name.endswith(".ainode.yaml")
    elif resource_type == "tool":
        assert file_path.name.endswith(".tool.py")
    elif resource_type == "chain":
        assert file_path.name.endswith(".chain.py")
    content = file_path.read_text()
    assert name in content or name.capitalize() in content


# ---------------------------------------------------------------------------
# Security violation --------------------------------------------------------
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_scaffolder_path_security(tmp_path):
    tool = WorkflowScaffolder()
    with pytest.raises(SecurityViolationError):
        # Attempt to escape tmp_path by using "../"
        await tool.run(
            ctx=None,
            resource_type="tool",
            name="evil",
            directory="../",
            generate_test=False,
        )
