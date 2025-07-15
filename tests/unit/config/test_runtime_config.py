"""Tests for RuntimeConfig."""

from ice_sdk.config import RuntimeConfig


class TestRuntimeConfig:
    """Test RuntimeConfig functionality."""

    def test_default_values(self):
        """Test default configuration values."""
        config = RuntimeConfig()
        assert config.max_tokens is None
        assert config.max_depth is None
        assert config.org_budget_usd is None
        assert config.runtime_mode == "production"
        assert config.budget_fail_open is True

    def test_from_env_with_values(self, monkeypatch):
        """Test loading configuration from environment variables."""
        monkeypatch.setenv("ICE_MAX_TOKENS", "1000")
        monkeypatch.setenv("ICE_MAX_DEPTH", "10")
        monkeypatch.setenv("ORG_BUDGET_USD", "50.0")
        monkeypatch.setenv("ICE_RUNTIME_MODE", "development")
        monkeypatch.setenv("BUDGET_FAIL_OPEN", "false")

        config = RuntimeConfig.from_env()
        assert config.max_tokens == 1000
        assert config.max_depth == 10
        assert config.org_budget_usd == 50.0
        assert config.runtime_mode == "development"
        assert config.budget_fail_open is False

    def test_from_env_without_values(self, monkeypatch):
        """Test loading configuration when env vars are not set."""
        # Clear any existing env vars
        monkeypatch.delenv("ICE_MAX_TOKENS", raising=False)
        monkeypatch.delenv("ICE_MAX_DEPTH", raising=False)
        monkeypatch.delenv("ORG_BUDGET_USD", raising=False)
        monkeypatch.delenv("ICE_RUNTIME_MODE", raising=False)
        monkeypatch.delenv("BUDGET_FAIL_OPEN", raising=False)

        config = RuntimeConfig.from_env()
        assert config.max_tokens is None
        assert config.max_depth is None
        assert config.org_budget_usd is None
        assert config.runtime_mode == "production"
        assert config.budget_fail_open is True

    def test_budget_fail_open_parsing(self, monkeypatch):
        """Test parsing of BUDGET_FAIL_OPEN environment variable."""
        # Test true values
        for value in ["true", "True", "TRUE", "1", "yes"]:
            monkeypatch.setenv("BUDGET_FAIL_OPEN", value)
            config = RuntimeConfig.from_env()
            print(f"Value: '{value}' -> budget_fail_open: {config.budget_fail_open}")
            assert config.budget_fail_open is True

        # Test false values
        for value in ["false", "False", "FALSE", "0", "no"]:
            monkeypatch.setenv("BUDGET_FAIL_OPEN", value)
            config = RuntimeConfig.from_env()
            print(f"Value: '{value}' -> budget_fail_open: {config.budget_fail_open}")
            assert config.budget_fail_open is False

    def test_global_runtime_config_reload(self, monkeypatch):
        """Test that the global runtime_config can be reloaded."""
        import importlib

        import ice_sdk.config

        # Set environment variable
        monkeypatch.setenv("ICE_MAX_TOKENS", "5000")

        # Reload the module to pick up the new environment variable
        importlib.reload(ice_sdk.config)

        # Check that the global config was updated
        assert ice_sdk.config.runtime_config.max_tokens == 5000
