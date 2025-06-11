"""Level-based workflow orchestrator.

Moved from *level_based_script_chain.py* into this ``executors`` package to
separate orchestration strategy from node-execution details.
"""
from __future__ import annotations

import asyncio
import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import structlog
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

from app.chains.events import EventDispatcher
from app.chains.metrics import ChainMetrics
from app.chains.orchestration.base_script_chain import BaseScriptChain, FailurePolicy
from app.chains.orchestration.node_dependency_graph import DependencyGraph
from app.chains.orchestration.workflow_execution_context import WorkflowExecutionContext
from app.models.node_models import (
    ChainExecutionResult,
    NodeConfig,
    NodeExecutionResult,
    NodeMetadata,
)
from app.nodes.factory import node_factory
from app.utils.artifact_store import ArtifactStore

from .node_executor import NodeExecutor

# ---------------------------------------------------------------------------
# Tracing & logging ----------------------------------------------------------
# ---------------------------------------------------------------------------
tracer = trace.get_tracer(__name__)
logger = structlog.get_logger(__name__)


class LevelBasedScriptChain(BaseScriptChain):  # noqa: D101 – public class, docstring below
    """Execute a directed acyclic workflow using *level-based* parallelism.

    Nodes at the same topological *level* (i.e. depth in the dependency DAG)
    are executed concurrently up to the configured ``max_parallel`` limit.
    """

    def __init__(
        self,
        nodes: List[NodeConfig],
        name: Optional[str] = None,
        *,
        context_manager: Optional[Any] = None,
        callbacks: Optional[List[Any]] = None,
        max_parallel: int = 5,
        persist_intermediate_outputs: bool = True,
        tool_service: Optional[Any] = None,
        initial_context: Optional[Dict[str, Any]] = None,
        workflow_context: Optional[WorkflowExecutionContext] = None,
        chain_id: Optional[str] = None,
        failure_policy: FailurePolicy = FailurePolicy.CONTINUE_POSSIBLE,
        artifact_store: Optional[ArtifactStore] = None,
        validate_outputs: bool = True,
    ) -> None:
        self.chain_id = chain_id or os.urandom(8).hex()
        super().__init__(
            nodes,
            name,
            context_manager,
            callbacks,
            max_parallel,
            persist_intermediate_outputs,
            tool_service,
            initial_context,
            workflow_context,
            failure_policy,
        )
        self.validate_outputs = validate_outputs

        # Build dependency graph ------------------------------------------
        self.graph = DependencyGraph(nodes)
        self.graph.validate_schema_alignment(nodes)
        self.levels = self.graph.get_level_nodes()

        # Metrics & events -------------------------------------------------
        self.metrics = ChainMetrics(self.name)
        self.events = EventDispatcher(self.callbacks)

        # Instantiate all nodes in advance --------------------------------
        self.node_instances: Dict[str, Any] = {
            node_id: node_factory(
                node,
                context_manager=self.context_manager,
                llm_config=getattr(node, "llm_config", None),
                callbacks=self.callbacks,
                tool_service=self.tool_service,
            )
            for node_id, node in self.nodes.items()
        }

        # Caching / artefacts ---------------------------------------------
        self.artifact_store = artifact_store
        self.large_output_threshold = 256 * 1024  # 256 KiB
        self._cache: Dict[str, NodeExecutionResult] = {}

        logger.info(
            "Initialized ScriptChain with %d nodes across %d levels",
            len(nodes),
            len(self.levels),
        )

    # ---------------------------------------------------------------------
    # Public API -----------------------------------------------------------
    # ---------------------------------------------------------------------
    async def execute(self) -> ChainExecutionResult:  # noqa: D401 – async
        start_time = datetime.utcnow()
        results: Dict[str, NodeExecutionResult] = {}
        errors: List[str] = []

        node_executor = NodeExecutor(
            context_manager=self.context_manager,
            chain_id=self.chain_id,
            persist_intermediate_outputs=self.persist_intermediate_outputs,
            callbacks=self.callbacks,
            tool_service=self.tool_service,
            initial_context=self.initial_context,
            workflow_context=self.workflow_context,
            artifact_store=self.artifact_store,
            large_output_threshold=self.large_output_threshold,
            cache=self._cache,
            enforce_output_schema=self.validate_outputs,
        )

        logger.info("Starting execution of chain '%s' (ID: %s)", self.name, self.chain_id)

        with tracer.start_as_current_span(
            "chain.execute",
            attributes={
                "chain_id": self.chain_id,
                "chain_name": self.name,
                "node_count": len(self.nodes),
            },
        ) as chain_span:
            for level_num in sorted(self.levels.keys()):
                level_node_ids = self.levels[level_num]
                level_nodes = [self.node_instances[node_id] for node_id in level_node_ids]

                level_results = await self._execute_level(level_nodes, node_executor, results)

                for node_id, result_obj in level_results.items():
                    results[node_id] = result_obj  # store full NodeExecutionResult

                    if result_obj.success:
                        # chain-level metrics --------------------------------
                        if hasattr(result_obj, "usage") and result_obj.usage:
                            self.metrics.update(node_id, result_obj)
                    else:
                        errors.append(f"Node {node_id} failed: {result_obj.error}")

                if errors and not self._should_continue(errors):
                    break

            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()
            logger.info(
                "Completed chain execution", chain=self.name, chain_id=self.chain_id, duration=duration
            )

            chain_span.set_attribute("success", len(errors) == 0)
            if errors:
                chain_span.set_status(Status(StatusCode.ERROR, ";".join(errors)))
            chain_span.end()

        final_node_id = self.graph.get_leaf_nodes()[0]

        return ChainExecutionResult(
            success=len(errors) == 0,
            output=results,
            error="\n".join(errors) if errors else None,
            metadata=NodeMetadata(
                node_id=final_node_id,
                node_type="script_chain",
                name=self.name,
                version="1.0.0",
                start_time=start_time,
                end_time=end_time,
                duration=duration,
            ),
            execution_time=duration,
            token_stats=self.metrics.as_dict(),
        )

    # ---------------------------------------------------------------------
    # Internal helpers -----------------------------------------------------
    # ---------------------------------------------------------------------
    async def _execute_level(
        self,
        level_nodes: List[Any],
        node_executor: NodeExecutor,
        accumulated_results: Dict[str, NodeExecutionResult],
    ) -> Dict[str, NodeExecutionResult]:
        semaphore = asyncio.Semaphore(self.max_parallel)

        async def process_node(node: Any):
            async with semaphore:
                return await node_executor.execute_node(node, accumulated_results)

        tasks = [process_node(node) for node in level_nodes]
        results = await asyncio.gather(*tasks)
        return dict(results)

    def _should_continue(self, errors: List[str]) -> bool:
        """Determine whether chain execution should proceed after errors."""

        if not errors:
            return True

        if self.failure_policy == FailurePolicy.HALT:
            return False
        if self.failure_policy == FailurePolicy.ALWAYS:
            return True

        # CONTINUE_POSSIBLE ----------------------------------------------
        failed_nodes: set[str] = set()
        for error in errors:
            if "Node " in error and " failed:" in error:
                try:
                    node_id = error.split("Node ")[1].split(" failed:")[0]
                    failed_nodes.add(node_id)
                except (IndexError, AttributeError):
                    continue

        for level_num in sorted(self.levels.keys()):
            for node_id in self.levels[level_num]:
                node = self.nodes[node_id]
                if node_id in failed_nodes:
                    continue
                depends_on_failed_node = any(dep in failed_nodes for dep in getattr(node, "dependencies", []))
                if not depends_on_failed_node:
                    logger.info(
                        "Chain execution continuing: Node '%s' can still execute independently",
                        node_id,
                    )
                    return True

        logger.warning(
            "Chain execution stopping: All remaining nodes depend on failed nodes: %s",
            failed_nodes,
        )
        return False

    # ---------------------------------------------------------------------
    # Graph inspection public API -----------------------------------------
    # ---------------------------------------------------------------------

    def get_node_dependencies(self, node_id: str) -> List[str]:
        return self.graph.get_node_dependencies(node_id)

    def get_node_dependents(self, node_id: str) -> List[str]:
        return self.graph.get_node_dependents(node_id)

    def get_node_level(self, node_id: str) -> int:  # noqa: D401 – simple proxy
        return self.graph.get_node_level(node_id)

    def get_level_nodes(self, level: int) -> List[str]:  # noqa: D401 – simple proxy
        return self.levels.get(level, [])

    def get_metrics(self) -> Dict[str, Any]:  # noqa: D401 – simple proxy
        return self.metrics.as_dict() 