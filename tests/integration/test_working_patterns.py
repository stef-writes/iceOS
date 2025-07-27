"""Integration tests based on working FB Marketplace demo patterns.

These tests validate the core functionality that powers our enhanced 
Facebook Marketplace automation demo.
"""
import pytest
import asyncio
from pathlib import Path
from typing import Dict, Any

from ice_core.unified_registry import registry, global_agent_registry
from ice_core.models.node_models import ToolConfig
from ice_core.models.enums import NodeType
from ice_orchestrator.memory.unified import UnifiedMemory, UnifiedMemoryConfig, MemoryConfig
from ice_orchestrator.agent.memory import MemoryAgent, MemoryAgentConfig
from ice_sdk.builders.workflow import WorkflowBuilder


class TestWorkingMemoryPatterns:
    """Test memory patterns that work in our FB marketplace demo."""
    
    @pytest.fixture
    async def unified_memory(self):
        """Create working memory config like in FB marketplace demo."""
        config = UnifiedMemoryConfig(
            enable_working=True,
            enable_episodic=True, 
            enable_semantic=True,
            enable_procedural=True,
            working_config=MemoryConfig(backend="memory"),
            episodic_config=MemoryConfig(backend="memory"),
            semantic_config=MemoryConfig(backend="memory"),
            procedural_config=MemoryConfig(backend="memory")
        )
        memory = UnifiedMemory(config)
        await memory.initialize()
        return memory

    @pytest.mark.asyncio
    async def test_memory_property_access(self, unified_memory):
        """Test direct property access to memory subsystems (working pattern)."""
        # These property accessors work in our FB marketplace demo
        assert hasattr(unified_memory, 'working')
        assert hasattr(unified_memory, 'episodic') 
        assert hasattr(unified_memory, 'semantic')
        assert hasattr(unified_memory, 'procedural')
        
        # Test they return memory instances
        assert unified_memory.working is not None
        assert unified_memory.episodic is not None
        assert unified_memory.semantic is not None
        assert unified_memory.procedural is not None

    @pytest.mark.asyncio
    async def test_basic_memory_operations(self, unified_memory):
        """Test basic memory operations that work in our demo."""
        # Test unified interface (works in demo)
        await unified_memory.store("test_key", "test_value")
        result = await unified_memory.retrieve("test_key")
        assert result is not None
        
        # Test search functionality
        results = await unified_memory.search("test")
        assert isinstance(results, list) 


class TestWorkingToolPatterns:
    """Test tool registration patterns that work in our demo."""
    
    def test_tool_registry_basic_operations(self):
        """Test basic tool registry operations."""
        # This pattern works in our FB marketplace demo
        original_tools = len(registry.list_tools())
        
        # Registration works (used in demo)
        from ice_core.base_tool import ToolBase
        
        class TestTool(ToolBase):
            name: str = "test_tool"
            description: str = "Test tool"
            
            async def _execute_impl(self, **kwargs):
                return {"result": "success"}
        
        test_tool = TestTool()
        
        # Use the pattern from our working demo
        registry.register_instance(NodeType.TOOL, "test_tool", test_tool)
        
        # Verify registration - much cleaner with nested structure!
        assert len(registry.list_tools()) == original_tools + 1
        assert registry.has_tool("test_tool")
        assert registry.get_tool("test_tool") == test_tool
        
        # Cleanup - more robust with nested structure
        if NodeType.TOOL in registry._instances and "test_tool" in registry._instances[NodeType.TOOL]:
            del registry._instances[NodeType.TOOL]["test_tool"]

    def test_agent_registry_basic_operations(self):
        """Test agent registry operations that work in our demo."""
        original_count = len(global_agent_registry._agents)
        
        # Agent registration pattern from FB marketplace demo
        test_agent_config = {
            "id": "test_agent",
            "package": "test.agent",
            "tools": [ToolConfig(name="test_tool", parameters={})],
            "memory": {"enable_working": True}
        }
        
        global_agent_registry.register_agent("test_agent", test_agent_config)
        
        # Verify registration
        assert len(global_agent_registry._agents) == original_count + 1
        assert "test_agent" in global_agent_registry._agents
        
        # Cleanup
        del global_agent_registry._agents["test_agent"]


class TestWorkingWorkflowPatterns:
    """Test workflow building patterns that work in our demo."""
    
    def test_workflow_builder_creation(self):
        """Test WorkflowBuilder creation (used successfully in demo)."""
        builder = WorkflowBuilder("Test Workflow")
        assert builder.name == "Test Workflow"
        assert builder.nodes == []
        assert builder.edges == []

    def test_workflow_builder_tool_addition(self):
        """Test adding tools to workflow (working pattern from demo)."""
        builder = WorkflowBuilder("Test Workflow")
        
        # This pattern works in our FB marketplace demo
        builder.add_tool("test_node", "test_tool", param1="value1")
        
        assert len(builder.nodes) == 1
        node = builder.nodes[0]
        assert node.id == "test_node"
        assert node.type.value == "tool"

    def test_workflow_builder_connections(self):
        """Test workflow connections (working pattern from demo)."""
        builder = WorkflowBuilder("Test Workflow")
        
        # Add nodes
        builder.add_tool("node1", "tool1")
        builder.add_tool("node2", "tool2")
        
        # Connect them (this pattern works in demo)
        builder.connect("node1", "node2")
        
        assert len(builder.edges) == 1
        assert builder.edges[0] == ("node1", "node2")

    def test_workflow_builder_to_workflow(self):
        """Test building final workflow (working pattern from demo)."""
        builder = WorkflowBuilder("Test Workflow")
        builder.add_tool("test_node", "test_tool")
        
        # This import and build pattern works in our demo
        workflow = builder.build()
        
        assert workflow is not None
        assert workflow.name == "Test Workflow"
        assert len(workflow.nodes) == 1 


@pytest.mark.integration
class TestDemoWorkflowValidation:
    """Validate that our FB marketplace demo patterns work end-to-end."""
    
    def test_demo_tools_importable(self):
        """Test that demo tools can be imported (validates our working demo structure)."""
        # These imports work in our actual demo
        try:
            from use_cases.RivaRidge.FB_Marketplace_Seller.tools.read_inventory_csv import ReadInventoryCSVTool
            from use_cases.RivaRidge.FB_Marketplace_Seller.tools.ai_enrichment import AIEnrichmentTool
            from use_cases.RivaRidge.FB_Marketplace_Seller.tools.facebook_publisher import FacebookPublisherTool
            from use_cases.RivaRidge.FB_Marketplace_Seller.tools.facebook_api_client import FacebookAPIClientTool
            from use_cases.RivaRidge.FB_Marketplace_Seller.tools.activity_simulator import ActivitySimulatorTool
            assert True, "All demo tools imported successfully"
        except ImportError as e:
            pytest.fail(f"Demo tool import failed: {e}")

    def test_demo_agents_importable(self):
        """Test that demo agents can be imported."""
        try:
            from use_cases.RivaRidge.FB_Marketplace_Seller.agents.customer_service_agent import CustomerServiceAgent
            from use_cases.RivaRidge.FB_Marketplace_Seller.agents.pricing_agent import PricingAgent
            assert True, "All demo agents imported successfully"
        except ImportError as e:
            pytest.fail(f"Demo agent import failed: {e}")

    def test_demo_workflow_builder_patterns(self):
        """Test the workflow patterns used in our working demo."""
        # This is the exact pattern that works in enhanced_blueprint_demo.py
        workflow = (WorkflowBuilder("FB Marketplace Demo")
            .add_tool("read_csv", "read_inventory_csv", csv_file="test.csv")
            .add_tool("dedupe", "dedupe_items", strategy="keep_first") 
            .add_tool("ai_enrich", "ai_enrichment", model_name="gpt-4o")
            .add_tool("publish", "facebook_publisher", auto_publish=True)
            .connect("read_csv", "dedupe")
            .connect("dedupe", "ai_enrich")
            .connect("ai_enrich", "publish")
            .build()
        )
        
        assert workflow.name == "FB Marketplace Demo"
        assert len(workflow.nodes) == 4
        # The build() succeeds, proving the pattern works 