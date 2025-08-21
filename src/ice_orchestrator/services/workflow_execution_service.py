"""Workflow execution service for the orchestrator."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from ice_core.metrics import EXEC_COMPLETED, EXEC_STARTED
from ice_core.models.mcp import NodeSpec
from ice_core.models.node_models import NodeExecutionResult
from ice_core.utils.node_conversion import convert_node_specs
from ice_orchestrator.workflow import Workflow

# Importing registry solely for side-effects would be unused; remove to satisfy linter


class WorkflowExecutionService:
    """Workflow execution service for the orchestrator runtime.

    This service provides two clear entry points:
    1. execute_blueprint - for MCP layer blueprints (List[NodeSpec])
    2. execute_workflow - for ready Workflow instances
    """

    async def execute_blueprint(
        self,
        node_specs: List[NodeSpec],
        *,
        inputs: Optional[Dict[str, Any]] = None,
        max_parallel: int = 5,
        name: str = "blueprint_run",
    ) -> NodeExecutionResult:
        """Execute a workflow from MCP blueprint specification.

        Args:
            node_specs: List of NodeSpec objects from MCP layer
            inputs: Initial inputs for the workflow
            max_parallel: Maximum parallel execution
            name: Workflow name

        Returns:
            Workflow execution results
        """
        # Preprocess: inject memory-aware helpers if requested (no duplication)
        processed_specs = self._apply_memory_aware_policy(node_specs)

        # Convert NodeSpec to NodeConfig
        node_configs = convert_node_specs(processed_specs)

        # Ensure first-party generated tools are registered explicitly
        try:
            from ice_orchestrator.plugins import load_first_party_tools

            load_first_party_tools()
        except Exception:
            pass

        # Create workflow with proper initial context
        # Merge provided inputs at the top level and also under the "inputs" key
        # so prompts can access placeholders like {topic} without nesting.
        initial_ctx = None
        if inputs:
            initial_ctx = {**inputs, "inputs": inputs}
        workflow = Workflow(
            nodes=node_configs,
            name=name,
            max_parallel=max_parallel,
            initial_context=initial_ctx,
        )

        # Execute workflow
        EXEC_STARTED.inc()
        try:
            result = await workflow.execute()
            EXEC_COMPLETED.inc()
            return result
        except Exception:
            EXEC_COMPLETED.inc()
            raise

    # ------------------------------------------------------------------
    # Memory-aware policy (opt-in per node)
    # ------------------------------------------------------------------
    def _apply_memory_aware_policy(self, node_specs: List[NodeSpec]) -> List[NodeSpec]:
        """Inject recent+transcript helpers for LLM nodes that opt-in.

        Opt-in signal: llm node contains a truthy field "memory_aware".
        Injection:
          - Add a recent_session_tool node (id=f"recent_{llm_id}") with scope=library and deps=[]
          - Amend llm node to depend on the recent node and prepend prompt lines to include its output
          - Add a memory_write_tool node (id=f"write_{llm_id}") depending on llm, writing transcript

        Notes:
          - Uses existing first-party tools; no runtime duplication.
          - Key used for transcript: chat:{{ inputs.session_id }}:{llm_id}
        """
        try:
            processed: List[Dict[str, Any]] = [
                ns.model_dump(mode="json") for ns in node_specs
            ]
        except Exception:
            # Best effort fallback if pydantic export fails
            processed = [dict(getattr(ns, "__dict__", {})) for ns in node_specs]

        out: List[Dict[str, Any]] = []
        for ns in processed:
            out.append(ns)
            try:
                if ns.get("type") != "llm":
                    continue
                mem_aware = bool(ns.get("memory_aware"))
                if not mem_aware:
                    continue
                llm_id = str(ns.get("id", "llm"))
                # Inject recent tool node
                recent_id = f"recent_{llm_id}"
                recent_node = {
                    "id": recent_id,
                    "type": "tool",
                    "tool_name": "recent_session_tool",
                    "tool_args": {
                        "session_id": "{{ inputs.session_id }}",
                        "scope": "library",
                        "org_id": "{{ inputs.org_id }}",
                        "limit": 5,
                    },
                    "dependencies": [],
                }
                out.append(recent_node)
                # Ensure llm depends on recent and prompt references it
                deps = list(ns.get("dependencies", []))
                if recent_id not in deps:
                    deps.append(recent_id)
                ns["dependencies"] = deps
                prompt = str(ns.get("prompt", ""))
                prefix = (
                    "You are memory-aware. Use recent chat turns when helpful.\n"
                    f"Recent session items: {{{{ {recent_id}['items'] }}}}\n"
                )
                ns["prompt"] = prefix + prompt
                # Inject transcript write node
                write_id = f"write_{llm_id}"
                write_node = {
                    "id": write_id,
                    "type": "tool",
                    "tool_name": "memory_write_tool",
                    "tool_args": {
                        "key": f"chat:{{{{ inputs.session_id }}}}:{llm_id}",
                        "content": f"{{{{ {llm_id}.response }}}}",
                        "scope": "library",
                        "org_id": "{{ inputs.org_id }}",
                        "user_id": "{{ inputs.user_id }}",
                    },
                    "dependencies": [llm_id],
                }
                out.append(write_node)
            except Exception:
                # Defensive: never break execution if injection fails
                continue

        try:
            return [NodeSpec.model_validate(n) for n in out]
        except Exception:
            # Fallback: return original specs on validation error
            return node_specs

    async def execute_workflow(
        self, workflow: Workflow, *, inputs: Optional[Dict[str, Any]] = None
    ) -> NodeExecutionResult:
        """Execute a ready Workflow instance.

        Args:
            workflow: Workflow instance to execute
            inputs: Initial inputs to inject into workflow context

        Returns:
            Workflow execution results
        """
        # Inject inputs into workflow context if provided
        if inputs:
            ctx = workflow.context_manager.get_context(session_id="run")
            if ctx:
                # Expose inputs both at top-level and nested under "inputs"
                ctx.metadata.update(inputs)
                ctx.metadata["inputs"] = inputs

        # Execute workflow
        EXEC_STARTED.inc()
        try:
            result = await workflow.execute()
            EXEC_COMPLETED.inc()
            return result
        except Exception:
            EXEC_COMPLETED.inc()
            raise

    async def execute_workflow_builder(
        self,
        builder: Any,  # WorkflowBuilder
        inputs: Optional[Dict[str, Any]] = None,
    ) -> NodeExecutionResult:
        """Execute a workflow directly from a builder.

        Args:
            builder: WorkflowBuilder instance
            inputs: Initial inputs for the workflow

        Returns:
            Workflow execution results
        """
        # Builder.build() returns a Blueprint, so use execute_blueprint
        blueprint = builder.build()
        return await self.execute_blueprint(
            blueprint.nodes, inputs=inputs, name=builder.name
        )
