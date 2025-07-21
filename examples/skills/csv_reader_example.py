#!/usr/bin/env python3
"""Example: Using *CSVReaderSkill* in isolation.

Run with:
    python examples/skills/csv_reader_example.py

This acts as an executable demo *and* a smoke-test.
"""
from __future__ import annotations

import asyncio
from pathlib import Path

from ice_sdk.skills.system.csv_reader_skill import CSVReaderSkill

# ---------------------------------------------------------------------------
# Helper – prepare minimal sample file next to this script -------------------
# ---------------------------------------------------------------------------
SAMPLE_CSV = Path(__file__).with_name("sample.csv")
if not SAMPLE_CSV.exists():
    SAMPLE_CSV.write_text("name,age\nAlice,30\nBob,25\n", encoding="utf-8")


async def main() -> None:  # noqa: D401 – script entrypoint
    skill = CSVReaderSkill()
    result = await skill.execute({"file_path": str(SAMPLE_CSV)})

    print("=== CSVReaderSkill Demo ===")
    print(f"Headers     : {result['headers']}")
    print(f"Total rows  : {result['total_rows']}")
    if result["rows"]:
        print("First record:", result["rows"][0])


if __name__ == "__main__":
    asyncio.run(main()) 