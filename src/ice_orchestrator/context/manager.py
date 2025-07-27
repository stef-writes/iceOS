"""Context manager for graph execution."""

import logging
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union, cast
from collections import OrderedDict, defaultdict

import networkx as nx
from pydantic import BaseModel, Field

from ice_sdk.services import ServiceLocator  # new
from ice_core.base_tool import ToolBase
from ice_core.models.enums import NodeType
from .types import ToolContext

# Unified tool execution via ToolService -------------------------------
# Tools are executed via tool execution service

# Local first-party imports (alphabetical) ---------------------------
from .formatter import ContextFormatter
from .memory import BaseMemory, NullMemory  # simplified memory adapter
from .store import ContextStore

if TYPE_CHECKING:  # pragma: no cover
    from ..agents import AgentNode

logger = logging.getLogger(__name__)

class GraphContext(BaseModel):
    """Context for graph execution."""

    session_id: str
    tenant: Optional[str] = None
    metadata: Dict[str, Any] = {}
    execution_id: Optional[str] = None
    start_time: datetime = Field(default_factory=datetime.utcnow)

class GraphContextManager:
    """
    Orchestrates context management for graph-based LLM node execution.
    Handles tool execution, context flow, and agent coordination.
    """

    def __init__(
        self,
        max_tokens: int = 4000,
        *,
        max_sessions: int = 10,
        graph: Optional[nx.DiGraph] = None,
        store: Optional[ContextStore] = None,
        formatter: Optional[ContextFormatter] = None,
        memory: Optional[BaseMemory] = None,
        project_root: Optional[Path] = None,
    ):
        """Create a ``GraphContextManager``.

        Args:
            max_tokens: Soft token window enforced when persisting context.
            max_sessions: Number of distinct *session_id*s to keep in memory
                before evicting the least-recently-used.  Old sessions can still
                be re-created on demand but any cached context is dropped.
            graph: Pre-existing execution graph to use.  Creates a new empty
                graph by default.
            store: Backing store for context persistence.  Creates an in-memory
                store by default.
            formatter: Custom formatter for rendering context as text.
            memory: Long-term memory implementation.
            project_root: Root directory for the project (defaults to current working directory).
        """
        from collections import OrderedDict

        self.max_tokens = max_tokens
        self.max_sessions = max_sessions
        self.graph = graph or nx.DiGraph()
        self.store = store or ContextStore()
        self.formatter = formatter or ContextFormatter()
        # Memory adapter ---------------------------------------------------
        self.memory: BaseMemory = memory or NullMemory()
        # 🚀 UNIFIED NESTED STRUCTURE: Better organization like registry pattern
        self._nodes: Dict[NodeType, Dict[str, Union["AgentNode", ToolBase]]] = defaultdict(dict)
        # Map of session_id -> GraphContext (acts as LRU cache) --------------
        self._contexts: "OrderedDict[str, GraphContext]" = OrderedDict()
        self._context: Optional[GraphContext] = None

        # Tool service is accessed via ServiceLocator when needed
        self._project_root = project_root or Path.cwd()

    def register_agent(self, agent: "AgentNode") -> None:
        """🚀 Register an agent using nested structure for better organization."""
        if agent.config.name in self._nodes[NodeType.AGENT]:
            raise ValueError(f"Agent '{agent.config.name}' already registered")
        self._nodes[NodeType.AGENT][agent.config.name] = agent

    def register_tool(self, tool: ToolBase) -> None:
        """🚀 Register a tool using nested structure for better organization.

        Args:
            tool: Tool to register
        """
        if tool.name in self._nodes[NodeType.TOOL]:
            raise ValueError(f"Tool '{tool.name}' already registered")
        self._nodes[NodeType.TOOL][tool.name] = tool

        # Register tool CLASS with ToolService for unified execution ----
        try:
            # Tools are auto-registered via @tool decorator
            pass
        except ValueError:
            # Ignore duplicate class registration
            pass

    def get_agent(self, name: str) -> Optional["AgentNode"]:
        """Look up an agent by name."""
        return self._nodes[NodeType.AGENT].get(name)

    def get_tool(self, name: str) -> Optional[ToolBase]:
        """🚀 Get registered tool by name using nested structure."""
        return self._nodes[NodeType.TOOL].get(name)

    def get_all_agents(self) -> Dict[str, "AgentNode"]:
        """🚀 Get all registered agents from nested structure."""
        return dict(self._nodes[NodeType.AGENT])

    def get_all_tools(self) -> Dict[str, ToolBase]:
        """🚀 Get all registered tools from nested structure."""
        return dict(self._nodes[NodeType.TOOL])

    def get_context(self, session_id: Optional[str] = None) -> Optional[GraphContext]:
        """Return the current :class:`GraphContext`.

        When *session_id* is provided, the manager ensures that the returned
        context matches that ID—creating a **new** context if necessary.  This
        prevents different chains sharing a manager from leaking data into one
        another.
        """
        # Use default behavior for context management
        if session_id is None:
            return self._context

        # No context yet or session mismatch → start/rotate ------------------
        if self._context is None or self._context.session_id != session_id:
            self._context = GraphContext(session_id=session_id)
            self._register_context(self._context)

        return self._context

    def set_context(self, context: GraphContext) -> None:
        """Set execution context."""
        self._context = context
        self._register_context(context)

    async def execute_tool(self, tool_name: str, **kwargs: Any) -> Any:
        """Execute a tool with the current context.

        Args:
            tool_name: Name of tool to execute
            **kwargs: Tool arguments
        """
        # Ensure we are within an execution context -----------------------
        if not self._context:
            raise RuntimeError("No execution context set")

        # Build minimal ctx dict expected by ToolService → ToolContext
        ctx_payload = {
            "agent_id": self._context.session_id,
            "session_id": self._context.execution_id or self._context.session_id,
            "metadata": self._context.metadata,
        }

        # 🚀 Prefer pre-instantiated tool instance from nested structure -----
        stateful_tool = self._nodes[NodeType.TOOL].get(tool_name)
        if stateful_tool is not None:
            try:
                call_kwargs = dict(kwargs)
                call_kwargs["ctx"] = ToolContext(**ctx_payload)  # type: ignore[arg-type]

                try:
                    result_obj = stateful_tool.run(**call_kwargs)  # type: ignore[arg-type]

                    import inspect

                    if inspect.isawaitable(result_obj):
                        result = await result_obj  # type: ignore[assignment]
                    else:
                        result = result_obj  # type: ignore[assignment]
                except TypeError as exc:
                    if "ctx" in str(exc):
                        # Retry without ctx when tool doesn't expect it ----
                        call_kwargs.pop("ctx", None)
                        result_obj = stateful_tool.run(**call_kwargs)  # type: ignore[arg-type]
                        if inspect.isawaitable(result_obj):
                            result = await result_obj  # type: ignore[assignment]
                        else:
                            result = result_obj  # type: ignore[assignment]
                    else:
                        raise
                return result
            except Exception as e:
                logger.error("Tool execution failed (stateful path): %s", e)
                raise

        # Execute tool directly via tool execution service
        tool_service = ServiceLocator.get("tool_execution_service")
        if tool_service:
            return await tool_service.execute_tool(tool_name, kwargs, ctx_payload)
        else:
            raise RuntimeError("Tool execution service not available")

    def update_node_context(
        self,
        node_id: str,
        content: Any,
        execution_id: Optional[str] = None,
        schema: Optional[Dict[str, str]] = None,
    ) -> None:
        """Update context for a specific node."""
        # ------------------------------------------------------------------
        # Enforce *max_tokens* window per GraphContextManager configuration --
        # ------------------------------------------------------------------
        try:
            # Serialize *content* for counting/truncation.  Non-string payloads
            # are converted to JSON-ish string so the token approximation is
            # still meaningful.
            import json

            from ice_core.models import ModelProvider
            from ice_core.utils.token_counter import TokenCounter

            if isinstance(content, str):
                serialised = content
            else:
                try:
                    serialised = json.dumps(content, ensure_ascii=False, default=str)
                except TypeError:
                    serialised = str(content)

            current_tokens = TokenCounter.estimate_tokens(
                serialised, model="", provider=ModelProvider.CUSTOM
            )

            if self.max_tokens and current_tokens > self.max_tokens:
                # Truncate string representation to fit token budget (≈4 chars/token)
                char_budget = self.max_tokens * 4
                serialised = serialised[:char_budget]

                # Try to re-parse back to original type when possible ---------
                try:
                    truncated_content = json.loads(serialised)
                except Exception:
                    truncated_content = serialised
                content = truncated_content
        except Exception:  # pragma: no cover – fallback when tiktoken missing
            # On failure, fall back to char-length based heuristic.
            if self.max_tokens and isinstance(content, str):
                char_budget = self.max_tokens * 4
                if len(content) > char_budget:
                    content = content[:char_budget]

        # Persist via underlying store --------------------------------------
        self.store.update(node_id, content, execution_id=execution_id, schema=schema)

    def get_node_context(self, node_id: str) -> Any:
        """Get context for a specific node."""
        return self.store.get(node_id)

    def clear_node_context(self, node_id: Optional[str] = None) -> None:
        """Clear context for a specific node or all nodes."""
        self.store.clear(node_id)

    def format_context(
        self, content: Any, rule: str, format_specs: Optional[Dict[str, Any]] = None
    ) -> str:
        """Format context content according to rules."""
        return self.formatter.format(content, rule, format_specs)

    async def _apply_formatter(self, value: Any) -> Any:
        """Apply the configured formatter to *value* if it is a string.

        The formatter may be implemented as a synchronous **or** asynchronous
        callable.  We therefore detect coroutine results at runtime and await
        them when necessary.  Non-string payloads are forwarded unchanged.
        """
        if isinstance(value, str) and self.formatter:
            # Pass an empty rule object when formatting ad-hoc strings -------
            result = self.formatter.format(value, rule="", format_specs=None)  # type: ignore[arg-type]
            import inspect

            if inspect.isawaitable(result):
                return await result  # type: ignore[return-value]
            return result
        return value

    def validate_context_rules(self, rules: Dict[str, Any]) -> bool:
        """Validate context rules against graph structure."""
        for node_id, rule in rules.items():
            if node_id not in self.graph.nodes:
                logger.warning(
                    f"Context rule specified for non-existent node: {node_id}"
                )
                return False
            if (
                hasattr(rule, "max_tokens")
                and rule.max_tokens
                and rule.max_tokens > self.max_tokens
            ):
                logger.warning(
                    f"Context rule max_tokens exceeds system limit for node: {node_id}"
                )
                return False
        return True

    def log_error(self, node_id: str, error: Exception) -> None:
        logger.error(f"Error in node {node_id}: {str(error)}")

    def list_agents(self) -> List[str]:
        """🚀 List registered agent names from nested structure."""
        return list(self._nodes[NodeType.AGENT].keys())

    def list_tools(self) -> List[str]:
        """🚀 List registered tool names from nested structure."""
        return list(self._nodes[NodeType.TOOL].keys())
    
    # 🚀 NEW: High-performance analytics methods
    def get_nodes_by_type(self, node_type: NodeType) -> Dict[str, Union["AgentNode", ToolBase]]:
        """Get all nodes of a specific type - perfect for monitoring!"""
        return dict(self._nodes.get(node_type, {}))
    
    def get_registered_node_types(self) -> List[NodeType]:
        """List all node types that have registrations - great for dashboard!"""
        return list(self._nodes.keys())
    
    def get_registration_summary(self) -> Dict[str, Dict[str, Any]]:
        """🚀 Get comprehensive registration summary by node type - ultimate overview!"""
        summary = {}
        for node_type in self.get_registered_node_types():
            nodes = self.get_nodes_by_type(node_type)
            summary[node_type.value] = {
                "count": len(nodes),
                "names": list(nodes.keys()),
                "types": [type(node).__name__ for node in nodes.values()]
            }
        return summary

    # ------------------------------------------------------------------
    # Experimental helpers ---------------------------------------------
    # ------------------------------------------------------------------

    def smart_context_compression(
        self,
        content: Any,
        *,
        schema: Optional[Dict[str, Any]] = None,
        strategy: str = "summarize",
        max_tokens: Optional[int] = None,
    ) -> Any:
        """Return a compressed variant of *content* according to *strategy*.

        This helper is **best-effort** and deliberately side-effect-free; it is
        safe to call within hot code-paths (e.g. during context updates).

        Parameters
        ----------
        content
            Arbitrary serialisable payload to compress.
        schema
            Optional type/schema information that can guide the compression
            algorithm (e.g. know which keys are essential).
        strategy
            Supported values:
            ``"summarize"``  – Short text summary (default)
            ``"truncate"``   – Hard trim to *max_tokens* (or manager-level limit)
            ``"embed"``      – Placeholder for embedding-based selection
        max_tokens
            Optional override for the *GraphContextManager.max_tokens* limit.
        """

        # Fallback defaults --------------------------------------------
        effective_max_tokens = max_tokens or self.max_tokens

        # Import token counter lazily to avoid heavy startup costs
        from ice_core.models import ModelProvider
        from ice_core.utils.token_counter import TokenCounter

        def _estimate_tokens(text: str) -> int:
            """Return token estimate for *text* as *int*."""
            return TokenCounter.estimate_tokens(
                text, model="", provider=ModelProvider.CUSTOM
            )

        # ------------------------------------------------------------------
        # Strategy: truncate (cheap) ---------------------------------------
        # ------------------------------------------------------------------
        if strategy == "truncate":
            if isinstance(content, str):
                tokens = _estimate_tokens(content)
                if effective_max_tokens and tokens > effective_max_tokens:
                    char_budget = effective_max_tokens * 4  # ≈4 chars/token
                    return content[:char_budget]
            return content  # nothing to do or non-str payload

        # ------------------------------------------------------------------
        # Strategy: summarize (LLM heavy) ----------------------------------
        # ------------------------------------------------------------------
        if strategy == "summarize":
            try:
                # Defer import – summariser is optional dependency
                from ice_core.utils.text import deterministic_summariser

                summary = deterministic_summariser(
                    content, schema=schema, max_tokens=effective_max_tokens
                )
                return summary
            except Exception:
                # Fall back to plain truncation when summarisation unavailable
                return self.smart_context_compression(
                    content,
                    schema=schema,
                    strategy="truncate",
                    max_tokens=effective_max_tokens,
                )

        # ------------------------------------------------------------------
        # Strategy: embed (placeholder – to be implemented) ----------------
        # ------------------------------------------------------------------
        if strategy == "embed":
            # Placeholder – will be implemented when embedding service lands
            return self.smart_context_compression(
                content,
                schema=schema,
                strategy="truncate",
                max_tokens=effective_max_tokens,
            )

        # Unknown strategy → pass through unchanged ------------------------
        return content

    # ------------------------------------------------------------------
    # Internal helpers ---------------------------------------------------
    # ------------------------------------------------------------------
    def _register_context(self, ctx: GraphContext) -> None:
        """Insert *ctx* into the LRU map and evict when necessary."""
        # Pop existing entry so we can push it to the right end (most recent)
        self._contexts.pop(ctx.session_id, None)
        self._contexts[ctx.session_id] = ctx

        # Evict oldest sessions above limit --------------------------------
        while len(self._contexts) > self.max_sessions:
            old_sess, _ = self._contexts.popitem(last=False)
            # Purge persisted node-context data for the evicted session -----
            # We assume node_ids are prefixed with session_id or otherwise
            # unique; if not, users can still call ContextStore.clear().
            # Here we only drop the in-memory reference.
            if self._context and self._context.session_id == old_sess:
                self._context = None
