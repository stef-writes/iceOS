"""Legacy ``app.chains`` package.

Everything related to orchestration logic has moved to ``ice_orchestrator``.
We leave the original *events* and *metrics* sub-packages in place so that
existing imports like ``from app.chains.events import EventDispatcher`` still
work.  Nothing here should import ``ice_orchestrator`` to avoid circular
initialisation.
"""

from importlib import import_module
import sys

# Preserve sub-modules that were **not** relocated.
for _name in ("events", "metrics"):
    _mod = import_module(f"app.chains.{_name}")
    sys.modules.setdefault(f"app.chains.{_name}", _mod)

# Note: orchestration classes now live in ``ice_orchestrator``.
