"""Builder service implementation using the new WorkflowBuilder."""
from typing import Any, Dict
from ice_core.services.contracts import IBuilderService
from ice_sdk.builders.workflow import WorkflowBuilder
from ice_core.models import NodeType
from ice_sdk.services.locator import ServiceLocator

class BuilderService(IBuilderService):
    """Concrete implementation of IBuilderService using WorkflowBuilder."""
    
    def create_workflow(self, name: str) -> WorkflowBuilder:
        """Create a new workflow builder instance."""
        return WorkflowBuilder(name)
    
    def add_node(self, builder: Any, node_type: str, node_id: str, **config: Any) -> Any:
        """Add a node to the workflow."""
        if not isinstance(builder, WorkflowBuilder):
            raise TypeError("Expected WorkflowBuilder instance")
        
        # Map node type strings to builder methods
        node_type_enum = NodeType(node_type)
        
        if node_type_enum == NodeType.TOOL:
            return builder.add_tool(node_id, **config)
        elif node_type_enum == NodeType.LLM:
            return builder.add_llm(node_id, **config)
        elif node_type_enum == NodeType.AGENT:
            return builder.add_agent(node_id, **config)
        elif node_type_enum == NodeType.CONDITION:
            return builder.add_condition(node_id, **config)
        elif node_type_enum == NodeType.UNIT:
            return builder.add_unit(node_id, **config)
        elif node_type_enum == NodeType.WORKFLOW:
            return builder.add_workflow(node_id, **config)
        elif node_type_enum == NodeType.LOOP:
            return builder.add_loop(node_id, **config)
        elif node_type_enum == NodeType.PARALLEL:
            return builder.add_parallel(node_id, **config)
        elif node_type_enum == NodeType.CODE:
            return builder.add_code(node_id, **config)
        else:
            raise ValueError(f"Unknown node type: {node_type}")
    
    def connect(self, builder: Any, from_node: str, to_node: str) -> Any:
        """Connect two nodes in the workflow."""
        if not isinstance(builder, WorkflowBuilder):
            raise TypeError("Expected WorkflowBuilder instance")
        return builder.connect(from_node, to_node)
    
    def build(self, builder: Any) -> Any:
        """Build the final workflow from the builder."""
        if not isinstance(builder, WorkflowBuilder):
            raise TypeError("Expected WorkflowBuilder instance")
        return builder.build()
    
    def to_dict(self, builder: Any) -> Dict[str, Any]:
        """Export workflow as dictionary."""
        if not isinstance(builder, WorkflowBuilder):
            raise TypeError("Expected WorkflowBuilder instance")
        return builder.to_dict()

# Register the service
ServiceLocator.register("builder_service", BuilderService()) 