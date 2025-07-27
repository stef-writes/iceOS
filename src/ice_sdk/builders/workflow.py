"""Fluent API for building workflows."""
from typing import List, Dict, Any, Optional
from ice_core.models import (
    NodeConfig, NodeType,
    ToolNodeConfig, LLMOperatorConfig,
    AgentNodeConfig, ConditionNodeConfig,
    LLMConfig, ModelProvider
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
        **kwargs
    ) -> "WorkflowBuilder":
        """Add a tool node."""
        self.nodes.append(ToolNodeConfig(
            id=node_id,
            type="tool",  # Use string literal as ToolNodeConfig expects
            tool_name=tool_name,  # Changed from tool_ref to tool_name
            tool_args=kwargs
        ))
        return self
    
    def add_llm(
        self,
        node_id: str,
        model: str,
        prompt: str,
        **kwargs
    ) -> "WorkflowBuilder":
        """Add an LLM node."""
        # Extract llm_config if provided in kwargs
        llm_config = kwargs.pop('llm_config', LLMConfig(provider=ModelProvider.OPENAI))
        
        self.nodes.append(LLMOperatorConfig(
            id=node_id,
            type="llm",  # Use string literal as expected
            model=model,
            prompt=prompt,  # LLMOperatorConfig expects 'prompt' not 'prompt_template'
            llm_config=llm_config,
            **kwargs
        ))
        return self
    
    def add_workflow(
        self,
        node_id: str,
        workflow_ref: str,
        exposed_outputs: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> "WorkflowBuilder":
        """Add an embedded workflow node."""
        from ice_core.models import WorkflowNodeConfig
        self.nodes.append(WorkflowNodeConfig(
            id=node_id,
            type="workflow",
            workflow_ref=workflow_ref,
            exposed_outputs=exposed_outputs or {},
            config_overrides=kwargs
        ))
        return self
    
    def add_agent(
        self,
        node_id: str,
        package: str,  # AgentNodeConfig uses 'package' not 'agent_ref'
        tools: Optional[List[str]] = None,
        memory: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> "WorkflowBuilder":
        """Add an agent node."""
        from ice_core.models import AgentNodeConfig, ToolConfig
        tool_configs = [ToolConfig(name=t, parameters={}) for t in (tools or [])]
        self.nodes.append(AgentNodeConfig(
            id=node_id,
            type="agent",
            package=package,
            tools=tool_configs,
            memory=memory,
            **kwargs
        ))
        return self
    
    def add_condition(
        self,
        node_id: str,
        expression: str,
        true_branch: List[str],
        false_branch: Optional[List[str]] = None,
        **kwargs
    ) -> "WorkflowBuilder":
        """Add a condition node."""
        from ice_core.models import ConditionNodeConfig
        self.nodes.append(ConditionNodeConfig(
            id=node_id,
            type="condition",
            expression=expression,
            true_branch=true_branch,
            false_branch=false_branch,
            **kwargs
        ))
        return self
    
    def add_loop(
        self,
        node_id: str,
        items_source: str,
        body_nodes: List[str],
        item_var: str = "item",
        parallel: bool = False,
        **kwargs
    ) -> "WorkflowBuilder":
        """Add a loop node."""
        from ice_core.models import LoopNodeConfig
        self.nodes.append(LoopNodeConfig(
            id=node_id,
            type="loop",
            items_source=items_source,
            item_var=item_var,
            body_nodes=body_nodes,
            parallel=parallel,
            **kwargs
        ))
        return self
    
    def add_parallel(
        self,
        node_id: str,
        branches: List[List[str]],
        max_concurrency: Optional[int] = None,
        **kwargs
    ) -> "WorkflowBuilder":
        """Add a parallel execution node."""
        from ice_core.models import ParallelNodeConfig
        self.nodes.append(ParallelNodeConfig(
            id=node_id,
            type="parallel",
            branches=branches,
            max_concurrency=max_concurrency,
            **kwargs
        ))
        return self
    
    def add_code(
        self,
        node_id: str,
        code: str,
        language: str = "python",
        sandbox: bool = True,
        **kwargs
    ) -> "WorkflowBuilder":
        """Add a code execution node."""
        from ice_core.models import CodeNodeConfig
        self.nodes.append(CodeNodeConfig(
            id=node_id,
            type="code",
            code=code,
            language=language,
            sandbox=sandbox,
            **kwargs
        ))
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
    
    def build(self):
        """Build the final workflow."""
        # Process edges to update node dependencies
        self._apply_connections()
        
        # Import Workflow class (avoid circular imports)
        from ice_orchestrator.workflow import Workflow
        
        # Create and return workflow instance
        return Workflow(
            nodes=self.nodes,
            name=self.name
        )
    
    def to_workflow(self):
        """Convert to Workflow instance using ServiceLocator.
        
        This method uses dependency injection to avoid direct imports.
        """
        from ice_sdk.services.locator import get_workflow_proto
        
        workflow_cls = get_workflow_proto()
        return workflow_cls(
            name=self.name,
            nodes=self.nodes
        ) 