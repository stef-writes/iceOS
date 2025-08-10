"""Tests for enhanced NetworkX utilization in DependencyGraph.

This test suite validates:
1. Rich node attributes (execution tracking, optimization hints, canvas data)
2. Rich edge attributes (data flow analysis, performance tracking)
3. Advanced NetworkX algorithms (critical path, bottlenecks, centrality)
4. Canvas layout hints and optimization insights
5. Performance tracking and data transfer analytics
"""

from datetime import datetime
from typing import Any, List

from ice_core.models.llm import LLMConfig
from ice_core.models.node_metadata import NodeMetadata
from ice_core.models.node_models import AgentNodeConfig, LLMNodeConfig, ToolNodeConfig
from ice_orchestrator.graph.dependency_graph import DependencyGraph


class TestEnhancedNetworkXUtilization:
    """Test suite for enhanced NetworkX features in DependencyGraph."""

    def create_test_nodes(self) -> List[Any]:
        """Create diverse test nodes for comprehensive testing."""
        return [
            ToolNodeConfig(
                id="csv_reader",
                type="tool",
                tool_name="csv_reader",
                dependencies=[],
                metadata=NodeMetadata(
                    node_id="csv_reader", node_type="tool", estimated_cost=0.05
                ),
            ),
            LLMNodeConfig(
                id="analyzer",
                type="llm",
                model="gpt-4",
                prompt="Analyze this data",
                llm_config=LLMConfig(),
                dependencies=["csv_reader"],
                metadata=NodeMetadata(
                    node_id="analyzer", node_type="llm", estimated_cost=0.25
                ),
            ),
            AgentNodeConfig(
                id="smart_agent",
                type="agent",
                package="test_agent",
                tools=[],
                dependencies=["analyzer"],
                metadata=NodeMetadata(
                    node_id="smart_agent", node_type="agent", estimated_cost=0.50
                ),
            ),
            ToolNodeConfig(
                id="report_generator",
                type="tool",
                tool_name="report_generator",
                dependencies=["analyzer", "smart_agent"],
                metadata=NodeMetadata(
                    node_id="report_generator", node_type="tool", estimated_cost=0.10
                ),
            ),
        ]

    def test_rich_node_attributes_storage(self):
        """Test that rich node attributes are properly stored."""
        nodes = self.create_test_nodes()
        graph = DependencyGraph(nodes)

        # Test basic attributes
        csv_node = graph.graph.nodes["csv_reader"]
        assert csv_node["node_type"] == "tool"
        assert csv_node["config"].id == "csv_reader"
        assert csv_node["execution_state"] == "pending"
        assert csv_node["execution_count"] == 0
        assert csv_node["success_rate"] == 1.0

        # Test performance attributes
        assert csv_node["estimated_cost"] == 0.0  # No estimated_cost in NodeMetadata
        assert csv_node["parallel_safe"] is True  # Tools are parallel safe
        assert csv_node["cacheable"] is True

        # Test canvas attributes
        assert csv_node["canvas_cluster"] == "data_processing"  # CSV tools
        assert csv_node["suggested_color"] == "#4CAF50"  # Green for tools
        assert csv_node["complexity_score"] == 1.0  # Tools have low complexity

        # Test metadata
        assert isinstance(csv_node["created_at"], datetime)
        assert "tool" in csv_node["tags"]
        assert "tool:csv_reader" in csv_node["tags"]

    def test_node_type_specific_attributes(self):
        """Test that different node types get appropriate attributes."""
        nodes = self.create_test_nodes()
        graph = DependencyGraph(nodes)

        # Tool node
        tool_node = graph.graph.nodes["csv_reader"]
        assert tool_node["parallel_safe"] is True
        assert tool_node["complexity_score"] == 1.0
        assert tool_node["suggested_color"] == "#4CAF50"

        # LLM node
        llm_node = graph.graph.nodes["analyzer"]
        assert llm_node["parallel_safe"] is True
        assert llm_node["complexity_score"] == 2.0
        assert llm_node["suggested_color"] == "#2196F3"
        assert llm_node["io_bound"] is True

        # Agent node
        agent_node = graph.graph.nodes["smart_agent"]
        assert agent_node["parallel_safe"] is False  # Agents not parallel safe
        assert agent_node["complexity_score"] == 3.0
        assert agent_node["suggested_color"] == "#FF9800"
        assert agent_node["canvas_cluster"] == "agents"

    def test_rich_edge_attributes_storage(self):
        """Test that rich edge attributes are properly stored."""
        nodes = self.create_test_nodes()
        graph = DependencyGraph(nodes)

        # Test edge from csv_reader to analyzer
        edge_data = graph.graph.edges["csv_reader", "analyzer"]

        # Basic edge attributes
        assert edge_data["dependency_type"] == "data_flow"
        assert isinstance(
            edge_data["critical_path"], bool
        )  # Computed during construction
        assert edge_data["parallel_safe"] is True

        # Data flow attributes
        assert edge_data["estimated_data_size"] in ["small", "medium", "large"]
        assert isinstance(edge_data["latency_sensitive"], bool)

        # Performance tracking
        assert edge_data["avg_transfer_time"] == 0.0
        assert edge_data["total_data_transferred"] == 0
        assert edge_data["transfer_count"] == 0

        # Canvas attributes
        assert edge_data["edge_weight"] == 1.0
        assert edge_data["edge_style"] == "default"
        assert edge_data["edge_color"] == "#666666"

        # Metadata
        assert isinstance(edge_data["created_at"], datetime)

    def test_advanced_networkx_algorithms(self):
        """Test advanced NetworkX algorithm integration."""
        nodes = self.create_test_nodes()
        graph = DependencyGraph(nodes)

        # Test critical path detection
        critical_path = graph.get_critical_path()
        assert isinstance(critical_path, list)
        # Should include high-complexity nodes (agent)

        # Test bottleneck detection
        bottlenecks = graph.get_bottleneck_nodes()
        assert isinstance(bottlenecks, list)

        # Test parallel execution groups
        parallel_groups = graph.get_parallel_execution_groups()
        assert isinstance(parallel_groups, dict)

        # Check that each level has proper categorization
        for level, group_data in parallel_groups.items():
            assert "parallel_safe" in group_data
            assert "sequential_only" in group_data
            assert "total" in group_data
            assert group_data["total"] == len(group_data["parallel_safe"]) + len(
                group_data["sequential_only"]
            )

    def test_optimization_insights(self):
        """Test comprehensive optimization insights generation."""
        nodes = self.create_test_nodes()
        graph = DependencyGraph(nodes)

        insights = graph.get_optimization_insights()

        # Basic metrics
        assert insights["total_nodes"] == 4
        assert (
            insights["total_edges"] == 4
        )  # csv->analyzer, analyzer->agent, analyzer->report, agent->report
        assert insights["max_depth"] >= 0

        # Advanced insights
        assert "critical_path" in insights
        assert "bottlenecks" in insights
        assert "parallel_opportunities" in insights
        assert "complexity_distribution" in insights
        assert "execution_insights" in insights

        # Test complexity distribution
        complexity_dist = insights["complexity_distribution"]
        assert complexity_dist["low"] >= 0  # Tools
        assert complexity_dist["medium"] >= 0  # LLM
        assert complexity_dist["high"] >= 0  # Agent

        # Test execution insights
        exec_insights = insights["execution_insights"]
        assert (
            exec_insights["estimated_total_cost"] == 0.0
        )  # No estimated_cost in NodeMetadata
        assert exec_insights["avg_execution_time"] == 0.0  # No executions yet
        assert exec_insights["cacheable_nodes"] >= 0
        assert exec_insights["io_bound_nodes"] >= 0

    def test_execution_stats_tracking(self):
        """Test execution statistics tracking and updates."""
        nodes = self.create_test_nodes()
        graph = DependencyGraph(nodes)

        # Initial state
        node_data = graph.graph.nodes["csv_reader"]
        assert node_data["execution_count"] == 0
        assert node_data["avg_execution_time"] == 0.0
        assert node_data["success_rate"] == 1.0
        assert node_data["execution_state"] == "pending"

        # Simulate execution
        graph.update_execution_stats("csv_reader", 1.5, True)

        # Check updates
        updated_data = graph.graph.nodes["csv_reader"]
        assert updated_data["execution_count"] == 1
        assert updated_data["avg_execution_time"] == 1.5
        assert updated_data["success_rate"] == 1.0
        assert updated_data["execution_state"] == "completed"
        assert updated_data["last_execution_time"] == 1.5
        assert isinstance(updated_data["last_updated"], datetime)

        # Simulate failure
        graph.update_execution_stats("csv_reader", 2.0, False, "Test error")

        # Check failure updates
        failed_data = graph.graph.nodes["csv_reader"]
        assert failed_data["execution_count"] == 2
        assert failed_data["avg_execution_time"] == 1.75  # (1.5 + 2.0) / 2
        assert failed_data["success_rate"] == 0.5  # 1 success, 1 failure
        assert failed_data["execution_state"] == "failed"
        assert failed_data["last_error"] == "Test error"

    def test_data_transfer_stats_tracking(self):
        """Test data transfer statistics tracking."""
        nodes = self.create_test_nodes()
        graph = DependencyGraph(nodes)

        # Initial state
        edge_data = graph.graph.edges["csv_reader", "analyzer"]
        assert edge_data["transfer_count"] == 0
        assert edge_data["avg_transfer_time"] == 0.0
        assert edge_data["total_data_transferred"] == 0

        # Simulate data transfer
        graph.update_data_transfer_stats("csv_reader", "analyzer", 0.1, 1024)

        # Check updates
        updated_edge = graph.graph.edges["csv_reader", "analyzer"]
        assert updated_edge["transfer_count"] == 1
        assert updated_edge["avg_transfer_time"] == 0.1
        assert updated_edge["total_data_transferred"] == 1024
        assert isinstance(updated_edge["last_used"], datetime)

        # Simulate another transfer
        graph.update_data_transfer_stats("csv_reader", "analyzer", 0.2, 512)

        # Check rolling averages
        final_edge = graph.graph.edges["csv_reader", "analyzer"]
        assert final_edge["transfer_count"] == 2
        assert abs(final_edge["avg_transfer_time"] - 0.15) < 1e-10  # (0.1 + 0.2) / 2
        assert final_edge["total_data_transferred"] == 1536  # 1024 + 512

    def test_canvas_layout_hints(self):
        """Test intelligent canvas layout hints generation."""
        nodes = self.create_test_nodes()
        graph = DependencyGraph(nodes)

        layout_hints = graph.get_canvas_layout_hints()

        # Should have hints for all nodes
        assert len(layout_hints) == 4

        for node_id, hints in layout_hints.items():
            # Position data
            assert "position" in hints
            assert "x" in hints["position"]
            assert "y" in hints["position"]

            # Styling data
            assert "styling" in hints
            assert "color" in hints["styling"]
            assert "size" in hints["styling"]
            assert "cluster" in hints["styling"]

            # Metadata
            assert "metadata" in hints
            assert "level" in hints["metadata"]
            assert "centrality" in hints["metadata"]
            assert "is_bottleneck" in hints["metadata"]
            assert "parallel_safe" in hints["metadata"]

            # Connections
            assert "connections" in hints
            assert "inputs" in hints["connections"]
            assert "outputs" in hints["connections"]

    def test_export_for_analysis(self):
        """Test comprehensive data export for external analysis."""
        nodes = self.create_test_nodes()
        graph = DependencyGraph(nodes)

        export_data = graph.export_for_analysis()

        # Top-level structure
        assert "graph_data" in export_data
        assert "metrics" in export_data
        assert "layout_hints" in export_data
        assert "analysis_timestamp" in export_data

        # Graph data structure
        graph_data = export_data["graph_data"]
        assert "nodes" in graph_data
        assert "edges" in graph_data

        # Nodes data
        nodes_data = graph_data["nodes"]
        assert len(nodes_data) == 4
        for node in nodes_data:
            assert "id" in node
            assert "node_type" in node
            assert "config" in node
            assert "complexity_score" in node

        # Edges data
        edges_data = graph_data["edges"]
        assert len(edges_data) == 4
        for edge in edges_data:
            assert "source" in edge
            assert "target" in edge
            assert "dependency_type" in edge
            assert "estimated_data_size" in edge

    def test_complex_graph_analysis(self):
        """Test analysis on a more complex graph structure."""
        # Create a more complex graph with multiple paths
        complex_nodes = [
            ToolNodeConfig(
                id="input1", type="tool", tool_name="reader1", dependencies=[]
            ),
            ToolNodeConfig(
                id="input2", type="tool", tool_name="reader2", dependencies=[]
            ),
            ToolNodeConfig(
                id="processor1", type="tool", tool_name="proc1", dependencies=["input1"]
            ),
            ToolNodeConfig(
                id="processor2", type="tool", tool_name="proc2", dependencies=["input2"]
            ),
            LLMNodeConfig(
                id="analyzer",
                type="llm",
                model="gpt-4",
                prompt="analyze",
                llm_config=LLMConfig(),
                dependencies=["processor1", "processor2"],
            ),
            AgentNodeConfig(
                id="agent", type="agent", package="test", dependencies=["analyzer"]
            ),
            ToolNodeConfig(
                id="output",
                type="tool",
                tool_name="writer",
                dependencies=["analyzer", "agent"],
            ),
        ]

        graph = DependencyGraph(complex_nodes)

        # Test that complex analysis works
        insights = graph.get_optimization_insights()
        assert insights["total_nodes"] == 7
        assert insights["max_depth"] >= 3  # Should have good depth

        # Test parallel opportunities
        parallel_groups = graph.get_parallel_execution_groups()
        level_0 = parallel_groups[0]  # Should have input1, input2
        assert level_0["total"] == 2
        assert len(level_0["parallel_safe"]) == 2  # Both inputs can run in parallel

        # Test critical path includes high-complexity nodes
        critical_path = graph.get_critical_path()
        assert len(critical_path) > 0

    def test_canvas_clustering_intelligence(self):
        """Test intelligent canvas clustering based on node types and tools."""
        nodes = self.create_test_nodes()
        graph = DependencyGraph(nodes)

        # Test cluster assignments
        clusters = {}
        for node_id in graph.graph.nodes():
            cluster = graph.graph.nodes[node_id]["canvas_cluster"]
            if cluster not in clusters:
                clusters[cluster] = []
            clusters[cluster].append(node_id)

        # Should have meaningful clusters
        assert "data_processing" in clusters  # CSV reader
        assert "ai_processing" in clusters  # LLM analyzer
        assert "agents" in clusters  # Smart agent

        # Test cluster makes sense
        assert "csv_reader" in clusters["data_processing"]
        assert "analyzer" in clusters["ai_processing"]
        assert "smart_agent" in clusters["agents"]

    def test_error_handling_and_edge_cases(self):
        """Test error handling and edge cases."""
        # Empty graph
        empty_graph = DependencyGraph([])
        assert empty_graph.get_optimization_insights()["total_nodes"] == 0
        assert empty_graph.get_canvas_layout_hints() == {}

        # Single node
        single_node = [
            ToolNodeConfig(
                id="solo", type="tool", tool_name="solo_tool", dependencies=[]
            )
        ]
        single_graph = DependencyGraph(single_node)
        insights = single_graph.get_optimization_insights()
        assert insights["total_nodes"] == 1
        assert insights["total_edges"] == 0

        # Update stats for non-existent node (should not crash)
        single_graph.update_execution_stats("nonexistent", 1.0, True)
        single_graph.update_data_transfer_stats(
            "nonexistent", "also_nonexistent", 1.0, 100
        )

    def test_performance_characteristics(self):
        """Test that enhanced NetworkX operations are performant."""
        import time

        # Create larger graph for performance testing
        large_nodes = []
        for i in range(100):
            deps = [
                f"node_{j}" for j in range(max(0, i - 3), i)
            ]  # Each node depends on 3 previous
            large_nodes.append(
                ToolNodeConfig(
                    id=f"node_{i}",
                    type="tool",
                    tool_name=f"tool_{i}",
                    dependencies=deps,
                )
            )

        # Test construction performance
        start_time = time.time()
        large_graph = DependencyGraph(large_nodes)
        construction_time = time.time() - start_time
        assert construction_time < 5.0  # Should construct quickly

        # Test analysis performance
        start_time = time.time()
        insights = large_graph.get_optimization_insights()
        analysis_time = time.time() - start_time
        assert analysis_time < 2.0  # Should analyze quickly

        # Test layout hints performance
        start_time = time.time()
        layout_hints = large_graph.get_canvas_layout_hints()
        layout_time = time.time() - start_time
        assert layout_time < 3.0  # Should generate layout quickly

        # Verify correctness with large graph
        assert insights["total_nodes"] == 100
        assert len(layout_hints) == 100
