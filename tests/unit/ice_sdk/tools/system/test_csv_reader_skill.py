pytestmark = [__import__('pytest').mark.unit]

import json
import pytest

from ice_sdk.tools.system.csv_reader_skill import CSVReaderSkill
from ice_sdk.utils.errors import SkillExecutionError


@pytest.mark.asyncio
async def test_csv_reader_happy(tmp_path):
    """CSVReaderSkill should parse rows and return JSON-serialisable output."""

    csv_file = tmp_path / "sample.csv"
    csv_file.write_text("item,qty\napple,3\nbanana,5\n", encoding="utf-8")

    skill = CSVReaderSkill()
    out = await skill.execute(file_path=str(csv_file), delimiter=",")

    assert out["headers"] == ["item", "qty"]
    assert len(out["rows"]) == 2

    rows_from_json = json.loads(out["rows_json"])
    assert rows_from_json[0]["item"] == "apple"
    assert rows_from_json[1]["qty"] == "5"  # original CSV values preserved as str


@pytest.mark.asyncio
async def test_csv_reader_missing_file(tmp_path):
    """Missing file should raise *SkillExecutionError*."""

    missing_path = tmp_path / "does_not_exist.csv"
    skill = CSVReaderSkill()

    with pytest.raises(SkillExecutionError):
        await skill.execute(file_path=str(missing_path), delimiter=",") 