"""Component definition validation before registration.

This module validates tool, agent, and workflow definitions BEFORE they are
registered, ensuring only valid components enter the registry. This enables
the Frosty/Canvas workflow where components are validated during design time.
"""

import ast

from ice_core.models.mcp import ComponentDefinition, ComponentValidationResult
from ice_core.unified_registry import registry, global_agent_registry
from ice_core.models import NodeType
from ice_orchestrator.validation.schema_validator import validate_blueprint
from ice_core.models.mcp import Blueprint


async def validate_tool_definition(
    definition: ComponentDefinition
) -> ComponentValidationResult:
    """Validate a tool definition before registration.
    
    Checks:
    - Python code syntax (if provided)
    - Class inheritance from ToolBase
    - Required methods (_execute_impl)
    - Input/output schema validity
    - No naming conflicts
    """
    result = ComponentValidationResult(
        valid=True,
        component_type="tool",
        component_id=f"tool_{definition.name}"
    )
    
    # Check for naming conflicts
    if registry.has_tool(definition.name):
        result.errors.append(f"Tool '{definition.name}' already exists in registry")
        result.valid = False
        return result
    
    # If Python code provided, validate it
    if definition.tool_class_code:
        try:
            # Parse the Python code
            tree = ast.parse(definition.tool_class_code)
            
            # Find the tool class
            tool_class_found = False
            inherits_toolbase = False
            has_execute_impl = False
            
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    tool_class_found = True
                    
                    # Check inheritance
                    for base in node.bases:
                        if isinstance(base, ast.Name) and base.id == "ToolBase":
                            inherits_toolbase = True
                    
                    # Check for _execute_impl method
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef) and item.name == "_execute_impl":
                            has_execute_impl = True
                            # Could add more checks on method signature here
            
            if not tool_class_found:
                result.errors.append("No class definition found in tool code")
                result.valid = False
            
            if not inherits_toolbase:
                result.warnings.append("Tool class should inherit from ToolBase")
                result.suggestions.append(
                    "Make sure your tool class inherits from ice_core.base_tool.ToolBase"
                )
            
            if not has_execute_impl:
                result.errors.append("Tool class must implement _execute_impl method")
                result.valid = False
                
        except SyntaxError as e:
            result.errors.append(f"Python syntax error: {str(e)}")
            result.valid = False
        except Exception as e:
            result.errors.append(f"Error parsing tool code: {str(e)}")
            result.valid = False
    
    # Validate schemas if provided
    if definition.tool_input_schema:
        if not isinstance(definition.tool_input_schema, dict):
            result.errors.append("Input schema must be a valid JSON schema object")
            result.valid = False
        else:
            # Could add JSON schema validation here
            result.validation_details["input_schema_validated"] = True
    
    if definition.tool_output_schema:
        if not isinstance(definition.tool_output_schema, dict):
            result.errors.append("Output schema must be a valid JSON schema object")
            result.valid = False
        else:
            result.validation_details["output_schema_validated"] = True
    
    # Add suggestions based on tool type
    if result.valid:
        result.suggestions.extend([
            "Consider adding comprehensive docstrings",
            "Implement proper error handling in _execute_impl",
            "Add type hints for better IDE support",
            "Consider adding input validation"
        ])
    
    return result


async def validate_agent_definition(
    definition: ComponentDefinition
) -> ComponentValidationResult:
    """Validate an agent definition before registration.
    
    Checks:
    - System prompt validity
    - Referenced tools exist
    - LLM config is valid
    - No naming conflicts
    """
    result = ComponentValidationResult(
        valid=True,
        component_type="agent",
        component_id=f"agent_{definition.name}"
    )
    
    # Check for naming conflicts
    existing_agents = [name for name, _ in global_agent_registry.available_agents()]
    if definition.name in existing_agents:
        result.errors.append(f"Agent '{definition.name}' already exists in registry")
        result.valid = False
        return result
    
    # Validate system prompt
    if definition.agent_system_prompt:
        if len(definition.agent_system_prompt) < 10:
            result.warnings.append("System prompt seems too short to be effective")
        result.validation_details["has_system_prompt"] = True
    else:
        result.warnings.append("Agent has no system prompt defined")
    
    # Validate referenced tools exist
    if definition.agent_tools:
        missing_tools = []
        for tool_name in definition.agent_tools:
            if not registry.has_tool(tool_name):
                missing_tools.append(tool_name)
        
        if missing_tools:
            result.errors.append(
                f"Agent references non-existent tools: {', '.join(missing_tools)}"
            )
            result.suggestions.append(
                "Use /components/validate to register missing tools first"
            )
            result.valid = False
    
    # Validate LLM config
    if definition.agent_llm_config:
        required_fields = ["provider", "model"]
        for field in required_fields:
            if field not in definition.agent_llm_config:
                result.errors.append(f"LLM config missing required field: {field}")
                result.valid = False
    
    # Add suggestions
    if result.valid:
        result.suggestions.extend([
            "Consider adding memory configuration for context retention",
            "Add retry strategies for resilience",
            "Consider limiting tool access for security",
            "Add specialized prompts for different scenarios"
        ])
    
    return result


async def validate_workflow_definition(
    definition: ComponentDefinition  
) -> ComponentValidationResult:
    """Validate a workflow definition before registration.
    
    Checks:
    - Node validity
    - Dependency graph
    - All referenced components exist
    - No cycles
    """
    result = ComponentValidationResult(
        valid=True,
        component_type="workflow",
        component_id=f"workflow_{definition.name}"
    )
    
    # Check for naming conflicts
    try:
        existing = registry.get_instance(NodeType.WORKFLOW, definition.name)
        if existing:
            result.errors.append(f"Workflow '{definition.name}' already exists")
            result.valid = False
            return result
    except Exception:
        # workflow not found – that's expected for new definitions
        pass
    
    # Validate nodes exist
    if not definition.workflow_nodes:
        result.errors.append("Workflow must have at least one node")
        result.valid = False
        return result
    
    # Create a temporary blueprint for validation
    try:
        temp_blueprint = Blueprint(
            blueprint_id=f"validation_{definition.name}",
            nodes=definition.workflow_nodes,
            metadata={"validation_only": True}
        )
        
        # Use existing blueprint validation
        await validate_blueprint(temp_blueprint)
        result.validation_details["blueprint_valid"] = True
        
    except Exception as e:
        result.errors.append(f"Workflow validation failed: {str(e)}")
        result.valid = False
    
    # Add workflow-specific suggestions
    if result.valid:
        node_count = len(definition.workflow_nodes)
        if node_count > 10:
            result.suggestions.append(
                "Consider breaking large workflows into sub-workflows for maintainability"
            )
        
        result.suggestions.extend([
            "Add error handling nodes for resilience",
            "Consider parallel execution where possible",
            "Add monitoring and logging nodes",
            "Document expected inputs and outputs"
        ])
    
    return result


async def validate_component(
    definition: ComponentDefinition
) -> ComponentValidationResult:
    """Main validation dispatcher for any component type."""
    
    # Basic validation
    if not definition.name or len(definition.name) < 2:
        return ComponentValidationResult(
            valid=False,
            errors=["Component name must be at least 2 characters"],
            component_type=definition.type
        )
    
    # Check name format (alphanumeric, underscore, dash)
    import re
    if not re.match(r'^[a-zA-Z][a-zA-Z0-9_-]*$', definition.name):
        return ComponentValidationResult(
            valid=False,
            errors=["Component name must start with letter and contain only letters, numbers, underscore, or dash"],
            component_type=definition.type
        )
    
    # Dispatch to specific validators
    if definition.type == "tool":
        return await validate_tool_definition(definition)
    elif definition.type == "agent":
        return await validate_agent_definition(definition)
    elif definition.type == "workflow":
        return await validate_workflow_definition(definition)
    else:
        return ComponentValidationResult(
            valid=False,
            errors=[f"Unknown component type: {definition.type}"],
            component_type=definition.type
        ) 