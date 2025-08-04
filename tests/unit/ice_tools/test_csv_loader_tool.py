"""Unit tests for CSVLoaderTool."""
from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from ice_tools.csv_loader import CSVLoaderTool


@pytest.mark.asyncio
async def test_csv_loader_reads_rows(tmp_path: Path) -> None:
    csv_content = """col1,col2\na,b\n1,2\n"""
    tmp_file = tmp_path / "sample.csv"
    tmp_file.write_text(csv_content, encoding="utf-8")

    tool = CSVLoaderTool(path=str(tmp_file))
    result = await tool.execute()
    assert result["rows"] == [{"col1": "a", "col2": "b"}, {"col1": "1", "col2": "2"}]
