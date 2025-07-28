"""
🚀 Built-in Tools - Optional Comprehensive Tool Suite
====================================================

Optional tools that can be easily enabled for workflows and analysis.

**🎯 EASY ENABLEMENT OPTIONS:**

```python
# 🚀 Enable EVERYTHING (one-liner)
from ice_sdk.tools.builtin import enable_everything
enable_everything()

# 🎨 Enable only Mermaid diagrams
from ice_sdk.tools.builtin import enable_mermaid_only
enable_mermaid_only()

# ⚡ Enable performance suite
from ice_sdk.tools.builtin import enable_performance_suite
enable_performance_suite()

# 📋 Enable executive reporting
from ice_sdk.tools.builtin import enable_executive_suite
enable_executive_suite()

# 🔧 Enable specific tools
from ice_sdk.tools.builtin import enable_specific_tools
enable_specific_tools(["post_execution_mermaid", "workflow_analyzer"])
```

**Environment Variable Control:**
- `ICEOS_AUTO_REGISTER_BUILTIN_TOOLS=true` - Auto-register tools
- `ICEOS_AUTO_EXECUTE_HOOKS=true` - Auto-execute post-workflow analysis
- `ICEOS_ENABLE_MERMAID=true` - Enable Mermaid generation
- `ICEOS_ENABLED_BUILTIN_TOOLS=tool1,tool2` - Enable specific tools

Key Features:
- Optional activation (disabled by default)
- Super easy one-line enablement
- Selective tool activation
- Environment variable control
- Post-execution analysis
- Visualization generation
"""

# Import configuration system
from .config import (
    enable_everything,
    enable_mermaid_only,
    enable_performance_suite, 
    enable_executive_suite,
    enable_specific_tools,
    disable_everything,
    is_tool_enabled,
    is_hook_enabled,
    get_enabled_tools,
    get_enabled_hooks,
    get_config
)

# Import tool classes for direct use
from .post_execution_mermaid import PostExecutionMermaidTool
from .workflow_analyzer import WorkflowAnalyzerTool
from .execution_summarizer import ExecutionSummarizerTool
from .performance_profiler import PerformanceProfilerTool

# Import auto-workflow functionality
from .auto_workflow_hooks import (
    execute_post_workflow_analysis,
    register_custom_hook,
    disable_auto_analysis,
    enable_auto_analysis
)

__all__ = [
    # Easy enablement functions (main API)
    "enable_everything",
    "enable_mermaid_only",
    "enable_performance_suite", 
    "enable_executive_suite",
    "enable_specific_tools",
    "disable_everything",
    
    # Status and configuration
    "is_tool_enabled",
    "is_hook_enabled", 
    "get_enabled_tools",
    "get_enabled_hooks",
    "get_config",
    
    # Tool classes (for direct use)
    "PostExecutionMermaidTool",
    "WorkflowAnalyzerTool",
    "ExecutionSummarizerTool", 
    "PerformanceProfilerTool",
    
    # Auto-workflow functions
    "execute_post_workflow_analysis",
    "register_custom_hook",
    "disable_auto_analysis",
    "enable_auto_analysis"
] 