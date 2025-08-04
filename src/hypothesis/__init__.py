"""Minimal stub for hypothesis to allow tests without the real library."""
import types

def given(*_args, **_kwargs):  # noqa: D401 – placeholder decorator
    def decorator(func):
        return func
    return decorator

def assume(condition):  # noqa: D401 – placeholder assume
    if not condition:
        raise AssertionError("assumption failed in stub")

# Stub strategies submodule with basic functions
a = types.ModuleType("hypothesis.strategies")

def lists(*_a, **_k):
    return None

a.lists = lists
import sys
sys.modules["hypothesis.strategies"] = a

__all__ = ["given", "assume"]