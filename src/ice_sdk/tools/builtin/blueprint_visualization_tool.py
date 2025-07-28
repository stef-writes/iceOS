"""
🎨 Blueprint Visualization Tool  
===============================

Generates Mermaid diagrams from blueprint structure during MCP API validation.
This tool analyzes the blueprint specification and creates visual representations
of the workflow before execution.

Key Features:
- Blueprint structure analysis
- Node dependency visualization  
- Node type classification
- Configuration parameter display
- Integration with MCP validation process
"""

import json
from datetime import datetime
from typing import Any, Dict, List, Optional, TYPE_CHECKING
from pydantic import Field

from ice_sdk.tools.base import ToolBase

if TYPE_CHECKING:
    from ice_core.models.mcp import Blueprint


class BlueprintVisualizationTool(ToolBase):
    """Generate Mermaid diagrams from blueprint specifications during MCP validation."""
    
    name: str = "blueprint_visualization"
    description: str = "Generate visual diagrams from blueprint structure for MCP validation"
    
    async def _execute_impl(self, **kwargs) -> Dict[str, Any]:
        """Generate Mermaid diagrams from blueprint structure.
        
        Args:
            blueprint: Blueprint object to visualize
            diagram_types: List of diagram types to generate (default: all)
            include_config: Include node configuration details (default: True)
            validation_context: Additional validation context (default: None)
            
        Returns:
            Dict containing multiple Mermaid diagrams and validation insights
        """
        try:
            blueprint = kwargs.get("blueprint")
            if not blueprint:
                raise ValueError("Blueprint is required for visualization")
                
            diagram_types = kwargs.get("diagram_types", ["dependency_graph", "flowchart", "config_overview"])
            include_config = kwargs.get("include_config", True)
            validation_context = kwargs.get("validation_context", {})
            
            diagrams = {}
            
            # Generate different diagram types based on blueprint structure
            if "dependency_graph" in diagram_types:
                diagrams["dependency_graph"] = self._generate_dependency_graph(blueprint)
            
            if "flowchart" in diagram_types:
                diagrams["workflow_flowchart"] = self._generate_workflow_flowchart(
                    blueprint, include_config
                )
            
            if "config_overview" in diagram_types:
                diagrams["config_overview"] = self._generate_config_overview(blueprint)
                
            if "validation_diagram" in diagram_types:
                diagrams["validation_diagram"] = self._generate_validation_diagram(
                    blueprint, validation_context
                )
                
            # Generate blueprint analysis summary
            analysis = self._analyze_blueprint_structure(blueprint)
            
            return {
                "status": "success",
                "diagrams": diagrams,
                "blueprint_analysis": analysis,
                "timestamp": datetime.now().isoformat(),
                "metadata": {
                    "blueprint_id": blueprint.blueprint_id,
                    "schema_version": blueprint.schema_version,
                    "total_nodes": len(blueprint.nodes),
                    "diagrams_generated": list(diagrams.keys()),
                    "validation_context": validation_context
                }
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def _generate_dependency_graph(self, blueprint: "Blueprint") -> str:
        """Generate node dependency graph from blueprint."""
        mermaid = ["graph TD"]
        
        # Add all nodes with their types
        for node in blueprint.nodes:
            node_type = node.node_type
            node_label = f"{node.id}<br/>({node_type})"
            
            # Style nodes based on type
            if node_type == "tool":
                mermaid.append(f'    {node.id}["{node_label}"]')
                mermaid.append(f'    {node.id} --> {node.id}_output["📊 Output"]')
            elif node_type == "agent":
                mermaid.append(f'    {node.id}["{node_label}"]')
                mermaid.append(f'    {node.id} --> {node.id}_decision["🧠 Decision"]')
            elif node_type == "llmoperator":
                mermaid.append(f'    {node.id}["{node_label}"]')
                mermaid.append(f'    {node.id} --> {node.id}_response["💬 Response"]')
            else:
                mermaid.append(f'    {node.id}["{node_label}"]')
        
        # Add dependencies
        for node in blueprint.nodes:
            for dep in node.dependencies:
                mermaid.append(f"    {dep} --> {node.id}")
        
        # Add styling
        mermaid.extend([
            "    classDef tool fill:#e8f5e8,stroke:#2e7d32,stroke-width:2px",
            "    classDef agent fill:#e3f2fd,stroke:#1976d2,stroke-width:2px", 
            "    classDef llm fill:#fff3e0,stroke:#f57c00,stroke-width:2px",
            "    classDef output fill:#f3e5f5,stroke:#7b1fa2,stroke-width:1px"
        ])
        
        # Apply styles to nodes based on type
        tool_nodes = [n.id for n in blueprint.nodes if n.node_type == "tool"]
        agent_nodes = [n.id for n in blueprint.nodes if n.node_type == "agent"]
        llm_nodes = [n.id for n in blueprint.nodes if n.node_type == "llmoperator"]
        
        if tool_nodes:
            mermaid.append(f"    class {','.join(tool_nodes)} tool")
        if agent_nodes:
            mermaid.append(f"    class {','.join(agent_nodes)} agent")
        if llm_nodes:
            mermaid.append(f"    class {','.join(llm_nodes)} llm")
        
        return "\n".join(mermaid)
    
    def _generate_workflow_flowchart(self, blueprint: "Blueprint", include_config: bool) -> str:
        """Generate workflow flowchart showing execution flow."""
        mermaid = ["flowchart TD"]
        
        # Start node
        mermaid.append('    start([Start]) --> first_node')
        
        # Get execution order (topological sort)
        execution_order = self._get_execution_order(blueprint)
        
        # Add nodes in execution order
        for i, node in enumerate(execution_order):
            node_label = node.id
            if include_config and hasattr(node, 'config') and node.config:
                # Add key config details to label
                config_details = []
                config = node.config
                if hasattr(config, 'model') and config.model:
                    config_details.append(f"Model: {config.model}")
                if hasattr(config, 'tool_name') and config.tool_name:
                    config_details.append(f"Tool: {config.tool_name}")
                
                if config_details:
                    node_label += "<br/>" + "<br/>".join(config_details[:2])  # Limit to 2 details
            
            mermaid.append(f'    {node.id}["{node_label}"]')
            
            # Connect to next node
            if i < len(execution_order) - 1:
                next_node = execution_order[i + 1]
                mermaid.append(f"    {node.id} --> {next_node.id}")
            else:
                # Last node connects to end
                mermaid.append(f"    {node.id} --> end_node")
        
        # End node  
        mermaid.append('    end_node([End])')
        
        # Replace first_node reference with actual first node
        if execution_order:
            first_node_id = execution_order[0].id
            mermaid[1] = mermaid[1].replace('first_node', first_node_id)
        
        return "\n".join(mermaid)
    
    def _generate_config_overview(self, blueprint: "Blueprint") -> str:
        """Generate configuration overview diagram."""
        mermaid = ["graph LR"]
        
        # Blueprint info
        mermaid.append(f'    blueprint["{blueprint.blueprint_id}<br/>v{blueprint.schema_version}"]')
        
        # Group nodes by type
        node_types = {}
        for node in blueprint.nodes:
            node_type = node.node_type
            if node_type not in node_types:
                node_types[node_type] = []
            node_types[node_type].append(node)
        
        # Add type groups
        for node_type, nodes in node_types.items():
            type_id = f"type_{node_type}"
            mermaid.append(f'    {type_id}["{node_type.upper()}<br/>{len(nodes)} nodes"]')
            mermaid.append(f"    blueprint --> {type_id}")
            
            # Add individual nodes
            for node in nodes:
                mermaid.append(f'    {type_id} --> {node.id}["{node.id}"]')
        
        # Add metadata if present
        if blueprint.metadata:
            mermaid.append('    metadata["📋 Metadata"]')
            mermaid.append("    blueprint --> metadata")
            for key in list(blueprint.metadata.keys())[:3]:  # Show first 3 metadata keys
                mermaid.append(f'    metadata --> meta_{key}["{key}"]')
        
        return "\n".join(mermaid)
    
    def _generate_validation_diagram(self, blueprint: "Blueprint", validation_context: Dict) -> str:
        """Generate validation-specific diagram showing validation results."""
        mermaid = ["graph TD"]
        
        # Validation root
        mermaid.append(f'    validation["🔍 Blueprint Validation<br/>{blueprint.blueprint_id}"]')
        
        # Schema validation
        mermaid.append('    schema_check["✅ Schema Check<br/>v1.1.0"]')
        mermaid.append("    validation --> schema_check")
        
        # Node validation
        node_validation = f"node_validation[\"📋 Node Validation<br/>{len(blueprint.nodes)} nodes\"]"
        mermaid.append(f"    {node_validation}")
        mermaid.append("    validation --> node_validation")
        
        # Dependency validation
        total_deps = sum(len(node.dependencies) for node in blueprint.nodes)
        dep_validation = f"dep_validation[\"🔗 Dependency Check<br/>{total_deps} dependencies\"]"
        mermaid.append(f"    {dep_validation}")
        mermaid.append("    validation --> dep_validation")
        
        # Add validation results if available
        if validation_context.get("validation_errors"):
            mermaid.append('    errors["❌ Validation Errors"]')
            mermaid.append("    validation --> errors")
            for error in validation_context["validation_errors"][:3]:  # Show first 3 errors
                error_id = f"error_{hash(error) % 1000}"
                mermaid.append(f'    errors --> {error_id}["{error[:50]}..."]')
        
        if validation_context.get("warnings"):
            mermaid.append('    warnings["⚠️ Warnings"]')
            mermaid.append("    validation --> warnings")
        
        return "\n".join(mermaid)
    
    def _analyze_blueprint_structure(self, blueprint: "Blueprint") -> Dict[str, Any]:
        """Analyze blueprint structure and provide insights."""
        analysis = {
            "total_nodes": len(blueprint.nodes),
            "node_types": {},
            "dependency_depth": 0,
            "complexity_score": 0,
            "potential_issues": []
        }
        
        # Count node types
        for node in blueprint.nodes:
            node_type = node.node_type
            analysis["node_types"][node_type] = analysis["node_types"].get(node_type, 0) + 1
        
        # Calculate dependency depth (longest path)
        analysis["dependency_depth"] = self._calculate_dependency_depth(blueprint)
        
        # Calculate complexity score
        total_dependencies = sum(len(node.dependencies) for node in blueprint.nodes)
        analysis["complexity_score"] = (
            len(blueprint.nodes) * 2 + 
            total_dependencies * 1.5 + 
            len(analysis["node_types"]) * 0.5
        )
        
        # Identify potential issues
        if len(blueprint.nodes) > 50:
            analysis["potential_issues"].append("Large workflow: Consider breaking into smaller blueprints")
        
        if analysis["dependency_depth"] > 10:
            analysis["potential_issues"].append("Deep dependency chain: May impact performance")
        
        orphaned_nodes = [n.id for n in blueprint.nodes if not n.dependencies and len(blueprint.nodes) > 1]
        if len(orphaned_nodes) > 1:
            analysis["potential_issues"].append(f"Multiple orphaned nodes: {orphaned_nodes}")
        
        return analysis
    
    def _get_execution_order(self, blueprint: "Blueprint") -> List[Any]:
        """Get nodes in topological execution order."""
        # Simple topological sort
        in_degree = {node.id: len(node.dependencies) for node in blueprint.nodes}
        queue = [node for node in blueprint.nodes if in_degree[node.id] == 0]
        result = []
        
        while queue:
            current = queue.pop(0)
            result.append(current)
            
            # Update in-degrees for dependent nodes
            for node in blueprint.nodes:
                if current.id in node.dependencies:
                    in_degree[node.id] -= 1
                    if in_degree[node.id] == 0:
                        queue.append(node)
        
        return result
    
    def _calculate_dependency_depth(self, blueprint: "Blueprint") -> int:
        """Calculate the maximum dependency depth."""
        memo = {}
        
        def depth(node_id: str) -> int:
            if node_id in memo:
                return memo[node_id]
            
            node = next((n for n in blueprint.nodes if n.id == node_id), None)
            if not node or not node.dependencies:
                memo[node_id] = 1
                return 1
            
            max_dep_depth = max(depth(dep) for dep in node.dependencies)
            memo[node_id] = max_dep_depth + 1
            return memo[node_id]
        
        return max(depth(node.id) for node in blueprint.nodes) if blueprint.nodes else 0 