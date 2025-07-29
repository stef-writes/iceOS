"""
📝 Execution Summarizer Tool
===========================

Generate concise, human-readable summaries of workflow execution.
Perfect for executive reports, debugging, and quick insights.

Key Features:
- Executive summary generation
- Performance highlights
- Key insights extraction
- Error summaries
- Resource usage summaries
"""

from datetime import datetime
from typing import Any, Dict, List
from ice_sdk.tools.base import ToolBase


class ExecutionSummarizerTool(ToolBase):
    """Generate comprehensive execution summaries for workflows."""
    
    name: str = "execution_summarizer"
    description: str = "Generate human-readable execution summaries and reports"
    
    async def _execute_impl(self, **kwargs) -> Dict[str, Any]:
        """Generate execution summary from trace and result data.
        
        Args:
            execution_trace: Workflow execution trace data
            workflow_result: Final workflow execution result
            summary_type: Type of summary (executive, technical, detailed)
            include_recommendations: Include optimization recommendations
            
        Returns:
            Formatted summary with key insights and metrics
        """
        try:
            execution_trace = kwargs.get("execution_trace", {})
            workflow_result = kwargs.get("workflow_result", {})
            summary_type = kwargs.get("summary_type", "executive")
            include_recommendations = kwargs.get("include_recommendations", True)
            
            # Generate different summary types
            if summary_type == "executive":
                summary = self._generate_executive_summary(execution_trace, workflow_result)
            elif summary_type == "technical":
                summary = self._generate_technical_summary(execution_trace, workflow_result)
            else:  # detailed
                summary = self._generate_detailed_summary(execution_trace, workflow_result)
            
            # Add recommendations if requested
            if include_recommendations:
                summary["recommendations"] = self._generate_recommendations(execution_trace, workflow_result)
            
            # Add key metrics
            summary["key_metrics"] = self._extract_key_metrics(execution_trace, workflow_result)
            
            return {
                "status": "success",
                "summary": summary,
                "summary_type": summary_type,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def _generate_executive_summary(self, trace: Dict, result: Dict) -> Dict[str, Any]:
        """Generate executive-level summary focused on outcomes and business impact."""
        workflows = result.get("workflows_executed", [])
        total_duration = self._calculate_total_duration(trace)
        
        # Extract business outcomes
        business_outcomes = []
        results_data = result.get("results", {})
        
        if "literature_analysis" in results_data:
            lit_data = results_data["literature_analysis"]
            papers_count = lit_data.get("papers_analyzed", 0)
            confidence = lit_data.get("confidence_score", 0)
            business_outcomes.append(f"Analyzed {papers_count} research papers with {confidence:.0%} confidence")
        
        if "recursive_synthesis" in results_data:
            synth_data = results_data["recursive_synthesis"]
            final_confidence = synth_data.get("confidence_score", 0)
            convergence = synth_data.get("convergence_achieved", False)
            business_outcomes.append(f"Achieved {final_confidence:.0%} investment confidence {'with' if convergence else 'without'} full convergence")
        
        return {
            "title": "Workflow Execution Summary",
            "execution_date": datetime.now().strftime("%B %d, %Y"),
            "overview": f"Successfully executed {len(workflows)} workflows in {total_duration:.1f} seconds",
            "business_outcomes": business_outcomes,
            "success_status": "✅ Completed Successfully" if result.get("overall_success", True) else "⚠️ Completed with Issues",
            "key_achievements": self._extract_key_achievements(result),
            "performance_summary": f"Average workflow performance: {self._calculate_avg_performance(trace)}"
        }
    
    def _generate_technical_summary(self, trace: Dict, result: Dict) -> Dict[str, Any]:
        """Generate technical summary focused on system performance and implementation."""
        node_executions = trace.get("node_executions", [])
        api_calls = trace.get("api_calls", [])
        agent_thoughts = trace.get("agent_thoughts", [])
        
        # Technical metrics
        nodes_executed = len([ex for ex in node_executions if ex.get("phase") == "completed"])
        total_nodes = len(set(ex.get("node_id") for ex in node_executions if ex.get("phase") == "started"))
        
        return {
            "title": "Technical Execution Report",
            "system_performance": {
                "nodes_executed": f"{nodes_executed}/{total_nodes}",
                "completion_rate": f"{(nodes_executed/total_nodes*100):.1f}%" if total_nodes > 0 else "0%",
                "total_api_calls": len(api_calls),
                "agent_thoughts": len(agent_thoughts)
            },
            "infrastructure_usage": self._analyze_infrastructure_usage(trace),
            "error_analysis": self._analyze_errors(trace),
            "performance_bottlenecks": self._identify_bottlenecks(trace),
            "resource_efficiency": self._calculate_resource_efficiency(trace)
        }
    
    def _generate_detailed_summary(self, trace: Dict, result: Dict) -> Dict[str, Any]:
        """Generate comprehensive detailed summary with all available information."""
        return {
            "title": "Detailed Execution Analysis",
            "executive_overview": self._generate_executive_summary(trace, result),
            "technical_details": self._generate_technical_summary(trace, result),
            "workflow_breakdown": self._analyze_workflow_breakdown(result),
            "agent_coordination": self._analyze_agent_coordination(trace),
            "timeline_analysis": self._generate_timeline_analysis(trace),
            "data_flow": self._analyze_data_flow(trace, result)
        }
    
    def _extract_key_achievements(self, result: Dict) -> List[str]:
        """Extract key achievements from workflow results."""
        achievements = []
        results_data = result.get("results", {})
        
        for workflow_name, workflow_result in results_data.items():
            if isinstance(workflow_result, dict):
                confidence = workflow_result.get("confidence_score", 0)
                if confidence > 0.8:
                    achievements.append(f"High-confidence {workflow_name.replace('_', ' ')} ({confidence:.0%})")
                elif confidence > 0.6:
                    achievements.append(f"Moderate-confidence {workflow_name.replace('_', ' ')} ({confidence:.0%})")
        
        return achievements
    
    def _calculate_total_duration(self, trace: Dict) -> float:
        """Calculate total execution duration."""
        node_executions = trace.get("node_executions", [])
        execution_times = []
        
        for execution in node_executions:
            if execution.get("phase") == "completed":
                details = execution.get("details", {})
                if "execution_time" in details:
                    execution_times.append(details["execution_time"])
        
        return sum(execution_times)
    
    def _calculate_avg_performance(self, trace: Dict) -> str:
        """Calculate average performance rating."""
        total_duration = self._calculate_total_duration(trace)
        node_count = len(set(ex.get("node_id") for ex in trace.get("node_executions", [])))
        
        if node_count == 0:
            return "No data"
        
        avg_time = total_duration / node_count
        
        if avg_time < 1.0:
            return "Excellent (< 1s per node)"
        elif avg_time < 3.0:
            return "Good (< 3s per node)"
        elif avg_time < 10.0:
            return "Fair (< 10s per node)"
        else:
            return "Needs optimization (> 10s per node)"
    
    def _analyze_infrastructure_usage(self, trace: Dict) -> Dict[str, Any]:
        """Analyze infrastructure and resource usage."""
        api_calls = trace.get("api_calls", [])
        
        # Service usage breakdown
        service_usage = {}
        total_api_time = 0
        
        for api_call in api_calls:
            service = api_call.get("service", "unknown")
            duration = api_call.get("duration", 0)
            
            if service not in service_usage:
                service_usage[service] = {"calls": 0, "time": 0}
            
            service_usage[service]["calls"] += 1
            service_usage[service]["time"] += duration
            total_api_time += duration
        
        return {
            "total_api_time": f"{total_api_time:.2f}s",
            "service_breakdown": service_usage,
            "most_used_service": max(service_usage.keys(), key=lambda x: service_usage[x]["calls"]) if service_usage else "None"
        }
    
    def _analyze_errors(self, trace: Dict) -> Dict[str, Any]:
        """Analyze errors and issues during execution."""
        node_executions = trace.get("node_executions", [])
        
        errors = []
        warnings = []
        
        for execution in node_executions:
            if execution.get("phase") == "failed":
                errors.append({
                    "node": execution.get("node_id", "unknown"),
                    "error": execution.get("details", {}).get("error", "Unknown error")
                })
        
        # Check for warning patterns in agent thoughts
        agent_thoughts = trace.get("agent_thoughts", [])
        for thought in agent_thoughts:
            content = thought.get("content", "").lower()
            if "limitation" in content or "fallback" in content:
                warnings.append({
                    "agent": thought.get("agent_id", "unknown"),
                    "warning": thought.get("content", "")[:100] + "..."
                })
        
        return {
            "error_count": len(errors),
            "warning_count": len(warnings),
            "errors": errors[:5],  # Top 5 errors
            "warnings": warnings[:3],  # Top 3 warnings
            "overall_health": "Healthy" if not errors else "Issues detected"
        }
    
    def _identify_bottlenecks(self, trace: Dict) -> List[Dict[str, Any]]:
        """Identify performance bottlenecks."""
        node_executions = trace.get("node_executions", [])
        bottlenecks = []
        
        for execution in node_executions:
            if execution.get("phase") == "completed":
                details = execution.get("details", {})
                exec_time = details.get("execution_time", 0)
                
                if exec_time > 5.0:  # Bottleneck threshold
                    bottlenecks.append({
                        "node": execution.get("node_id", "unknown"),
                        "duration": f"{exec_time:.2f}s",
                        "type": details.get("node_type", "unknown")
                    })
        
        return sorted(bottlenecks, key=lambda x: float(x["duration"].replace("s", "")), reverse=True)[:3]
    
    def _calculate_resource_efficiency(self, trace: Dict) -> str:
        """Calculate overall resource efficiency rating."""
        api_calls = trace.get("api_calls", [])
        agent_thoughts = trace.get("agent_thoughts", [])
        
        if not api_calls:
            return "No API usage"
        
        # Simple efficiency metric: thoughts per API call
        efficiency_ratio = len(agent_thoughts) / len(api_calls) if api_calls else 0
        
        if efficiency_ratio > 5:
            return "High efficiency (good thought-to-API ratio)"
        elif efficiency_ratio > 2:
            return "Moderate efficiency"
        else:
            return "Low efficiency (consider optimizing API usage)"
    
    def _analyze_workflow_breakdown(self, result: Dict) -> Dict[str, Any]:
        """Analyze individual workflow performance."""
        workflows = result.get("workflows_executed", [])
        results_data = result.get("results", {})
        
        breakdown = {}
        for workflow in workflows:
            if workflow in results_data:
                workflow_result = results_data[workflow]
                if isinstance(workflow_result, dict):
                    breakdown[workflow] = {
                        "confidence": workflow_result.get("confidence_score", 0),
                        "execution_time": workflow_result.get("execution_time", 0),
                        "status": "success" if workflow_result.get("confidence_score", 0) > 0.5 else "needs_improvement"
                    }
        
        return breakdown
    
    def _analyze_agent_coordination(self, trace: Dict) -> Dict[str, Any]:
        """Analyze agent coordination patterns."""
        agent_thoughts = trace.get("agent_thoughts", [])
        
        agents = set(thought.get("agent_id") for thought in agent_thoughts)
        coordination_events = len([t for t in agent_thoughts if "coordination" in t.get("thought_type", "")])
        
        return {
            "total_agents": len(agents),
            "coordination_events": coordination_events,
            "coordination_density": f"{coordination_events/len(agent_thoughts)*100:.1f}%" if agent_thoughts else "0%",
            "most_active_agent": max(agents, key=lambda agent: len([t for t in agent_thoughts if t.get("agent_id") == agent])) if agents else "None"
        }
    
    def _generate_timeline_analysis(self, trace: Dict) -> Dict[str, Any]:
        """Generate timeline analysis of execution."""
        node_executions = trace.get("node_executions", [])
        
        # Extract timestamps and phases
        timeline_events = []
        for execution in node_executions:
            timeline_events.append({
                "timestamp": execution.get("timestamp", ""),
                "event": f"{execution.get('node_id', 'unknown')} {execution.get('phase', 'unknown')}",
                "phase": execution.get("phase", "unknown")
            })
        
        # Calculate phase durations
        phases = ["started", "completed"]
        phase_counts = {phase: len([e for e in timeline_events if e["phase"] == phase]) for phase in phases}
        
        return {
            "total_events": len(timeline_events),
            "phase_breakdown": phase_counts,
            "timeline_span": "Full execution trace available"
        }
    
    def _analyze_data_flow(self, trace: Dict, result: Dict) -> Dict[str, Any]:
        """Analyze data flow through the workflow."""
        api_calls = trace.get("api_calls", [])
        
        # Data sources
        data_sources = set()
        for api_call in api_calls:
            service = api_call.get("service", "unknown")
            data_sources.add(service)
        
        # Data outputs
        results_data = result.get("results", {})
        output_types = list(results_data.keys())
        
        return {
            "data_sources": list(data_sources),
            "output_types": output_types,
            "data_flow_complexity": len(data_sources) + len(output_types),
            "integration_points": len(api_calls)
        }
    
    def _generate_recommendations(self, trace: Dict, result: Dict) -> List[Dict[str, Any]]:
        """Generate optimization recommendations."""
        recommendations = []
        
        # Performance recommendations
        bottlenecks = self._identify_bottlenecks(trace)
        if bottlenecks:
            recommendations.append({
                "category": "Performance",
                "priority": "High",
                "title": "Optimize Slow Nodes",
                "description": f"Consider optimizing {len(bottlenecks)} nodes with execution times > 5s",
                "nodes_affected": [b["node"] for b in bottlenecks]
            })
        
        # Resource recommendations
        api_calls = trace.get("api_calls", [])
        if len(api_calls) > 10:
            recommendations.append({
                "category": "Resources",
                "priority": "Medium", 
                "title": "Consider API Caching",
                "description": f"High API usage ({len(api_calls)} calls) could benefit from caching",
                "estimated_savings": "20-30% execution time reduction"
            })
        
        # Agent coordination recommendations
        agent_thoughts = trace.get("agent_thoughts", [])
        coordination_ratio = len([t for t in agent_thoughts if "coordination" in t.get("thought_type", "")]) / len(agent_thoughts) if agent_thoughts else 0
        
        if coordination_ratio > 0.3:
            recommendations.append({
                "category": "Architecture",
                "priority": "Low",
                "title": "Review Agent Coordination",
                "description": f"High coordination overhead ({coordination_ratio:.1%}) - consider workflow restructuring",
                "impact": "Reduced coordination complexity"
            })
        
        return recommendations
    
    def _extract_key_metrics(self, trace: Dict, result: Dict) -> Dict[str, Any]:
        """Extract key metrics for dashboard display."""
        node_executions = trace.get("node_executions", [])
        api_calls = trace.get("api_calls", [])
        agent_thoughts = trace.get("agent_thoughts", [])
        
        return {
            "execution_time": f"{self._calculate_total_duration(trace):.1f}s",
            "nodes_executed": len(set(ex.get("node_id") for ex in node_executions)),
            "api_calls": len(api_calls),
            "agent_thoughts": len(agent_thoughts),
            "success_rate": "100%" if result.get("overall_success", True) else "Partial",
            "confidence_level": f"{result.get('results', {}).get('recursive_synthesis', {}).get('confidence_score', 0):.0%}"
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
                "summary_type": {
                    "type": "string",
                    "enum": ["executive", "technical", "detailed"],
                    "description": "Type of summary to generate",
                    "default": "executive"
                },
                "include_recommendations": {
                    "type": "boolean",
                    "description": "Include optimization recommendations",
                    "default": True
                }
            },
            "required": ["execution_trace", "workflow_result"]
        } 