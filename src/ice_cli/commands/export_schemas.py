"""Export JSON schemas for all iceOS models.

This module generates JSON schemas for:
- All node type configurations (Tool, LLM, Agent, etc.)
- Blueprint and ComponentDefinition models
- MCP protocol models
"""

from __future__ import annotations

import json
import pathlib
from typing import Any, Dict, List, Type

import yaml
from pydantic import BaseModel

# Import all node configurations
from ice_core.models import (  # Node configurations; Other node types; MCP models
    AgentNodeConfig,
    AgentSpec,
    BaseNodeConfig,
    ChainExecutionResult,
    CodeNodeConfig,
    ConditionNodeConfig,
    ContextRule,
    HumanNodeConfig,
    InputMapping,
    LLMNodeConfig,
    LoopNodeConfig,
    MonitorNodeConfig,
    NodeExecutionResult,
    NodeMetadata,
    ParallelNodeConfig,
    RecursiveNodeConfig,
    RetryPolicy,
    SwarmNodeConfig,
    ToolConfig,
    ToolNodeConfig,
    WorkflowNodeConfig,
)
from ice_core.models.llm import LLMConfig
from ice_core.models.mcp import (
    Blueprint,
    BlueprintAck,
    ComponentDefinition,
    NodeSpec,
    PartialBlueprint,
    PartialNodeSpec,
)

# Mapping of schema names to Pydantic models
SCHEMA_MODELS: Dict[str, Type[BaseModel]] = {
    # Node configurations (ordered by importance)
    "ToolNodeConfig": ToolNodeConfig,
    "LLMNodeConfig": LLMNodeConfig,
    "AgentNodeConfig": AgentNodeConfig,
    "ConditionNodeConfig": ConditionNodeConfig,
    "WorkflowNodeConfig": WorkflowNodeConfig,
    "LoopNodeConfig": LoopNodeConfig,
    "ParallelNodeConfig": ParallelNodeConfig,
    "RecursiveNodeConfig": RecursiveNodeConfig,
    "CodeNodeConfig": CodeNodeConfig,
    "SwarmNodeConfig": SwarmNodeConfig,
    "HumanNodeConfig": HumanNodeConfig,
    "MonitorNodeConfig": MonitorNodeConfig,
    # MCP models
    "Blueprint": Blueprint,
    "BlueprintAck": BlueprintAck,
    "ComponentDefinition": ComponentDefinition,
    "NodeSpec": NodeSpec,
    "PartialBlueprint": PartialBlueprint,
    "PartialNodeSpec": PartialNodeSpec,
    # Supporting models
    "BaseNodeConfig": BaseNodeConfig,
    "LLMConfig": LLMConfig,
    "NodeMetadata": NodeMetadata,
    "RetryPolicy": RetryPolicy,
    "ContextRule": ContextRule,
    "InputMapping": InputMapping,
    "ToolConfig": ToolConfig,
    "AgentSpec": AgentSpec,
    # Execution results
    "NodeExecutionResult": NodeExecutionResult,
    "ChainExecutionResult": ChainExecutionResult,
}


def generate_schema_with_metadata(model: Type[BaseModel], name: str) -> Dict[str, Any]:
    """Generate JSON schema with additional metadata.

    Args:
        model: Pydantic model to generate schema for
        name: Name of the model

    Returns:
        Dict containing the JSON schema with metadata
    """
    # Generate base schema
    schema = model.model_json_schema(mode="serialization")

    # Add metadata
    schema["$id"] = f"https://iceos.ai/schemas/{name}.json"
    schema["$comment"] = f"Generated from {model.__module__}.{model.__name__}"
    schema["x-iceos-version"] = "1.0.0"

    # Add examples if available
    # Pydantic v2 stores optional extras in `model_config` dict-like object.
    extra = getattr(model, "model_config", {})
    if isinstance(extra, dict):
        examples = (
            extra.get("json_schema_extra", {}).get("examples")
            if extra.get("json_schema_extra")
            else None
        )
        if examples:
            schema["examples"] = examples

    return schema


def get_schema_categories() -> Dict[str, List[str]]:
    """Get schema names organized by category."""
    return {
        "node_configs": [
            "ToolNodeConfig",
            "LLMNodeConfig",
            "AgentNodeConfig",
            "ConditionNodeConfig",
            "WorkflowNodeConfig",
            "LoopNodeConfig",
            "ParallelNodeConfig",
            "RecursiveNodeConfig",
            "CodeNodeConfig",
            "SwarmNodeConfig",
            "HumanNodeConfig",
            "MonitorNodeConfig",
        ],
        "mcp_models": [
            "Blueprint",
            "BlueprintAck",
            "ComponentDefinition",
            "NodeSpec",
            "PartialBlueprint",
            "PartialNodeSpec",
        ],
        "supporting_models": [
            "BaseNodeConfig",
            "LLMConfig",
            "NodeMetadata",
            "RetryPolicy",
            "ContextRule",
            "InputMapping",
            "ToolConfig",
            "AgentSpec",
        ],
        "execution_results": [
            "NodeExecutionResult",
            "ChainExecutionResult",
        ],
    }


def export_all_schemas(output_dir: str, format: str = "json") -> int:
    """Export all schemas to the specified directory.

    Args:
        output_dir: Directory to write schema files
        format: Output format ('json' or 'yaml')

    Returns:
        Number of schemas exported
    """
    output_path = pathlib.Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Create category subdirectories
    categories = get_schema_categories()
    for category in categories:
        (output_path / category).mkdir(exist_ok=True)

    # Track exported schemas
    exported_count = 0

    # Export schemas by category
    for category, schema_names in categories.items():
        category_path = output_path / category

        for name in schema_names:
            if name not in SCHEMA_MODELS:
                continue

            model = SCHEMA_MODELS[name]
            schema = generate_schema_with_metadata(model, name)

            # Write schema file
            file_extension = format
            file_path = category_path / f"{name}.{file_extension}"

            if format == "json":
                file_path.write_text(
                    json.dumps(schema, indent=2, ensure_ascii=False) + "\n"
                )
            else:  # yaml
                file_path.write_text(
                    yaml.dump(schema, default_flow_style=False, sort_keys=False)
                )

            exported_count += 1

    # Generate index file
    index_path = output_path / f"index.{format}"
    index_data = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "$id": "https://iceos.ai/schemas/index.json",
        "title": "iceOS Schema Index",
        "description": "Index of all available iceOS schemas",
        "x-iceos-version": "1.0.0",
        "categories": {
            category: [
                f"{category}/{name}.{format}" for name in names if name in SCHEMA_MODELS
            ]
            for category, names in categories.items()
        },
        "total_schemas": exported_count,
    }

    if format == "json":
        index_path.write_text(
            json.dumps(index_data, indent=2, ensure_ascii=False) + "\n"
        )
    else:
        index_path.write_text(
            yaml.dump(index_data, default_flow_style=False, sort_keys=False)
        )

    return exported_count


def validate_schema_completeness() -> List[str]:
    """Validate that we're exporting schemas for all necessary models.

    Returns:
        List of missing model names
    """
    # This could be expanded to check against the actual imports
    # For now, we'll just ensure our categories cover all registered models
    categories = get_schema_categories()
    all_categorized = set()

    for names in categories.values():
        all_categorized.update(names)

    missing = []
    for name in SCHEMA_MODELS:
        if name not in all_categorized:
            missing.append(name)

    return missing
