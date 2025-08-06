"""Fluent API for building workflows."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Literal, Optional

if TYPE_CHECKING:
    from ._map_proxy import _MapBuilderProxy

from ice_core.models import (
    LLMConfig,
    LLMOperatorConfig,
    ModelProvider,
    NodeConfig,
    ToolNodeConfig,
)

# All node types now have config classes


class WorkflowBuilder:
    """Build workflows with a fluent API."""

    def __init__(self, name: str):
        self.name = name
        self.nodes: List[NodeConfig] = []
        self.edges: List[tuple[str, str]] = []

    def add_tool(
        self,
        node_id: str,
        tool_name: str,
        **tool_args: Any,
    ) -> "WorkflowBuilder":
        """Add a tool node."""
        self.nodes.append(
            ToolNodeConfig(
                id=node_id,
                tool_name=tool_name,  # Changed from tool_ref to tool_name
                tool_args=tool_args,
                name=tool_name,
                input_selection=None,
                output_selection=None,
            )
        )
        return self

    def add_llm(
        self,
        node_id: str,
        model: str,
        prompt: str,
        **llm_kwargs: Any,
    ) -> "WorkflowBuilder":
        """Add an LLM node."""
        # Extract llm_config if provided in kwargs
        llm_config = llm_kwargs.pop(
            "llm_config", LLMConfig(provider=ModelProvider.OPENAI)
        )

        self.nodes.append(
            LLMOperatorConfig(
                id=node_id,
                type="llm",  # Use string literal as expected
                model=model,
                prompt=prompt,  # LLMOperatorConfig expects 'prompt' not 'prompt_template'
                llm_config=llm_config,
                name=node_id,
                input_selection=None,
                output_selection=None,
                **llm_kwargs,
            )
        )
        return self

    def add_workflow(
        self,
        node_id: str,
        workflow_ref: str,
        exposed_outputs: Optional[Dict[str, str]] = None,
        **wf_kwargs: Any,
    ) -> "WorkflowBuilder":
        """Add an embedded workflow node."""
        from ice_core.models import WorkflowNodeConfig

        self.nodes.append(
            WorkflowNodeConfig(
                id=node_id,
                type="workflow",
                workflow_ref=workflow_ref,
                exposed_outputs=exposed_outputs or {},
                config_overrides=wf_kwargs,
                name=node_id,
                input_selection=None,
                output_selection=None,
            )
        )
        return self

    def add_agent(
        self,
        node_id: str,
        package: str,  # AgentNodeConfig uses 'package' not 'agent_ref'
        tools: Optional[List[str]] = None,
        memory: Optional[Dict[str, Any]] = None,
        **agent_kwargs: Any,
    ) -> "WorkflowBuilder":
        """Add an agent node."""
        from ice_core.models import AgentNodeConfig, ToolConfig

        tool_configs = [ToolConfig(name=t, parameters={}) for t in (tools or [])]
        self.nodes.append(
            AgentNodeConfig(
                id=node_id,
                type="agent",
                package=package,
                tools=tool_configs,
                memory=memory,
                name=node_id,
                input_selection=None,
                output_selection=None,
                **agent_kwargs,
            )
        )
        return self

    def add_condition(
        self,
        node_id: str,
        expression: str,
        true_path: List["NodeConfig"],
        false_path: Optional[List["NodeConfig"]] = None,
        **cond_kwargs: Any,
    ) -> "WorkflowBuilder":
        """Add a condition node with nested node configurations."""
        from ice_core.models import ConditionNodeConfig

        self.nodes.append(
            ConditionNodeConfig(
                id=node_id,
                type="condition",
                expression=expression,
                true_path=true_path,
                false_path=false_path,
                name=node_id,
                input_selection=None,
                output_selection=None,
                **cond_kwargs,
            )
        )
        return self

    def add_loop(
        self,
        node_id: str,
        items_source: str,
        body: List["NodeConfig"],
        item_var: str = "item",
        parallel: bool = False,
        **loop_kwargs: Any,
    ) -> "WorkflowBuilder":
        """Add a loop node with nested node configurations."""
        from ice_core.models import LoopNodeConfig

        self.nodes.append(
            LoopNodeConfig(
                id=node_id,
                type="loop",
                items_source=items_source,
                item_var=item_var,
                body=body,
                parallel=parallel,
                name=node_id,
                input_selection=None,
                output_selection=None,
                **loop_kwargs,
            )
        )
        return self

    def add_parallel(
        self,
        node_id: str,
        branches: List[List["NodeConfig"]],
        max_concurrency: Optional[int] = None,
        **par_kwargs: Any,
    ) -> "WorkflowBuilder":
        """Add a parallel execution node with nested node configurations."""
        from ice_core.models import ParallelNodeConfig

        self.nodes.append(
            ParallelNodeConfig(
                id=node_id,
                type="parallel",
                branches=branches,
                max_concurrency=max_concurrency,
                name=node_id,
                input_selection=None,
                output_selection=None,
                **par_kwargs,
            )
        )
        return self

    def add_code(
        self,
        node_id: str,
        code: str,
        language: Literal["python", "javascript"] = "python",
        sandbox: bool = True,
        **code_kwargs: Any,
    ) -> "WorkflowBuilder":
        """Add a code execution node."""
        from ice_core.models import CodeNodeConfig

        self.nodes.append(
            CodeNodeConfig(
                id=node_id,
                type="code",
                code=code,
                language=language,
                sandbox=sandbox,
                name=node_id,
                input_selection=None,
                output_selection=None,
                **code_kwargs,
            )
        )
        return self

    def add_recursive(
        self,
        node_id: str,
        agent_package: Optional[str] = None,
        workflow_ref: Optional[str] = None,
        recursive_sources: Optional[List[str]] = None,
        convergence_condition: Optional[str] = None,
        max_iterations: int = 50,
        preserve_context: bool = True,
        **rec_kwargs: Any,
    ) -> "WorkflowBuilder":
        """Add a recursive node for agent conversations until convergence."""
        from ice_core.models import RecursiveNodeConfig

        if not recursive_sources:
            recursive_sources = []

        self.nodes.append(
            RecursiveNodeConfig(
                id=node_id,
                type="recursive",
                agent_package=agent_package,
                workflow_ref=workflow_ref,
                recursive_sources=recursive_sources,
                convergence_condition=convergence_condition,
                max_iterations=max_iterations,
                preserve_context=preserve_context,
                name=node_id,
                input_selection=None,
                output_selection=None,
                **rec_kwargs,
            )
        )
        return self

    def connect(self, from_node: str, to_node: str) -> "WorkflowBuilder":
        """Connect two nodes."""
        self.edges.append((from_node, to_node))

        # Update dependencies (all node types use 'dependencies' from BaseNodeConfig)
        for node in self.nodes:
            if node.id == to_node:
                if from_node not in node.dependencies:
                    node.dependencies.append(from_node)

        return self

    def _apply_connections(self) -> None:
        """Apply all edge connections to update node dependencies."""
        # Clear existing dependencies first (all nodes inherit from BaseNodeConfig)
        for node in self.nodes:
            node.dependencies = []

        # Apply all edges to update dependencies
        for from_node, to_node in self.edges:
            for node in self.nodes:
                if node.id == to_node:
                    if from_node not in node.dependencies:
                        node.dependencies.append(from_node)

    def build(self) -> Any:
        """Return an MCP Blueprint ready for validation/compilation."""

        # Update node dependencies according to the recorded edges
        self._apply_connections()

        # Convert NodeConfig objects to plain NodeSpec dictionaries so the
        # compiler tier ( 0ice_api 0) can accept them without importing
        # runtime classes.  We rely on Pydantic's ".model_dump" for a JSON-safe
        # representation.
        from ice_core.models.mcp import Blueprint, NodeSpec

        node_specs = [
            NodeSpec.model_validate(node.model_dump())  # type: ignore[arg-type]
            for node in self.nodes
        ]

        return Blueprint(
            nodes=node_specs, metadata={"draft_name": self.name}, schema_version="1.1.0"
        )

    def to_workflow(self, workflow_cls: Any | None = None) -> Any:
        """Instantiate a concrete Workflow.

        Parameters
        ----------
        workflow_cls : Any
            Concrete `Workflow` class (e.g. ``ice_orchestrator.workflow.Workflow``).

        Returns
        -------
        Any
            Instantiated workflow.
        """
        from ice_core.runtime import workflow_factory  # late import to avoid heavy deps

        if workflow_cls is None:
            if workflow_factory is None:
                raise TypeError(
                    "workflow_cls argument missing and runtime.workflow_factory not set"
                )
            workflow_cls = workflow_factory  # type: ignore[assignment]
        return workflow_cls(name=self.name, nodes=self.nodes)

    # ------------------------------------------------------------------
    # Preview helpers ---------------------------------------------------
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # Convenience sugar -------------------------------------------------
    # ------------------------------------------------------------------

    def map(self, items_source: str) -> "_MapBuilderProxy":
        """Return a proxy that allows `.with_tool()` map sugar.

        Example
        -------
        >>> builder.map("load_csv.rows").with_tool("listing", tool_name="listing_agent")
        """
        return _MapBuilderProxy(self, items_source)

    def preview(self) -> str:
        """Return a Mermaid graph diagram of the current builder state."""
        # Ensure dependencies reflect the recorded edges
        self._apply_connections()

        lines: list[str] = ["graph TD;"]
        # Declare nodes with type label
        for node in self.nodes:
            label = f"{node.id} ({getattr(node, 'type', '?')})"
            lines.append(f'    {node.id}["{label}"];')
        # Declare edges
        for src, dst in self.edges:
            lines.append(f"    {src} --> {dst};")

        return "\n".join(lines)
