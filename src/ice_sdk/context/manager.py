"""Context manager for graph execution."""
import logging
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional

import networkx as nx
from pydantic import BaseModel, Field

from ..tools.base import BaseTool, ToolContext
from .formatter import ContextFormatter
from .store import ContextStore

if TYPE_CHECKING:  # pragma: no cover
    from ..agents import AgentNode

logger = logging.getLogger(__name__)


class GraphContext(BaseModel):
    """Context for graph execution."""
    session_id: str
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
    ):
        """Create a ``GraphContextManager``.

        Args:
            max_tokens: Soft token window enforced when persisting context.
            max_sessions: Number of distinct *session_id*s to keep in memory
                before evicting the least-recently-used.  Old sessions can still
                be re-created on demand but any cached context is dropped.
        """
        from collections import OrderedDict

        self.max_tokens = max_tokens
        self.max_sessions = max_sessions
        self.graph = graph or nx.DiGraph()
        self.store = store or ContextStore()
        self.formatter = formatter or ContextFormatter()
        self._agents: Dict[str, 'AgentNode'] = {}
        self._tools: Dict[str, BaseTool] = {}
        # Map of session_id -> GraphContext (acts as LRU cache) --------------
        self._contexts: 'OrderedDict[str, GraphContext]' = OrderedDict()
        self._context: Optional[GraphContext] = None

    def register_agent(self, agent: 'AgentNode') -> None:
        """Register an agent for lookup by other agents."""
        if agent.config.name in self._agents:
            raise ValueError(f"Agent '{agent.config.name}' already registered")
        self._agents[agent.config.name] = agent

    def register_tool(self, tool: BaseTool) -> None:
        """Register a tool for use by agents.
        
        Args:
            tool: Tool to register
        """
        if tool.name in self._tools:
            raise ValueError(f"Tool '{tool.name}' already registered")
        self._tools[tool.name] = tool

    def get_agent(self, name: str) -> Optional['AgentNode']:
        """Look up an agent by name."""
        return self._agents.get(name)

    def get_tool(self, name: str) -> Optional[BaseTool]:
        """Get registered tool by name."""
        return self._tools.get(name)

    def get_all_agents(self) -> Dict[str, 'AgentNode']:
        """Get all registered agents."""
        return dict(self._agents)

    def get_all_tools(self) -> Dict[str, BaseTool]:
        """Get all registered tools."""
        return dict(self._tools)

    def get_context(self, session_id: Optional[str] = None) -> Optional[GraphContext]:
        """Return the current :class:`GraphContext`.

        When *session_id* is provided, the manager ensures that the returned
        context matches that ID—creating a **new** context if necessary.  This
        prevents different chains sharing a manager from leaking data into one
        another.
        """
        # No special handling requested – maintain legacy behaviour ----------
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

    async def execute_tool(
        self,
        tool_name: str,
        **kwargs
    ) -> Any:
        """Execute a tool with the current context.
        
        Args:
            tool_name: Name of tool to execute
            **kwargs: Tool arguments
        """
        tool = self.get_tool(tool_name)
        if not tool:
            raise ValueError(f"Tool '{tool_name}' not found")
            
        if not self._context:
            raise RuntimeError("No execution context set")
            
        # Create tool context
        tool_ctx = ToolContext(
            agent_id=self._context.session_id,
            session_id=self._context.execution_id or self._context.session_id,
            metadata=self._context.metadata
        )
        
        # Execute tool
        try:
            result = await tool.run(ctx=tool_ctx, **kwargs)
            return result
        except Exception as e:
            logger.error(f"Tool execution failed: {str(e)}")
            raise

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

            from ice_sdk.models.config import ModelProvider
            from ice_sdk.utils.token_counter import TokenCounter

            if isinstance(content, str):
                serialised = content
            else:
                try:
                    serialised = json.dumps(content, ensure_ascii=False, default=str)
                except TypeError:
                    serialised = str(content)

            current_tokens = TokenCounter.estimate_tokens(serialised, model="", provider=ModelProvider.CUSTOM)

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
        self,
        content: Any,
        rule: str,
        format_specs: Optional[Dict[str, Any]] = None
    ) -> str:
        """Format context content according to rules."""
        return self.formatter.format(content, rule, format_specs)

    def validate_context_rules(self, rules: Dict[str, Any]) -> bool:
        """Validate context rules against graph structure."""
        for node_id, rule in rules.items():
            if node_id not in self.graph.nodes:
                logger.warning(f"Context rule specified for non-existent node: {node_id}")
                return False
            if (
                hasattr(rule, "max_tokens")
                and rule.max_tokens
                and rule.max_tokens > self.max_tokens
            ):
                logger.warning(f"Context rule max_tokens exceeds system limit for node: {node_id}")
                return False
        return True

    def log_error(self, node_id: str, error: Exception) -> None:
        logger.error(f"Error in node {node_id}: {str(error)}")

    def list_agents(self) -> List[str]:
        """List registered agent names."""
        return list(self._agents.keys())

    def list_tools(self) -> List[str]:
        """List registered tool names."""
        return list(self._tools.keys())

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
        from ice_sdk.utils.token_counter import TokenCounter
        from ice_sdk.models.config import ModelProvider

        def _estimate_tokens(text: str) -> int:
            return TokenCounter.estimate_tokens(text, model="", provider=ModelProvider.CUSTOM)

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
                from ice_sdk.tools.builtins.deterministic import deterministic_summariser  # type: ignore

                summary = deterministic_summariser(content, schema=schema, max_tokens=effective_max_tokens)
                return summary
            except Exception:  # noqa: BLE001
                # Fall back to plain truncation when summarisation unavailable
                return self.smart_context_compression(
                    content,
                    schema=schema,
                    strategy="truncate",
                    max_tokens=effective_max_tokens,
                )

        # ------------------------------------------------------------------
        # Strategy: embed (TODO) -------------------------------------------
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
