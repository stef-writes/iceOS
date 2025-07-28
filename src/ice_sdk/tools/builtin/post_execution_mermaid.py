"""
📊 Post-Execution Mermaid Generator
==================================

Automatically generates detailed Mermaid diagrams after workflow execution.
Creates comprehensive visualizations showing:
- Execution flow and timing
- Node performance metrics  
- Resource usage patterns
- Error paths and retries
- Agent interactions
- Memory operations
"""

import json
from datetime import datetime
from typing import Any, Dict, List, Optional
from ice_sdk.tools.base import ToolBase


class PostExecutionMermaidTool(ToolBase):
    """Generate comprehensive Mermaid diagrams from workflow execution traces."""
    
    name: str = "post_execution_mermaid"
    description: str = "Generate detailed Mermaid diagrams from workflow execution data"
    
    async def _execute_impl(self, **kwargs) -> Dict[str, Any]:
        """Generate Mermaid diagrams from execution trace data.
        
        Args:
            execution_trace: Workflow execution trace data
            workflow_result: Final workflow execution result
            diagram_types: List of diagram types to generate (default: all)
            include_timing: Include execution timing data (default: True)
            include_resources: Include resource usage (default: True)
            
        Returns:
            Dict containing multiple Mermaid diagrams and metadata
        """
        try:
            execution_trace = kwargs.get("execution_trace", {})
            workflow_result = kwargs.get("workflow_result", {})
            diagram_types = kwargs.get("diagram_types", ["flowchart", "sequence", "gantt", "graph"])
            include_timing = kwargs.get("include_timing", True)
            include_resources = kwargs.get("include_resources", True)
            
            diagrams = {}
            
            # Generate different diagram types
            if "flowchart" in diagram_types:
                diagrams["execution_flowchart"] = self._generate_execution_flowchart(
                    execution_trace, include_timing, include_resources
                )
            
            if "sequence" in diagram_types:
                diagrams["agent_sequence"] = self._generate_agent_sequence_diagram(
                    execution_trace
                )
            
            if "gantt" in diagram_types:
                diagrams["timing_gantt"] = self._generate_timing_gantt(
                    execution_trace
                )
                
            if "graph" in diagram_types:
                diagrams["dependency_graph"] = self._generate_dependency_graph(
                    execution_trace, workflow_result
                )
                
            # Generate summary metrics
            summary = self._generate_execution_summary(execution_trace, workflow_result)
            
            return {
                "status": "success",
                "diagrams": diagrams,
                "execution_summary": summary,
                "timestamp": datetime.now().isoformat(),
                "metadata": {
                    "total_diagrams": len(diagrams),
                    "diagram_types": list(diagrams.keys()),
                    "execution_duration": summary.get("total_duration", 0),
                    "nodes_analyzed": summary.get("total_nodes", 0)
                }
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def _generate_execution_flowchart(self, trace: Dict, include_timing: bool, include_resources: bool) -> str:
        """Generate detailed execution flowchart."""
        mermaid = ["flowchart TD"]
        
        # Extract node executions
        node_executions = trace.get("node_executions", [])
        
        # Define node styles
        styles = []
        
        for execution in node_executions:
            node_id = execution.get("node_id", "unknown")
            phase = execution.get("phase", "unknown")
            details = execution.get("details", {})
            
            if phase == "started":
                # Node definition with timing if available
                node_label = f"{node_id}"
                if include_timing and "execution_time" in details:
                    node_label += f"<br/>{details['execution_time']:.2f}s"
                if include_resources and "memory_usage" in details:
                    node_label += f"<br/>{details.get('memory_usage', 0)}MB"
                    
                mermaid.append(f'    {node_id}["{node_label}"]')
                
                # Node type styling
                node_type = details.get("node_type", "unknown")
                if node_type == "tool":
                    styles.append(f"    {node_id} --> {node_id}_result")
                    mermaid.append(f'    {node_id}_result["{details.get("tool_name", "result")}"]')
                elif node_type == "agent":
                    styles.append(f"    {node_id} --> {node_id}_thought")
                    mermaid.append(f'    {node_id}_thought["🧠 Agent Reasoning"]')
                elif node_type == "recursive":
                    styles.append(f"    {node_id} --> {node_id}_loop")
                    mermaid.append(f'    {node_id}_loop["🔄 Recursive Loop"]')
        
        # Add workflow connections
        agent_thoughts = trace.get("agent_thoughts", [])
        for i in range(len(agent_thoughts) - 1):
            current = agent_thoughts[i]
            next_thought = agent_thoughts[i + 1]
            current_agent = current.get("agent_id", "unknown")
            next_agent = next_thought.get("agent_id", "unknown")
            
            if current_agent != next_agent:
                mermaid.append(f"    {current_agent} --> {next_agent}")
        
        # Add styles for different node types
        mermaid.extend([
            "    classDef toolNode fill:#e1f5fe,stroke:#01579b,stroke-width:2px",
            "    classDef agentNode fill:#f3e5f5,stroke:#4a148c,stroke-width:2px", 
            "    classDef recursiveNode fill:#fff3e0,stroke:#e65100,stroke-width:2px",
            "    classDef errorNode fill:#ffebee,stroke:#c62828,stroke-width:2px"
        ])
        
        return "\n".join(mermaid)
    
    def _generate_agent_sequence_diagram(self, trace: Dict) -> str:
        """Generate agent interaction sequence diagram."""
        mermaid = ["sequenceDiagram"]
        
        agent_thoughts = trace.get("agent_thoughts", [])
        api_calls = trace.get("api_calls", [])
        
        # Extract unique agents
        agents = set()
        for thought in agent_thoughts:
            agents.add(thought.get("agent_id", "unknown"))
        
        # Add participants
        for agent in sorted(agents):
            mermaid.append(f"    participant {agent}")
        mermaid.append("    participant arXiv")
        mermaid.append("    participant MarketData")
        
        # Add interactions
        for thought in agent_thoughts:
            agent_id = thought.get("agent_id", "unknown")
            thought_type = thought.get("thought_type", "unknown")
            content = thought.get("content", "")[:50] + "..."
            
            if thought_type == "api_preparation":
                if "arXiv" in content:
                    mermaid.append(f"    {agent_id}->>arXiv: Search Papers")
                    mermaid.append(f"    arXiv-->>({agent_id}: Papers Retrieved")
            elif thought_type == "memory_retrieval":
                mermaid.append(f"    {agent_id}->>+{agent_id}: Access Memory")
                mermaid.append(f"    {agent_id}->>-{agent_id}: Memory Retrieved")
            elif thought_type == "coordination":
                # Find other agents in conversation
                for other_agent in agents:
                    if other_agent != agent_id:
                        mermaid.append(f"    {agent_id}->>+{other_agent}: Coordinate")
                        mermaid.append(f"    {other_agent}-->>-{agent_id}: Response")
        
        # Add API calls
        for api_call in api_calls:
            service = api_call.get("service", "unknown")
            if service == "arxiv":
                mermaid.append("    Note over arXiv: 15 papers retrieved")
            elif service == "market_data":
                mermaid.append("    Note over MarketData: Stock data fetched")
        
        return "\n".join(mermaid)
    
    def _generate_timing_gantt(self, trace: Dict) -> str:
        """Generate execution timing Gantt chart."""
        mermaid = [
            "gantt",
            "    title Workflow Execution Timeline",
            "    dateFormat X",
            "    axisFormat %L"
        ]
        
        node_executions = trace.get("node_executions", [])
        
        # Process executions by timeline
        section_nodes = {}
        for execution in node_executions:
            node_id = execution.get("node_id", "unknown")
            phase = execution.get("phase", "unknown")
            details = execution.get("details", {})
            
            if phase == "started":
                node_type = details.get("node_type", "general")
                if node_type not in section_nodes:
                    section_nodes[node_type] = []
                
                execution_time = details.get("execution_time", 1000)  # Default 1s in ms
                section_nodes[node_type].append({
                    "name": node_id,
                    "duration": int(execution_time * 1000)  # Convert to ms
                })
        
        # Add sections
        start_time = 0
        for section_name, nodes in section_nodes.items():
            mermaid.append(f"    section {section_name.title()}")
            for node in nodes:
                end_time = start_time + node["duration"]
                mermaid.append(f"    {node['name']} : {start_time}, {end_time}")
                start_time = end_time + 100  # Small gap between nodes
        
        return "\n".join(mermaid)
    
    def _generate_dependency_graph(self, trace: Dict, result: Dict) -> str:
        """Generate node dependency graph."""
        mermaid = ["graph LR"]
        
        # Extract workflow structure from results
        workflows_executed = result.get("workflows_executed", [])
        
        for workflow in workflows_executed:
            mermaid.append(f"    {workflow}[{workflow.replace('_', ' ').title()}]")
        
        # Add connections based on execution order
        if len(workflows_executed) > 1:
            for i in range(len(workflows_executed) - 1):
                current = workflows_executed[i]
                next_wf = workflows_executed[i + 1]
                mermaid.append(f"    {current} --> {next_wf}")
        
        # Add final result
        mermaid.append("    final_result[📊 Investment Recommendation]")
        if workflows_executed:
            last_workflow = workflows_executed[-1]
            mermaid.append(f"    {last_workflow} --> final_result")
        
        # Add styling
        mermaid.extend([
            "    classDef workflow fill:#e8f5e8,stroke:#2e7d32,stroke-width:2px",
            "    classDef result fill:#fff3e0,stroke:#f57c00,stroke-width:3px",
            f"    class {','.join(workflows_executed)} workflow",
            "    class final_result result"
        ])
        
        return "\n".join(mermaid)
    
    def _generate_execution_summary(self, trace: Dict, result: Dict) -> Dict[str, Any]:
        """Generate comprehensive execution summary."""
        node_executions = trace.get("node_executions", [])
        agent_thoughts = trace.get("agent_thoughts", [])
        api_calls = trace.get("api_calls", [])
        
        # Calculate timing metrics
        execution_times = []
        for execution in node_executions:
            if execution.get("phase") == "completed":
                details = execution.get("details", {})
                if "execution_time" in details:
                    execution_times.append(details["execution_time"])
        
        total_duration = sum(execution_times)
        avg_duration = total_duration / len(execution_times) if execution_times else 0
        
        return {
            "total_duration": total_duration,
            "average_node_duration": avg_duration,
            "total_nodes": len(set(ex.get("node_id") for ex in node_executions)),
            "total_agent_thoughts": len(agent_thoughts),
            "total_api_calls": len(api_calls),
            "unique_agents": len(set(thought.get("agent_id") for thought in agent_thoughts)),
            "workflows_executed": result.get("workflows_executed", []),
            "final_confidence": result.get("results", {}).get("recursive_synthesis", {}).get("confidence_score", 0),
            "papers_analyzed": result.get("results", {}).get("literature_analysis", {}).get("papers_analyzed", 0)
        }

    @classmethod
    def get_input_schema(cls) -> Dict[str, Any]:
        """Return input schema for this tool."""
        return {
            "type": "object",
            "properties": {
                "execution_trace": {
                    "type": "object",
                    "description": "Workflow execution trace data"
                },
                "workflow_result": {
                    "type": "object", 
                    "description": "Final workflow execution result"
                },
                "diagram_types": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Types of diagrams to generate",
                    "default": ["flowchart", "sequence", "gantt", "graph"]
                },
                "include_timing": {
                    "type": "boolean",
                    "description": "Include timing information",
                    "default": True
                },
                "include_resources": {
                    "type": "boolean", 
                    "description": "Include resource usage data",
                    "default": True
                }
            },
            "required": ["execution_trace", "workflow_result"]
        } 