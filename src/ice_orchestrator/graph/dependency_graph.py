from datetime import datetime
from typing import Any, Dict, List, Optional, Union

import networkx as nx

from ice_core.exceptions import CycleDetectionError as CircularDependencyError


class DependencyGraph:
    """
    Enhanced dependency graph with rich NetworkX utilization.

    Provides comprehensive graph analysis including:
    - Rich node attributes for execution tracking and optimization
    - Rich edge attributes for data flow analysis
    - Advanced NetworkX algorithms for critical path and bottleneck detection
    - Canvas layout hints and performance insights
    """

    def __init__(self, nodes: List[Any]):
        self.graph = nx.DiGraph()
        # Mapping of node_id -> topological level (depth) ------------------
        self.node_levels: Dict[str, int] = {}
        self._node_map = {node.id: node for node in nodes}
        self._build_graph(nodes)
        self._assign_levels(nodes)

    def _build_graph(self, nodes: List[Any]) -> None:
        """Enhanced graph construction with rich node and edge attributes."""
        node_ids = {node.id for node in nodes}

        for node in nodes:
            # 🚀 RICH NODE ATTRIBUTES: Store comprehensive node metadata
            node_attrs = {
                # Basic attributes
                "level": 0,
                "node_type": getattr(node, "type", "unknown"),
                "config": node,  # Full NodeConfig object
                # Execution state tracking
                "execution_state": "pending",  # pending/running/completed/failed
                "execution_count": 0,
                "last_execution_time": None,
                "avg_execution_time": 0.0,
                "success_rate": 1.0,
                "last_error": None,
                # Performance and optimization hints
                "estimated_cost": self._extract_estimated_cost(node),
                "cacheable": getattr(node, "use_cache", True),
                "parallel_safe": self._is_parallel_safe(node),
                "memory_intensive": self._is_memory_intensive(node),
                "io_bound": self._is_io_bound(node),
                # Canvas and UI hints
                "canvas_cluster": self._infer_canvas_cluster(node),
                "suggested_color": self._get_node_color(node),
                "complexity_score": self._calculate_complexity(node),
                # Metadata for analysis
                "created_at": datetime.utcnow(),
                "last_updated": None,
                "tags": self._extract_tags(node),
                # Graph analysis (computed later)
                "centrality_score": 0.0,
                "is_bottleneck": False,
                "is_critical_path": False,
                "parallel_group": None,
            }

            self.graph.add_node(node.id, **node_attrs)

            # 🚀 RICH EDGE ATTRIBUTES: Store data flow information
            for dep in getattr(node, "dependencies", []):
                if dep not in node_ids:
                    raise ValueError(f"Dependency {dep} not found for node {node.id}")

                edge_attrs = {
                    # Data flow characteristics
                    "dependency_type": "data_flow",
                    "data_schema": self._infer_data_schema(dep, node.id),
                    "estimated_data_size": self._estimate_data_size(dep, node.id),
                    "latency_sensitive": self._is_latency_sensitive(dep, node.id),
                    # Execution characteristics
                    "critical_path": False,  # Computed later
                    "parallel_safe": True,
                    "cached": False,
                    # Canvas visualization
                    "edge_weight": 1.0,
                    "edge_style": "default",
                    "edge_color": "#666666",
                    # Performance tracking
                    "avg_transfer_time": 0.0,
                    "total_data_transferred": 0,
                    "transfer_count": 0,
                    # Metadata
                    "created_at": datetime.utcnow(),
                    "last_used": None,
                }

                self.graph.add_edge(dep, node.id, **edge_attrs)

        # Check for cycles - now supports controlled cycles for recursive nodes
        self._check_cycles_with_recursive_support(nodes)

        # Enhanced analysis after graph construction
        self._compute_advanced_metrics()

        # Security & compliance validations
        self._validate_no_sensitive_data_flows(nodes)
        self._enforce_airgap_compliance(nodes)

    def _extract_estimated_cost(self, node: Any) -> float:
        """Extract estimated cost from node metadata."""
        if hasattr(node, "metadata") and node.metadata:
            return getattr(node.metadata, "estimated_cost", 0.0)
        return 0.0

    def _is_parallel_safe(self, node: Any) -> bool:
        """Determine if node can run in parallel with others."""
        node_type = getattr(node, "type", "")
        # Agents and stateful operations are generally not parallel safe
        if node_type in ["agent", "loop"]:
            return False
        # Tools and LLM nodes are generally parallel safe
        return True

    def _is_memory_intensive(self, node: Any) -> bool:
        """Determine if node is memory intensive."""
        node_type = getattr(node, "type", "")
        tool_name = getattr(node, "tool_name", "").lower()
        return (
            "embedding" in tool_name
            or "vector" in tool_name
            or "csv" in tool_name
            or node_type == "agent"
        )

    def _is_io_bound(self, node: Any) -> bool:
        """Determine if node is I/O bound."""
        node_type = getattr(node, "type", "")
        tool_name = getattr(node, "tool_name", "").lower()
        return (
            "http" in tool_name
            or "api" in tool_name
            or "file" in tool_name
            or node_type == "llm"
        )

    def _infer_canvas_cluster(self, node: Any) -> str:
        """Infer canvas cluster for UI grouping."""
        node_type = getattr(node, "type", "")
        tool_name = getattr(node, "tool_name", "").lower()

        if node_type == "agent":
            return "agents"
        elif node_type == "llm":
            return "ai_processing"
        elif "csv" in tool_name or "data" in tool_name:
            return "data_processing"
        elif "http" in tool_name or "api" in tool_name:
            return "external_apis"
        else:
            return "utilities"

    def _get_node_color(self, node: Any) -> str:
        """Get suggested color for node visualization."""
        node_type = getattr(node, "type", "")
        color_map = {
            "tool": "#4CAF50",  # Green
            "llm": "#2196F3",  # Blue
            "agent": "#FF9800",  # Orange
            "condition": "#9C27B0",  # Purple
            "loop": "#F44336",  # Red
            "workflow": "#795548",  # Brown
        }
        return color_map.get(node_type, "#607D8B")  # Blue Grey default

    def _calculate_complexity(self, node: Any) -> float:
        """Calculate node complexity score."""
        base_score = 1.0
        node_type = getattr(node, "type", "")

        # Type-based complexity
        complexity_map = {
            "tool": 1.0,
            "llm": 2.0,
            "agent": 3.0,
            "loop": 2.5,
            "condition": 1.5,
            "workflow": 4.0,
        }

        return complexity_map.get(node_type, base_score)

    def _extract_tags(self, node: Any) -> List[str]:
        """Extract tags from node for categorization."""
        tags = []
        node_type = getattr(node, "type", "")
        tool_name = getattr(node, "tool_name", "")

        tags.append(node_type)
        if tool_name:
            tags.append(f"tool:{tool_name}")

        if hasattr(node, "metadata") and node.metadata:
            if hasattr(node.metadata, "tags"):
                tags.extend(node.metadata.tags)

        return tags

    def _infer_data_schema(self, source_id: str, target_id: str) -> str:
        """Infer the data schema flowing between nodes."""
        source_node = self._node_map.get(source_id)
        if source_node and hasattr(source_node, "output_schema"):
            return str(type(source_node.output_schema).__name__)
        return "unknown"

    def _estimate_data_size(self, source_id: str, target_id: str) -> str:
        """Estimate data size flowing between nodes."""
        source_node = self._node_map.get(source_id)
        if source_node:
            tool_name = getattr(source_node, "tool_name", "").lower()
            if "csv" in tool_name:
                return "large"
            elif "llm" in str(getattr(source_node, "type", "")):
                return "medium"
        return "small"

    def _is_latency_sensitive(self, source_id: str, target_id: str) -> bool:
        """Determine if the data flow is latency sensitive."""
        target_node = self._node_map.get(target_id)
        if target_node:
            return getattr(target_node, "type", "") == "agent"
        return False

    def _compute_advanced_metrics(self) -> None:
        """Compute advanced graph metrics using NetworkX algorithms."""
        if not self.graph.nodes():
            return

        # Centrality analysis
        try:
            centrality = nx.betweenness_centrality(self.graph)
            for node_id, score in centrality.items():
                self.graph.nodes[node_id]["centrality_score"] = score
                self.graph.nodes[node_id]["is_bottleneck"] = score > 0.3
        except Exception:
            pass  # Skip if graph analysis fails

        # Critical path analysis (by complexity score)
        try:
            critical_path = nx.dag_longest_path(self.graph, weight="complexity_score")
            for node_id in critical_path:
                self.graph.nodes[node_id]["is_critical_path"] = True
                # Mark edges on critical path
                for i in range(len(critical_path) - 1):
                    if self.graph.has_edge(critical_path[i], critical_path[i + 1]):
                        self.graph.edges[critical_path[i], critical_path[i + 1]][
                            "critical_path"
                        ] = True
        except Exception:
            pass

        # Parallel group assignment
        levels = self.get_level_nodes()
        for level, nodes in levels.items():
            for node_id in nodes:
                self.graph.nodes[node_id]["parallel_group"] = level

    # 🚀 ADVANCED NETWORKX ANALYSIS METHODS

    def get_critical_path(self) -> List[str]:
        """Get the critical path using NetworkX longest path algorithm."""
        try:
            path = nx.dag_longest_path(self.graph, weight="avg_execution_time")
            return list(path) if path else []
        except Exception:
            try:
                path = nx.dag_longest_path(self.graph, weight="complexity_score")
                return list(path) if path else []
            except Exception:
                return []

    def get_bottleneck_nodes(self) -> List[str]:
        """Identify bottleneck nodes using betweenness centrality."""
        try:
            centrality = nx.betweenness_centrality(self.graph)
            return [str(node) for node, score in centrality.items() if score > 0.3]
        except Exception:
            return []

    def get_parallel_execution_groups(
        self,
    ) -> Dict[int, Dict[str, Union[List[str], int]]]:
        """Get enhanced parallel execution groups with safety analysis."""
        levels = self.get_level_nodes()
        result: Dict[int, Dict[str, Union[List[str], int]]] = {}

        for level, nodes in levels.items():
            parallel_safe = []
            sequential_only = []

            for node_id in nodes:
                node_data = self.graph.nodes[node_id]
                if node_data.get("parallel_safe", True):
                    parallel_safe.append(node_id)
                else:
                    sequential_only.append(node_id)

            result[level] = {
                "parallel_safe": parallel_safe,
                "sequential_only": sequential_only,
                "total": len(nodes),
            }

        return result

    def get_optimization_insights(self) -> Dict[str, Any]:
        """Get comprehensive optimization insights."""
        insights = {
            "total_nodes": self.graph.number_of_nodes(),
            "total_edges": self.graph.number_of_edges(),
            "max_depth": max(self.node_levels.values()) if self.node_levels else 0,
            "critical_path": self.get_critical_path(),
            "bottlenecks": self.get_bottleneck_nodes(),
            "parallel_opportunities": sum(
                len(nodes) for nodes in self.get_parallel_execution_groups().values()
            ),
            "complexity_distribution": self._get_complexity_distribution(),
            "execution_insights": self._get_execution_insights(),
        }
        return insights

    def _get_complexity_distribution(self) -> Dict[str, int]:
        """Get distribution of node complexities."""
        distribution = {"low": 0, "medium": 0, "high": 0}

        for node_id in self.graph.nodes():
            score = self.graph.nodes[node_id].get("complexity_score", 1.0)
            if score <= 1.5:
                distribution["low"] += 1
            elif score <= 3.0:
                distribution["medium"] += 1
            else:
                distribution["high"] += 1

        return distribution

    def _get_execution_insights(self) -> Dict[str, Any]:
        """Get execution performance insights."""
        total_cost = sum(
            self.graph.nodes[node_id].get("estimated_cost", 0.0)
            for node_id in self.graph.nodes()
        )

        avg_execution_time = sum(
            self.graph.nodes[node_id].get("avg_execution_time", 0.0)
            for node_id in self.graph.nodes()
        ) / max(self.graph.number_of_nodes(), 1)

        return {
            "estimated_total_cost": total_cost,
            "avg_execution_time": avg_execution_time,
            "cacheable_nodes": len(
                [
                    n
                    for n in self.graph.nodes()
                    if self.graph.nodes[n].get("cacheable", True)
                ]
            ),
            "io_bound_nodes": len(
                [
                    n
                    for n in self.graph.nodes()
                    if self.graph.nodes[n].get("io_bound", False)
                ]
            ),
        }

    def update_execution_stats(
        self,
        node_id: str,
        execution_time: float,
        success: bool,
        error: Optional[str] = None,
    ) -> None:
        """Update node execution statistics."""
        if node_id not in self.graph.nodes:
            return

        node_data = self.graph.nodes[node_id]

        # Update execution stats
        node_data["execution_count"] += 1
        node_data["last_execution_time"] = execution_time
        node_data["last_updated"] = datetime.utcnow()

        if error:
            node_data["last_error"] = error

        # Update rolling average execution time
        count = node_data["execution_count"]
        current_avg = node_data["avg_execution_time"]
        node_data["avg_execution_time"] = (
            (current_avg * (count - 1)) + execution_time
        ) / count

        # Update success rate
        current_success_rate = node_data["success_rate"]
        node_data["success_rate"] = (
            (current_success_rate * (count - 1)) + (1.0 if success else 0.0)
        ) / count

        # Update execution state
        node_data["execution_state"] = "completed" if success else "failed"

    def update_data_transfer_stats(
        self, source_id: str, target_id: str, transfer_time: float, data_size: int
    ) -> None:
        """Update edge data transfer statistics."""
        if not self.graph.has_edge(source_id, target_id):
            return

        edge_data = self.graph.edges[source_id, target_id]

        # Update transfer stats
        edge_data["transfer_count"] += 1
        edge_data["last_used"] = datetime.utcnow()
        edge_data["total_data_transferred"] += data_size

        # Update rolling average transfer time
        count = edge_data["transfer_count"]
        current_avg = edge_data["avg_transfer_time"]
        edge_data["avg_transfer_time"] = (
            (current_avg * (count - 1)) + transfer_time
        ) / count

    def get_canvas_layout_hints(self) -> Dict[str, Dict[str, Any]]:
        """Generate intelligent canvas layout hints using NetworkX algorithms."""
        if not self.graph.nodes():
            return {}

        layout_hints = {}

        try:
            # Use spring layout as base positioning
            pos = nx.spring_layout(self.graph, k=3, iterations=50)

            # Get levels for Y-axis positioning (unused but kept for future use)

            for node_id in self.graph.nodes():
                node_data = self.graph.nodes[node_id]
                level = self.node_levels.get(node_id, 0)

                layout_hints[node_id] = {
                    "position": {
                        "x": pos[node_id][0] * 800,  # Scale for screen coordinates
                        "y": level * 150,  # Level-based Y positioning
                    },
                    "styling": {
                        "color": node_data.get("suggested_color", "#607D8B"),
                        "size": max(
                            20, min(60, node_data.get("complexity_score", 1.0) * 20)
                        ),
                        "cluster": node_data.get("canvas_cluster", "default"),
                    },
                    "metadata": {
                        "level": level,
                        "centrality": node_data.get("centrality_score", 0.0),
                        "is_bottleneck": node_data.get("is_bottleneck", False),
                        "is_critical": node_data.get("is_critical_path", False),
                        "parallel_safe": node_data.get("parallel_safe", True),
                        "execution_state": node_data.get("execution_state", "pending"),
                    },
                    "connections": {
                        "inputs": list(self.graph.predecessors(node_id)),
                        "outputs": list(self.graph.successors(node_id)),
                    },
                }

        except Exception:
            # Fallback to simple layout
            for i, node_id in enumerate(self.graph.nodes()):
                layout_hints[node_id] = {
                    "position": {"x": (i % 5) * 150, "y": (i // 5) * 100},
                    "styling": {"color": "#607D8B", "size": 30, "cluster": "default"},
                    "metadata": {"level": self.node_levels.get(node_id, 0)},
                    "connections": {
                        "inputs": list(self.graph.predecessors(node_id)),
                        "outputs": list(self.graph.successors(node_id)),
                    },
                }

        return layout_hints

    def export_for_analysis(self) -> Dict[str, Any]:
        """Export rich graph data for external analysis tools."""
        return {
            "graph_data": {
                "nodes": [
                    {"id": node_id, **data}
                    for node_id, data in self.graph.nodes(data=True)
                ],
                "edges": [
                    {"source": u, "target": v, **data}
                    for u, v, data in self.graph.edges(data=True)
                ],
            },
            "metrics": self.get_optimization_insights(),
            "layout_hints": self.get_canvas_layout_hints(),
            "analysis_timestamp": datetime.utcnow().isoformat(),
        }

    def _assign_levels(self, nodes: List[Any]) -> None:
        """Assign execution levels to nodes, handling cycles for recursive nodes."""

        # Get all recursive node IDs
        recursive_nodes = {
            node.id
            for node in nodes
            if hasattr(node, "type") and node.type == "recursive"
        }

        # Create a temporary graph without recursive edges for level assignment
        temp_graph = self.graph.copy()
        recursive_edges = []

        # Remove edges that create cycles involving recursive nodes
        for edge in list(temp_graph.edges()):
            from_node, to_node = edge
            if from_node in recursive_nodes or to_node in recursive_nodes:
                # Check if this edge creates a cycle
                temp_graph.remove_edge(from_node, to_node)
                if nx.has_path(temp_graph, to_node, from_node):
                    # This edge creates a cycle, keep it removed for level assignment
                    recursive_edges.append((from_node, to_node))
                else:
                    # This edge doesn't create a cycle, add it back
                    temp_graph.add_edge(from_node, to_node)

        # Now assign levels using the cycle-free temporary graph
        node_map = {node.id: node for node in nodes}

        try:
            for node_id in nx.topological_sort(temp_graph):
                node = node_map[node_id]
                node.level = (
                    max(
                        (
                            node_map[dep].level
                            for dep in (
                                getattr(node, "dependencies", [])
                                if isinstance(getattr(node, "dependencies", []), list)
                                else [getattr(node, "dependencies", [])]
                            )
                            # Filter out dependencies that create cycles
                            if dep
                            not in {e[0] for e in recursive_edges if e[1] == node_id}
                        ),
                        default=-1,
                    )
                    + 1
                )
        except nx.NetworkXUnfeasible:
            # Fallback: assign levels manually for remaining cycles
            remaining_nodes = [n for n in nodes if not hasattr(n, "level")]
            for i, node in enumerate(remaining_nodes):
                node.level = i + 1

        # Store the level mapping for quick lookup
        self.node_levels = {node.id: node.level for node in nodes}

    def get_level_nodes(self) -> Dict[int, List[str]]:
        """Return mapping of *level → node_ids*.

        Example::

            >>> dg.get_level_nodes()
            {0: ["root"], 1: ["child1", "child2"]}
        """

        levels: Dict[int, List[str]] = {}
        for node_id, level in self.node_levels.items():
            if level not in levels:
                levels[level] = []
            levels[level].append(node_id)
        return levels

    def get_node_dependencies(self, node_id: str) -> List[str]:
        return list(self.graph.predecessors(node_id))

    def get_node_dependents(self, node_id: str) -> List[str]:
        return list(self.graph.successors(node_id))

    def get_node_level(self, node_id: str) -> int:
        return self.node_levels[node_id]

    def get_leaf_nodes(self) -> List[str]:
        """Return nodes without outgoing edges (terminal nodes).

        Useful when you need the chain’s "result" node(s).  A short example::

            >>> dg.get_leaf_nodes()
            ["final"]
        """

        # NetworkX typing stubs treat ``out_degree`` as *Mapping[node, int]* rather than
        # an iterable of *(node, degree)* tuples.  Avoid the unpacking to satisfy
        # Pyright by querying degree per node explicitly.
        return [n for n in self.graph.nodes() if self.graph.out_degree(n) == 0]

    def validate_schema_alignment(self, nodes: List[Any]) -> None:
        node_map = {node.id: node for node in nodes}
        for node in nodes:
            # Check input mappings to ensure they reference valid dependencies and output keys
            for placeholder, mapping in getattr(node, "input_mappings", {}).items():
                # Skip validation when mapping is a literal/static value (str, int, etc.)
                # Only InputMapping objects or dicts with explicit "source_node_id" participate
                if not (
                    hasattr(mapping, "source_node_id")
                    or (isinstance(mapping, dict) and "source_node_id" in mapping)
                ):
                    # This placeholder is bound to a constant – no dependency validation needed
                    continue

                if hasattr(mapping, "source_node_id"):
                    dep_id = mapping.source_node_id  # type: ignore[attr-defined]
                    output_key = mapping.source_output_key  # type: ignore[attr-defined]
                else:
                    # ``mapping`` is a ``dict`` with the required keys (validated above)
                    dep_id = mapping["source_node_id"]  # type: ignore[index]
                    output_key = mapping["source_output_key"]  # type: ignore[index]

                if dep_id not in self.get_node_dependencies(node.id):
                    raise ValueError(
                        f"Node '{node.id}' has an input mapping for '{placeholder}' from '{dep_id}', which is not a direct dependency."
                    )

                dep_node = node_map.get(dep_id)
                if not dep_node:
                    raise ValueError(
                        f"Dependency node '{dep_id}' not found in the chain configuration."
                    )

                # Handle both Pydantic models and dicts for schema
                if hasattr(dep_node.output_schema, "model_fields"):
                    # It's a Pydantic model
                    output_keys = dep_node.output_schema.model_fields.keys()
                else:
                    # It's a dictionary
                    output_keys = getattr(dep_node, "output_schema", {}).keys()

                # The source_output_key can be nested, e.g., 'data.result'.
                # We'll check the top-level key for now.
                top_level_key = output_key.split(".")[0]

                if top_level_key not in output_keys and output_key != ".":
                    raise ValueError(
                        f"Node '{node.id}' expects input for '{placeholder}' from key '{output_key}' "
                        f"of node '{dep_id}', but '{top_level_key}' is not in its output schema. "
                        f"Available keys: {list(output_keys)}"
                    )

    # -----------------------------------------------------------------
    # Security helpers -------------------------------------------------
    # -----------------------------------------------------------------

    def _validate_no_sensitive_data_flows(self, nodes: List[Any]) -> None:
        """Placeholder – Ensure nodes flagged as *contains_sensitive_data*
        do not feed into external calls without explicit approval."""

        for node in nodes:
            if getattr(node, "contains_sensitive_data", False):
                for succ in self.get_node_dependents(node.id):
                    succ_node = next((n for n in nodes if n.id == succ), None)
                    if succ_node and getattr(succ_node, "requires_external_io", False):
                        raise ValueError(
                            f"Sensitive data from node '{node.id}' flows into external I/O node '{succ}'."
                        )

    def _enforce_airgap_compliance(self, nodes: List[Any]) -> None:
        """Placeholder hook to prevent nodes that need internet access when
        running in *air-gapped* environments.  Actual enforcement should be
        provided by deployment config; this is a best-effort static guard."""

        if not any(getattr(n, "airgap_mode", False) for n in nodes):
            return

        for node in nodes:
            if getattr(node, "requires_external_io", False):
                raise ValueError(
                    f"Air-gap compliance violation: node '{node.id}' requires external I/O."
                )

    # ---------------------------------------------------------------------
    # Developer ergonomics -------------------------------------------------
    # ---------------------------------------------------------------------

    def __repr__(self) -> str:
        return (
            f"<DependencyGraph nodes={self.graph.number_of_nodes()} "
            f"edges={self.graph.number_of_edges()} "
            f"levels={len(self.node_levels)}>"
        )

    def _check_cycles_with_recursive_support(self, nodes: List[Any]) -> None:
        """Allow controlled cycles for recursive nodes, block unintended cycles."""

        # Get all recursive node IDs and their configuration
        recursive_nodes = {}
        for node in nodes:
            if hasattr(node, "type") and node.type == "recursive":
                recursive_nodes[node.id] = node

        cycles = list(nx.simple_cycles(self.graph))
        if cycles:
            for cycle in cycles:
                # Check if cycle involves only recursive nodes and their declared sources
                if not self._is_valid_recursive_cycle(cycle, recursive_nodes):
                    cycle_str = " -> ".join(cycle)
                    raise CircularDependencyError(
                        f"Invalid cycle detected: {cycle_str}. "
                        f"Only recursive nodes with properly declared recursive_sources may form cycles."
                    )

    def _is_valid_recursive_cycle(
        self, cycle: List[str], recursive_nodes: Dict[str, Any]
    ) -> bool:
        """Validate that cycles are intentional and properly configured."""
        # Must contain at least one recursive node
        recursive_in_cycle = [
            node_id for node_id in cycle if node_id in recursive_nodes
        ]
        if not recursive_in_cycle:
            return False

        # Check that recursive sources are properly declared
        for recursive_node_id in recursive_in_cycle:
            recursive_node = recursive_nodes[recursive_node_id]
            recursive_sources = getattr(recursive_node, "recursive_sources", [])

            # All other nodes in the cycle should be declared as recursive sources
            other_nodes_in_cycle = [n for n in cycle if n != recursive_node_id]

            # Check if at least one of the other nodes is a declared source
            if not any(source in recursive_sources for source in other_nodes_in_cycle):
                return False

        return True
