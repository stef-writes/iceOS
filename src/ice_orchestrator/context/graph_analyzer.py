"""Graph analysis utilities for iceOS dependency structures.

This module provides graph intelligence that leverages the powerful NetworkX
infrastructure already in place but underutilized across iceOS layers.
"""

from typing import Any, Dict, List, Optional, Set, Tuple
import networkx as nx
from dataclasses import dataclass

from ice_core.models.node_models import NodeConfig


@dataclass
class GraphMetrics:
    """Comprehensive graph analysis metrics."""
    
    total_nodes: int
    total_edges: int
    max_depth: int
    parallel_opportunities: int
    critical_path_length: int
    complexity_score: float
    bottleneck_nodes: List[str]
    leaf_nodes: List[str]
    root_nodes: List[str]


@dataclass  
class DependencyImpact:
    """Impact analysis for node changes."""
    
    node_id: str
    direct_dependents: List[str]
    transitive_dependents: List[str]
    affected_levels: List[int]
    estimated_impact_score: float


class GraphAnalyzer:
    """Advanced graph analysis for workflow dependency structures.
    
    Provides insights that can drive:
    - Canvas layout optimization
    - Performance bottleneck identification  
    - Impact analysis for changes
    - Intelligent suggestions for workflow composition
    """
    
    def __init__(self, graph: nx.DiGraph):
        self.graph = graph
        
    @classmethod
    def from_nodes(cls, nodes: List[NodeConfig]) -> "GraphAnalyzer":
        """Create analyzer from node configurations."""
        graph = nx.DiGraph()
        
        for node in nodes:
            graph.add_node(node.id, node_type=node.type, config=node)
            
            for dep in getattr(node, 'dependencies', []):
                graph.add_edge(dep, node.id)
                
        return cls(graph)
        
    def get_metrics(self) -> GraphMetrics:
        """Get comprehensive graph metrics."""
        
        # Basic structure
        total_nodes = self.graph.number_of_nodes()
        total_edges = self.graph.number_of_edges()
        
        # Depth analysis
        try:
            max_depth = max(nx.shortest_path_length(self.graph, source).values() 
                          for source in self.get_root_nodes()) or 0
        except ValueError:
            max_depth = 0
            
        # Parallelism opportunities
        levels = self._compute_levels()
        parallel_opportunities = sum(len(nodes) for nodes in levels.values() if len(nodes) > 1)
        
        # Critical path
        critical_path_length = self._compute_critical_path_length()
        
        # Complexity (based on branching factor and dependencies)
        complexity_score = self._compute_complexity_score()
        
        # Bottlenecks (nodes with high fan-out)
        bottleneck_nodes = self._identify_bottlenecks()
        
        return GraphMetrics(
            total_nodes=total_nodes,
            total_edges=total_edges,
            max_depth=max_depth,
            parallel_opportunities=parallel_opportunities,
            critical_path_length=critical_path_length,
            complexity_score=complexity_score,
            bottleneck_nodes=bottleneck_nodes,
            leaf_nodes=self.get_leaf_nodes(),
            root_nodes=self.get_root_nodes()
        )
        
    def analyze_dependency_impact(self, node_id: str) -> DependencyImpact:
        """Analyze the impact of changes to a specific node."""
        
        if node_id not in self.graph:
            raise ValueError(f"Node {node_id} not found in graph")
            
        # Direct dependents
        direct_dependents = list(self.graph.successors(node_id))
        
        # Transitive dependents (all downstream nodes)
        transitive_dependents = list(nx.descendants(self.graph, node_id))
        
        # Affected levels
        levels = self._compute_levels()
        affected_levels = []
        for level, nodes in levels.items():
            if any(n in transitive_dependents or n == node_id for n in nodes):
                affected_levels.append(level)
                
        # Impact score (based on downstream node count and complexity)
        impact_score = self._compute_impact_score(node_id, transitive_dependents)
        
        return DependencyImpact(
            node_id=node_id,
            direct_dependents=direct_dependents,
            transitive_dependents=transitive_dependents,
            affected_levels=affected_levels,
            estimated_impact_score=impact_score
        )
        
    def suggest_optimizations(self) -> List[Dict[str, Any]]:
        """Suggest workflow optimizations based on graph analysis."""
        
        suggestions = []
        metrics = self.get_metrics()
        
        # Parallelization opportunities
        if metrics.parallel_opportunities < metrics.total_nodes * 0.3:
            suggestions.append({
                "type": "parallelization",
                "priority": "high",
                "description": "Consider breaking up sequential chains to enable more parallel execution",
                "affected_nodes": self._find_sequential_chains()
            })
            
        # Bottleneck identification
        if metrics.bottleneck_nodes:
            suggestions.append({
                "type": "bottleneck",
                "priority": "medium", 
                "description": f"Nodes with high fan-out may cause execution delays",
                "affected_nodes": metrics.bottleneck_nodes
            })
            
        # Complexity reduction
        if metrics.complexity_score > 10.0:
            suggestions.append({
                "type": "complexity",
                "priority": "low",
                "description": "Consider breaking down complex workflows into sub-workflows",
                "complexity_score": metrics.complexity_score
            })
            
        return suggestions
        
    def get_spatial_layout_hints(self) -> Dict[str, Dict[str, Any]]:
        """Generate spatial layout hints for canvas visualization."""
        
        layout_hints = {}
        levels = self._compute_levels()
        
        # Use force-directed layout as base
        pos = nx.spring_layout(self.graph, k=3, iterations=50)
        
        # Adjust for level-based layout
        for level, nodes in levels.items():
            for i, node_id in enumerate(nodes):
                # Get node configuration for styling
                node_data = self.graph.nodes.get(node_id, {})
                node_config = node_data.get('config')
                
                layout_hints[node_id] = {
                    "position": {
                        "x": pos[node_id][0] * 500,  # Scale for screen coordinates
                        "y": level * 150  # Level-based Y positioning
                    },
                    "level": level,
                    "connections": {
                        "inputs": list(self.graph.predecessors(node_id)),
                        "outputs": list(self.graph.successors(node_id))
                    },
                    "graph_metrics": {
                        "in_degree": self.graph.in_degree(node_id),
                        "out_degree": self.graph.out_degree(node_id),
                        "betweenness": nx.betweenness_centrality(self.graph).get(node_id, 0),
                        "is_bottleneck": node_id in self._identify_bottlenecks(),
                        "is_critical_path": self._is_on_critical_path(node_id)
                    }
                }
                
                # Add node-specific styling based on graph position
                if node_config:
                    layout_hints[node_id]["style"] = self._get_graph_aware_style(node_config, layout_hints[node_id])
                    
        return layout_hints
        
    def find_similar_patterns(self, pattern_nodes: List[str]) -> List[List[str]]:
        """Find similar subgraph patterns in the workflow."""
        
        if len(pattern_nodes) < 2:
            return []
            
        # Extract pattern subgraph
        pattern_subgraph = self.graph.subgraph(pattern_nodes)
        
        # Find isomorphic subgraphs
        similar_patterns = []
        
        for nodes in nx.enumerate_all_cliques(self.graph):
            if len(nodes) == len(pattern_nodes):
                candidate_subgraph = self.graph.subgraph(nodes)
                
                # Check for isomorphism
                if nx.is_isomorphic(pattern_subgraph, candidate_subgraph):
                    similar_patterns.append(list(nodes))
                    
        return similar_patterns
        
    def get_execution_path_analysis(self) -> Dict[str, Any]:
        """Analyze possible execution paths through the workflow."""
        
        root_nodes = self.get_root_nodes()
        leaf_nodes = self.get_leaf_nodes()
        
        # Find all simple paths from roots to leaves
        all_paths = []
        for root in root_nodes:
            for leaf in leaf_nodes:
                try:
                    paths = list(nx.all_simple_paths(self.graph, root, leaf))
                    all_paths.extend(paths)
                except nx.NetworkXNoPath:
                    continue
                    
        # Analyze path characteristics
        path_lengths = [len(path) for path in all_paths]
        
        return {
            "total_paths": len(all_paths),
            "average_path_length": sum(path_lengths) / len(path_lengths) if path_lengths else 0,
            "longest_path": max(path_lengths) if path_lengths else 0,
            "shortest_path": min(path_lengths) if path_lengths else 0,
            "critical_paths": self._identify_critical_paths(all_paths),
            "branch_points": self._identify_branch_points(),
            "merge_points": self._identify_merge_points()
        }
        
    # Helper methods
    
    def get_root_nodes(self) -> List[str]:
        """Get nodes with no dependencies."""
        return [n for n in self.graph.nodes() if self.graph.in_degree(n) == 0]
        
    def get_leaf_nodes(self) -> List[str]:
        """Get nodes with no dependents."""
        return [n for n in self.graph.nodes() if self.graph.out_degree(n) == 0]
        
    def _compute_levels(self) -> Dict[int, List[str]]:
        """Compute topological levels."""
        levels: Dict[int, List[str]] = {}
        
        try:
            for node in nx.topological_sort(self.graph):
                # Level is the longest path from any root node
                level = 0
                for pred in self.graph.predecessors(node):
                    pred_level = next(l for l, nodes in levels.items() if pred in nodes)
                    level = max(level, pred_level + 1)
                    
                if level not in levels:
                    levels[level] = []
                levels[level].append(node)
                
        except nx.NetworkXError:
            # Fallback for graphs with cycles
            levels = {0: list(self.graph.nodes())}
            
        return levels
        
    def _compute_critical_path_length(self) -> int:
        """Compute the length of the critical path."""
        try:
            return max(nx.dag_longest_path_length(self.graph, weight=None), 0)
        except (nx.NetworkXError, ValueError):
            return 0
            
    def _compute_complexity_score(self) -> float:
        """Compute workflow complexity score."""
        n_nodes = self.graph.number_of_nodes()
        n_edges = self.graph.number_of_edges()
        
        if n_nodes == 0:
            return 0.0
            
        # Factors: density, branching, depth
        density = n_edges / (n_nodes * (n_nodes - 1)) if n_nodes > 1 else 0
        avg_degree = sum(dict(self.graph.degree()).values()) / n_nodes
        depth = self._compute_critical_path_length()
        
        return (density * 5) + (avg_degree * 2) + (depth * 0.5)
        
    def _identify_bottlenecks(self) -> List[str]:
        """Identify nodes that could be bottlenecks."""
        bottlenecks = []
        
        for node in self.graph.nodes():
            out_degree = self.graph.out_degree(node)
            if out_degree > 3:  # High fan-out threshold
                bottlenecks.append(node)
                
        return bottlenecks
        
    def _compute_impact_score(self, node_id: str, dependents: List[str]) -> float:
        """Compute impact score for a node change."""
        base_score = len(dependents)
        
        # Weight by node complexity
        complexity_weight = 1.0
        for dep in dependents:
            dep_out_degree = self.graph.out_degree(dep)
            complexity_weight += dep_out_degree * 0.1
            
        return base_score * complexity_weight
        
    def _find_sequential_chains(self) -> List[List[str]]:
        """Find long sequential chains that could be parallelized."""
        chains = []
        
        for node in self.graph.nodes():
            if (self.graph.in_degree(node) == 1 and 
                self.graph.out_degree(node) == 1):
                # Part of a potential chain
                continue
                
        # TODO: Implement chain detection algorithm
        return chains
        
    def _is_on_critical_path(self, node_id: str) -> bool:
        """Check if node is on the critical path."""
        try:
            critical_path = nx.dag_longest_path(self.graph)
            return node_id in critical_path
        except nx.NetworkXError:
            return False
            
    def _get_graph_aware_style(self, node_config: NodeConfig, layout_info: Dict[str, Any]) -> Dict[str, Any]:
        """Get styling based on graph position and properties."""
        
        style = {
            "opacity": 1.0,
            "border_width": 1,
            "highlight": False
        }
        
        # Highlight critical path nodes
        if layout_info["graph_metrics"]["is_critical_path"]:
            style["border_width"] = 3
            style["highlight"] = True
            
        # Adjust opacity based on centrality
        centrality = layout_info["graph_metrics"]["betweenness"]
        style["opacity"] = max(0.5, min(1.0, 0.5 + centrality))
        
        # Highlight bottlenecks
        if layout_info["graph_metrics"]["is_bottleneck"]:
            style["border_color"] = "#ff4444"
            
        return style
        
    def _identify_critical_paths(self, all_paths: List[List[str]]) -> List[List[str]]:
        """Identify critical execution paths."""
        if not all_paths:
            return []
            
        max_length = max(len(path) for path in all_paths)
        return [path for path in all_paths if len(path) == max_length]
        
    def _identify_branch_points(self) -> List[str]:
        """Identify nodes where execution branches."""
        return [n for n in self.graph.nodes() if self.graph.out_degree(n) > 1]
        
    def _identify_merge_points(self) -> List[str]:
        """Identify nodes where execution paths merge."""
        return [n for n in self.graph.nodes() if self.graph.in_degree(n) > 1] 