import logging
from datetime import datetime
from typing import Any, Dict, List

from app.models.node_models import NodeConfig, NodeExecutionResult
from app.utils.callbacks import ScriptChainCallback

logger = logging.getLogger(__name__)


class DebugCallback(ScriptChainCallback):
    """Debug callback implementation that logs all chain events."""

    def __init__(self):
        """Initialize the debug callback."""
        self.events: List[Dict[str, Any]] = []

    async def on_chain_start(self, chain_id: str, config: Dict[str, Any]) -> None:
        """Log chain start event."""
        event = {
            "type": "chain_start",
            "chain_id": chain_id,
            "config": config,
            "timestamp": datetime.utcnow().isoformat(),
        }
        self.events.append(event)
        logger.debug(f"Chain {chain_id} started with config: {config}")

    async def on_chain_end(self, chain_id: str, result: Dict[str, Any]) -> None:
        """Log chain end event."""
        event = {
            "type": "chain_end",
            "chain_id": chain_id,
            "result": result,
            "timestamp": datetime.utcnow().isoformat(),
        }
        self.events.append(event)
        logger.debug(f"Chain {chain_id} ended with result: {result}")

    async def on_node_start(self, node_id: str, config: NodeConfig) -> None:
        """Log node start event."""
        event = {
            "type": "node_start",
            "node_id": node_id,
            "config": config,
            "timestamp": datetime.utcnow().isoformat(),
        }
        self.events.append(event)
        logger.debug(f"Node {node_id} started with config: {config}")

    async def on_node_complete(self, node_id: str, result: NodeExecutionResult) -> None:
        """Log node completion event."""
        event = {
            "type": "node_complete",
            "node_id": node_id,
            "result": result,
            "timestamp": datetime.utcnow().isoformat(),
        }
        self.events.append(event)
        logger.debug(f"Node {node_id} completed with result: {result}")

    async def on_node_error(self, node_id: str, error: Exception) -> None:
        """Log node error event."""
        event = {
            "type": "node_error",
            "node_id": node_id,
            "error": str(error),
            "timestamp": datetime.utcnow().isoformat(),
        }
        self.events.append(event)
        logger.error(f"Node {node_id} encountered error: {error}")

    async def on_context_update(self, node_id: str, context: Dict[str, Any]) -> None:
        """Log context update event."""
        event = {
            "type": "context_update",
            "node_id": node_id,
            "context": context,
            "timestamp": datetime.utcnow().isoformat(),
        }
        self.events.append(event)
        logger.debug(f"Context updated for node {node_id}: {context}")

    def get_events(self) -> List[Dict[str, Any]]:
        """Get all logged events.

        Returns:
            List of event dictionaries
        """
        return self.events
