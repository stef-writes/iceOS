"""EnterpriseKBNode – bridges *KnowledgeService* with ScriptChain execution.

The node is **async** and returns a fully-populated ``NodeExecutionResult`` so
that it integrates seamlessly with the orchestrator.  It *does not* depend on
LLM providers directly; instead, it exposes *context* chunks that downstream
AI nodes can include in their prompt.
"""

from __future__ import annotations

from typing import Any, Dict

from ice_core.models import NodeMetadata
from ice_sdk.base_node import BaseNode
from ice_sdk.models.node_models import NodeConfig, NodeExecutionResult
from iceos.services.document_processor import DocumentProcessor
from iceos.services.knowledge_service import KnowledgeConfig, KnowledgeService

__all__ = ["EnterpriseKBNode"]


class EnterpriseKBNode(BaseNode):
    """Node wrapping :class:`iceos.services.knowledge_service.KnowledgeService`."""

    def __init__(self, config: NodeConfig):  # noqa: D401 – constructor
        super().__init__(config)
        params: Dict[str, Any] = getattr(config, "params", {})  # legacy shim
        self._kb_service = KnowledgeService(KnowledgeConfig(**params))
        self._processor = DocumentProcessor(self._kb_service)
        # Non-blocking start – watchdog spins its own thread
        self._processor.start_watching()

    # ------------------------------------------------------------------
    # Validation --------------------------------------------------------
    # ------------------------------------------------------------------
    def validate(self) -> None:  # noqa: D401 – required by repo rule 13
        if not self._kb_service.config.watch_dirs:
            raise ValueError("EnterpriseKBNode requires at least one watch directory")

    # ------------------------------------------------------------------
    # Execution ---------------------------------------------------------
    # ------------------------------------------------------------------
    async def execute(self, input_data: Dict[str, Any]) -> NodeExecutionResult:  # type: ignore[override]
        """Return documents relevant to *input_data['query']*."""

        query: str = str(input_data.get("query", ""))
        docs = await self._kb_service.query(query)

        output: Dict[str, Any] = {
            "context": [doc["document"] for doc in docs],
            "sources": [doc["metadata"]["source"] for doc in docs],
        }

        metadata = NodeMetadata(node_id=self.config.id, node_type="knowledge")
        return NodeExecutionResult(success=True, output=output, metadata=metadata)
