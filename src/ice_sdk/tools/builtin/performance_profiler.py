"""
⚡ Performance Profiler Tool
===========================

Deep performance analysis and profiling for workflow executions.
Provides detailed timing analysis, resource usage patterns, and optimization opportunities.

Key Features:
- Detailed timing analysis
- Memory usage profiling
- CPU utilization tracking
- Bottleneck identification
- Performance trending
- Optimization recommendations
"""

from datetime import datetime
from typing import Any, Dict, List
from ice_sdk.tools.base import ToolBase
import statistics


class PerformanceProfilerTool(ToolBase):
    """Advanced performance profiling and analysis for workflow executions."""
    
    name: str = "performance_profiler"
    description: str = "Deep performance analysis and optimization recommendations"
    
    async def _execute_impl(self, **kwargs) -> Dict[str, Any]:
        """Perform comprehensive performance profiling.
        
        Args:
            execution_trace: Workflow execution trace data
            workflow_result: Final workflow execution result
            profiling_depth: Depth of analysis (basic, detailed, comprehensive)
            compare_baseline: Optional baseline data for comparison
            focus_metrics: Specific metrics to analyze
            
        Returns:
            Comprehensive performance profile with detailed analysis
        """
        try:
            execution_trace = kwargs.get("execution_trace", {})
            workflow_result = kwargs.get("workflow_result", {})
            profiling_depth = kwargs.get("profiling_depth", "detailed")
            compare_baseline = kwargs.get("compare_baseline")
            focus_metrics = kwargs.get("focus_metrics", ["timing", "resources", "efficiency"])
            
            profile = {
                "timestamp": datetime.now().isoformat(),
                "profiling_depth": profiling_depth,
                "focus_metrics": focus_metrics,
                "performance_overview": {},
                "detailed_analysis": {},
                "optimization_opportunities": [],
                "performance_score": 0.0
            }
            
            # Core performance analysis
            if "timing" in focus_metrics:
                profile["detailed_analysis"]["timing"] = self._analyze_timing_performance(
                    execution_trace, profiling_depth
                )
            
            if "resources" in focus_metrics:
                profile["detailed_analysis"]["resources"] = self._analyze_resource_performance(
                    execution_trace, profiling_depth
                )
            
            if "efficiency" in focus_metrics:
                profile["detailed_analysis"]["efficiency"] = self._analyze_efficiency_metrics(
                    execution_trace, workflow_result, profiling_depth
                )
            
            # Generate performance overview
            profile["performance_overview"] = self._generate_performance_overview(
                profile["detailed_analysis"]
            )
            
            # Calculate overall performance score
            profile["performance_score"] = self._calculate_performance_score(
                profile["detailed_analysis"]
            )
            
            # Generate optimization opportunities
            profile["optimization_opportunities"] = self._identify_optimization_opportunities(
                profile["detailed_analysis"], profiling_depth
            )
            
            # Baseline comparison if provided
            if compare_baseline:
                profile["baseline_comparison"] = self._compare_with_baseline(
                    profile, compare_baseline
                )
            
            return {
                "status": "success",
                "profile": profile,
                "insights_count": len(profile["optimization_opportunities"]),
                "performance_grade": self._assign_performance_grade(profile["performance_score"])
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def _analyze_timing_performance(self, trace: Dict, depth: str) -> Dict[str, Any]:
        """Analyze timing performance patterns."""
        node_executions = trace.get("node_executions", [])
        
        # Extract execution times by node and type
        timing_data = {}
        node_times = []
        type_times = {}
        
        for execution in node_executions:
            if execution.get("phase") == "completed":
                node_id = execution.get("node_id", "unknown")
                details = execution.get("details", {})
                exec_time = details.get("execution_time", 0)
                node_type = details.get("node_type", "unknown")
                
                timing_data[node_id] = {
                    "execution_time": exec_time,
                    "node_type": node_type
                }
                node_times.append(exec_time)
                
                if node_type not in type_times:
                    type_times[node_type] = []
                type_times[node_type].append(exec_time)
        
        # Calculate timing statistics
        timing_stats = self._calculate_timing_statistics(node_times)
        type_stats = {node_type: self._calculate_timing_statistics(times) 
                     for node_type, times in type_times.items()}
        
        analysis = {
            "total_execution_time": sum(node_times),
            "node_count": len(timing_data),
            "timing_statistics": timing_stats,
            "by_node_type": type_stats,
            "slowest_nodes": self._identify_slowest_nodes(timing_data, 5),
            "timing_distribution": self._analyze_timing_distribution(node_times)
        }
        
        if depth in ["detailed", "comprehensive"]:
            analysis["timing_patterns"] = self._analyze_timing_patterns(timing_data)
            analysis["critical_path"] = self._calculate_critical_path(timing_data)
            analysis["parallel_potential"] = self._calculate_parallel_potential(timing_data)
        
        if depth == "comprehensive":
            analysis["timing_trends"] = self._analyze_timing_trends(trace)
            analysis["performance_regression"] = self._detect_performance_regression(timing_data)
        
        return analysis
    
    def _analyze_resource_performance(self, trace: Dict, depth: str) -> Dict[str, Any]:
        """Analyze resource usage performance."""
        api_calls = trace.get("api_calls", [])
        memory_operations = trace.get("memory_operations", [])
        
        # API resource analysis
        api_resources = self._analyze_api_resources(api_calls)
        
        # Memory usage analysis
        memory_resources = self._analyze_memory_resources(memory_operations)
        
        analysis = {
            "api_resources": api_resources,
            "memory_resources": memory_resources,
            "resource_efficiency": self._calculate_resource_efficiency(api_calls, memory_operations),
            "resource_bottlenecks": self._identify_resource_bottlenecks(api_calls)
        }
        
        if depth in ["detailed", "comprehensive"]:
            analysis["resource_patterns"] = self._analyze_resource_patterns(api_calls, memory_operations)
            analysis["resource_optimization"] = self._calculate_resource_optimization_potential(api_calls)
        
        return analysis
    
    def _analyze_efficiency_metrics(self, trace: Dict, result: Dict, depth: str) -> Dict[str, Any]:
        """Analyze workflow efficiency metrics."""
        node_executions = trace.get("node_executions", [])
        agent_thoughts = trace.get("agent_thoughts", [])
        api_calls = trace.get("api_calls", [])
        
        # Calculate efficiency ratios
        total_nodes = len(set(ex.get("node_id") for ex in node_executions if ex.get("phase") == "started"))
        completed_nodes = len([ex for ex in node_executions if ex.get("phase") == "completed"])
        
        efficiency_metrics = {
            "completion_efficiency": completed_nodes / total_nodes if total_nodes > 0 else 0,
            "thought_to_api_ratio": len(agent_thoughts) / len(api_calls) if api_calls else 0,
            "coordination_overhead": self._calculate_coordination_overhead(agent_thoughts),
            "resource_utilization": self._calculate_resource_utilization(api_calls, agent_thoughts)
        }
        
        # Business efficiency
        business_metrics = self._calculate_business_efficiency(result)
        
        analysis = {
            "efficiency_metrics": efficiency_metrics,
            "business_metrics": business_metrics,
            "efficiency_score": self._calculate_overall_efficiency_score(efficiency_metrics, business_metrics),
            "efficiency_bottlenecks": self._identify_efficiency_bottlenecks(efficiency_metrics)
        }
        
        if depth in ["detailed", "comprehensive"]:
            analysis["efficiency_trends"] = self._analyze_efficiency_trends(trace)
            analysis["optimization_potential"] = self._calculate_efficiency_optimization_potential(efficiency_metrics)
        
        return analysis
    
    def _calculate_timing_statistics(self, times: List[float]) -> Dict[str, float]:
        """Calculate comprehensive timing statistics."""
        if not times:
            return {"mean": 0, "median": 0, "min": 0, "max": 0, "std_dev": 0}
        
        return {
            "mean": statistics.mean(times),
            "median": statistics.median(times),
            "min": min(times),
            "max": max(times),
            "std_dev": statistics.stdev(times) if len(times) > 1 else 0,
            "p95": self._percentile(times, 95),
            "p99": self._percentile(times, 99)
        }
    
    def _percentile(self, data: List[float], percentile: int) -> float:
        """Calculate percentile value."""
        if not data:
            return 0
        sorted_data = sorted(data)
        index = (percentile / 100.0) * (len(sorted_data) - 1)
        if index.is_integer():
            return sorted_data[int(index)]
        else:
            lower_index = int(index)
            upper_index = lower_index + 1
            if upper_index >= len(sorted_data):
                return sorted_data[lower_index]
            weight = index - lower_index
            return sorted_data[lower_index] * (1 - weight) + sorted_data[upper_index] * weight
    
    def _identify_slowest_nodes(self, timing_data: Dict, count: int) -> List[Dict[str, Any]]:
        """Identify the slowest performing nodes."""
        sorted_nodes = sorted(
            timing_data.items(),
            key=lambda x: x[1]["execution_time"],
            reverse=True
        )
        
        return [
            {
                "node_id": node_id,
                "execution_time": data["execution_time"],
                "node_type": data["node_type"]
            }
            for node_id, data in sorted_nodes[:count]
        ]
    
    def _analyze_timing_distribution(self, times: List[float]) -> Dict[str, Any]:
        """Analyze the distribution of execution times."""
        if not times:
            return {}
        
        # Categorize times
        fast_threshold = 1.0  # < 1 second
        moderate_threshold = 5.0  # < 5 seconds
        
        fast = [t for t in times if t < fast_threshold]
        moderate = [t for t in times if fast_threshold <= t < moderate_threshold]
        slow = [t for t in times if t >= moderate_threshold]
        
        return {
            "fast_nodes": {"count": len(fast), "percentage": len(fast) / len(times) * 100},
            "moderate_nodes": {"count": len(moderate), "percentage": len(moderate) / len(times) * 100},
            "slow_nodes": {"count": len(slow), "percentage": len(slow) / len(times) * 100},
            "distribution_balance": "well_balanced" if len(fast) > len(slow) else "needs_optimization"
        }
    
    def _analyze_timing_patterns(self, timing_data: Dict) -> Dict[str, Any]:
        """Analyze patterns in timing data."""
        # Group by node type
        type_patterns = {}
        for node_id, data in timing_data.items():
            node_type = data["node_type"]
            if node_type not in type_patterns:
                type_patterns[node_type] = []
            type_patterns[node_type].append(data["execution_time"])
        
        # Analyze consistency within types
        consistency_analysis = {}
        for node_type, times in type_patterns.items():
            if len(times) > 1:
                cv = statistics.stdev(times) / statistics.mean(times) if statistics.mean(times) > 0 else 0
                consistency_analysis[node_type] = {
                    "coefficient_variation": cv,
                    "consistency": "high" if cv < 0.3 else "moderate" if cv < 0.7 else "low"
                }
        
        return {
            "type_patterns": type_patterns,
            "consistency_analysis": consistency_analysis,
            "pattern_insights": self._generate_pattern_insights(consistency_analysis)
        }
    
    def _calculate_critical_path(self, timing_data: Dict) -> List[str]:
        """Calculate the critical path through the workflow."""
        # Simplified critical path: nodes with highest execution times
        # Real implementation would consider dependencies
        sorted_nodes = sorted(
            timing_data.items(),
            key=lambda x: x[1]["execution_time"],
            reverse=True
        )
        
        # Return top 30% of nodes by time as critical path
        critical_count = max(1, len(sorted_nodes) // 3)
        return [node_id for node_id, _ in sorted_nodes[:critical_count]]
    
    def _calculate_parallel_potential(self, timing_data: Dict) -> Dict[str, Any]:
        """Calculate potential for parallel execution."""
        # Identify independent operations (tools, API calls)
        parallelizable_nodes = []
        sequential_nodes = []
        
        for node_id, data in timing_data.items():
            node_type = data["node_type"]
            if node_type in ["tool", "api_call"]:
                parallelizable_nodes.append(data["execution_time"])
            else:
                sequential_nodes.append(data["execution_time"])
        
        current_time = sum(timing_data[node]["execution_time"] for node in timing_data)
        potential_parallel_time = max(parallelizable_nodes) if parallelizable_nodes else 0
        sequential_time = sum(sequential_nodes)
        optimized_time = potential_parallel_time + sequential_time
        
        return {
            "parallelizable_nodes": len(parallelizable_nodes),
            "current_execution_time": current_time,
            "optimized_execution_time": optimized_time,
            "potential_savings": current_time - optimized_time,
            "savings_percentage": ((current_time - optimized_time) / current_time * 100) if current_time > 0 else 0
        }
    
    def _analyze_api_resources(self, api_calls: List[Dict]) -> Dict[str, Any]:
        """Analyze API resource usage."""
        if not api_calls:
            return {"total_calls": 0, "total_duration": 0}
        
        total_duration = sum(call.get("duration", 0) for call in api_calls)
        service_breakdown = {}
        
        for call in api_calls:
            service = call.get("service", "unknown")
            duration = call.get("duration", 0)
            
            if service not in service_breakdown:
                service_breakdown[service] = {"calls": 0, "duration": 0}
            
            service_breakdown[service]["calls"] += 1
            service_breakdown[service]["duration"] += duration
        
        return {
            "total_calls": len(api_calls),
            "total_duration": total_duration,
            "average_call_duration": total_duration / len(api_calls),
            "service_breakdown": service_breakdown,
            "most_expensive_service": max(service_breakdown.keys(), 
                                        key=lambda x: service_breakdown[x]["duration"]) if service_breakdown else None
        }
    
    def _analyze_memory_resources(self, memory_ops: List[Dict]) -> Dict[str, Any]:
        """Analyze memory operation performance."""
        if not memory_ops:
            return {"total_operations": 0}
        
        operation_types = {}
        for op in memory_ops:
            op_type = op.get("operation", "unknown")
            if op_type not in operation_types:
                operation_types[op_type] = 0
            operation_types[op_type] += 1
        
        return {
            "total_operations": len(memory_ops),
            "operation_breakdown": operation_types,
            "most_frequent_operation": max(operation_types.keys(), 
                                         key=lambda x: operation_types[x]) if operation_types else None
        }
    
    def _calculate_resource_efficiency(self, api_calls: List[Dict], memory_ops: List[Dict]) -> float:
        """Calculate overall resource efficiency score."""
        if not api_calls and not memory_ops:
            return 1.0
        
        # Simple efficiency metric
        total_operations = len(api_calls) + len(memory_ops)
        total_time = sum(call.get("duration", 0) for call in api_calls)
        
        if total_time == 0:
            return 1.0
        
        # Lower time per operation = higher efficiency
        time_per_operation = total_time / total_operations
        
        # Scale to 0-1 (assuming 1 second per operation is baseline)
        efficiency = max(0, min(1, 1 / (time_per_operation + 1)))
        return efficiency
    
    def _identify_resource_bottlenecks(self, api_calls: List[Dict]) -> List[Dict[str, Any]]:
        """Identify resource usage bottlenecks."""
        bottlenecks = []
        
        for call in api_calls:
            duration = call.get("duration", 0)
            if duration > 2.0:  # Bottleneck threshold
                bottlenecks.append({
                    "service": call.get("service", "unknown"),
                    "endpoint": call.get("endpoint", "unknown"),
                    "duration": duration,
                    "severity": "high" if duration > 5.0 else "moderate"
                })
        
        return sorted(bottlenecks, key=lambda x: x["duration"], reverse=True)
    
    def _calculate_coordination_overhead(self, agent_thoughts: List[Dict]) -> float:
        """Calculate coordination overhead ratio."""
        if not agent_thoughts:
            return 0.0
        
        coordination_thoughts = len([
            t for t in agent_thoughts 
            if "coordination" in t.get("thought_type", "").lower()
        ])
        
        return coordination_thoughts / len(agent_thoughts)
    
    def _calculate_resource_utilization(self, api_calls: List[Dict], agent_thoughts: List[Dict]) -> float:
        """Calculate resource utilization efficiency."""
        if not api_calls or not agent_thoughts:
            return 0.0
        
        # Ratio of productive API calls to total agent thoughts
        return len(api_calls) / len(agent_thoughts)
    
    def _calculate_business_efficiency(self, result: Dict) -> Dict[str, Any]:
        """Calculate business-level efficiency metrics."""
        results_data = result.get("results", {})
        
        # Extract confidence scores
        confidence_scores = []
        for workflow_result in results_data.values():
            if isinstance(workflow_result, dict):
                confidence = workflow_result.get("confidence_score", 0)
                if confidence > 0:
                    confidence_scores.append(confidence)
        
        avg_confidence = statistics.mean(confidence_scores) if confidence_scores else 0
        
        return {
            "average_confidence": avg_confidence,
            "workflows_successful": len([c for c in confidence_scores if c > 0.7]),
            "business_outcome_quality": "high" if avg_confidence > 0.8 else "moderate" if avg_confidence > 0.6 else "low"
        }
    
    def _calculate_overall_efficiency_score(self, efficiency_metrics: Dict, business_metrics: Dict) -> float:
        """Calculate overall efficiency score."""
        # Weighted combination of different efficiency metrics
        completion_weight = 0.3
        coordination_weight = 0.2
        resource_weight = 0.2
        business_weight = 0.3
        
        completion_score = efficiency_metrics.get("completion_efficiency", 0)
        coordination_score = 1 - efficiency_metrics.get("coordination_overhead", 0)  # Lower overhead = higher score
        resource_score = efficiency_metrics.get("resource_utilization", 0)
        business_score = business_metrics.get("average_confidence", 0)
        
        overall_score = (
            completion_score * completion_weight +
            coordination_score * coordination_weight +
            resource_score * resource_weight +
            business_score * business_weight
        )
        
        return min(1.0, max(0.0, overall_score))
    
    def _identify_efficiency_bottlenecks(self, efficiency_metrics: Dict) -> List[Dict[str, Any]]:
        """Identify efficiency bottlenecks."""
        bottlenecks = []
        
        if efficiency_metrics.get("completion_efficiency", 1.0) < 0.8:
            bottlenecks.append({
                "type": "completion",
                "severity": "high",
                "description": "Low completion rate affecting overall efficiency"
            })
        
        if efficiency_metrics.get("coordination_overhead", 0) > 0.3:
            bottlenecks.append({
                "type": "coordination",
                "severity": "moderate",
                "description": "High coordination overhead reducing efficiency"
            })
        
        if efficiency_metrics.get("resource_utilization", 0) < 0.5:
            bottlenecks.append({
                "type": "resource_utilization",
                "severity": "moderate",
                "description": "Low resource utilization indicating inefficient operations"
            })
        
        return bottlenecks
    
    def _generate_performance_overview(self, detailed_analysis: Dict) -> Dict[str, Any]:
        """Generate high-level performance overview."""
        overview = {}
        
        if "timing" in detailed_analysis:
            timing = detailed_analysis["timing"]
            overview["timing"] = {
                "total_time": timing.get("total_execution_time", 0),
                "average_node_time": timing.get("timing_statistics", {}).get("mean", 0),
                "slowest_node_time": timing.get("timing_statistics", {}).get("max", 0)
            }
        
        if "resources" in detailed_analysis:
            resources = detailed_analysis["resources"]
            overview["resources"] = {
                "api_calls": resources.get("api_resources", {}).get("total_calls", 0),
                "resource_efficiency": resources.get("resource_efficiency", 0)
            }
        
        if "efficiency" in detailed_analysis:
            efficiency = detailed_analysis["efficiency"]
            overview["efficiency"] = {
                "overall_score": efficiency.get("efficiency_score", 0),
                "completion_rate": efficiency.get("efficiency_metrics", {}).get("completion_efficiency", 0)
            }
        
        return overview
    
    def _calculate_performance_score(self, detailed_analysis: Dict) -> float:
        """Calculate overall performance score (0-100)."""
        scores = []
        
        # Timing score (based on distribution)
        if "timing" in detailed_analysis:
            timing_dist = detailed_analysis["timing"].get("timing_distribution", {})
            fast_pct = timing_dist.get("fast_nodes", {}).get("percentage", 0)
            timing_score = fast_pct / 100.0  # Higher percentage of fast nodes = better score
            scores.append(timing_score)
        
        # Resource score
        if "resources" in detailed_analysis:
            resource_efficiency = detailed_analysis["resources"].get("resource_efficiency", 0)
            scores.append(resource_efficiency)
        
        # Efficiency score
        if "efficiency" in detailed_analysis:
            efficiency_score = detailed_analysis["efficiency"].get("efficiency_score", 0)
            scores.append(efficiency_score)
        
        # Average all component scores
        if scores:
            return statistics.mean(scores) * 100  # Convert to 0-100 scale
        else:
            return 0.0
    
    def _identify_optimization_opportunities(self, detailed_analysis: Dict, depth: str) -> List[Dict[str, Any]]:
        """Identify optimization opportunities."""
        opportunities = []
        
        # Timing optimizations
        if "timing" in detailed_analysis:
            timing = detailed_analysis["timing"]
            
            # Slow nodes optimization
            slowest_nodes = timing.get("slowest_nodes", [])
            if slowest_nodes:
                opportunities.append({
                    "category": "timing",
                    "priority": "high",
                    "title": "Optimize Slowest Nodes",
                    "description": f"Focus on optimizing {len(slowest_nodes)} slowest performing nodes",
                    "potential_impact": f"Up to {sum(node['execution_time'] for node in slowest_nodes[:3]) * 0.3:.1f}s savings",
                    "nodes": [node["node_id"] for node in slowest_nodes[:3]]
                })
            
            # Parallel execution optimization
            parallel_potential = timing.get("parallel_potential", {})
            if parallel_potential.get("savings_percentage", 0) > 20:
                opportunities.append({
                    "category": "architecture",
                    "priority": "medium",
                    "title": "Implement Parallel Execution",
                    "description": f"Parallelize {parallel_potential.get('parallelizable_nodes', 0)} independent nodes",
                    "potential_impact": f"{parallel_potential.get('savings_percentage', 0):.1f}% time reduction"
                })
        
        # Resource optimizations
        if "resources" in detailed_analysis:
            resources = detailed_analysis["resources"]
            
            # API bottlenecks
            bottlenecks = resources.get("resource_bottlenecks", [])
            high_severity_bottlenecks = [b for b in bottlenecks if b.get("severity") == "high"]
            if high_severity_bottlenecks:
                opportunities.append({
                    "category": "resources",
                    "priority": "high",
                    "title": "Resolve Resource Bottlenecks",
                    "description": f"Address {len(high_severity_bottlenecks)} high-severity resource bottlenecks",
                    "services_affected": list(set(b["service"] for b in high_severity_bottlenecks))
                })
        
        # Efficiency optimizations
        if "efficiency" in detailed_analysis:
            efficiency = detailed_analysis["efficiency"]
            
            # Coordination overhead
            efficiency_bottlenecks = efficiency.get("efficiency_bottlenecks", [])
            for bottleneck in efficiency_bottlenecks:
                opportunities.append({
                    "category": "efficiency",
                    "priority": bottleneck.get("severity", "low"),
                    "title": f"Address {bottleneck['type'].replace('_', ' ').title()} Issues",
                    "description": bottleneck.get("description", "")
                })
        
        return sorted(opportunities, key=lambda x: {"high": 3, "medium": 2, "low": 1}[x["priority"]], reverse=True)
    
    def _assign_performance_grade(self, score: float) -> str:
        """Assign performance grade based on score."""
        if score >= 90:
            return "A+ (Excellent)"
        elif score >= 80:
            return "A (Very Good)"
        elif score >= 70:
            return "B (Good)"
        elif score >= 60:
            return "C (Fair)"
        elif score >= 50:
            return "D (Needs Improvement)"
        else:
            return "F (Poor)"
    
    def _compare_with_baseline(self, current_profile: Dict, baseline: Dict) -> Dict[str, Any]:
        """Compare current performance with baseline."""
        # Simplified baseline comparison
        current_score = current_profile.get("performance_score", 0)
        baseline_score = baseline.get("performance_score", 0)
        
        improvement = current_score - baseline_score
        
        return {
            "performance_change": improvement,
            "performance_trend": "improved" if improvement > 5 else "declined" if improvement < -5 else "stable",
            "comparison_summary": f"Performance {'improved' if improvement > 0 else 'declined'} by {abs(improvement):.1f} points"
        }
    
    def _analyze_timing_trends(self, trace: Dict) -> Dict[str, Any]:
        """Analyze timing trends over execution."""
        # Placeholder for trend analysis
        return {"trend_analysis": "Would require multiple execution samples for trending"}
    
    def _detect_performance_regression(self, timing_data: Dict) -> Dict[str, Any]:
        """Detect performance regression patterns."""
        # Placeholder for regression detection
        return {"regression_detected": False, "analysis": "No baseline for regression detection"}
    
    def _analyze_resource_patterns(self, api_calls: List[Dict], memory_ops: List[Dict]) -> Dict[str, Any]:
        """Analyze resource usage patterns."""
        # Simple pattern analysis
        if not api_calls:
            return {"pattern": "no_api_usage"}
        
        # Analyze call frequency patterns
        services = [call.get("service", "unknown") for call in api_calls]
        service_counts = {service: services.count(service) for service in set(services)}
        
        return {
            "api_call_pattern": "distributed" if len(service_counts) > 1 else "concentrated",
            "service_distribution": service_counts
        }
    
    def _calculate_resource_optimization_potential(self, api_calls: List[Dict]) -> Dict[str, Any]:
        """Calculate resource optimization potential."""
        if not api_calls:
            return {"optimization_potential": "none"}
        
        # Look for optimization opportunities
        duplicate_endpoints = {}
        for call in api_calls:
            endpoint = call.get("endpoint", "unknown")
            if endpoint not in duplicate_endpoints:
                duplicate_endpoints[endpoint] = 0
            duplicate_endpoints[endpoint] += 1
        
        cacheable_calls = sum(count - 1 for count in duplicate_endpoints.values() if count > 1)
        
        return {
            "cacheable_calls": cacheable_calls,
            "caching_potential": f"{cacheable_calls / len(api_calls) * 100:.1f}%" if api_calls else "0%",
            "optimization_recommendation": "implement_caching" if cacheable_calls > 0 else "no_immediate_optimization"
        }
    
    def _analyze_efficiency_trends(self, trace: Dict) -> Dict[str, Any]:
        """Analyze efficiency trends."""
        # Placeholder for efficiency trend analysis
        return {"trend_analysis": "Requires historical data for trend analysis"}
    
    def _calculate_efficiency_optimization_potential(self, efficiency_metrics: Dict) -> Dict[str, Any]:
        """Calculate efficiency optimization potential."""
        optimization_areas = []
        
        completion_eff = efficiency_metrics.get("completion_efficiency", 1.0)
        if completion_eff < 0.9:
            optimization_areas.append("completion_rate")
        
        coordination_overhead = efficiency_metrics.get("coordination_overhead", 0)
        if coordination_overhead > 0.2:
            optimization_areas.append("coordination_efficiency")
        
        resource_util = efficiency_metrics.get("resource_utilization", 1.0)
        if resource_util < 0.7:
            optimization_areas.append("resource_utilization")
        
        return {
            "optimization_areas": optimization_areas,
            "optimization_potential": "high" if len(optimization_areas) > 2 else "moderate" if optimization_areas else "low"
        }
    
    def _generate_pattern_insights(self, consistency_analysis: Dict) -> List[str]:
        """Generate insights from pattern analysis."""
        insights = []
        
        for node_type, analysis in consistency_analysis.items():
            consistency = analysis.get("consistency", "unknown")
            if consistency == "low":
                insights.append(f"{node_type} nodes show inconsistent performance - investigate variance")
            elif consistency == "high":
                insights.append(f"{node_type} nodes show consistent performance - good optimization baseline")
        
        return insights

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
                "profiling_depth": {
                    "type": "string",
                    "enum": ["basic", "detailed", "comprehensive"],
                    "description": "Depth of performance analysis",
                    "default": "detailed"
                },
                "compare_baseline": {
                    "type": "object",
                    "description": "Optional baseline performance data for comparison"
                },
                "focus_metrics": {
                    "type": "array",
                    "items": {"type": "string", "enum": ["timing", "resources", "efficiency"]},
                    "description": "Specific metrics to focus analysis on",
                    "default": ["timing", "resources", "efficiency"]
                }
            },
            "required": ["execution_trace", "workflow_result"]
        } 