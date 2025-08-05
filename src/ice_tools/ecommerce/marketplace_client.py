"""MarketplaceClientTool – async HTTP POST wrapper for product listings.

Keeps network I/O confined to `_execute_impl` and supports `test_mode` for
offline execution.
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any, Dict, Optional
from urllib.parse import urlparse

import httpx
from pydantic import Field, SecretStr, validator

from ice_core.base_tool import ToolBase
from ice_core.exceptions import ValidationError
from ice_core.models.enums import NodeType
from ice_core.unified_registry import registry

__all__: list[str] = ["MarketplaceClientTool"]

logger = logging.getLogger(__name__)


class MarketplaceClientTool(ToolBase):
    """Create a product listing via HTTP POST (or simulate in test_mode)."""

    # Metadata ----------------------------------------------------------------
    name: str = "marketplace_client"
    description: str = "POST a product listing to an external marketplace API."

    # Config ------------------------------------------------------------------
    # Defaults can be overridden via env vars for zero-config deployment
    endpoint_url: str = Field(
        default_factory=lambda: os.getenv(
            "ICE_MARKETPLACE_ENDPOINT", "https://example.com/api/listings"
        ),
        description="Marketplace listings endpoint (HTTPS)",
    )
    # API key may be missing in dev environments – keep it Optional but
    # avoid instantiating SecretStr with *None* which violates the type.
    api_key: Optional[SecretStr] = Field(
        default_factory=lambda: (
            SecretStr(os.getenv("ICE_MARKETPLACE_API_KEY", ""))
            if os.getenv("ICE_MARKETPLACE_API_KEY")
            else None
        ),
        description="Bearer token for Authorization header",
    )
    test_mode: bool = Field(
        default_factory=lambda: os.getenv("ICE_TEST_MODE", "0") in {"1", "true", "True"}
    )

    # Validators --------------------------------------------------------------
    @validator("endpoint_url")
    def _must_be_https(cls, v: str) -> str:  # noqa: D401
        parsed = urlparse(str(v))
        if parsed.scheme != "https":
            raise ValueError("Marketplace endpoint must be HTTPS for security reasons")
        return v

    async def validate(self) -> None:  # type: ignore[override]
        """Optional lightweight connectivity probe (HEAD)."""
        if self.test_mode:
            return
        timeout = httpx.Timeout(3.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            try:
                await client.head(str(self.endpoint_url))
            except Exception as exc:  # pragma: no cover – network path
                raise ValidationError(
                    f"Marketplace endpoint unreachable: {exc}"
                ) from exc

    # Execution ---------------------------------------------------------------
    async def _execute_impl(self, **kwargs: Any) -> Dict[str, Any]:  # noqa: D401
        item: dict[str, Any] = kwargs.get("item", {})
        if "sku" not in item:
            raise ValidationError("'item' must include at least a 'sku' field")

        if self.test_mode:
            await asyncio.sleep(0.05)  # Simulate latency
            simulated_id = f"TEST-{item['sku']}"
            logger.debug(
                "[TEST_MODE] listing simulated | sku=%s id=%s",
                item["sku"],
                simulated_id,
            )
            return {"listing_id": simulated_id, "raw_response": {"status": "simulated"}}

        headers: Dict[str, str] = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key.get_secret_value()}"

        timeout = httpx.Timeout(10.0)
        max_attempts = 3
        delay = 1.0
        for attempt in range(1, max_attempts + 1):
            try:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    logger.debug(
                        "Marketplace POST → %s | attempt=%s payload=%s",
                        self.endpoint_url,
                        attempt,
                        item,
                    )
                    resp = await client.post(
                        str(self.endpoint_url), json=item, headers=headers
                    )
                break  # success – exit retry loop
            except (httpx.RequestError, httpx.TimeoutException) as exc:
                if attempt == max_attempts:
                    raise ValidationError(
                        f"Marketplace request failed after {max_attempts} attempts: {exc}"
                    ) from exc
                logger.warning(
                    "Marketplace request failed (attempt %s/%s): %s",
                    attempt,
                    max_attempts,
                    exc,
                )
                await asyncio.sleep(delay * attempt)

        if resp.status_code not in {200, 201}:
            raise ValidationError(
                f"Marketplace returned {resp.status_code}: {resp.text[:200]}"
            )

        data = resp.json() if resp.content else {}
        listing_id = data.get("id") or data.get("listing_id") or data.get("result")
        if not listing_id:
            raise ValidationError("Marketplace response lacks 'id' field")

        logger.debug("Marketplace response OK | id=%s", listing_id)
        return {"listing_id": listing_id, "raw_response": data}


# Auto-registration -----------------------------------------------------------
_instance = MarketplaceClientTool(
    endpoint_url="https://example.com/api/listings", test_mode=True
)
registry.register_instance(NodeType.TOOL, _instance.name, _instance, validate=False)  # type: ignore[arg-type]
