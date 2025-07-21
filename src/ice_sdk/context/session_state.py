from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional


class SessionState:
    """Lightweight container for per-user / per-session memory.

    It intentionally holds only **plain Python types** so it can be stored in
    JSON, Redis, SQLite, etc.  Swap the backend by serialising this object.
    """

    def __init__(self, session_id: str, *, created_at: Optional[datetime] = None):
        self.session_id = session_id
        self.created_at = created_at or datetime.utcnow()
        self.conversation_history: List[Dict[str, Any]] = []  # list of {role, content}
        self.agent_state: Dict[str, Any] = {}  # per-agent scratch space
        self.last_outputs: Dict[str, Any] = {}  # node_id/agent_name ➜ last output

    # ------------------------------------------------------------------
    # Conversation helpers
    # ------------------------------------------------------------------
    def add_message(self, role: str, content: str) -> None:
        self.conversation_history.append({"role": role, "content": content})

    # ------------------------------------------------------------------
    # Output helpers
    # ------------------------------------------------------------------
    def set_output(self, source: str, output: Any) -> None:
        self.last_outputs[source] = output

    def get_output(self, source: str, default: Any = None) -> Any:
        return self.last_outputs.get(source, default)

    # ------------------------------------------------------------------
    # Pickle / dict helpers for persistence
    # ------------------------------------------------------------------
    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "created_at": self.created_at.isoformat(),
            "conversation_history": self.conversation_history,
            "agent_state": self.agent_state,
            "last_outputs": self.last_outputs,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SessionState":
        obj = cls(
            data["session_id"], created_at=datetime.fromisoformat(data["created_at"])
        )
        obj.conversation_history = data.get("conversation_history", [])
        obj.agent_state = data.get("agent_state", {})
        obj.last_outputs = data.get("last_outputs", {})
        return obj
