"""
Concrete node implementations using the data models
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from app.models.config import LLMConfig, MessageTemplate

# Existing imports
# This is a test comment to trigger reload
from app.models.node_models import NodeConfig, NodeExecutionResult, NodeMetadata
from app.nodes.ai.llm_executor import llm_execute
from app.nodes.utils.error_handling import OpenAIErrorHandler

# Local imports --------------------------------------------------------------
from app.nodes.utils.prompt_builder import build_tool_preamble, prepare_prompt
from app.services.llm_service import LLMService
from app.utils.callbacks import ScriptChainCallback
from app.utils.context.manager import GraphContextManager
from app.utils.logging import logger
from ice_sdk import ToolService
from ice_sdk.base_node import BaseNode


class AiNode(BaseNode):
    """AI-powered node supporting LLM text generation and tool/function calling"""

    def __init__(
        self,
        config: NodeConfig,
        context_manager: GraphContextManager,
        llm_config: LLMConfig,
        callbacks: Optional[List[ScriptChainCallback]] = None,
        llm_service: Optional[LLMService] = None,
        tool_service: Optional[ToolService] = None,
        workflow_context=None,
    ):
        """Initialize AI node with LLM and Tool services."""
        super().__init__(config)
        self.context_manager = context_manager
        self._llm_config = llm_config
        self.callbacks = callbacks or []
        self.llm_service = llm_service or LLMService()
        self.tool_service = tool_service or ToolService()
        self.workflow_context = workflow_context

    def __getattr__(self, name: str) -> Any:
        """Allow direct access to config attributes."""
        if hasattr(self.config, name):
            return getattr(self.config, name)
        raise AttributeError(f"'AiNode' object has no attribute '{name}'")

    def build_tool_preamble(self, tools: list) -> str:
        """Generate a human-readable preamble describing available tools, their parameters, and usage examples."""
        return build_tool_preamble(tools)

    async def prepare_prompt(self, inputs: Dict[str, Any]) -> str:
        """Prepare prompt with selected context from inputs, including a tool preamble if tools are available."""
        return await prepare_prompt(
            self.config,
            self.context_manager,
            self._llm_config,
            self.tool_service,
            inputs,
            workflow_context=self.workflow_context,
        )

    def _truncate_prompt(self, prompt: str, current_tokens: int) -> str:
        """Truncate prompt to fit within token limit.

        Args:
            prompt: Prompt to truncate
            current_tokens: Current token count

        Returns:
            Truncated prompt
        """
        max_tokens = (
            self._llm_config.max_context_tokens
            if self._llm_config.max_context_tokens is not None
            else 4096
        )
        if current_tokens <= max_tokens:
            return prompt

        # Calculate how many tokens to remove
        tokens_to_remove = current_tokens - max_tokens

        # Estimate characters to remove (roughly 4 chars per token)
        chars_to_remove = tokens_to_remove * 4

        # Truncate from the end, preserving complete sentences
        truncated = prompt[:-chars_to_remove]
        last_period = truncated.rfind(".")
        if last_period > 0:
            truncated = truncated[: last_period + 1]

        return truncated

    def _prepare_messages(self, context: Optional[Dict] = None) -> List[Dict[str, str]]:
        """Prepare messages for the API call.

        Args:
            context: Optional context data

        Returns:
            List of message dictionaries
        """
        messages = []
        context = context or {}

        # Add system message if available
        if self.config.templates and "system" in self.config.templates:
            try:
                system_content = self.config.templates["system"].format(**context)
                messages.append({"role": "system", "content": system_content})
            except KeyError as e:
                logger.warning(f"Missing context key for system message: {e}")

        # Add user message
        try:
            user_content = self.config.prompt.format(**context)
            messages.append({"role": "user", "content": user_content})
        except KeyError as e:
            raise ValueError(f"Missing required context key: {e}")

        return messages

    async def execute(
        self, context: Dict[str, Any] = None, max_steps: int = 5
    ) -> NodeExecutionResult:
        """
        Execute the node: if type is 'tool', run the tool directly; otherwise, run the LLM (with tool-calling enabled).
        """
        # Always execute as an LLM-powered node. Deterministic tools are handled by the
        # dedicated `ToolNode` class.  This keeps the responsibility boundaries clear.

        return await llm_execute(
            config=self.config,
            context_manager=self.context_manager,
            llm_config=self._llm_config,
            llm_service=self.llm_service,
            tool_service=self.tool_service,
            context=context,
            max_steps=max_steps,
            workflow_context=self.workflow_context,
        )

    def validate_inputs(self, inputs: Dict[str, Any]) -> bool:
        """Validate input data against schema (dict or Pydantic model)."""
        # Allow context-driven schema adaptation
        if hasattr(self.config, "adapt_schema_from_context"):
            self.config.adapt_schema_from_context(inputs)
        schema = self.config.input_schema
        if not schema:
            return True
        if hasattr(
            self.config, "is_pydantic_schema"
        ) and self.config.is_pydantic_schema(schema):
            try:
                schema.model_validate(inputs)
                return True
            except Exception:
                return False
        # Fallback to dict-based validation
        try:
            fields = {key: (eval(type_str), ...) for key, type_str in schema.items()}
            from pydantic import ValidationError, create_model

            InputModel = create_model("InputModel", **fields)
            InputModel(**inputs)
            return True
        except (ValidationError, NameError, SyntaxError):
            return False

    def _calculate_cost(self, usage: Dict[str, int]) -> float:
        """Calculate the cost of the API call.

        Args:
            usage: Token usage data

        Returns:
            Cost in USD
        """
        # TODO: Implement cost calculation based on model and provider
        return 0.0

    @property
    def input_keys(self) -> List[str]:
        """Get list of input keys."""
        return list(self.config.input_schema.keys()) if self.config.input_schema else []

    @property
    def output_keys(self) -> List[str]:
        """Get list of output keys."""
        return (
            list(self.config.output_schema.keys()) if self.config.output_schema else []
        )

    def get_template(self, role: str) -> MessageTemplate:
        """Get message template for a role.

        Args:
            role: Message role

        Returns:
            MessageTemplate object
        """
        if not self.config.templates or role not in self.config.templates:
            return None
        return self.config.templates[role]

    def _format_error(self, error: Exception) -> str:
        """Format error message using centralized error handler."""
        return OpenAIErrorHandler.format_error_message(error)

    def _update_execution_stats(self, result: NodeExecutionResult):
        """Update execution statistics."""
        if result.usage:
            self.metrics["total_tokens"] += result.usage["total_tokens"]
            self.metrics["token_usage"][self._llm_config.provider] = result.usage

    def _create_error_metadata(
        self, start_time: datetime, error_type_str: str
    ) -> NodeMetadata:
        """Helper to create metadata for error results."""
        return NodeMetadata(
            node_id=self.config.id,
            node_type=self.config.type,
            version=self.config.metadata.version if self.config.metadata else "1.0.0",
            start_time=start_time,
            end_time=datetime.utcnow(),
            duration=(datetime.utcnow() - start_time).total_seconds(),
            error_type=error_type_str,
            provider=self.config.provider,
        )
