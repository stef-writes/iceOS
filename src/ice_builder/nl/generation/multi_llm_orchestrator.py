"""Multi-LLM orchestrator that coordinates the blueprint generation pipeline.

This is the main engine that transforms natural language specifications into
validated iceOS Blueprints using multiple specialized LLM providers.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List

from ice_builder.public import create_partial_blueprint
from ice_core.models.enums import ModelProvider
from ice_core.models.llm import LLMConfig
from ice_core.models.mcp import Blueprint
from ice_core.models.node_models import BaseNodeConfig

from ..providers import get_provider
from .node_selection_heuristics import NODE_TYPE_PATTERNS
from .prompt_templates import (
    format_code_prompt,
    format_decomposition_prompt,
    format_intent_prompt,
    format_mermaid_prompt,
    format_planning_prompt,
)
from .registry_integration import RegistryIntegration

logger = logging.getLogger(__name__)


class MultiLLMOrchestrator:
    """Orchestrates multiple LLMs to generate a complete Blueprint.

    The pipeline consists of:
    1. Intent extraction (OpenAI GPT-4o)
    2. High-level planning (DeepSeek R1)
    3. Node decomposition (Internal logic + DeepSeek R1)
    4. Mermaid diagram generation (DeepSeek R1)
    5. Code generation (Claude-3 Haiku)
    """

    def __init__(self, specification: str) -> None:
        """Initialize the orchestrator with a user specification.

        Args:
            specification: Natural language description of desired workflow.
        """
        self.specification = specification
        # Based on benchmark data - Claude 3.5 Sonnet is best for code (93.7% HumanEval)
        # DeepSeek models are cost-effective for other tasks
        self.providers = {
            "intent": get_provider("openai-gpt4o"),  # Best at understanding intent
            "planning": get_provider("deepseek-r1"),  # Specialized reasoning model
            "decomposition": get_provider("deepseek-r1"),
            "diagram": get_provider("openai-gpt4o"),  # Best at structured output
            "code": get_provider(
                "openai-gpt4o"
            ),  # Changed from claude3-haiku (75.9%) to gpt4o
        }
        self.registry = RegistryIntegration()

        # Memory for context across stages
        self.memory: Dict[str, Any] = {
            "available_tools": self.registry.get_available_tools(),
            "available_agents": self.registry.get_available_agents(),
        }

    async def generate(self) -> Blueprint:
        """Generate a complete Blueprint through the multi-LLM pipeline.

        Returns:
            A validated Blueprint ready for execution.

        Raises:
            RuntimeError: If any pipeline stage fails.
        """
        logger.info(f"Starting blueprint generation for: {self.specification[:100]}...")

        # Stage 1: Extract intent and requirements
        intent_data = await self._extract_intent()
        logger.debug(f"Extracted intent: {intent_data}")

        # Stage 2: Create high-level plan
        plan = await self._create_plan(intent_data)
        logger.debug(f"Created plan with {len(plan.splitlines())} steps")

        # Stage 3: Decompose into node configurations
        nodes_data = await self._decompose_plan(plan)
        logger.debug(f"Decomposed into {len(nodes_data)} nodes")

        # Stage 4: Generate Mermaid diagram
        mermaid_diagram = await self._generate_diagram(nodes_data)
        logger.debug("Generated Mermaid diagram")

        # Stage 5: Generate code for applicable nodes
        code_implementations = await self._generate_code(nodes_data)
        logger.debug(f"Generated code for {len(code_implementations)} nodes")

        # Stage 6: Assemble into Blueprint
        blueprint = self._assemble_blueprint(
            nodes_data, mermaid_diagram, code_implementations
        )
        logger.info(f"Generated blueprint with {len(blueprint.nodes)} nodes")

        return blueprint

    async def _extract_intent(self) -> Dict[str, Any]:
        """Extract structured intent from the user specification."""
        prompt = format_intent_prompt(self.specification)
        raw_response = await self.providers["intent"].complete(prompt)

        # Attempt JSON parsing first
        try:
            data = json.loads(raw_response)
            if isinstance(data, dict):
                return data
        except Exception:
            pass  # fallthrough to best-effort fallback

        # Fallback – wrap raw text so downstream stages can still proceed
        return {"raw": raw_response}

    async def _create_plan(self, intent_data: Dict[str, Any]) -> str:
        """Create a high-level execution plan."""
        # Add available tools to intent data
        enhanced_intent = intent_data.copy()
        enhanced_intent["available_tools"] = list(self.memory["available_tools"].keys())
        enhanced_intent["suggested_tools"] = self.registry.suggest_tools_for_task(
            self.specification
        )

        prompt = format_planning_prompt(enhanced_intent)
        plan = await self.providers["planning"].complete(prompt)
        return plan

    async def _decompose_plan(self, plan: str) -> List[Dict[str, Any]]:
        """Decompose the plan into concrete node configurations."""
        prompt = format_decomposition_prompt(plan)
        response = await self.providers["decomposition"].complete(prompt)

        try:
            data = json.loads(response)
            from typing import Dict, List, cast

            return cast(List[Dict[str, Any]], data.get("nodes", []))
        except json.JSONDecodeError:
            logger.error(f"Failed to parse decomposition JSON: {response}")
            # Fallback to simple tool node
            return [
                {
                    "id": "fallback_node",
                    "type": "tool",
                    "description": "Execute main task",
                    "config": {"tool_name": "hello"},
                    "dependencies": [],
                }
            ]

    async def _generate_diagram(self, nodes_data: List[Dict[str, Any]]) -> str:
        """Generate a Mermaid flowchart diagram."""
        prompt = format_mermaid_prompt(nodes_data)
        diagram = await self.providers["diagram"].complete(prompt)
        return diagram.strip()

    async def _generate_code(self, nodes_data: List[Dict[str, Any]]) -> Dict[str, str]:
        """Generate code implementations for nodes that need it."""
        # Filter nodes that need code
        code_nodes = [
            node
            for node in nodes_data
            if node["type"] in ["code", "tool"] and "code" not in node.get("config", {})
        ]

        if not code_nodes:
            return {}

        prompt = format_code_prompt(code_nodes)
        response = await self.providers["code"].complete(prompt)

        # Parse code blocks (simple extraction)
        implementations = {}
        current_node = None
        current_code: List[str] = []

        for line in response.split("\n"):
            if line.startswith("# Node:"):
                if current_node and current_code:
                    implementations[current_node] = "\n".join(current_code).strip()
                current_node = line.split(":")[-1].strip()

            elif current_node:
                current_code.append(line)

        # Don't forget the last node
        if current_node and current_code:
            implementations[current_node] = "\n".join(current_code).strip()

        return implementations

    def _assemble_blueprint(
        self,
        nodes_data: List[Dict[str, Any]],
        mermaid_diagram: str,
        code_implementations: Dict[str, str],
    ) -> Blueprint:
        """Assemble all components into a validated Blueprint."""
        pb = create_partial_blueprint("frosty_generated")
        pb.metadata = {"diagram": mermaid_diagram}

        # Create actual NodeConfig objects
        node_map: Dict[str, BaseNodeConfig] = {}

        for node_data in nodes_data:
            node_id = node_data["id"]
            node_type = node_data["type"]
            config = node_data.get("config", {})

            if node_type not in NODE_TYPE_PATTERNS:
                logger.warning("Unknown node type '%s', defaulting to LLM", node_type)
                node_type = "llm"

            NodeClass = NODE_TYPE_PATTERNS[node_type]
            fields: Dict[str, Any] = {"id": node_id}

            if node_type == "llm":
                fields.update(
                    {
                        "prompt": config.get(
                            "prompt", node_data.get("description", "Process input")
                        ),
                        "model": config.get("model", "gpt-4o-mini"),
                        "provider": ModelProvider.OPENAI,
                        "llm_config": LLMConfig(temperature=0.7),
                    }
                )
            elif node_type == "agent":
                fields.update(
                    {
                        "package": config.get("package", "ice_tools.base_agent"),
                        "agent_config": config.get("agent_config", {}),
                        "tools": config.get("tools", []),
                    }
                )
            elif node_type == "tool":
                fields.update(
                    {
                        "tool_name": config.get("tool_name", "hello"),
                        "tool_args": config.get("tool_args", {}),
                    }
                )
            elif node_type == "code":
                code_impl = code_implementations.get(node_id, config.get("code", ""))
                fields.update({"language": "python", "code": code_impl})
            elif node_type == "human":
                fields.update(
                    {
                        "prompt_message": config.get(
                            "prompt", "Please review and approve"
                        ),
                        "approval_type": config.get("approval_type", "approve_reject"),
                    }
                )
            else:
                # Fallback: merge config verbatim
                fields.update(config)

            # Construct without full validation to allow partial configs during generation
            node = NodeClass.model_construct(**fields)  # type: ignore[arg-type]

            # Set dependencies afterwards (skip validation for speed)
            node.dependencies = node_data.get("dependencies", [])  # type: ignore[attr-defined]

            node_map[node_id] = node  # type: ignore[arg-type]
            from ice_core.models.mcp import NodeSpec

            pb.nodes.append(NodeSpec.model_construct(**node.model_dump()))

        # Convert to full Blueprint with validation
        try:
            blueprint = Blueprint(**pb.model_dump())
            return blueprint
        except Exception as e:
            logger.error(f"Blueprint validation failed: {e}")
            raise RuntimeError(f"Failed to create valid blueprint: {e}")
