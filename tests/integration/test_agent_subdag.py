"""Integration tests for agent-generated SubDAG execution."""

import pytest
from ice_core.models.node_models import NodeConfig
from ice_core.models.workflow import SubDAGResult

from ice_orchestrator import Workflow


@pytest.mark.asyncio
async def test_nested_workflow_execution():
    """Test that a workflow can execute a SubDAGResult from an agent."""
    # Create a simple workflow
    workflow = Workflow(nodes=[], name="test_workflow")

    # Create a mock SubDAG result
    subdag_data = {
        "nodes": [
            {"id": "test_node", "type": "echo", "name": "Test Node", "dependencies": []}
        ],
        "name": "sub_workflow",
        "version": "1.0.0",
    }

    subdag_result = SubDAGResult(
        workflow_data=subdag_data,
        idempotency_key="test_key_1234567890123456789012345678901234567890123456789012345678901234",
    )

    # Mock the executor to return SubDAGResult
    class MockExecutor:
        async def execute_node(self, node_id: str, input_data: dict):
            from ice_core.models.node_models import NodeExecutionResult

            return NodeExecutionResult(
                success=True, output=subdag_result, metadata=None
            )

    workflow._executor = MockExecutor()

    # Test that the workflow can handle SubDAG execution
    result = await workflow.execute_node("test_node", {})

    assert result.success
    # The result should be from the executed subDAG, not the original SubDAGResult


@pytest.mark.asyncio
async def test_workflow_protocol_compliance():
    """Test that Workflow implements WorkflowProto correctly."""
    from ice_core.models.workflow import WorkflowProto

    workflow = Workflow(nodes=[], name="test")

    # Test protocol compliance
    assert isinstance(workflow, WorkflowProto)

    # Test add_node method
    node_config = NodeConfig(id="test", type="echo", name="Test")
    node_id = workflow.add_node(node_config)
    assert node_id == "node_0"

    # Test to_dict and from_dict
    workflow_dict = workflow.to_dict()
    assert "nodes" in workflow_dict
    assert "name" in workflow_dict

    # Test from_dict
    new_workflow = Workflow.from_dict(workflow_dict)
    assert new_workflow.name == workflow.name
    assert len(new_workflow.nodes) == len(workflow.nodes)

    # Test validate method
    workflow.validate()  # Should not raise


@pytest.mark.asyncio
async def test_subdag_metrics():
    """Test that SubDAG execution time is properly tracked."""
    from ice_orchestrator.execution.metrics import SubDAGMetrics

    # Reset metrics
    SubDAGMetrics.SUB_DAG_EXECUTION_TIME = 0.0

    # Create a workflow that will trigger SubDAG execution
    workflow = Workflow(nodes=[], name="test_workflow")

    # Mock executor that returns SubDAGResult
    class MockExecutor:
        async def execute_node(self, node_id: str, input_data: dict):
            from ice_core.models.node_models import NodeExecutionResult
            from ice_core.models.workflow import SubDAGResult

            subdag_result = SubDAGResult(
                workflow_data={"nodes": [], "name": "sub", "version": "1.0.0"},
                idempotency_key="test_key_1234567890123456789012345678901234567890123456789012345678901234",
            )

            return NodeExecutionResult(
                success=True, output=subdag_result, metadata=None
            )

    workflow._executor = MockExecutor()

    # Execute and check metrics
    await workflow.execute_node("test", {})

    # Metrics should be updated
    assert SubDAGMetrics.get_total_time() > 0.0
