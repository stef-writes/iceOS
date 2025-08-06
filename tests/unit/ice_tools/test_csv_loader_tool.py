"""Unit tests for CSVLoaderTool."""
from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from ice_tools.toolkits.common.csv_loader import CSVLoaderTool


@pytest.mark.asyncio
async def test_csv_loader_reads_rows(tmp_path: Path) -> None:
    csv_content = """col1,col2\na,b\n1,2\n"""
    tmp_file = tmp_path / "sample.csv"
    tmp_file.write_text(csv_content, encoding="utf-8")

    tool = CSVLoaderTool(path=str(tmp_file))
    result = await tool.execute()
    assert result["rows"] == [{"col1": "a", "col2": "b"}, {"col1": "1", "col2": "2"}]


@pytest.mark.asyncio
async def test_csv_loader_factory_pattern() -> None:
    """Test CSV loader using factory pattern."""
    from ice_core.unified_registry import registry
    
    # Test factory instantiation
    tool = registry.get_tool_instance("csv_loader", path="/dev/null")
    assert tool.name == "csv_loader"
    assert tool.path == "/dev/null"
    
    # Test with custom parameters
    tool2 = registry.get_tool_instance("csv_loader", path="/tmp/test.csv", delimiter=";", max_rows=100)
    assert tool2.path == "/tmp/test.csv"
    assert tool2.delimiter == ";"
    assert tool2.max_rows == 100
    
    # Verify fresh instances (not singletons)
    assert tool is not tool2
