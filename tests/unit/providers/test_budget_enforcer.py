"""Tests for BudgetEnforcer."""

import pytest

from ice_sdk.providers.budget_enforcer import BudgetEnforcer


class TestBudgetEnforcer:
    """Test BudgetEnforcer functionality."""

    def test_basic_initialization(self):
        """Test basic initialization with default values."""
        enforcer = BudgetEnforcer()
        assert enforcer.llm_calls == 0
        assert enforcer.tool_execs == 0
        assert enforcer.total_cost == 0.0

    def test_custom_limits(self):
        """Test initialization with custom limits."""
        enforcer = BudgetEnforcer(
            org_budget_usd=10.0, max_llm_calls=5, max_tool_executions=8
        )
        assert enforcer.org_budget_usd == 10.0
        assert enforcer.max_llm_calls == 5
        assert enforcer.max_tool_executions == 8

    def test_llm_call_tracking(self):
        """Test LLM call tracking and budget enforcement."""
        enforcer = BudgetEnforcer(max_llm_calls=2)

        # First two calls should succeed
        enforcer.register_llm_call(cost=1.0)
        enforcer.register_llm_call(cost=2.0)
        assert enforcer.llm_calls == 2
        assert enforcer.total_cost == 3.0

        # Third call should trigger budget violation
        with pytest.raises(RuntimeError, match="LLM call budget exceeded"):
            enforcer.register_llm_call(cost=1.0)

    def test_tool_execution_tracking(self):
        """Test tool execution tracking and budget enforcement."""
        enforcer = BudgetEnforcer(max_tool_executions=3)

        # First three executions should succeed
        enforcer.register_tool_execution()
        enforcer.register_tool_execution()
        enforcer.register_tool_execution()
        assert enforcer.tool_execs == 3

        # Fourth execution should trigger budget violation
        with pytest.raises(RuntimeError, match="Tool execution budget exceeded"):
            enforcer.register_tool_execution()

    def test_cost_budget_enforcement(self):
        """Test cost budget enforcement."""
        enforcer = BudgetEnforcer(org_budget_usd=5.0)

        # First few calls within budget
        enforcer.register_llm_call(cost=1.0)
        enforcer.register_llm_call(cost=2.0)
        assert enforcer.total_cost == 3.0

        # Call that exceeds budget
        with pytest.raises(RuntimeError, match="Cost budget exceeded"):
            enforcer.register_llm_call(cost=3.0)

    def test_fail_open_behavior(self, monkeypatch):
        """Test fail-open behavior in development mode."""
        # Set environment to development mode with fail-open
        monkeypatch.setenv("ICE_RUNTIME_MODE", "development")
        monkeypatch.setenv("BUDGET_FAIL_OPEN", "true")

        enforcer = BudgetEnforcer(max_llm_calls=1)
        enforcer.register_llm_call()  # First call

        # Second call should log warning but not raise
        enforcer.register_llm_call()
        assert enforcer.llm_calls == 2  # Should have continued

    def test_fail_closed_behavior(self, monkeypatch):
        """Test fail-closed behavior in production mode."""
        # Set environment to production mode
        monkeypatch.setenv("ICE_RUNTIME_MODE", "production")

        enforcer = BudgetEnforcer(max_llm_calls=1)
        enforcer.register_llm_call()  # First call

        # Second call should raise exception
        with pytest.raises(RuntimeError, match="LLM call budget exceeded"):
            enforcer.register_llm_call()

    def test_environment_variable_limits(self, monkeypatch):
        """Test that environment variables are respected."""
        monkeypatch.setenv("ICE_MAX_LLM_CALLS", "3")
        monkeypatch.setenv("ICE_MAX_TOOL_EXECUTIONS", "5")
        monkeypatch.setenv("ORG_BUDGET_USD", "10.0")

        enforcer = BudgetEnforcer()
        assert enforcer.max_llm_calls == 3
        assert enforcer.max_tool_executions == 5
        assert enforcer.org_budget_usd == 10.0

    def test_get_status(self):
        """Test get_status method returns correct information."""
        enforcer = BudgetEnforcer(
            org_budget_usd=10.0, max_llm_calls=5, max_tool_executions=8
        )

        enforcer.register_llm_call(cost=2.0)
        enforcer.register_tool_execution()

        status = enforcer.get_status()
        assert status["llm_calls"] == 1
        assert status["tool_executions"] == 1
        assert status["total_cost"] == 2.0
        assert status["max_llm_calls"] == 5
        assert status["max_tool_executions"] == 8
        assert status["org_budget_usd"] == 10.0
