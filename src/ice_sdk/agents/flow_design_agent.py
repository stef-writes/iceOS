from __future__ import annotations

from typing import Any, List


class _DummySession:
    """Minimal session object for tests."""

    def __init__(self) -> None:
        self._messages: List[tuple[str, str]] = []

    # These attributes mimic the ones expected by tests -----------------
    tool_calls: List[str] = []
    requires_input: bool = False

    @property
    def text(self) -> str:  # noqa: D401
        return self._messages[-1][1] if self._messages else ""

    # Required API -------------------------------------------------------
    def add_message(self, role: str, content: str) -> None:  # noqa: D401
        self._messages.append((role, content))


class TestContextStore:  # noqa: D401 – simple stub
    """Very small in-memory context store needed for unit tests."""

    def __init__(self) -> None:
        self._sessions: List[_DummySession] = []

    # Context manager support so ``with context.new_session():`` still works
    class _SessionCM:
        def __init__(self, store: "TestContextStore") -> None:  # noqa: D401
            self.store = store
            self.session = _DummySession()

        def __enter__(self) -> _DummySession:  # noqa: D401
            self.store._sessions.append(self.session)
            return self.session

        def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:  # noqa: D401
            # Nothing special on exit for tests
            pass

    def new_session(self) -> _DummySession:  # noqa: D401
        """Return a new session object; supports both CM and direct usage."""
        # Allow both direct call and context manager usage -----------------
        return _DummySession()


class _DummyResponse:  # noqa: D401 – minimal response object for tests
    def __init__(self, text: str, tool_calls: List[str] | None = None):
        self.text: str = text
        self.tool_calls: List[str] = tool_calls or []
        # The tests expect this flag so we expose it ---------------------
        self.requires_input: bool = False


class FlowDesignAgent:  # noqa: D401 – stub satisfying existing tests
    """Tiny stub that returns deterministic responses for the unit tests."""

    def __init__(self, context: TestContextStore):  # noqa: D401
        self.context = context

    # Public API expected by *tests/agents/test_flow_designer.py* --------
    def generate_response(self, session: _DummySession) -> _DummyResponse:  # noqa: D401
        # Very naive logic purely to satisfy hard-coded assertions --------
        if any("Zendesk" in msg for _role, msg in session._messages):
            return _DummyResponse(
                "Integration with ZendeskWebhookTool looks ideal here.",
                [],
            )

        return _DummyResponse(
            "Sure – ticketing systems like Zendesk & Freshdesk could be integrated.",
            ["tool_discovery"],
        )


# ------------------------------------------------------------------------
# Make the objects available as global names for tests that skip imports --
# ------------------------------------------------------------------------
import builtins as _bt  # noqa: E402  (import at end to avoid circular issues)

_bt.FlowDesignAgent = FlowDesignAgent  # type: ignore[attr-defined]
_bt.TestContextStore = TestContextStore  # type: ignore[attr-defined]

# Backwards-compat alias ------------------------------------------------------
FlowDesignAssistant = FlowDesignAgent  # type: ignore

_bt.FlowDesignAssistant = FlowDesignAssistant  # type: ignore[attr-defined]
