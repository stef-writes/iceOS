from __future__ import annotations

from typing import Any

import pytest

from ice_orchestrator.graph.dependency_graph import DependencyGraph

# ---------------------------------------------------------------------------
# Helpers -------------------------------------------------------------------
# ---------------------------------------------------------------------------


class _Stub:
    def __init__(self, node_id: str, deps: list[str] | None = None, **attrs: Any):
        self.id = node_id
        self.dependencies = deps or []
        for k, v in attrs.items():
            setattr(self, k, v)


# ---------------------------------------------------------------------------
# Tests ---------------------------------------------------------------------
# ---------------------------------------------------------------------------


def test_sensitive_data_flow_blocked():
    pii_src = _Stub("src", contains_sensitive_data=True)
    risky = _Stub("risky", deps=["src"], requires_external_io=True)

    with pytest.raises(ValueError):
        DependencyGraph([pii_src, risky])


def test_sensitive_data_flow_allowed_after_anonymizer():
    pii_src = _Stub("src", contains_sensitive_data=True)
    anonymizer = _Stub("anon", deps=["src"], requires_external_io=False)
    external = _Stub("ext", deps=["anon"], requires_external_io=True)

    # Should *not* raise – flow passes through anonymizer first
    DependencyGraph([pii_src, anonymizer, external])


# Factory using stub


def _n(node_id: str, **attrs):
    return _Stub(node_id, **attrs)
