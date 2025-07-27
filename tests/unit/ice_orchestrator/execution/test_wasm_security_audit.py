"""Security audit tests for WASM sandboxing implementation.

These tests validate that the WASM sandboxing effectively prevents
security violations and enforces resource limits.
"""

import asyncio
import pytest
from datetime import datetime
from unittest.mock import Mock, patch

from ice_orchestrator.execution.wasm_executor import WasmExecutor, execute_node_with_wasm
from ice_orchestrator.execution.wasm_resource_monitor import (
    WasmResourceMonitor, ResourceLimits, SecurityViolation
)
from ice_core.models import NodeExecutionResult, NodeMetadata


class TestWasmSecurityAudit:
    """Comprehensive security audit tests for WASM execution."""
    
    @pytest.fixture
    def wasm_executor(self):
        """Create a WASM executor for testing."""
        return WasmExecutor()
    
    @pytest.fixture
    def resource_monitor(self):
        """Create a resource monitor for testing."""
        return WasmResourceMonitor()
    
    @pytest.mark.asyncio
    async def test_memory_limit_enforcement(self, wasm_executor):
        """Test that memory limits are enforced."""
        # Code that tries to allocate excessive memory
        memory_bomb_code = """
# Attempt to allocate large amount of memory
large_list = []
for i in range(1000000):  # Try to create large list
    large_list.append('x' * 1000)  # 1KB per item = 1GB total
output['result'] = len(large_list)
"""
        
        result = await wasm_executor.execute_python_code(
            code=memory_bomb_code,
            context={},
            node_type="code",
            node_id="memory_test"
        )
        
        # Should fail due to memory limits
        assert not result["success"] or result.get("memory_used_pages", 0) <= 512
    
    @pytest.mark.asyncio
    async def test_cpu_limit_enforcement(self, wasm_executor):
        """Test that CPU limits are enforced."""
        # Code that tries to consume excessive CPU
        cpu_bomb_code = """
# Infinite loop to consume CPU
count = 0
while count < 10000000:  # Large iteration count
    count += 1
    # Do some computation
    x = count * count / (count + 1)
output['result'] = count
"""
        
        result = await wasm_executor.execute_python_code(
            code=cpu_bomb_code,
            context={},
            node_type="code",
            node_id="cpu_test"
        )
        
        # Should fail due to CPU limits or timeout
        assert not result["success"] or result.get("execution_time", 0) <= 15  # Allow some grace
    
    @pytest.mark.asyncio
    async def test_import_restriction_enforcement(self, wasm_executor):
        """Test that dangerous imports are blocked."""
        dangerous_import_code = """
# Try to import dangerous modules
import os  # Should be blocked
import sys  # Should be blocked  
import subprocess  # Should be blocked
import socket  # Should be blocked

output['result'] = 'dangerous imports succeeded'
"""
        
        result = await wasm_executor.execute_python_code(
            code=dangerous_import_code,
            context={},
            node_type="code",
            allowed_imports=[],  # No imports allowed
            node_id="import_test"
        )
        
        # Should fail due to import restrictions
        assert not result["success"]
        assert "import" in result.get("error", "").lower()
    
    @pytest.mark.asyncio
    async def test_file_system_access_blocked(self, wasm_executor):
        """Test that file system access is blocked."""
        file_access_code = """
# Try to access file system
try:
    with open('/etc/passwd', 'r') as f:
        content = f.read()
    output['result'] = 'file access succeeded'
except Exception as e:
    output['error'] = str(e)
"""
        
        result = await wasm_executor.execute_python_code(
            code=file_access_code,
            context={},
            node_type="code",
            node_id="file_test"
        )
        
        # Should fail - either execution fails or open() is not available
        if result["success"]:
            # If execution succeeded, should have error about missing open()
            assert "error" in result.get("output", {})
    
    @pytest.mark.asyncio
    async def test_network_access_blocked(self, wasm_executor):
        """Test that network access is blocked."""
        network_code = """
# Try to make network requests
try:
    import urllib.request
    response = urllib.request.urlopen('http://example.com')
    output['result'] = 'network access succeeded'
except Exception as e:
    output['error'] = str(e)
"""
        
        result = await wasm_executor.execute_python_code(
            code=network_code,
            context={},
            node_type="code",
            allowed_imports=["urllib.request"],  # Even if allowed, should be blocked
            node_id="network_test"
        )
        
        # Should fail due to network restrictions
        if result["success"]:
            # Should have error about network access
            assert "error" in result.get("output", {})
    
    @pytest.mark.asyncio
    async def test_eval_exec_blocked(self, wasm_executor):
        """Test that eval() and exec() are blocked."""
        eval_code = """
# Try to use eval and exec
try:
    result1 = eval('1 + 1')
    exec('x = 42')
    output['result'] = 'eval/exec succeeded'
except Exception as e:
    output['error'] = str(e)
"""
        
        result = await wasm_executor.execute_python_code(
            code=eval_code,
            context={},
            node_type="code",
            node_id="eval_test"
        )
        
        # Should fail - eval/exec should not be available
        if result["success"]:
            assert "error" in result.get("output", {})
    
    @pytest.mark.asyncio
    async def test_timeout_enforcement(self, wasm_executor):
        """Test that execution timeouts are enforced."""
        infinite_loop_code = """
# Infinite loop
while True:
    pass
"""
        
        result = await wasm_executor.execute_python_code(
            code=infinite_loop_code,
            context={},
            node_type="code",
            custom_limits={"timeout": 1},  # 1 second timeout
            node_id="timeout_test"
        )
        
        # Should fail due to timeout
        assert not result["success"]
        assert "timeout" in result.get("error", "").lower()
    
    @pytest.mark.asyncio
    async def test_context_isolation(self, wasm_executor):
        """Test that executions are isolated from each other."""
        # First execution sets a variable
        code1 = """
global_var = 'secret_data'
output['result'] = 'first execution'
"""
        
        # Second execution tries to access the variable
        code2 = """
try:
    result = global_var  # Should not be available
    output['result'] = f'accessed: {result}'
except NameError:
    output['result'] = 'isolated correctly'
"""
        
        result1 = await wasm_executor.execute_python_code(
            code=code1,
            context={},
            node_type="code",
            node_id="isolation_test_1"
        )
        
        result2 = await wasm_executor.execute_python_code(
            code=code2,
            context={},
            node_type="code",
            node_id="isolation_test_2"
        )
        
        # Both should succeed but be isolated
        assert result1["success"]
        assert result2["success"]
        assert result2["output"]["result"]["result"] == "isolated correctly"
    
    @pytest.mark.asyncio
    async def test_resource_monitoring_integration(self, resource_monitor):
        """Test integration with resource monitoring."""
        violations_detected = []
        
        def violation_callback(violation: SecurityViolation):
            violations_detected.append(violation)
        
        resource_monitor.add_violation_callback(violation_callback)
        
        # Create a mock execution that violates limits
        async def mock_execution():
            # Simulate execution result with violations
            return {
                "success": True,
                "output": {
                    "memory_used_pages": 2000,  # Exceeds limit
                    "fuel_consumed": 500000,    # Within limit
                    "result": "test"
                }
            }
        
        limits = ResourceLimits(
            memory_pages=1000,
            fuel=1000000,
            timeout=5.0
        )
        
        result, usage = await resource_monitor.monitor_execution(
            node_id="test_node",
            node_type="test",
            limits=limits,
            execution_func=mock_execution
        )
        
        # Should detect memory violation
        assert len(violations_detected) == 1
        assert violations_detected[0].violation_type == "memory_limit"
        assert violations_detected[0].severity == "high"
    
    @pytest.mark.asyncio
    async def test_safe_imports_allowed(self, wasm_executor):
        """Test that safe imports are properly allowed."""
        safe_code = """
import json
import math
import datetime

data = {'number': 42}
json_str = json.dumps(data)
sqrt_val = math.sqrt(16)
now = datetime.datetime.now()

output['result'] = {
    'json_works': json_str,
    'math_works': sqrt_val,
    'datetime_works': str(now)
}
"""
        
        result = await wasm_executor.execute_python_code(
            code=safe_code,
            context={},
            node_type="code",
            allowed_imports=["json", "math", "datetime"],
            node_id="safe_imports_test"
        )
        
        # Should succeed with safe imports
        assert result["success"]
        output = result["output"]["result"]
        assert "json_works" in output
        assert "math_works" in output  
        assert "datetime_works" in output
    
    @pytest.mark.asyncio
    async def test_node_type_resource_limits(self, wasm_executor):
        """Test that different node types have appropriate resource limits."""
        simple_code = "output['result'] = 'test'"
        
        # Test code node limits (should be restrictive)
        code_result = await wasm_executor.execute_python_code(
            code=simple_code,
            context={},
            node_type="code",
            node_id="code_limits_test"
        )
        
        # Test agent node limits (should be more generous)
        agent_result = await wasm_executor.execute_python_code(
            code=simple_code,
            context={},
            node_type="agent", 
            node_id="agent_limits_test"
        )
        
        # Both should succeed but agent should have higher limits
        assert code_result["success"]
        assert agent_result["success"]
        
        # Verify limits are different (check the WasmExecutor resource_limits)
        executor = wasm_executor
        code_limits = executor.resource_limits["code"]
        agent_limits = executor.resource_limits["agent"]
        
        assert agent_limits["memory_pages"] > code_limits["memory_pages"]
        assert agent_limits["fuel"] > code_limits["fuel"]
        assert agent_limits["timeout"] > code_limits["timeout"]
    
    @pytest.mark.asyncio
    async def test_malicious_code_patterns(self, wasm_executor):
        """Test detection of common malicious code patterns."""
        malicious_patterns = [
            # Resource exhaustion
            "for i in range(999999999): pass",
            # Memory bomb
            "'x' * (1024 * 1024 * 1024)",
            # Recursive function bomb
            "def bomb(): bomb()\nbomb()",
        ]
        
        for i, pattern in enumerate(malicious_patterns):
            result = await wasm_executor.execute_python_code(
                code=f"{pattern}\noutput['result'] = 'completed'",
                context={},
                node_type="code",
                node_id=f"malicious_test_{i}"
            )
            
            # Should fail or be limited
            assert not result["success"] or result.get("execution_time", 0) < 15
    
    @pytest.mark.asyncio
    async def test_secure_context_handling(self, wasm_executor):
        """Test that context data is safely handled."""
        sensitive_context = {
            "api_key": "secret123",
            "password": "admin123", 
            "private_data": {"ssn": "123-45-6789"}
        }
        
        context_access_code = """
# Access context data safely
api_key = inputs.get('api_key', 'not_found')
password = inputs.get('password', 'not_found') 
private_data = inputs.get('private_data', {})

output['result'] = {
    'api_key_accessed': api_key != 'not_found',
    'password_accessed': password != 'not_found',
    'private_data_accessed': len(private_data) > 0
}

# Try to modify context (should not affect original)
inputs['api_key'] = 'modified'
"""
        
        result = await wasm_executor.execute_python_code(
            code=context_access_code,
            context=sensitive_context,
            node_type="code",
            node_id="context_test"
        )
        
        # Should succeed and access context safely
        assert result["success"]
        
        # Original context should be unchanged
        assert sensitive_context["api_key"] == "secret123"
        assert sensitive_context["password"] == "admin123"


class TestSecurityAuditReporting:
    """Test security audit reporting and monitoring."""
    
    @pytest.mark.asyncio
    async def test_violation_reporting(self):
        """Test that security violations are properly reported."""
        monitor = WasmResourceMonitor()
        violations_logged = []
        
        def capture_violation(violation: SecurityViolation):
            violations_logged.append(violation)
        
        monitor.add_violation_callback(capture_violation)
        
        # Create violation
        violation = SecurityViolation(
            violation_type="test_violation",
            description="Test security violation",
            severity="high",
            timestamp=datetime.utcnow(),
            node_id="test_node",
            node_type="test"
        )
        
        await monitor._handle_violation(violation)
        
        # Should be captured by callback
        assert len(violations_logged) == 1
        assert violations_logged[0].violation_type == "test_violation"
    
    @pytest.mark.asyncio
    async def test_execution_tracking(self):
        """Test that active executions are tracked."""
        monitor = WasmResourceMonitor()
        
        # Mock execution function
        async def mock_execution():
            await asyncio.sleep(0.1)
            return {"success": True, "output": {}}
        
        limits = ResourceLimits(
            memory_pages=100,
            fuel=1000,
            timeout=1.0
        )
        
        # Start execution (should be tracked)
        task = asyncio.create_task(
            monitor.monitor_execution(
                node_id="tracked_node",
                node_type="test",
                limits=limits,
                execution_func=mock_execution
            )
        )
        
        # Allow execution to start
        await asyncio.sleep(0.05)
        
        # Should be in active executions
        active = monitor.get_active_executions()
        assert len(active) >= 1
        
        # Complete execution
        await task
        
        # Should be removed from active executions
        active_after = monitor.get_active_executions()
        assert len(active_after) == 0
    
    def test_resource_limits_configuration(self):
        """Test that resource limits are properly configured."""
        executor = WasmExecutor()
        
        # Verify all node types have limits
        required_node_types = ["code", "tool", "agent", "llm", "condition", "loop", "workflow"]
        
        for node_type in required_node_types:
            assert node_type in executor.resource_limits
            limits = executor.resource_limits[node_type]
            
            # All limits should be positive
            assert limits["memory_pages"] > 0
            assert limits["fuel"] > 0
            assert limits["timeout"] > 0
            
        # Verify hierarchy: agent > tool > code for resources
        assert executor.resource_limits["agent"]["memory_pages"] > executor.resource_limits["tool"]["memory_pages"]
        assert executor.resource_limits["tool"]["memory_pages"] > executor.resource_limits["code"]["memory_pages"]
    
    def test_safe_imports_configuration(self):
        """Test that safe imports are properly configured."""
        executor = WasmExecutor()
        
        # Verify safe imports include standard library modules
        expected_safe = ["json", "math", "datetime", "re", "uuid"]
        
        for module in expected_safe:
            assert module in executor.safe_imports
        
        # Verify dangerous modules are not in safe imports
        dangerous = ["os", "sys", "subprocess", "socket", "urllib", "__import__"]
        
        for module in dangerous:
            assert module not in executor.safe_imports


@pytest.mark.integration
class TestWasmSecurityIntegration:
    """Integration tests for WASM security with real node execution."""
    
    @pytest.mark.asyncio
    async def test_end_to_end_security(self):
        """Test end-to-end security with actual node execution."""
        
        # Test code execution with security
        result = await execute_node_with_wasm(
            node_type="code",
            code="output['result'] = sum(range(100))",
            context={},
            node_id="integration_test"
        )
        
        assert result.success
        assert result.metadata.sandboxed
        assert result.execution_time > 0
    
    @pytest.mark.asyncio 
    async def test_security_under_load(self):
        """Test security enforcement under concurrent load."""
        
        async def run_secure_execution(i):
            return await execute_node_with_wasm(
                node_type="code",
                code=f"output['result'] = {i} * 2",
                context={},
                node_id=f"load_test_{i}"
            )
        
        # Run multiple concurrent executions
        tasks = [run_secure_execution(i) for i in range(10)]
        results = await asyncio.gather(*tasks)
        
        # All should succeed and be secure
        for result in results:
            assert result.success
            assert result.metadata.sandboxed 