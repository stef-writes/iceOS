"""Stub implementation of the catalog adapter used by FastAPI smoke tests.

Provides minimal *CatalogSummary* and *get_catalog* so that *ice_api.main*
imports succeed without wiring the full catalog back-end.
"""

from dataclasses import dataclass
from typing import List

__all__ = ["CatalogSummary", "get_catalog"]


@dataclass
class CatalogSummary:
    id: str
    name: str
    description: str = "stub"


async def get_catalog(tenant: str | None = None) -> List[CatalogSummary]:  # noqa: D401
    """Return dummy catalog items for tests."""

    return [CatalogSummary(id="demo", name="Demo Chain")] 