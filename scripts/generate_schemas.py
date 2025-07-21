"""Utility script to generate JSON-Schema files from Pydantic models.

Run with::

    python -m scripts.generate_schemas

The script writes schema files into ``schemas/runtime`` relative to the
repository root.
"""

from __future__ import annotations

import json
from pathlib import Path

from ice_core.models import (
    ChainExecutionResult,
    LLMOperatorConfig,
    NodeExecutionResult,
    NodeMetadata,
    SkillNodeConfig,
)
from ice_sdk.models.config import AppConfig, LLMConfig, MessageTemplate

TARGET_DIR = Path(__file__).resolve().parent.parent / "schemas" / "runtime"
TARGET_DIR.mkdir(parents=True, exist_ok=True)

# Map descriptive filename → Pydantic model -----------------------------------
MODELS = {
    "LLMOperatorConfig.json": LLMOperatorConfig,
    "SkillNodeConfig.json": SkillNodeConfig,
    "NodeMetadata.json": NodeMetadata,
    "NodeExecutionResult.json": NodeExecutionResult,
    "ChainExecutionResult.json": ChainExecutionResult,
    "LLMConfig.json": LLMConfig,
    "AppConfig.json": AppConfig,
    "MessageTemplate.json": MessageTemplate,
}


def main() -> None:
    """Generate schema files under *TARGET_DIR*."""
    for filename, model in MODELS.items():
        schema = model.model_json_schema()  # type: ignore[attr-defined]
        # Embedd provenance ---------------------------------------------------
        schema.setdefault(
            "$comment", f"generated from {model.__module__}:{model.__name__}"
        )
        (TARGET_DIR / filename).write_text(
            json.dumps(schema, indent=2, ensure_ascii=False)
        )
        print(f"✅  wrote {filename}")


if __name__ == "__main__":
    main()
