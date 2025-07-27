from typing import Any, Dict, List, Set, Tuple

import networkx as nx

from ice_core.exceptions import CycleDetectionError as CircularDependencyError

class DependencyGraph:
    """
    Handles dependency graph construction, cycle detection, level assignment, and queries for ScriptChain.
    """

    def __init__(self, nodes: List[Any]):
        self.graph = nx.DiGraph()
        # Mapping of node_id -> topological level (depth) ------------------
        self.node_levels: Dict[str, int] = {}
        self._build_graph(nodes)
        self._assign_levels(nodes)

    def _build_graph(self, nodes: List[Any]) -> None:
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

        # --------------------------------------------------------------
        # Security & compliance validations ----------------------------
        # --------------------------------------------------------------
        self._validate_no_sensitive_data_flows(nodes)
        self._enforce_airgap_compliance(nodes)

    def _assign_levels(self, nodes: List[Any]) -> None:
        node_map = {node.id: node for node in nodes}
        for node_id in nx.topological_sort(self.graph):
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
                    ),
                    default=-1,
                )
                + 1
            )
            self.node_levels[node_id] = node.level

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
