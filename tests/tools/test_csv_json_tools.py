from __future__ import annotations

import json
from pathlib import Path

import pytest  # type: ignore

from ice_sdk.tools.builtins.file_tools import CsvLoaderTool, JsonQueryTool


@pytest.mark.asyncio
async def test_csv_loader_local(tmp_path: Path) -> None:
    """CsvLoaderTool should load local CSV and parse as dict rows."""

    csv_file = tmp_path / "sample.csv"
    csv_file.write_text("""name,age\nAlice,30\nBob,25\n""")

    tool = CsvLoaderTool()
    result = await tool.run(source=str(csv_file))

    assert isinstance(result["rows"], list)
    assert result["rows"][0]["name"] == "Alice"
    assert result["truncated"] is False


@pytest.mark.asyncio
async def test_json_query_inline() -> None:
    """JsonQueryTool should evaluate JMESPath query against inline JSON."""

    import importlib.util

    if importlib.util.find_spec("jmespath") is None:  # pragma: no cover
        pytest.skip("'jmespath' dependency not available in environment")

    data = {"foo": {"bar": 42}}
    tool = JsonQueryTool()
    result = await tool.run(query="foo.bar", source=json.dumps(data))

    # JsonQueryTool returns string representation of the result
    assert result["result"] == "42"
    assert result["truncated"] is False
