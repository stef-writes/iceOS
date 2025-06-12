"""
Callback handlers for ScriptChain execution events.

This module provides a set of callback handlers for monitoring and tracking ScriptChain execution:

1. ScriptChainCallback: Abstract base class defining the callback interface
2. LoggingCallback: Basic logging for production use
3. MetricsCallback: Performance and usage metrics collection

For debugging purposes, see debug_callback.py which provides the DebugCallback class
with more detailed event tracking and analysis capabilities.
"""

import json
import logging
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from ice_sdk.utils.logging import logger


class ScriptChainCallback(ABC):
    """Abstract base class for ScriptChain callbacks"""

    @abstractmethod
    def on_chain_start(self, chain_id: str, inputs: Dict[str, Any]) -> None:
        """Called when chain execution starts.

        Args:
            chain_id: Unique identifier for the chain
            inputs: Input parameters for the chain
        """
        pass

    @abstractmethod
    def on_chain_end(
        self, chain_id: str, outputs: Dict[str, Any], error: Optional[Exception] = None
    ) -> None:
        """Called when chain execution ends.

        Args:
            chain_id: Unique identifier for the chain
            outputs: Output results from the chain
            error: Optional error if execution failed
        """
        pass

    @abstractmethod
    def on_node_start(
        self, chain_id: str, node_id: str, inputs: Dict[str, Any]
    ) -> None:
        """Called when node execution starts.

        Args:
            chain_id: Unique identifier for the chain
            node_id: Unique identifier for the node
            inputs: Input parameters for the node
        """
        pass

    @abstractmethod
    def on_node_end(self, chain_id: str, node_id: str, outputs: Dict[str, Any]) -> None:
        """Called when node execution ends successfully.

        Args:
            chain_id: Unique identifier for the chain
            node_id: Unique identifier for the node
            outputs: Output results from the node
        """
        pass

    @abstractmethod
    def on_node_error(self, chain_id: str, node_id: str, error: Exception) -> None:
        """Called when node execution fails.

        Args:
            chain_id: Unique identifier for the chain
            node_id: Unique identifier for the node
            error: Exception that caused the failure
        """
        pass


class LoggingCallback(ScriptChainCallback):
    """Callback handler that logs execution events"""

    def __init__(self, log_level: int = logging.INFO):
        """Initialize logging callback.

        Args:
            log_level: Logging level to use
        """
        self.log_level = log_level

    def on_chain_start(self, chain_id: str, inputs: Dict[str, Any]) -> None:
        logger.log(self.log_level, f"Starting chain execution: {chain_id}")

    def on_chain_end(
        self, chain_id: str, outputs: Dict[str, Any], error: Optional[Exception] = None
    ) -> None:
        if error:
            logger.log(
                self.log_level,
                f"Chain execution failed: {chain_id}, Error: {str(error)}",
            )
        else:
            logger.log(self.log_level, f"Chain execution completed: {chain_id}")

    def on_node_start(
        self, chain_id: str, node_id: str, inputs: Dict[str, Any]
    ) -> None:
        logger.log(self.log_level, f"Starting node execution: {chain_id}/{node_id}")

    def on_node_end(self, chain_id: str, node_id: str, outputs: Dict[str, Any]) -> None:
        logger.log(self.log_level, f"Node execution completed: {chain_id}/{node_id}")

    def on_node_error(self, chain_id: str, node_id: str, error: Exception) -> None:
        logger.log(
            self.log_level,
            f"Node execution failed: {chain_id}/{node_id}, Error: {str(error)}",
        )


class MetricsCallback(ScriptChainCallback):
    """Callback handler that collects execution metrics"""

    def __init__(self):
        """Initialize metrics callback"""
        self.metrics: Dict[str, Dict[str, Any]] = {}

    def on_chain_start(self, chain_id: str, inputs: Dict[str, Any]) -> None:
        self.metrics[chain_id] = {
            "start_time": time.time(),
            "inputs": inputs,
            "nodes": {},
        }

    def on_chain_end(
        self, chain_id: str, outputs: Dict[str, Any], error: Optional[Exception] = None
    ) -> None:
        if chain_id in self.metrics:
            self.metrics[chain_id].update(
                {
                    "end_time": time.time(),
                    "duration": time.time() - self.metrics[chain_id]["start_time"],
                    "outputs": outputs,
                    "error": str(error) if error else None,
                    "success": error is None,
                }
            )

    def on_node_start(
        self, chain_id: str, node_id: str, inputs: Dict[str, Any]
    ) -> None:
        if chain_id in self.metrics:
            self.metrics[chain_id]["nodes"][node_id] = {
                "start_time": time.time(),
                "inputs": inputs,
            }

    def on_node_end(self, chain_id: str, node_id: str, outputs: Dict[str, Any]) -> None:
        if chain_id in self.metrics and node_id in self.metrics[chain_id]["nodes"]:
            node_metrics = self.metrics[chain_id]["nodes"][node_id]
            node_metrics.update(
                {
                    "end_time": time.time(),
                    "duration": time.time() - node_metrics["start_time"],
                    "outputs": outputs,
                    "success": True,
                }
            )

    def on_node_error(self, chain_id: str, node_id: str, error: Exception) -> None:
        if chain_id in self.metrics and node_id in self.metrics[chain_id]["nodes"]:
            node_metrics = self.metrics[chain_id]["nodes"][node_id]
            node_metrics.update(
                {
                    "end_time": time.time(),
                    "duration": time.time() - node_metrics["start_time"],
                    "error": str(error),
                    "success": False,
                }
            )

    def get_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Get all collected metrics.

        Returns:
            Dictionary containing all chain and node metrics
        """
        return self.metrics

    def export_metrics(self, filepath: str) -> None:
        """Export collected metrics to a JSON file.

        Args:
            filepath: Path to save metrics file
        """
        with open(filepath, "w") as f:
            json.dump(self.metrics, f, indent=2)
