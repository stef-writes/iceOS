"""Run the *ice* CLI with ``python -m ice_cli``.

This thin shim simply delegates to :pydata:`ice_cli.cli.app` so users do not
need the Poetry-generated console script when running inside editable clones
or zipped site-packages.
"""

from __future__ import annotations

from ice_sdk.context import GraphContextManager as _Ctx
from ice_sdk.providers.llm_service import LLMService as _LLMSvc
from ice_sdk.services import ServiceLocator as _Svc
from ice_sdk.tools.service import ToolService as _TSvc

from .cli import app

# Pre-register global services for CLI commands -----------------------------
_Svc.register("tool_service", _TSvc())
_Svc.register("context_manager", _Ctx())
_Svc.register("llm_service", _LLMSvc())

if __name__ == "__main__":
    # Typer's .main() helper respects shell completion & exit codes.
    app()
