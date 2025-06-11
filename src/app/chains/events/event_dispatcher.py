import logging
from typing import Any, List, Optional

logger = logging.getLogger(__name__)


class EventDispatcher:
    """
    Handles callback/event registration and dispatch for ScriptChain events.
    Supports node_start, node_end, and node_error events.
    """

    def __init__(self, callbacks: Optional[List[Any]] = None):
        self.callbacks = callbacks or []

    def register(self, callback: Any):
        self.callbacks.append(callback)

    async def dispatch(self, event: str, data: Any):
        for callback in self.callbacks:
            try:
                if event == "node_start":
                    await callback.on_node_start(data)
                elif event == "node_end":
                    await callback.on_node_end(data)
                elif event == "node_error":
                    await callback.on_node_error(data)
            except Exception as e:
                logger.error(
                    f"Error in callback {callback.__class__.__name__}: {str(e)}"
                )
