from contextvars import ContextVar  # Track agent call stack across coroutines
from typing import Any, ClassVar, Dict, List, Optional

from ..context.manager import GraphContextManager
from ..exceptions import CycleDetectionError
from ..models.agent_models import AgentConfig
from ..models.config import LLMConfig, ModelProvider
from ..models.node_models import NodeExecutionResult
from ..providers.costs import calculate_cost
from ..tools.base import BaseTool

# Context-local stack of agent names to detect cycles -------------------------
_AGENT_CALL_STACK: ContextVar[list[str]] = ContextVar("_AGENT_CALL_STACK", default=[])


class AgentNode:
    """Agent node that can execute tools and generate responses."""

    def __init__(
        self,
        config: AgentConfig,
        context_manager: GraphContextManager,
        llm_service: Any = None,
    ):
        """Initialize agent node.

        Args:
            config: Agent configuration
            context_manager: Context manager
            llm_service: Optional LLM service
        """
        self.config = config
        self.context_manager = context_manager
        self.llm_service = llm_service
        # Tools explicitly declared in the config act as a *whitelist* that the
        # LLM planner can choose from.  Fall back to an empty list when the
        # user did not specify any tools in the ``AgentConfig`` (legacy
        # behaviour).
        self.tools: List[BaseTool] = list(config.tools or [])

    def as_tool(self, name: str, description: str) -> BaseTool:
        """Convert agent to tool.

        Args:
            name: Tool name
            description: Tool description
        """

        class AgentTool(BaseTool):
            name: ClassVar[str] = name  # type: ignore[misc]
            description: ClassVar[str] = description  # type: ignore[misc]
            parameters_schema: ClassVar[Dict[str, Any]] = {
                "type": "object",
                "properties": {
                    "input": {"type": "object", "description": "Input to agent"}
                },
                "required": ["input"],
            }

            # The parent ``AgentNode`` instance is patched onto the tool after
            # instantiation (see below).  Declare the attribute so that static
            # analysis is aware of it.
            agent: Optional["AgentNode"] = None  # type: ignore[assignment]

            async def run(self, input: Dict[str, Any], **_kwargs: Any) -> Any:  # type: ignore[override]
                """Execute the underlying agent while guarding against cycles."""
                assert self.agent is not None

                # ----------------------------------------------------------
                # Cycle detection using a context-local call stack
                # ----------------------------------------------------------
                stack = _AGENT_CALL_STACK.get().copy()
                current_agent_id = self.agent.config.name

                if current_agent_id in stack:
                    # Cycle detected → raise immediately to avoid infinite loop
                    cycle_path = " -> ".join(stack + [current_agent_id])
                    raise CycleDetectionError(cycle_path)

                # Push current agent on the stack and execute ----------------
                stack.append(current_agent_id)
                _AGENT_CALL_STACK.set(stack)

                try:
                    result = await self.agent.execute(input)
                finally:
                    # Pop after execution regardless of success/failure
                    stack.pop()
                    _AGENT_CALL_STACK.set(stack)

                return result.output

        tool = AgentTool()
        tool.agent = self
        return tool

    async def execute(self, input: Dict[str, Any]) -> NodeExecutionResult:
        """Execute agent with input.

        Args:
            input: Input to agent
        """
        import json
        import logging
        import time
        from datetime import datetime

        from ..core.validation import (  # pylint: disable=import-error
            SchemaValidationError,
            validate_or_raise,
        )
        from ..models.node_models import NodeMetadata, UsageMetadata

        logger = logging.getLogger(__name__)

        start_ts = time.perf_counter()

        # ------------------------------------------------------------------
        # 1. Fast input validation (best-effort) -----------------------------
        # ------------------------------------------------------------------
        try:
            validate_or_raise(input, getattr(self.config, "input_schema", None))  # type: ignore[arg-type]
        except SchemaValidationError as exc:
            metadata = NodeMetadata(  # type: ignore[call-arg]
                node_id=self.config.name,
                node_type="agent",
                start_time=datetime.utcnow(),
            )
            return NodeExecutionResult(  # type: ignore[call-arg]
                success=False, error=str(exc), metadata=metadata
            )

        # ------------------------------------------------------------------
        # 2. Prepare prompt & LLM service -----------------------------------
        # ------------------------------------------------------------------
        self.llm_service = self.llm_service or self.context_manager.get_tool(
            "__llm_service__"
        )  # may be None
        if self.llm_service is None:
            # Fallback – instantiate lazily to avoid import cycles at module top.
            from ..providers.llm_service import LLMService

            self.llm_service = LLMService()

        system_prompt = self.config.instructions
        user_content = (
            json.dumps(input, ensure_ascii=False)
            if not isinstance(input, str)
            else input
        )
        # --------------------------------------------------------------
        # Load & trim persistent conversation history ------------------
        # --------------------------------------------------------------
        history: List[dict[str, str]] = []
        summary_text: str | None = None
        if self.config.memory_enabled:
            previous = self.context_manager.get_node_context(self.config.name)
            if isinstance(previous, list):
                history = previous[-(self.config.memory_window * 2) :]
            # Retrieve existing long-term summary -----------------------
            summary_text = self.context_manager.get_node_context(
                f"{self.config.name}__summary"
            )

        summary_block: list[dict[str, str]] = (
            [{"role": "system", "content": f"Conversation summary: {summary_text}"}]
            if summary_text
            else []
        )

        conversation: list[dict[str, str]] = (
            [{"role": "system", "content": system_prompt}]
            + summary_block
            + history
            + [{"role": "user", "content": user_content}]
        )

        # Helpful metadata holder ------------------------------------------------
        metadata = NodeMetadata(  # type: ignore[call-arg]
            node_id=self.config.name, node_type="agent", start_time=datetime.utcnow()
        )

        # Convert *ModelSettings* to *LLMConfig* ---------------------------------
        model_settings = self.config.model_settings
        llm_config = LLMConfig(
            provider=model_settings.provider,
            model=model_settings.model or self.config.model,
            temperature=model_settings.temperature,
            max_tokens=model_settings.max_tokens,
        )

        # Pre-serialised list of tools in the structured format expected by
        # LLM providers that support *function calling*.
        tool_dicts = [tool.as_dict() for tool in self.tools]

        # ------------------------------------------------------------------
        # 3. LLM–tool loop --------------------------------------------------
        # ------------------------------------------------------------------
        MAX_ROUNDS = self.config.max_rounds  # honour per-agent override
        aggregate_usage: dict[str, int] = {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
        }

        tool_result_cache: dict[str, Any] = {}
        final_output: Any | None = None

        for round_idx in range(MAX_ROUNDS):
            prompt = "\n".join(
                [f"{msg['role'].upper()}: {msg['content']}" for msg in conversation]
            )

            text, usage, error = await self.llm_service.generate(  # type: ignore[attr-defined]
                llm_config=llm_config,
                prompt=prompt,
                context={},
                tools=tool_dicts or None,
            )

            # Update token usage aggregator --------------------------------
            if usage:
                for k in aggregate_usage.keys():
                    aggregate_usage[k] += usage.get(k, 0)

            if error:
                logger.warning("LLMService returned error: %s", error)
                return NodeExecutionResult(  # type: ignore[call-arg]
                    success=False,
                    error=error,
                    metadata=metadata,
                    usage=UsageMetadata(
                        prompt_tokens=aggregate_usage["prompt_tokens"],
                        completion_tokens=aggregate_usage["completion_tokens"],
                        total_tokens=aggregate_usage["total_tokens"],
                        cost=0.0,
                        api_calls=round_idx + 1,
                        model=llm_config.model or "unknown",
                        node_id=self.config.name,
                        provider=ModelProvider(llm_config.provider or "openai"),
                    ),
                )

            # Try to parse JSON tool call -----------------------------------
            try:
                payload = json.loads(text)
            except json.JSONDecodeError:
                # Consider raw text the final answer
                final_output = text
                break

            if isinstance(payload, dict) and "tool_name" in payload:
                tool_name = payload["tool_name"]
                args = payload.get("arguments", {})

                # Avoid infinite loops where the LLM keeps invoking the same tool
                cache_key = f"{tool_name}:{json.dumps(args, sort_keys=True)}"
                if cache_key in tool_result_cache:
                    logger.warning("Repeated tool invocation detected, aborting loop")
                    final_output = str(tool_result_cache[cache_key])
                    break

                # ------------------------------------------------------------------
                # 3a. Tool whitelist enforcement -----------------------------------
                # ------------------------------------------------------------------
                if self.tools and tool_name not in [t.name for t in self.tools]:
                    err_msg = (
                        f"Tool '{tool_name}' is not allowed by agent configuration"
                    )
                    logger.error(err_msg)
                    return NodeExecutionResult(  # type: ignore[call-arg]
                        success=False,
                        error=err_msg,
                        metadata=metadata,
                    )

                # Execute tool --------------------------------------------------
                try:
                    tool_result = await self.context_manager.execute_tool(tool_name, **args)  # type: ignore[arg-type]
                except Exception as exc:  # pylint: disable=broad-except
                    err_msg = f"Tool '{tool_name}' failed: {exc}"
                    logger.error(err_msg)
                    return NodeExecutionResult(  # type: ignore[call-arg]
                        success=False, error=err_msg, metadata=metadata
                    )

                tool_result_cache[cache_key] = tool_result

                # Feed tool result back into the conversation and continue ----
                conversation.append({"role": "assistant", "content": text})
                conversation.append({"role": "tool", "content": str(tool_result)})
                continue  # next round with updated context

            # If the payload is JSON but not a valid tool call, use as output --
            final_output = payload
            break

        # ------------------------------------------------------------------
        # 4. Build NodeExecutionResult --------------------------------------
        # ------------------------------------------------------------------
        duration = time.perf_counter() - start_ts

        usage_meta = UsageMetadata(
            prompt_tokens=aggregate_usage["prompt_tokens"],
            completion_tokens=aggregate_usage["completion_tokens"],
            total_tokens=aggregate_usage["total_tokens"],
            cost=float(
                calculate_cost(
                    provider=ModelProvider(llm_config.provider or "openai"),
                    model=llm_config.model or "unknown",
                    prompt_tokens=aggregate_usage["prompt_tokens"],
                    completion_tokens=aggregate_usage["completion_tokens"],
                )
            ),
            api_calls=min(round_idx + 1, MAX_ROUNDS),
            model=llm_config.model or "unknown",
            node_id=self.config.name,
            provider=ModelProvider(llm_config.provider or "openai"),
        )

        metadata.end_time = datetime.utcnow()
        metadata.duration = duration

        # --------------------------------------------------------------
        # Persist trimmed conversation history for future invocations ---
        # --------------------------------------------------------------
        if self.config.memory_enabled:
            # Summarise *overflow* messages when dialog grows too large ----
            if len(conversation) > self.config.memory_window * 4:
                overflow = conversation[: -self.config.memory_window * 2]
                try:
                    summary = self.context_manager.smart_context_compression(
                        overflow, strategy="summarize", max_tokens=200
                    )
                    self.context_manager.update_node_context(
                        f"{self.config.name}__summary", summary
                    )
                except Exception:
                    pass  # summary is best-effort

            try:
                self.context_manager.update_node_context(
                    self.config.name,
                    conversation[-(self.config.memory_window * 2) :],
                )
            except Exception:
                # Persistence errors must never break agent execution
                pass

        return NodeExecutionResult(  # type: ignore[call-arg]
            success=True,
            output=final_output,
            metadata=metadata,
            usage=usage_meta,
            execution_time=duration,
        )

    # ------------------------------------------------------------------
    # Memory helpers ----------------------------------------------------
    # ------------------------------------------------------------------

    async def recall(self, query: str, k: int = 5):  # noqa: D401 – helper name
        """Retrieve similar snippets from the pluggable memory adapter.

        Example
        -------
        >>> snippets = await agent.recall("Paris", k=3)
        >>> for text, score in snippets:
        ...     print(text, score)
        """
        try:
            memory = getattr(self.context_manager, "memory", None)
            if memory is None:
                return []
            return await memory.retrieve(query, k=k)  # type: ignore[attr-defined]
        except Exception:  # pragma: no cover – defensive blanket
            return []
