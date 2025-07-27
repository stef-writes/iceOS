"""Registry system integrity tests.

These tests validate the unified registry system works correctly and maintains
backward compatibility with the legacy registry interfaces. They ensure that
the migration from individual registries to the unified registry preserves
all functionality while improving maintainability.
"""

import pytest
from unittest.mock import Mock

from ice_core.unified_registry import (
    registry, 
    global_agent_registry, 
    global_chain_registry,
    Registry,
    RegistryError
)
from ice_core.models import NodeType


class TestUnifiedRegistryCore:
    """Test the core unified registry functionality."""
    
    def setup_method(self):
        """Clear registry before each test."""
        # Clear all internal registries
        registry._nodes.clear()
        registry._instances.clear() 
        registry._executors.clear()
        registry._chains.clear()
        registry._units.clear()
        registry._agents.clear()
    
    def teardown_method(self):
        """Clear registry after each test."""
        registry._nodes.clear()
        registry._instances.clear()
        registry._executors.clear()
        registry._chains.clear()
        registry._units.clear()
        registry._agents.clear()
    
    def test_node_class_registration(self):
        """Test registering and retrieving node classes."""
        mock_node_class = Mock()
        
        registry.register_class(NodeType.TOOL, "test_tool", mock_node_class)
        
        retrieved = registry.get_class(NodeType.TOOL, "test_tool")
        assert retrieved is mock_node_class
    
    def test_node_instance_registration(self):
        """Test registering and retrieving node instances."""
        mock_instance = Mock()
        
        registry.register_instance(NodeType.TOOL, "test_instance", mock_instance)
        
        retrieved = registry.get_instance(NodeType.TOOL, "test_instance")
        assert retrieved is mock_instance
    
    def test_duplicate_registration_raises_error(self):
        """Test that duplicate registrations raise RegistryError."""
        mock_class = Mock()
        
        registry.register_class(NodeType.TOOL, "duplicate", mock_class)
        
        with pytest.raises(RegistryError, match="Node tool:duplicate already registered"):
            registry.register_class(NodeType.TOOL, "duplicate", mock_class)
    
    def test_missing_node_raises_error(self):
        """Test that missing nodes raise RegistryError."""
        with pytest.raises(RegistryError, match="Node class tool:missing not found"):
            registry.get_class(NodeType.TOOL, "missing")
    
    def test_get_instance_creates_from_class(self):
        """Test that get_instance creates instance from registered class."""
        mock_class = Mock()
        mock_instance = Mock()
        mock_class.return_value = mock_instance
        
        registry.register_class(NodeType.TOOL, "auto_create", mock_class)
        
        retrieved = registry.get_instance(NodeType.TOOL, "auto_create")
        assert retrieved is mock_instance
        mock_class.assert_called_once()
    
    def test_list_nodes_filtering(self):
        """Test listing nodes with type filtering."""
        mock_tool = Mock()
        mock_llm = Mock()
        
        registry.register_class(NodeType.TOOL, "tool1", mock_tool)
        registry.register_class(NodeType.LLM, "llm1", mock_llm)
        
        # List all nodes
        all_nodes = registry.list_nodes()
        assert len(all_nodes) == 2
        assert (NodeType.TOOL, "tool1") in all_nodes
        assert (NodeType.LLM, "llm1") in all_nodes
        
        # List only tools
        tools = registry.list_nodes(NodeType.TOOL)
        assert len(tools) == 1
        assert (NodeType.TOOL, "tool1") in tools
        assert (NodeType.LLM, "llm1") not in tools


class TestUnifiedRegistryExecutors:
    """Test executor registration in unified registry."""
    
    def setup_method(self):
        registry._executors.clear()
    
    def teardown_method(self):
        registry._executors.clear()
    
    def test_executor_registration(self):
        """Test registering and retrieving executors."""
        async def test_executor(chain, cfg, ctx):
            return Mock()
        
        registry.register_executor("test_type", test_executor)
        
        retrieved = registry.get_executor("test_type")
        assert retrieved is test_executor
    
    def test_duplicate_executor_raises_error(self):
        """Test that duplicate executor registration raises error."""
        async def executor1(chain, cfg, ctx):
            pass
        
        async def executor2(chain, cfg, ctx):
            pass
        
        registry.register_executor("duplicate", executor1)
        
        with pytest.raises(RegistryError, match="Executor for duplicate already registered"):
            registry.register_executor("duplicate", executor2)
    
    def test_missing_executor_raises_error(self):
        """Test that missing executor raises KeyError."""
        with pytest.raises(KeyError, match="No executor registered for node type: missing"):
            registry.get_executor("missing")


class TestUnifiedRegistryChains:
    """Test chain registration in unified registry."""
    
    def setup_method(self):
        registry._chains.clear()
    
    def teardown_method(self):
        registry._chains.clear()
    
    def test_chain_registration(self):
        """Test registering and retrieving chains."""
        mock_chain = Mock()
        
        registry.register_chain("test_chain", mock_chain)
        
        retrieved = registry.get_chain("test_chain")
        assert retrieved is mock_chain
    
    def test_list_chains(self):
        """Test listing registered chains."""
        chain1 = Mock()
        chain2 = Mock()
        
        registry.register_chain("chain1", chain1)
        registry.register_chain("chain2", chain2)
        
        chains = registry.list_chains()
        assert "chain1" in chains
        assert "chain2" in chains
        assert len(chains) == 2
    
    def test_available_chains(self):
        """Test getting all chains with instances."""
        chain1 = Mock()
        chain2 = Mock()
        
        registry.register_chain("chain1", chain1)
        registry.register_chain("chain2", chain2)
        
        available = registry.available_chains()
        assert len(available) == 2
        assert ("chain1", chain1) in available
        assert ("chain2", chain2) in available


class TestUnifiedRegistryAgents:
    """Test agent registration in unified registry."""
    
    def setup_method(self):
        registry._agents.clear()
    
    def teardown_method(self):
        registry._agents.clear()
    
    def test_agent_registration(self):
        """Test registering and retrieving agents."""
        registry.register_agent("test_agent", "path.to.agent")
        
        path = registry.get_agent_import_path("test_agent")
        assert path == "path.to.agent"
    
    def test_available_agents(self):
        """Test listing available agents."""
        registry.register_agent("agent1", "path.to.agent1")
        registry.register_agent("agent2", "path.to.agent2")
        
        available = registry.available_agents()
        assert len(available) == 2
        assert ("agent1", "path.to.agent1") in available
        assert ("agent2", "path.to.agent2") in available


class TestBackwardCompatibilityWrappers:
    """Test that backward compatibility wrappers work correctly."""
    
    def setup_method(self):
        registry._chains.clear()
        registry._agents.clear()
    
    def teardown_method(self):
        registry._chains.clear()
        registry._agents.clear()
    
    def test_global_chain_registry_wrapper(self):
        """Test that global_chain_registry wrapper delegates correctly."""
        mock_chain = Mock()
        
        # Registration through wrapper should work
        global_chain_registry.register_chain("test_chain", mock_chain)
        
        # Retrieval through wrapper should work
        retrieved = global_chain_registry.get_chain("test_chain")
        assert retrieved is mock_chain
        
        # Should also be available through main registry
        assert registry.get_chain("test_chain") is mock_chain
    
    def test_global_chain_registry_iteration(self):
        """Test that global_chain_registry supports iteration."""
        chain1 = Mock()
        chain2 = Mock()
        
        global_chain_registry.register_chain("chain1", chain1)
        global_chain_registry.register_chain("chain2", chain2)
        
        # Should support iteration
        chains = list(global_chain_registry)
        assert len(chains) == 2
        assert ("chain1", chain1) in chains
        assert ("chain2", chain2) in chains
    
    def test_global_agent_registry_wrapper(self):
        """Test that global_agent_registry wrapper delegates correctly."""
        global_agent_registry.register_agent("test_agent", "path.to.agent")
        
        # Retrieval through wrapper should work
        path = global_agent_registry.get_agent_import_path("test_agent")
        assert path == "path.to.agent"
        
        # Should also be available through main registry
        assert registry.get_agent_import_path("test_agent") == "path.to.agent"



class TestRegistryErrorHandling:
    """Test comprehensive error handling in registry system."""
    
    def setup_method(self):
        registry._chains.clear()
        registry._agents.clear()
        registry._nodes.clear()
        registry._instances.clear()
    
    def teardown_method(self):
        registry._chains.clear()
        registry._agents.clear()
        registry._nodes.clear()
        registry._instances.clear()
    
    def test_chain_registry_error_propagation(self):
        """Test that errors propagate correctly through wrapper."""
        mock_chain = Mock()
        global_chain_registry.register_chain("test_chain", mock_chain)
        
        # Duplicate registration should raise error
        with pytest.raises(RegistryError, match="Chain test_chain already registered"):
            global_chain_registry.register_chain("test_chain", mock_chain)
    
    def test_missing_chain_error(self):
        """Test error when retrieving missing chain."""
        with pytest.raises(KeyError, match="Chain missing not found"):
            global_chain_registry.get_chain("missing")
    
    def test_agent_registry_error_propagation(self):
        """Test that agent registry errors propagate correctly."""
        global_agent_registry.register_agent("test_agent", "path.to.agent")
        
        # Duplicate registration should raise error
        with pytest.raises(RegistryError, match="Agent test_agent already registered"):
            global_agent_registry.register_agent("test_agent", "another.path")
    
    def test_missing_agent_error(self):
        """Test error when retrieving missing agent."""
        with pytest.raises(KeyError, match="Agent missing not found"):
            global_agent_registry.get_agent_import_path("missing")


class TestRegistryEntryPointsIntegration:
    """Test integration with Python entry points system."""
    
    def test_load_entry_points_no_crash(self):
        """Test that loading entry points doesn't crash even if none exist."""
        # This should not raise an exception even if no entry points are defined
        count = registry.load_entry_points("nonexistent.group")
        assert count == 0
    
    def test_load_entry_points_with_mock(self):
        """Test entry point loading with mocked entry points."""
        from unittest.mock import patch, Mock
        
        # Mock an entry point
        mock_ep = Mock()
        mock_ep.name = "tool:test_tool"
        mock_ep.load.return_value = Mock  # Mock class
        
        with patch('importlib.metadata.entry_points') as mock_eps:
            mock_eps.return_value = [mock_ep]
            
            count = registry.load_entry_points("test.group")
            assert count == 1
            
            # Should have registered the tool
            registered = registry.get_class(NodeType.TOOL, "test_tool")
            assert registered is Mock


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 