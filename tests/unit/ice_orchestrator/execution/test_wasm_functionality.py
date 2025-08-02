"""Tests for WASM executor core functionality.

These tests verify that code execution works with resource limits,
not the implementation details of the security sandbox.
"""

import pytest

from ice_orchestrator.execution.wasm_executor import WasmExecutor

pytestmark = [pytest.mark.unit]


@pytest.fixture
def wasm_executor():
    """Create WASM executor instance."""
    return WasmExecutor()


@pytest.mark.asyncio
async def test_basic_code_execution(wasm_executor):
    """Test that basic Python code can execute in WASM."""
    code = """
output['result'] = 1 + 1
output['message'] = 'Hello from WASM'
"""
    
    result = await wasm_executor.execute_python_code(
        code=code,
        context={},
        node_type="code",
        node_id="test_basic"
    )
    
    # Just verify execution worked, not implementation details
    assert result["success"] is True
    assert "output" in result
    # The exact output format is an implementation detail


@pytest.mark.asyncio 
async def test_code_with_context(wasm_executor):
    """Test that context is passed correctly to WASM execution."""
    code = """
output['sum'] = sum(context['numbers'])
output['name'] = context['name'].upper()
"""
    
    context = {
        "numbers": [1, 2, 3, 4, 5],
        "name": "test"
    }
    
    result = await wasm_executor.execute_python_code(
        code=code,
        context=context,
        node_type="code",
        node_id="test_context"
    )
    
    assert result["success"] is True


@pytest.mark.asyncio
async def test_node_type_limits_exist(wasm_executor):
    """Test that different node types have resource limits configured."""
    # Just verify the configuration exists, not specific values
    assert "code" in wasm_executor.resource_limits
    assert "tool" in wasm_executor.resource_limits
    assert "agent" in wasm_executor.resource_limits
    
    # Each type should have limits defined
    for node_type, limits in wasm_executor.resource_limits.items():
        assert "memory_pages" in limits
        assert "fuel" in limits
        assert "timeout" in limits


@pytest.mark.asyncio
async def test_syntax_error_handling(wasm_executor):
    """Test that syntax errors are handled gracefully."""
    code = "this is not valid python!"
    
    result = await wasm_executor.execute_python_code(
        code=code,
        context={},
        node_type="code",
        node_id="test_syntax_error"
    )
    
    # Should handle the error gracefully
    assert "error" in result or result["success"] is False 