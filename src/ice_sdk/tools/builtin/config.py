"""
⚙️ Built-in Tools Configuration
==============================

Configuration system for built-in tools - makes them optional but easy to enable.

Key Features:
- Environment variable control
- Programmatic enabling/disabling
- Selective tool activation
- One-line "enable everything" functions
"""

import os
from typing import Dict, List, Optional, Set
from dataclasses import dataclass


@dataclass
class BuiltinToolsConfig:
    """Configuration for built-in tools system."""
    
    # Auto-registration controls
    auto_register_tools: bool = False
    auto_register_hooks: bool = False
    
    # Selective tool enablement
    enabled_tools: Set[str] = None
    enabled_hooks: Set[str] = None
    
    # Execution controls
    auto_execute_hooks: bool = False
    hook_execution_timeout: float = 30.0
    
    # Convenience flags
    enable_mermaid_generation: bool = False
    enable_performance_analysis: bool = False
    enable_executive_summaries: bool = False
    
    def __post_init__(self):
        if self.enabled_tools is None:
            self.enabled_tools = set()
        if self.enabled_hooks is None:
            self.enabled_hooks = set()


# Global configuration instance
_config = BuiltinToolsConfig()


def get_config() -> BuiltinToolsConfig:
    """Get the current built-in tools configuration."""
    return _config


def load_config_from_env() -> BuiltinToolsConfig:
    """Load configuration from environment variables."""
    global _config
    
    # Auto-registration from env
    _config.auto_register_tools = _env_bool("ICEOS_AUTO_REGISTER_BUILTIN_TOOLS", False)
    _config.auto_register_hooks = _env_bool("ICEOS_AUTO_REGISTER_BUILTIN_HOOKS", False)
    
    # Auto-execution from env
    _config.auto_execute_hooks = _env_bool("ICEOS_AUTO_EXECUTE_HOOKS", False)
    
    # Selective enablement from env
    enabled_tools_str = os.getenv("ICEOS_ENABLED_BUILTIN_TOOLS", "")
    if enabled_tools_str:
        _config.enabled_tools = set(enabled_tools_str.split(","))
    
    enabled_hooks_str = os.getenv("ICEOS_ENABLED_BUILTIN_HOOKS", "")
    if enabled_hooks_str:
        _config.enabled_hooks = set(enabled_hooks_str.split(","))
    
    # Convenience flags from env
    _config.enable_mermaid_generation = _env_bool("ICEOS_ENABLE_MERMAID", False)
    _config.enable_performance_analysis = _env_bool("ICEOS_ENABLE_PERFORMANCE", False)
    _config.enable_executive_summaries = _env_bool("ICEOS_ENABLE_SUMMARIES", False)
    
    # Timeout configuration
    timeout_str = os.getenv("ICEOS_HOOK_TIMEOUT", "30.0")
    try:
        _config.hook_execution_timeout = float(timeout_str)
    except ValueError:
        _config.hook_execution_timeout = 30.0
    
    return _config


def _env_bool(key: str, default: bool = False) -> bool:
    """Parse boolean from environment variable."""
    value = os.getenv(key, "").lower()
    if value in ("true", "1", "yes", "on"):
        return True
    elif value in ("false", "0", "no", "off"):
        return False
    else:
        return default


# =============================================================================
# Easy Enablement Functions
# =============================================================================

def enable_everything() -> None:
    """🚀 Enable ALL built-in tools and features (one-liner activation)."""
    global _config
    _config.auto_register_tools = True
    _config.auto_register_hooks = True
    _config.auto_execute_hooks = True
    _config.enable_mermaid_generation = True
    _config.enable_performance_analysis = True
    _config.enable_executive_summaries = True
    _config.enabled_tools = {"post_execution_mermaid", "workflow_analyzer", "execution_summarizer", "performance_profiler"}
    _config.enabled_hooks = {"mermaid_generation", "execution_summary", "performance_analysis", "comprehensive_profiling"}
    
    # Trigger registration if not already done
    _register_enabled_tools()
    _register_enabled_hooks()


def enable_mermaid_only() -> None:
    """🎨 Enable only Mermaid diagram generation (minimal setup)."""
    global _config
    _config.auto_register_tools = True
    _config.auto_execute_hooks = True
    _config.enable_mermaid_generation = True
    _config.enabled_tools.add("post_execution_mermaid")
    _config.enabled_hooks.add("mermaid_generation")
    
    _register_enabled_tools()
    _register_enabled_hooks()


def enable_performance_suite() -> None:
    """⚡ Enable performance analysis tools (performance focus)."""
    global _config
    _config.auto_register_tools = True
    _config.auto_execute_hooks = True
    _config.enable_performance_analysis = True
    _config.enabled_tools.update({"workflow_analyzer", "performance_profiler"})
    _config.enabled_hooks.update({"performance_analysis", "comprehensive_profiling"})
    
    _register_enabled_tools()
    _register_enabled_hooks()


def enable_executive_suite() -> None:
    """📋 Enable executive reporting tools (business focus)."""
    global _config
    _config.auto_register_tools = True
    _config.auto_execute_hooks = True
    _config.enable_executive_summaries = True
    _config.enabled_tools.update({"execution_summarizer", "workflow_analyzer"})
    _config.enabled_hooks.update({"execution_summary", "performance_analysis"})
    
    _register_enabled_tools()
    _register_enabled_hooks()


def enable_specific_tools(tool_names: List[str], auto_execute: bool = True) -> None:
    """🔧 Enable specific tools by name."""
    global _config
    _config.auto_register_tools = True
    _config.auto_execute_hooks = auto_execute
    _config.enabled_tools.update(tool_names)
    
    # Map tools to hooks
    tool_to_hook = {
        "post_execution_mermaid": "mermaid_generation",
        "workflow_analyzer": "performance_analysis", 
        "execution_summarizer": "execution_summary",
        "performance_profiler": "comprehensive_profiling"
    }
    
    for tool in tool_names:
        if tool in tool_to_hook:
            _config.enabled_hooks.add(tool_to_hook[tool])
    
    _register_enabled_tools()
    if auto_execute:
        _register_enabled_hooks()


def disable_everything() -> None:
    """🛑 Disable all built-in tools and hooks."""
    global _config
    _config.auto_register_tools = False
    _config.auto_register_hooks = False
    _config.auto_execute_hooks = False
    _config.enable_mermaid_generation = False
    _config.enable_performance_analysis = False
    _config.enable_executive_summaries = False
    _config.enabled_tools.clear()
    _config.enabled_hooks.clear()
    
    # Disable hook manager
    from .auto_workflow_hooks import disable_auto_analysis
    disable_auto_analysis()


def is_tool_enabled(tool_name: str) -> bool:
    """Check if a specific tool is enabled."""
    return tool_name in _config.enabled_tools


def is_hook_enabled(hook_name: str) -> bool:
    """Check if a specific hook is enabled."""
    return hook_name in _config.enabled_hooks


def get_enabled_tools() -> List[str]:
    """Get list of enabled tool names."""
    return list(_config.enabled_tools)


def get_enabled_hooks() -> List[str]:
    """Get list of enabled hook names."""
    return list(_config.enabled_hooks)


# =============================================================================
# Internal Registration Functions
# =============================================================================

def _register_enabled_tools() -> None:
    """Register only the enabled tools."""
    if not _config.auto_register_tools:
        return
    
    from ice_core.models import NodeType
    from ice_core.unified_registry import registry
    
    # Tool mapping
    available_tools = {
        "post_execution_mermaid": lambda: __import__("ice_sdk.tools.builtin.post_execution_mermaid", fromlist=["PostExecutionMermaidTool"]).PostExecutionMermaidTool(),
        "workflow_analyzer": lambda: __import__("ice_sdk.tools.builtin.workflow_analyzer", fromlist=["WorkflowAnalyzerTool"]).WorkflowAnalyzerTool(),
        "execution_summarizer": lambda: __import__("ice_sdk.tools.builtin.execution_summarizer", fromlist=["ExecutionSummarizerTool"]).ExecutionSummarizerTool(),
        "performance_profiler": lambda: __import__("ice_sdk.tools.builtin.performance_profiler", fromlist=["PerformanceProfilerTool"]).PerformanceProfilerTool(),
    }
    
    for tool_name in _config.enabled_tools:
        if tool_name in available_tools:
            try:
                tool_instance = available_tools[tool_name]()
                registry.register_instance(NodeType.TOOL, tool_name, tool_instance)
            except Exception:
                # Ignore re-registration errors
                pass


def _register_enabled_hooks() -> None:
    """Register only the enabled hooks."""
    if not _config.auto_register_hooks:
        return
    
    from .auto_workflow_hooks import global_hook_manager
    
    # Hook mapping
    available_hooks = {
        "mermaid_generation": lambda: __import__("ice_sdk.tools.builtin.auto_workflow_hooks", fromlist=["MermaidGenerationHook"]).MermaidGenerationHook(),
        "execution_summary": lambda: __import__("ice_sdk.tools.builtin.auto_workflow_hooks", fromlist=["ExecutionSummaryHook"]).ExecutionSummaryHook(),
        "performance_analysis": lambda: __import__("ice_sdk.tools.builtin.auto_workflow_hooks", fromlist=["PerformanceAnalysisHook"]).PerformanceAnalysisHook(),
        "comprehensive_profiling": lambda: __import__("ice_sdk.tools.builtin.auto_workflow_hooks", fromlist=["ComprehensiveProfilingHook"]).ComprehensiveProfilingHook(),
    }
    
    # Clear existing hooks and register only enabled ones
    global_hook_manager.hooks.clear()
    
    for hook_name in _config.enabled_hooks:
        if hook_name in available_hooks:
            try:
                hook_instance = available_hooks[hook_name]()
                global_hook_manager.register_hook(hook_instance)
            except Exception:
                # Ignore registration errors
                pass
    
    # Enable hook execution if configured
    if _config.auto_execute_hooks:
        from .auto_workflow_hooks import enable_auto_analysis
        enable_auto_analysis()


# Load configuration from environment on import
load_config_from_env()


# =============================================================================
# Public API
# =============================================================================

__all__ = [
    # Configuration
    "BuiltinToolsConfig",
    "get_config",
    "load_config_from_env",
    
    # Easy enablement functions
    "enable_everything",
    "enable_mermaid_only", 
    "enable_performance_suite",
    "enable_executive_suite",
    "enable_specific_tools",
    "disable_everything",
    
    # Status functions
    "is_tool_enabled",
    "is_hook_enabled", 
    "get_enabled_tools",
    "get_enabled_hooks",
] 