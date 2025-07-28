"""
📈 Workflow Analyzer Tool
========================

Comprehensive analysis of workflow execution patterns, performance bottlenecks,
and optimization opportunities.

Key Features:
- Performance bottleneck detection
- Resource usage analysis  
- Agent coordination patterns
- Critical path identification
- Optimization recommendations
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from ice_sdk.tools.base import ToolBase


class WorkflowAnalyzerTool(ToolBase):
    """Analyze workflow execution for performance insights and optimization opportunities."""
    
    name: str = "workflow_analyzer"
    description: str = "Comprehensive workflow execution analysis and optimization recommendations"
    
    async def _execute_impl(self, **kwargs) -> Dict[str, Any]:
        """Analyze workflow execution data for insights and recommendations.
        
        Args:
            execution_trace: Workflow execution trace data
            workflow_result: Final workflow execution result
            analysis_depth: Analysis depth level (basic, detailed, comprehensive)
            focus_areas: Specific areas to analyze (performance, agents, resources)
            
        Returns:
            Comprehensive analysis report with recommendations
        """
        try:
            execution_trace = kwargs.get("execution_trace", {})
            workflow_result = kwargs.get("workflow_result", {})
            analysis_depth = kwargs.get("analysis_depth", "detailed")
            focus_areas = kwargs.get("focus_areas", ["performance", "agents", "resources"])
            
            analysis = {
                "timestamp": datetime.now().isoformat(),
                "analysis_depth": analysis_depth,
                "focus_areas": focus_areas,
                "summary": {},
                "detailed_analysis": {},
                "recommendations": [],
                "metrics": {}
            }
            
            # Performance Analysis
            if "performance" in focus_areas:
                analysis["detailed_analysis"]["performance"] = self._analyze_performance(
                    execution_trace, analysis_depth
                )
            
            # Agent Coordination Analysis
            if "agents" in focus_areas:
                analysis["detailed_analysis"]["agent_coordination"] = self._analyze_agent_coordination(
                    execution_trace, analysis_depth
                )
            
            # Resource Usage Analysis
            if "resources" in focus_areas:
                analysis["detailed_analysis"]["resource_usage"] = self._analyze_resource_usage(
                    execution_trace, workflow_result, analysis_depth
                )
            
            # Generate overall summary
            analysis["summary"] = self._generate_summary(analysis["detailed_analysis"])
            
            # Generate optimization recommendations
            analysis["recommendations"] = self._generate_recommendations(
                analysis["detailed_analysis"], analysis_depth
            )
            
            # Calculate key metrics
            analysis["metrics"] = self._calculate_key_metrics(execution_trace, workflow_result)
            
            return {
                "status": "success",
                "analysis": analysis,
                "insights_count": len(analysis["recommendations"]),
                "critical_issues": [r for r in analysis["recommendations"] if r.get("priority") == "high"]
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def _analyze_performance(self, trace: Dict, depth: str) -> Dict[str, Any]:
        """Analyze workflow performance patterns."""
        node_executions = trace.get("node_executions", [])
        
        # Extract execution times
        execution_times = {}
        bottlenecks = []
        
        for execution in node_executions:
            if execution.get("phase") == "completed":
                node_id = execution.get("node_id")
                details = execution.get("details", {})
                exec_time = details.get("execution_time", 0)
                
                if node_id:
                    execution_times[node_id] = exec_time
                    
                    # Identify bottlenecks (>5 seconds)
                    if exec_time > 5.0:
                        bottlenecks.append({
                            "node_id": node_id,
                            "execution_time": exec_time,
                            "node_type": details.get("node_type", "unknown")
                        })
        
        # Calculate statistics
        times = list(execution_times.values())
        avg_time = sum(times) / len(times) if times else 0
        max_time = max(times) if times else 0
        min_time = min(times) if times else 0
        
        analysis = {
            "total_nodes": len(execution_times),
            "total_execution_time": sum(times),
            "average_execution_time": avg_time,
            "max_execution_time": max_time,
            "min_execution_time": min_time,
            "bottlenecks": sorted(bottlenecks, key=lambda x: x["execution_time"], reverse=True),
            "performance_distribution": self._categorize_performance(execution_times)
        }
        
        if depth in ["detailed", "comprehensive"]:
            analysis["parallel_opportunities"] = self._identify_parallel_opportunities(trace)
            analysis["critical_path"] = self._identify_critical_path(execution_times)
        
        return analysis
    
    def _analyze_agent_coordination(self, trace: Dict, depth: str) -> Dict[str, Any]:
        """Analyze agent coordination patterns and effectiveness."""
        agent_thoughts = trace.get("agent_thoughts", [])
        memory_operations = trace.get("memory_operations", [])
        
        # Agent activity analysis
        agent_activity = {}
        coordination_patterns = []
        
        for thought in agent_thoughts:
            agent_id = thought.get("agent_id")
            thought_type = thought.get("thought_type")
            
            if agent_id:
                if agent_id not in agent_activity:
                    agent_activity[agent_id] = {
                        "total_thoughts": 0,
                        "thought_types": {},
                        "memory_operations": 0
                    }
                
                agent_activity[agent_id]["total_thoughts"] += 1
                
                if thought_type not in agent_activity[agent_id]["thought_types"]:
                    agent_activity[agent_id]["thought_types"][thought_type] = 0
                agent_activity[agent_id]["thought_types"][thought_type] += 1
                
                # Detect coordination patterns
                if thought_type in ["coordination", "consensus_calculation", "multi_agent_synthesis"]:
                    coordination_patterns.append({
                        "agent": agent_id,
                        "type": thought_type,
                        "timestamp": thought.get("timestamp")
                    })
        
        # Memory usage by agents
        for memory_op in memory_operations:
            agent_id = memory_op.get("agent_id")
            if agent_id in agent_activity:
                agent_activity[agent_id]["memory_operations"] += 1
        
        analysis = {
            "total_agents": len(agent_activity),
            "agent_activity": agent_activity,
            "coordination_events": len(coordination_patterns),
            "coordination_patterns": coordination_patterns,
            "most_active_agent": max(agent_activity.keys(), 
                                   key=lambda x: agent_activity[x]["total_thoughts"]) if agent_activity else None
        }
        
        if depth in ["detailed", "comprehensive"]:
            analysis["coordination_efficiency"] = self._calculate_coordination_efficiency(coordination_patterns)
            analysis["agent_specialization"] = self._analyze_agent_specialization(agent_activity)
        
        return analysis
    
    def _analyze_resource_usage(self, trace: Dict, result: Dict, depth: str) -> Dict[str, Any]:
        """Analyze resource usage patterns."""
        api_calls = trace.get("api_calls", [])
        
        # API usage analysis
        api_usage = {}
        total_api_time = 0
        
        for api_call in api_calls:
            service = api_call.get("service", "unknown")
            duration = api_call.get("duration", 0)
            
            if service not in api_usage:
                api_usage[service] = {
                    "call_count": 0,
                    "total_duration": 0,
                    "endpoints": set()
                }
            
            api_usage[service]["call_count"] += 1
            api_usage[service]["total_duration"] += duration
            total_api_time += duration
            
            endpoint = api_call.get("endpoint", "")
            if endpoint:
                api_usage[service]["endpoints"].add(endpoint)
        
        # Convert sets to lists for JSON serialization
        for service in api_usage:
            api_usage[service]["endpoints"] = list(api_usage[service]["endpoints"])
        
        # Cost analysis (if available)
        cost_data = result.get("total_cost_estimate", 0)
        
        analysis = {
            "total_api_calls": len(api_calls),
            "total_api_time": total_api_time,
            "api_usage_by_service": api_usage,
            "estimated_cost": cost_data,
            "resource_efficiency": total_api_time / len(api_calls) if api_calls else 0
        }
        
        if depth in ["detailed", "comprehensive"]:
            analysis["cost_breakdown"] = self._analyze_cost_patterns(api_usage, cost_data)
            analysis["optimization_opportunities"] = self._identify_resource_optimizations(api_usage)
        
        return analysis
    
    def _categorize_performance(self, execution_times: Dict[str, float]) -> Dict[str, List[str]]:
        """Categorize nodes by performance."""
        categories = {
            "fast": [],      # < 1 second
            "moderate": [],  # 1-5 seconds
            "slow": [],      # > 5 seconds
        }
        
        for node_id, time in execution_times.items():
            if time < 1.0:
                categories["fast"].append(node_id)
            elif time < 5.0:
                categories["moderate"].append(node_id)
            else:
                categories["slow"].append(node_id)
        
        return categories
    
    def _identify_parallel_opportunities(self, trace: Dict) -> List[Dict[str, Any]]:
        """Identify opportunities for parallel execution."""
        node_executions = trace.get("node_executions", [])
        
        # Simple heuristic: nodes that don't depend on each other
        # This is a simplified analysis - real implementation would need dependency graph
        opportunities = []
        
        independent_nodes = []
        for execution in node_executions:
            if execution.get("phase") == "started":
                node_type = execution.get("details", {}).get("node_type")
                if node_type in ["tool", "api_call"]:
                    independent_nodes.append({
                        "node_id": execution.get("node_id"),
                        "execution_time": execution.get("details", {}).get("execution_time", 0)
                    })
        
        if len(independent_nodes) > 1:
            opportunities.append({
                "type": "parallel_tool_execution",
                "description": f"Could parallelize {len(independent_nodes)} independent tool calls",
                "potential_savings": sum(node["execution_time"] for node in independent_nodes) * 0.7,
                "nodes": independent_nodes
            })
        
        return opportunities
    
    def _identify_critical_path(self, execution_times: Dict[str, float]) -> List[str]:
        """Identify the critical path through the workflow."""
        # Simple heuristic: nodes with longest execution times
        # Real implementation would analyze dependency graph
        return sorted(execution_times.keys(), key=lambda x: execution_times[x], reverse=True)[:3]
    
    def _calculate_coordination_efficiency(self, patterns: List[Dict]) -> float:
        """Calculate how efficiently agents coordinate."""
        if not patterns:
            return 1.0
        
        # Simple metric: fewer coordination events = more efficient
        # This is a placeholder for more sophisticated analysis
        total_events = len(patterns)
        if total_events <= 3:
            return 1.0
        elif total_events <= 6:
            return 0.8
        else:
            return 0.6
    
    def _analyze_agent_specialization(self, activity: Dict) -> Dict[str, str]:
        """Analyze what each agent specializes in."""
        specializations = {}
        
        for agent_id, data in activity.items():
            thought_types = data.get("thought_types", {})
            if not thought_types:
                specializations[agent_id] = "general"
                continue
            
            # Find the most common thought type
            dominant_type = max(thought_types.keys(), key=lambda x: thought_types[x])
            
            # Map to specialization
            specialization_map = {
                "api_preparation": "data_retrieval",
                "analysis": "analysis", 
                "coordination": "coordination",
                "memory_retrieval": "memory_management",
                "planning": "strategic_planning"
            }
            
            specializations[agent_id] = specialization_map.get(dominant_type, "general")
        
        return specializations
    
    def _analyze_cost_patterns(self, api_usage: Dict, total_cost: float) -> Dict[str, Any]:
        """Analyze cost patterns and expensive operations."""
        return {
            "total_estimated_cost": total_cost,
            "cost_per_api_call": total_cost / sum(service["call_count"] for service in api_usage.values()) if api_usage else 0,
            "most_expensive_service": max(api_usage.keys(), key=lambda x: api_usage[x]["call_count"]) if api_usage else None
        }
    
    def _identify_resource_optimizations(self, api_usage: Dict) -> List[Dict[str, Any]]:
        """Identify resource optimization opportunities."""
        optimizations = []
        
        for service, data in api_usage.items():
            call_count = data["call_count"]
            avg_duration = data["total_duration"] / call_count if call_count > 0 else 0
            
            # High-frequency service optimization
            if call_count > 5:
                optimizations.append({
                    "type": "caching_opportunity",
                    "service": service,
                    "description": f"Consider caching {service} responses ({call_count} calls)",
                    "potential_savings": f"{(call_count - 1) * avg_duration:.2f}s"
                })
            
            # Slow service optimization
            if avg_duration > 2.0:
                optimizations.append({
                    "type": "performance_optimization", 
                    "service": service,
                    "description": f"Optimize {service} calls (avg {avg_duration:.2f}s)",
                    "potential_savings": f"{avg_duration * 0.5:.2f}s per call"
                })
        
        return optimizations
    
    def _generate_summary(self, detailed_analysis: Dict) -> Dict[str, Any]:
        """Generate executive summary of the analysis."""
        summary = {}
        
        if "performance" in detailed_analysis:
            perf = detailed_analysis["performance"]
            summary["performance"] = {
                "total_execution_time": perf.get("total_execution_time", 0),
                "bottleneck_count": len(perf.get("bottlenecks", [])),
                "parallel_opportunities": len(perf.get("parallel_opportunities", []))
            }
        
        if "agent_coordination" in detailed_analysis:
            coord = detailed_analysis["agent_coordination"]
            summary["coordination"] = {
                "agents_involved": coord.get("total_agents", 0),
                "coordination_events": coord.get("coordination_events", 0),
                "most_active": coord.get("most_active_agent", "unknown")
            }
        
        if "resource_usage" in detailed_analysis:
            resources = detailed_analysis["resource_usage"]
            summary["resources"] = {
                "api_calls": resources.get("total_api_calls", 0),
                "api_time": resources.get("total_api_time", 0),
                "estimated_cost": resources.get("estimated_cost", 0)
            }
        
        return summary
    
    def _generate_recommendations(self, detailed_analysis: Dict, depth: str) -> List[Dict[str, Any]]:
        """Generate actionable optimization recommendations."""
        recommendations = []
        
        # Performance recommendations
        if "performance" in detailed_analysis:
            perf = detailed_analysis["performance"]
            bottlenecks = perf.get("bottlenecks", [])
            
            for bottleneck in bottlenecks[:3]:  # Top 3 bottlenecks
                recommendations.append({
                    "category": "performance",
                    "priority": "high" if bottleneck["execution_time"] > 10 else "medium",
                    "title": f"Optimize {bottleneck['node_id']} execution",
                    "description": f"Node takes {bottleneck['execution_time']:.2f}s - consider optimization",
                    "estimated_impact": f"Save {bottleneck['execution_time'] * 0.3:.2f}s per execution"
                })
            
            parallel_ops = perf.get("parallel_opportunities", [])
            for opp in parallel_ops:
                recommendations.append({
                    "category": "architecture",
                    "priority": "medium",
                    "title": opp["type"].replace("_", " ").title(),
                    "description": opp["description"],
                    "estimated_impact": f"Save {opp['potential_savings']:.2f}s"
                })
        
        # Resource recommendations
        if "resource_usage" in detailed_analysis:
            resources = detailed_analysis["resource_usage"]
            optimizations = resources.get("optimization_opportunities", [])
            
            for opt in optimizations:
                recommendations.append({
                    "category": "resources",
                    "priority": "low",
                    "title": opt["type"].replace("_", " ").title(),
                    "description": opt["description"],
                    "estimated_impact": opt["potential_savings"]
                })
        
        return recommendations
    
    def _calculate_key_metrics(self, trace: Dict, result: Dict) -> Dict[str, Any]:
        """Calculate key performance metrics."""
        node_executions = trace.get("node_executions", [])
        agent_thoughts = trace.get("agent_thoughts", [])
        
        total_nodes = len(set(ex.get("node_id") for ex in node_executions if ex.get("phase") == "started"))
        completed_nodes = len([ex for ex in node_executions if ex.get("phase") == "completed"])
        
        return {
            "completion_rate": completed_nodes / total_nodes if total_nodes > 0 else 0,
            "agent_efficiency": len(agent_thoughts) / total_nodes if total_nodes > 0 else 0,
            "workflow_complexity": total_nodes,
            "coordination_density": len([t for t in agent_thoughts if "coordination" in t.get("thought_type", "")]) / len(agent_thoughts) if agent_thoughts else 0
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
                "analysis_depth": {
                    "type": "string",
                    "enum": ["basic", "detailed", "comprehensive"],
                    "description": "Depth of analysis to perform",
                    "default": "detailed"
                },
                "focus_areas": {
                    "type": "array",
                    "items": {"type": "string", "enum": ["performance", "agents", "resources"]},
                    "description": "Specific areas to analyze",
                    "default": ["performance", "agents", "resources"]
                }
            },
            "required": ["execution_trace", "workflow_result"]
        } 