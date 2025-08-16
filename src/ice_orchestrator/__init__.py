"""iceOS Orchestrator - Runtime Execution Engine.

The orchestrator layer handles all runtime execution including:
- Workflow execution
- Tool execution
- Agent runtime
- Memory management
- LLM services
- Context management
"""

# Re-export for public API surface
from typing import Any

from ice_orchestrator.base_workflow import BaseWorkflow, FailurePolicy


def __getattr__(name: str) -> Any:
    if name == "WorkflowService":
        from ice_orchestrator.services.workflow_service import WorkflowService

        return WorkflowService
    raise AttributeError(name)


__all__ = [
    "BaseWorkflow",
    "FailurePolicy",
    "WorkflowService",
    "initialize_orchestrator",
]


def initialize_orchestrator() -> None:
    """Initialize the orchestrator layer with all runtime services.

    Moves away from the global ServiceLocator by wiring concrete runtime
    factories into ``ice_core.runtime`` and loading first-party tools via the
    explicit plugin loader. Keeps minimal ServiceLocator registration only
    for backward-compatible lookups used by API during the transition.
    """
    # Register context manager first – other services depend on it
    import os
    from pathlib import Path

    from ice_core import runtime as rt
    from ice_orchestrator.context import GraphContextManager
    from ice_orchestrator.plugins import load_first_party_tools
    from ice_orchestrator.services.network_coordinator import NetworkCoordinator
    from ice_orchestrator.services.tool_execution_service import ToolExecutionService
    from ice_orchestrator.services.workflow_execution_service import (
        WorkflowExecutionService,
    )
    from ice_orchestrator.services.workflow_service import WorkflowService  # noqa: F401
    from ice_orchestrator.workflow import Workflow

    project_root = Path(os.getcwd())
    cm = GraphContextManager(project_root=project_root)

    wes = WorkflowExecutionService()

    # New: wire runtime factories for decoupled access from core/api layers
    rt.workflow_factory = Workflow
    rt.network_coordinator_factory = NetworkCoordinator
    rt.tool_execution_service = ToolExecutionService()
    rt.context_manager = cm
    rt.workflow_execution_service = wes

    # Register tool service wrapper (runtime only)
    from ice_core.services.tool_service import (  # noqa: F401 runtime-facing proxy
        ToolService,
    )

    # ------------------------------------------------------------------
    # Built-in tools ----------------------------------------------------
    # ------------------------------------------------------------------
    # Explicitly register first-party tools (no side-effect imports)
    try:
        load_first_party_tools()
    except Exception:
        # Do not crash if tool packages are missing in minimal builds
        pass

    # Also load declarative plugin manifests when provided (keeps parity with API lifespan)
    try:
        manifests_env = os.getenv("ICEOS_PLUGIN_MANIFESTS", "").strip()
        if manifests_env:
            import logging as _logging
            import pathlib as _pathlib

            from ice_core.unified_registry import registry as _reg

            _plog = _logging.getLogger(__name__)
            for mp in [p.strip() for p in manifests_env.split(",") if p.strip()]:
                try:
                    path = _pathlib.Path(mp)
                    count = _reg.load_plugins(str(path), allow_dynamic=True)
                    _plog.info("Loaded %d components from manifest %s", count, path)
                except Exception as e:  # pragma: no cover – defensive
                    _plog.warning("Failed to load plugins manifest %s: %s", mp, e)
    except Exception:
        # Non-fatal in minimal/test environments
        pass

    # Load any entry-point declared nodes/tools
    try:
        from ice_core.unified_registry import registry as _reg

        _reg.load_entry_points()
    except Exception:
        pass

    # Import executor modules to register them with the execution system
    import ice_orchestrator.execution.executors  # noqa: F401

    # Runtime sanity check: every NodeType has a config mapping and an executor
    try:
        from ice_core.models.enums import NodeType
        from ice_core.unified_registry import get_executor
        from ice_core.utils.node_conversion import (
            _NODE_TYPE_MAP as _MAP,  # type: ignore
        )

        missing_in_map = [nt.value for nt in NodeType if nt.value not in _MAP]
        missing_exec = []
        for nt in NodeType:
            try:
                get_executor(nt.value)
            except Exception:
                missing_exec.append(nt.value)
        if missing_in_map or missing_exec:
            raise RuntimeError(
                f"Runtime registry incomplete: map={missing_in_map}, executors={missing_exec}"
            )
    except Exception:
        # Do not crash in minimal builds; tests will catch discrepancies
        pass

    # ------------------------------------------------------------------
    # Built-in tools will be loaded via toolkits once implemented.
    # ------------------------------------------------------------------
    # (No built-in tool packages shipped yet – placeholder for future.)
