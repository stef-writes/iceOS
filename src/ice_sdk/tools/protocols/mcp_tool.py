"""Model Context Protocol (MCP) integration tool.

This *general* tool exposes the three core MCP actions (``read_wiki_structure``,
``read_wiki_contents`` and ``ask_question``) against any MCP-compatible server
(public or private).  Built-in presets are provided for the two currently
known servers:

* ``deepwiki`` – https://mcp.deepwiki.com  (no authentication)
* ``devin``    – https://mcp.devin.ai      (Bearer token authentication)

Additional servers can be used by passing a custom ``base_url`` and optional
HTTP ``headers`` at call time.

External side-effects are limited to network I/O performed through *httpx*,
which satisfies the repository rule that side-effects live exclusively inside
Tool implementations.
"""

from __future__ import annotations

import os
from typing import Any, ClassVar, Dict, MutableMapping, Optional

import httpx
from pydantic import BaseModel, Field, PrivateAttr

from ..base import BaseTool, ToolError

__all__: list[str] = ["MCPTool"]


class _PresetConfig(BaseModel):
    """Internal helper model for server presets."""

    base_url: str
    headers: Dict[str, str] = Field(default_factory=dict)
    protocol: str = "mcp"  # "mcp" (streamable HTTP) or "sse"


# ---------------------------------------------------------------------------
# Preset registry ------------------------------------------------------------
# ---------------------------------------------------------------------------
_PRESETS: Dict[str, _PresetConfig] = {
    "deepwiki": _PresetConfig(base_url="https://mcp.deepwiki.com"),
    # *Authorization* header will be filled dynamically with DEVIN_API_KEY if
    # present.  Place holder value kept for clarity.
    "devin": _PresetConfig(
        base_url="https://mcp.devin.ai",
        headers={"Authorization": "Bearer ${DEVIN_API_KEY}"},
    ),
}


class MCPTool(BaseTool):
    """Interact with any MCP-compatible documentation/search server."""

    name: ClassVar[str] = "mcp"
    description: ClassVar[str] = (
        "Access git repository documentation via the Model Context Protocol (MCP)."
    )

    # ------------------------------------------------------------------
    # JSON schema for function parameters -------------------------------
    # ------------------------------------------------------------------
    parameters_schema: ClassVar[Dict[str, Any]] = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": [
                    "read_wiki_structure",
                    "read_wiki_contents",
                    "ask_question",
                ],
                "description": "MCP action to perform",
            },
            "repository": {
                "type": "string",
                "description": "GitHub repository identifier (owner/repo)",
            },
            "topic": {
                "type": "string",
                "description": "Documentation topic (for read_wiki_contents)",
            },
            "question": {
                "type": "string",
                "description": "Free-form question (for ask_question)",
            },
            "server": {
                "type": "string",
                "description": (
                    "Name of preset MCP server (e.g. 'deepwiki', 'devin'). "
                    "If omitted defaults to 'deepwiki'.",
                ),
            },
            "base_url": {
                "type": "string",
                "description": (
                    "Override server base URL. Ignored when *server* preset is provided."
                ),
            },
            "protocol": {
                "type": "string",
                "enum": ["mcp", "sse"],
                "description": "Wire protocol endpoint (default: 'mcp')",
            },
            "headers": {
                "type": "object",
                "description": (
                    "Additional HTTP headers to merge with preset/default ones",
                ),
            },
            "timeout": {
                "type": "number",
                "description": "Request timeout in seconds (default 30)",
                "minimum": 1,
                "maximum": 120,
            },
        },
        "required": ["action", "repository"],
    }

    # Simple output schema ----------------------------------------------
    output_schema: ClassVar[Dict[str, Any]] = {
        "type": "object",
        "properties": {
            "status": {"type": "string"},
            "result": {"type": "object"},
            "error": {"type": "string"},
        },
        "required": ["status", "result"],
    }

    # Allow private attributes for runtime config -----------------------
    model_config = {
        "extra": "allow",
    }

    # Internal runtime state (not validated) -----------------------------
    _runtime_headers: MutableMapping[str, str] = PrivateAttr(default_factory=dict)
    _endpoint: str = PrivateAttr(default="")
    _timeout: float = PrivateAttr(default=30.0)

    # ------------------------------------------------------------------
    # Public API --------------------------------------------------------
    # ------------------------------------------------------------------
    async def run(self, **kwargs: Any) -> Dict[str, Any]:  # type: ignore[override]
        """Execute the requested MCP *action*.

        Mandatory arguments:
            action – one of the 3 MCP actions
            repository – GitHub repository slug

        Optional arguments allow overriding the target server, protocol, headers…
        """

        try:
            return await self._run_impl(**kwargs)
        except ToolError:
            raise  # Already a ToolError, bubble up unchanged
        except Exception as exc:  # pragma: no cover – catch-all for clarity
            raise ToolError(f"MCPTool failed: {exc}") from exc

    # ------------------------------------------------------------------
    # Internal helpers --------------------------------------------------
    # ------------------------------------------------------------------
    async def _run_impl(self, **kwargs: Any) -> Dict[str, Any]:
        # ---------------------------
        # Extract & validate inputs
        # ---------------------------
        action: str = kwargs["action"]  # required by schema
        repository: str = kwargs["repository"]  # required by schema
        topic: Optional[str] = kwargs.get("topic")
        question: Optional[str] = kwargs.get("question")

        if action == "read_wiki_contents" and not topic:
            raise ToolError("'topic' is required when action='read_wiki_contents'")
        if action == "ask_question" and not question:
            raise ToolError("'question' is required when action='ask_question'")

        # ---------------------------
        # Build connection settings
        # ---------------------------
        server_name: str = kwargs.get("server", "deepwiki")
        preset = _PRESETS.get(server_name)

        # Start config with either preset or empty defaults
        if preset is not None:
            base_url: str = str(preset.base_url)
            headers: Dict[str, str] = dict(preset.headers)
            protocol: str = preset.protocol
        else:
            # Custom server path
            base_url_raw = kwargs.get("base_url")
            if not base_url_raw:
                raise ToolError("'base_url' must be provided for custom servers")
            base_url = str(base_url_raw)
            headers = {}
            protocol = "mcp"

        # Allow explicit overrides -------------------------------------------------
        if "base_url" in kwargs and kwargs["base_url"]:
            base_url = str(kwargs["base_url"])  # ensure str
        if "protocol" in kwargs and kwargs["protocol"] in {"mcp", "sse"}:
            protocol = kwargs["protocol"]
        # Merge caller-supplied headers (lowest priority → highest priority)
        headers.update(kwargs.get("headers", {}))

        # Fill placeholder API keys when needed ------------------------------------
        auth_header = headers.get("Authorization")
        if auth_header and "${DEVIN_API_KEY}" in auth_header:
            api_key = kwargs.get("api_key") or os.getenv("DEVIN_API_KEY")
            if not api_key:
                raise ToolError("DEVIN_API_KEY environment variable not set")
            headers["Authorization"] = auth_header.replace("${DEVIN_API_KEY}", api_key)

        # Always ensure JSON content type for POST
        if "Content-Type" not in headers:
            headers["Content-Type"] = "application/json"

        self._runtime_headers = headers
        self._endpoint = f"{base_url.rstrip('/')}/{protocol.lstrip('/')}"
        self._timeout = float(kwargs.get("timeout", 30.0))

        # Build request body -------------------------------------------------------
        payload: Dict[str, Any] = {"action": action, "repository": repository}
        if topic is not None:
            payload["topic"] = topic
        if question is not None:
            payload["question"] = question

        # ---------------------------
        # Perform network request
        # ---------------------------
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.post(self._endpoint, json=payload, headers=headers)
                resp.raise_for_status()
                data: Any = resp.json()
        except httpx.HTTPStatusError as exc:
            return {
                "status": "error",
                "result": {},
                "error": f"HTTP {exc.response.status_code}: {exc.response.text}",
            }
        except Exception as exc:  # pragma: no cover – network errors etc.
            return {
                "status": "error",
                "result": {},
                "error": f"Request failed: {exc}",
            }

        return {"status": "success", "result": data}
