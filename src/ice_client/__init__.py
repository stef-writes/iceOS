"""Public interface for talking to a remote iceOS orchestrator service.

This package intentionally contains *no* orchestrator logic – it is a thin
network client that turns convenience method calls into HTTP / Server-Sent
Event requests against the `/api/v1/mcp` REST facade exposed by the private
orchestrator service.

The API surface is deliberately minimal: only what Frosty and other end-user
tools need today.  More routes can be added incrementally without leaking any
internal abstractions.
"""

from .client import IceClient, OrchestratorError, RunStatus

__all__: list[str] = [
    "IceClient",
    "OrchestratorError",
    "RunStatus",
]
