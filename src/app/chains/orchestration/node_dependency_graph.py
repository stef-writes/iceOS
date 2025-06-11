from typing import Any, Dict, List

import networkx as nx

from app.chains.chain_errors import CircularDependencyError


class DependencyGraph:
    """
    Handles dependency graph construction, cycle detection, level assignment, and queries for ScriptChain.
    """

    def __init__(self, nodes: List[Any]):
        self.graph = nx.DiGraph()
        self.node_levels = {}
        self._build_graph(nodes)
        self._assign_levels(nodes)

    def _build_graph(self, nodes: List[Any]):
        node_ids = {node.id for node in nodes}
        for node in nodes:
            self.graph.add_node(node.id, level=0)
            for dep in getattr(node, "dependencies", []):
                if dep not in node_ids:
                    raise ValueError(f"Dependency {dep} not found for node {node.id}")
                self.graph.add_edge(dep, node.id)
        # Check for cycles
        try:
            cycles = list(nx.simple_cycles(self.graph))
            if cycles:
                cycle_str = " -> ".join(cycles[0])
                raise CircularDependencyError(
                    f"Circular dependency detected: {cycle_str}"
                )
        except nx.NetworkXNoCycle:
            pass

    def _assign_levels(self, nodes: List[Any]):
        node_map = {node.id: node for node in nodes}
        for node_id in nx.topological_sort(self.graph):
            node = node_map[node_id]
            node.level = (
                max(
                    (node_map[dep].level for dep in getattr(node, "dependencies", [])),
                    default=-1,
                )
                + 1
            )
            self.node_levels[node_id] = node.level

    def get_level_nodes(self) -> Dict[int, List[str]]:
        levels = {}
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
        return [node for node, out_degree in self.graph.out_degree() if out_degree == 0]

    def validate_schema_alignment(self, nodes: List[Any]):
        node_map = {node.id: node for node in nodes}
        for node in nodes:
            # Check input mappings to ensure they reference valid dependencies and output keys
            for placeholder, mapping in getattr(node, "input_mappings", {}).items():
                dep_id = mapping.source_node_id
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
                top_level_key = mapping.source_output_key.split(".")[0]

                if (
                    top_level_key not in output_keys
                    and mapping.source_output_key != "."
                ):
                    raise ValueError(
                        f"Node '{node.id}' expects input for '{placeholder}' from key '{mapping.source_output_key}' "
                        f"of node '{dep_id}', but '{top_level_key}' is not in its output schema. "
                        f"Available keys: {list(output_keys)}"
                    )
