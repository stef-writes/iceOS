import logging
from typing import Any, Dict, Optional

import networkx as nx

from .formatter import ContextFormatter
from .store import ContextStore

logger = logging.getLogger(__name__)


class GraphContextManager:
    """
    Orchestrates context management for graph-based LLM node execution.
    Delegates storage and formatting to ContextStore and ContextFormatter.
    """

    def __init__(
        self,
        max_tokens: int = 4000,
        graph: Optional[nx.DiGraph] = None,
        store: Optional[ContextStore] = None,
        formatter: Optional[ContextFormatter] = None,
    ):
        self.max_tokens = max_tokens
        self.graph = graph or nx.DiGraph()
        self.store = store or ContextStore()
        self.formatter = formatter or ContextFormatter()

    def get_node_output(self, node_id: str) -> Any:
        return self.store.get(node_id)

    def get_context(self, node_id: str) -> Dict[str, Any]:
        return self.store.get(node_id)

    def set_context(
        self,
        node_id: str,
        context: Dict[str, Any],
        schema: Optional[Dict[str, str]] = None,
    ) -> None:
        self.store.set(node_id, context, schema=schema)

    def update_context(
        self,
        node_id: str,
        content: Any,
        execution_id: Optional[str] = None,
        schema: Optional[Dict[str, str]] = None,
    ) -> None:
        self.store.update(node_id, content, execution_id=execution_id, schema=schema)

    def clear_context(self, node_id: Optional[str] = None) -> None:
        self.store.clear(node_id)

    def format_context(
        self, content: Any, rule, format_specs: Optional[Dict[str, Any]] = None
    ) -> str:
        return self.formatter.format(content, rule, format_specs)

    def validate_context_rules(self, rules: Dict[str, Any]) -> bool:
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
