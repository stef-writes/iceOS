"""Tests for recursive flow functionality in iceOS workflows.

Tests the new recursive node type that enables agent conversations until convergence.
"""

import pytest
from unittest.mock import Mock, patch
from ice_core.models import RecursiveNodeConfig, NodeExecutionResult, NodeMetadata
from ice_orchestrator.execution.executors.unified import recursive_executor
from ice_orchestrator.workflow import Workflow
from ice_sdk.builders.workflow import WorkflowBuilder


@pytest.fixture
def sample_recursive_config():
    """Create a sample recursive node configuration."""
    return RecursiveNodeConfig(
        id="negotiation_loop",
        type="recursive",
        agent_package="test_agents.negotiator",
        recursive_sources=["buyer_agent", "seller_agent"],
        convergence_condition="agreement_reached == True",
        max_iterations=10,
        preserve_context=True
    )


@pytest.fixture
def mock_workflow():
    """Create a mock workflow for testing."""
    workflow = Mock(spec=Workflow)
    workflow.nodes = {}
    return workflow


class TestRecursiveNodeConfig:
    """Test RecursiveNodeConfig validation and functionality."""
    
    def test_recursive_config_validation_success(self):
        """Test that valid recursive config passes validation."""
        config = RecursiveNodeConfig(
            id="test_recursive",
            type="recursive",
            agent_package="test.agent",
            recursive_sources=["node1", "node2"],
            convergence_condition="done == True"
        )
        assert config.id == "test_recursive"
        assert config.agent_package == "test.agent"
        assert config.recursive_sources == ["node1", "node2"]
    
    def test_recursive_config_validation_no_package_or_workflow(self):
        """Test that config fails validation without agent_package or workflow_ref."""
        with pytest.raises(ValueError, match="must specify either agent_package or workflow_ref"):
            RecursiveNodeConfig(
                id="test_recursive",
                type="recursive",
                recursive_sources=["node1"]
            )
    
    def test_recursive_config_validation_both_package_and_workflow(self):
        """Test that config fails validation with both agent_package and workflow_ref."""
        with pytest.raises(ValueError, match="cannot specify both agent_package and workflow_ref"):
            RecursiveNodeConfig(
                id="test_recursive",
                type="recursive",
                agent_package="test.agent",
                workflow_ref="test.workflow",
                recursive_sources=["node1"]
            )
    
    def test_recursive_config_validation_no_sources(self):
        """Test that config fails validation without recursive_sources."""
        with pytest.raises(ValueError, match="must specify at least one recursive_source"):
            RecursiveNodeConfig(
                id="test_recursive",
                type="recursive",
                agent_package="test.agent",
                recursive_sources=[]
            )


class TestRecursiveExecutor:
    """Test the recursive executor functionality."""
    
    @pytest.mark.asyncio
    async def test_recursive_executor_max_iterations(self, sample_recursive_config, mock_workflow):
        """Test that recursive executor respects max iterations."""
        ctx = {"_recursive_iteration": 10}  # At max iterations
        
        result = await recursive_executor(mock_workflow, sample_recursive_config, ctx)
        
        assert result.success == True
        assert result.output["converged"] == False
        assert result.output["reason"] == "max_iterations_reached"
        assert result.output["iterations"] == 10
    
    @pytest.mark.asyncio
    async def test_recursive_executor_convergence_condition_met(self, sample_recursive_config, mock_workflow):
        """Test that recursive executor stops when convergence condition is met."""
        ctx = {
            "_recursive_iteration": 3,
            "agreement_reached": True  # Convergence condition is met
        }
        
        result = await recursive_executor(mock_workflow, sample_recursive_config, ctx)
        
        assert result.success == True
        assert result.output["converged"] == True
        assert result.output["reason"] == "condition_met"
        assert result.output["iterations"] == 3
    
    @pytest.mark.asyncio
    async def test_recursive_executor_continues_when_no_convergence(self, sample_recursive_config, mock_workflow):
        """Test that recursive executor continues when convergence condition is not met."""
        ctx = {
            "_recursive_iteration": 3,
            "agreement_reached": False  # Convergence condition not met
        }
        
        # Mock the agent executor
        with patch('ice_orchestrator.execution.executors.unified.agent_executor') as mock_agent_exec:
            mock_result = NodeExecutionResult(
                success=True,
                output={"negotiation_progress": "ongoing"},
                execution_time=1.0,
                metadata=NodeMetadata(
                    node_id="negotiation_loop",
                    node_type="agent",
                    name="test_agent"
                )
            )
            mock_agent_exec.return_value = mock_result
            
            result = await recursive_executor(mock_workflow, sample_recursive_config, ctx)
            
            assert result.output["_recursive_iteration"] == 4
            assert result.output["_can_recurse"] == True
            assert result.output["_recursive_node_id"] == "negotiation_loop"


class TestWorkflowBuilder:
    """Test WorkflowBuilder recursive functionality."""
    
    def test_add_recursive_agent(self):
        """Test adding a recursive node with an agent."""
        builder = WorkflowBuilder("test_recursive_workflow")
        
        builder.add_recursive(
            "negotiation",
            agent_package="agents.negotiator",
            recursive_sources=["buyer", "seller"],
            convergence_condition="deal_agreed == True",
            max_iterations=20
        )
        
        assert len(builder.nodes) == 1
        node = builder.nodes[0]
        assert node.id == "negotiation"
        assert node.type == "recursive"
        assert node.agent_package == "agents.negotiator"
        assert node.recursive_sources == ["buyer", "seller"]
        assert node.convergence_condition == "deal_agreed == True"
        assert node.max_iterations == 20
    
    def test_add_recursive_workflow(self):
        """Test adding a recursive node with a workflow reference."""
        builder = WorkflowBuilder("test_recursive_workflow")
        
        builder.add_recursive(
            "conversation_loop",
            workflow_ref="conversation_workflow",
            recursive_sources=["agent1", "agent2"],
            convergence_condition="consensus_reached == True"
        )
        
        node = builder.nodes[0]
        assert node.workflow_ref == "conversation_workflow"
        assert node.agent_package is None


class TestWorkflowRecursiveExecution:
    """Test recursive flows in complete workflow execution."""
    
    @pytest.mark.asyncio 
    async def test_recursive_workflow_integration(self):
        """Test complete recursive workflow with mocked agents."""
        
        # Create a simple recursive workflow
        builder = WorkflowBuilder("agent_negotiation")
        
        # Add initial agents
        builder.add_agent("buyer", "test_agents.buyer")
        builder.add_agent("seller", "test_agents.seller")
        
        # Add recursive negotiation loop
        builder.add_recursive(
            "negotiation_loop",
            agent_package="test_agents.negotiator",
            recursive_sources=["buyer", "seller"],
            convergence_condition="deal_agreed == True",
            max_iterations=5
        )
        
        # Connect the workflow
        builder.connect("buyer", "negotiation_loop")
        builder.connect("seller", "negotiation_loop")
        
        # Test that the workflow builds successfully
        assert len(builder.nodes) == 3
        
        # Find the recursive node
        recursive_node = next(n for n in builder.nodes if n.type == "recursive")
        assert recursive_node.id == "negotiation_loop"
        assert recursive_node.recursive_sources == ["buyer", "seller"]
    
    def test_cycle_detection_allows_recursive_cycles(self):
        """Test that cycle detection allows properly configured recursive cycles."""
        from ice_core.graph.dependency_graph import DependencyGraph
        from ice_core.models import AgentNodeConfig
        
        # Create nodes with a recursive cycle
        buyer = AgentNodeConfig(id="buyer", type="agent", package="test.buyer")
        seller = AgentNodeConfig(id="seller", type="agent", package="test.seller") 
        
        recursive_node = RecursiveNodeConfig(
            id="negotiation",
            type="recursive",
            agent_package="test.negotiator",
            recursive_sources=["buyer", "seller"],
            dependencies=["buyer", "seller"]  # Creates cycle back to buyer/seller
        )
        
        # Add dependencies to create the cycle
        buyer.dependencies = ["negotiation"]  # buyer -> negotiation -> buyer (cycle)
        
        nodes = [buyer, seller, recursive_node]
        
        # This should NOT raise a CircularDependencyError
        graph = DependencyGraph(nodes)
        assert graph is not None
    
    def test_cycle_detection_blocks_invalid_cycles(self):
        """Test that cycle detection blocks improperly configured cycles."""
        from ice_core.graph.dependency_graph import DependencyGraph
        from ice_core.exceptions import CycleDetectionError as CircularDependencyError
        from ice_core.models import AgentNodeConfig
        
        # Create nodes with an invalid cycle (no recursive node)
        buyer = AgentNodeConfig(id="buyer", type="agent", package="test.buyer")
        seller = AgentNodeConfig(id="seller", type="agent", package="test.seller", dependencies=["buyer"])
        
        # Create cycle without recursive node
        buyer.dependencies = ["seller"]  # buyer -> seller -> buyer (invalid cycle)
        
        nodes = [buyer, seller]
        
        # This should raise a CircularDependencyError
        with pytest.raises(CircularDependencyError):
            DependencyGraph(nodes)


class TestRecursiveContextManagement:
    """Test context management in recursive flows."""
    
    @pytest.mark.asyncio
    async def test_context_preservation(self, sample_recursive_config, mock_workflow):
        """Test that context is preserved across recursive iterations."""
        ctx = {
            "_recursive_iteration": 2,
            "conversation_history": ["Hello", "Hi there"],
            "agreement_reached": False
        }
        
        with patch('ice_orchestrator.execution.executors.unified.agent_executor') as mock_agent_exec:
            mock_result = NodeExecutionResult(
                success=True,
                output={"response": "Let's negotiate"},
                execution_time=1.0,
                metadata=NodeMetadata(
                    node_id="negotiation_loop",
                    node_type="agent",
                    name="test_agent"
                )
            )
            mock_agent_exec.return_value = mock_result
            
            result = await recursive_executor(mock_workflow, sample_recursive_config, ctx)
            
            # Check that context is preserved and enhanced
            assert result.output["_recursive_iteration"] == 3
            assert "recursive_context" in result.output  # Default context_key
            context_data = result.output["recursive_context"]
            assert context_data["iteration"] == 3
            assert context_data["node_id"] == "negotiation_loop"


if __name__ == "__main__":
    pytest.main([__file__]) 