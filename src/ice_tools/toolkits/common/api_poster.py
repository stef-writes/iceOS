"""Generic HTTP POST tool.

Sends a JSON payload to a configurable endpoint.  In *mock* mode it POSTs
against the local mock-marketplace router so flows can be exercised without
calling external services.
"""
from __future__ import annotations

import asyncio
from typing import Any, Dict, Optional

import httpx
from pydantic import Field

from ice_core.base_tool import ToolBase


class APIPosterTool(ToolBase):
    """Generic HTTP POST wrapper.

    Example
    -------
    >>> tool = APIPosterTool()
    >>> await tool.execute(
    ...     url="http://localhost:8000/api/v1/mock/marketplace/items",
    ...     payload={"foo": "bar"},
    ...     mock=True,
    ... )
    {'status': 'accepted', 'http_status': 201}
    """

    name: str = "api_poster"
    description: str = "POST arbitrary JSON payloads to a REST endpoint"

    # ------------------------------------------------------------------
    # Tool implementation ------------------------------------------------
    # ------------------------------------------------------------------

    async def _execute_impl(self, **kwargs: Any) -> Dict[str, Any]:
        """Send payload to URL via HTTP POST - context-first approach."""
        # Extract URL - could be nested
        url = self._extract_url(kwargs)
        
        # Extract payload
        payload = self._extract_payload(kwargs)
        
        # Other parameters with defaults
        headers = kwargs.get("headers")
        mock = kwargs.get("mock", False)
        timeout = kwargs.get("timeout", 10.0)

        # In mock mode we treat any URL as internal and skip the request
        if mock:
            return {"status": "mocked", "url": url, "payload": payload}

        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(url, json=payload, headers=headers)
            return {
                "status": "accepted" if resp.status_code < 300 else "error",
                "http_status": resp.status_code,
                "response": resp.text,
            }
    
    def _extract_url(self, context: Dict[str, Any]) -> str:
        """Extract URL from context - handles nested access."""
        # Direct url parameter
        if "url" in context and isinstance(context["url"], str):
            return context["url"]
        
        # Check for mock_server.url pattern
        if "mock_server" in context and isinstance(context["mock_server"], dict):
            if "url" in context["mock_server"]:
                return context["mock_server"]["url"]
        
        # Look for any key ending in .url
        for key, value in context.items():
            if isinstance(value, dict) and "url" in value:
                return value["url"]
        
        raise ValueError("No URL found in context")
    
    def _extract_payload(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Extract payload from context."""
        # Direct payload parameter
        if "payload" in context and isinstance(context["payload"], dict):
            return context["payload"]
        
        # Look for facebook formatter output
        for key in ["fb_format", "formatted", "facebook_formatter"]:
            if key in context and isinstance(context[key], dict):
                return context[key]
        
        # Look for enriched product
        for key in ["enriched_product", "product", "item"]:
            if key in context and isinstance(context[key], dict):
                return context[key]
        
        # Default to empty dict
        return {}


# ---------------------------------------------------------------------------
# Auto-registration ---------------------------------------------------------
# ---------------------------------------------------------------------------
from ice_core.unified_registry import registry  # noqa: E402
from ice_core.models.enums import NodeType  # noqa: E402

_instance = APIPosterTool()
registry.register_instance(NodeType.TOOL, _instance.name, _instance, validate=False)  # type: ignore[arg-type]
