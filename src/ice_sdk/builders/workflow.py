"""Fluent API for building workflows."""
from typing import List, Dict, Any, Optional
from ice_core.models import (
    NodeConfig, NodeType,
    ToolNodeConfig, LLMOperatorConfig,
    AgentNodeConfig, ConditionNodeConfig,
    LLMConfig, ModelProvider
)
# Note: Unit, Workflow, Loop, Parallel, Code configs don't exist yet

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
    
    def add_unit(
        self,
        node_id: str,
        unit_ref: str,
        **kwargs
    ) -> "WorkflowBuilder":
        """Add a unit node."""
        self.nodes.append(UnitNodeConfig(
            id=node_id,
            type=NodeType.UNIT,
            unit_ref=unit_ref,
            config_overrides=kwargs
        ))
        return self
    
    def add_agent(
        self,
        node_id: str,
        package: str,  # AgentNodeConfig uses 'package' not 'agent_ref'
        tools: List[str] = None,
        **kwargs
    ) -> "WorkflowBuilder":
        """Add an agent node."""
        self.nodes.append(AgentNodeConfig(
            id=node_id,
            type="agent",  # Use string literal
            package=package,
            tools=[],  # AgentNodeConfig expects List[ToolConfig], not List[str]
            **kwargs
        ))
        return self
    
    def add_condition(
        self,
        node_id: str,
        expression: str,
        true_nodes: List[str] = None,
        false_nodes: List[str] = None
    ) -> "WorkflowBuilder":
        """Add a condition node."""
        self.nodes.append(ConditionNodeConfig(
            id=node_id,
            type=NodeType.CONDITION,
            expression=expression,
            true_nodes=true_nodes or [],
            false_nodes=false_nodes or []
        ))
        return self
    
    def add_workflow(
        self,
        node_id: str,
        workflow_ref: str,
        inputs: Dict[str, Any] = None
    ) -> "WorkflowBuilder":
        """Add a sub-workflow node."""
        self.nodes.append(WorkflowNodeConfig(
            id=node_id,
            type=NodeType.WORKFLOW,
            workflow_ref=workflow_ref,
            inputs=inputs or {}
        ))
        return self
    
    def add_loop(
        self,
        node_id: str,
        iterator_path: str,
        body_nodes: List[str] = None,
        max_iterations: int = 100
    ) -> "WorkflowBuilder":
        """Add a loop node."""
        self.nodes.append(LoopNodeConfig(
            id=node_id,
            type=NodeType.LOOP,
            iterator_path=iterator_path,
            body_nodes=body_nodes or [],
            max_iterations=max_iterations
        ))
        return self
    
    def add_parallel(
        self,
        node_id: str,
        branches: List[List[str]],
        wait_strategy: str = "all"
    ) -> "WorkflowBuilder":
        """Add a parallel node."""
        self.nodes.append(ParallelNodeConfig(
            id=node_id,
            type=NodeType.PARALLEL,
            branches=branches,
            wait_strategy=wait_strategy
        ))
        return self
    
    def add_code(
        self,
        node_id: str,
        code: str,
        runtime: str = "python"
    ) -> "WorkflowBuilder":
        """Add a code node."""
        self.nodes.append(CodeNodeConfig(
            id=node_id,
            type=NodeType.CODE,
            code=code,
            runtime=runtime
        ))
        return self
    
    def connect(self, from_node: str, to_node: str) -> "WorkflowBuilder":
        """Connect two nodes."""
        self.edges.append((from_node, to_node))
        
        # Update depends_on
        for node in self.nodes:
            if node.id == to_node:
                if from_node not in node.depends_on:
                    node.depends_on.append(from_node)
        
        return self
    
    def build(self) -> Dict[str, Any]:
        """Build the workflow specification.
        
        Returns a dictionary that can be passed to a workflow execution service.
        To execute, use ice_sdk.services.workflow_service.execute_workflow(spec).
        """
        return {
            "name": self.name,
            "nodes": [node.model_dump() for node in self.nodes],
            "version": "1.0"
        }
    
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