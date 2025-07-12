"""Auto-load webhook definitions from ``.ice/webhooks.yaml``.

Each entry in the YAML file should look like:

```yaml
webhooks:
  - url: "https://hooks.example.com/cli"
    events:
      - cli.run.completed
      - cli.tool_new.*
    headers:
      Authorization: Bearer <token>
```  

Only *exact* event names are supported for now (wildcards ignored).
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import List

try:
    import yaml  # PyYAML – optional dependency
except ModuleNotFoundError:  # pragma: no cover – optional
    yaml = None  # type: ignore

from ice_sdk.events import subscribe
from ice_sdk.events.models import EventEnvelope
from ice_sdk.tools.base import ToolContext
from ice_sdk.tools.web.webhook_tool import WebhookEmitterTool

_logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Config loading ------------------------------------------------------------
# ---------------------------------------------------------------------------


def _find_config_file() -> Path | None:  # noqa: D401 – helper
    """Return path to ``.ice/webhooks.yaml`` if it exists."""

    cwd = Path.cwd()
    path = cwd / ".ice" / "webhooks.yaml"
    return path if path.exists() else None


def _parse_config(path: Path) -> List[dict]:  # noqa: D401 – helper
    """Return list of webhook dicts parsed from *path*."""

    if yaml is None:
        _logger.warning("PyYAML not installed – skipping webhook config load.")
        return []

    try:
        data = yaml.safe_load(path.read_text()) or {}
    except Exception as exc:  # pragma: no cover – malformed YAML
        _logger.warning("Failed to parse %s: %s", path, exc)
        return []

    webhooks = data.get("webhooks", [])
    result: List[dict] = []
    for idx, item in enumerate(webhooks):
        if not isinstance(item, dict) or "url" not in item or "events" not in item:
            _logger.warning("Invalid entry at index %s in %s – skipped", idx, path)
            continue
        result.append(item)
    return result


# ---------------------------------------------------------------------------
# Subscriber factory --------------------------------------------------------
# ---------------------------------------------------------------------------


def _make_handler(cfg: dict):
    """Return async handler that POSTs *env* via WebhookEmitterTool."""

    tool = WebhookEmitterTool()
    url = cfg["url"]
    headers = cfg.get("headers", {})

    async def _handler(env: EventEnvelope):  # noqa: D401 – conforms to Subscriber
        ctx = ToolContext(
            agent_id="cli", session_id="webhook", metadata=env.model_dump()
        )
        await tool.run(ctx=ctx, url=url, headers=headers)

    return _handler


# ---------------------------------------------------------------------------
# Public API ----------------------------------------------------------------
# ---------------------------------------------------------------------------


def initialise() -> None:  # noqa: D401 – imperative helper
    """Load YAML and register subscribers once per process."""

    if os.getenv("ICE_DISABLE_WEBHOOKS") == "1":
        return

    path = _find_config_file()
    if path is None:
        return

    for cfg in _parse_config(path):
        for event_name in cfg["events"]:
            subscribe(event_name, _make_handler(cfg))

    _logger.info("Webhook subscribers registered from %s", path)


# Run eagerly when module imported by CLI entry-point -----------------------
if __name__ == "__main__":  # pragma: no cover
    initialise()
