from __future__ import annotations

"""Built-in tool that queries the arXiv API and returns a structured list of
papers matching a free-form query.

The implementation intentionally avoids third-party XML parsers to keep the
runtime footprint minimal.  It uses Python's stdlib `httpx` for HTTP and
`xml.etree.ElementTree` for lightweight Atom parsing.
"""

from typing import Any, Dict, List
import httpx
import xml.etree.ElementTree as ET
from pydantic import BaseModel, Field, ConfigDict, model_validator

from ice_core.base_tool import ToolBase
from ice_sdk.utils.errors import ToolExecutionError

__all__ = ["ArxivSearchTool", "ArxivSearchConfig"]


class ArxivSearchConfig(BaseModel):
    """Configuration for :class:`ArxivSearchTool`.

    Attributes
    ----------
    max_results : int, default=10
        Default number of search results (\<= 50) returned when the caller does
        not supply an explicit ``max_results`` argument.
    timeout : float, default=10.0
        Network timeout in seconds for the underlying HTTP request.
    """

    max_results: int = Field(default=10, ge=1, le=50)
    timeout: float = Field(default=10.0, ge=1.0, le=30.0)

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def _clamp_results(cls, model: "ArxivSearchConfig") -> "ArxivSearchConfig":  # type: ignore[override]
        if model.max_results > 50:
            model.max_results = 50  # pragma: no cover – guard
        return model

    @classmethod
    def default(cls) -> "ArxivSearchConfig":
        return cls()


class ArxivSearchTool(ToolBase):
    """Search academic papers on *arXiv*.

    Example
    -------
    >>> import asyncio
    >>> tool = ArxivSearchTool()
    >>> asyncio.run(tool.execute(query="brain computer interface", max_results=3))  # doctest: +SKIP
    {"papers": [...]}  # 3 simplified dicts
    """

    name: str = "arxiv_search"
    description: str = (
        "Search the arXiv catalogue and return metadata for matching papers."
    )

    # Lazy instantiation to avoid unexpected env requirements during import
    config: ArxivSearchConfig = ArxivSearchConfig.default()
    model_config = ConfigDict(extra="allow")

    # ------------------------------------------------------------------
    # Execution implementation
    # ------------------------------------------------------------------
    async def _execute_impl(
        self,
        *,
        query: str,
        max_results: int | None = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        query = (query or "").strip()
        if not query:
            raise ToolExecutionError(self.name, "'query' parameter is required")

        n: int = max_results or self.config.max_results
        n = max(1, min(n, 50))  # Hard upper-bound per arXiv guideline

        params = {
            "search_query": query,
            "start": 0,
            "max_results": n,
        }

        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            resp = await client.get("https://export.arxiv.org/api/query", params=params)

        if resp.status_code != 200:
            snippet = resp.text[:200]
            raise ToolExecutionError(
                self.name, f"arXiv API error {resp.status_code}: {snippet}"
            )

        try:
            root = ET.fromstring(resp.text)
        except ET.ParseError as e:  # pragma: no cover
            raise ToolExecutionError(self.name, f"Failed to parse arXiv XML: {e}")

        # The Atom namespace – arXiv uses the default Atom 1.0
        ns = {"atom": "http://www.w3.org/2005/Atom"}

        papers: List[Dict[str, str]] = []
        for entry in root.findall("atom:entry", ns):
            title = (entry.findtext("atom:title", default="", namespaces=ns) or "").strip()
            summary = (entry.findtext("atom:summary", default="", namespaces=ns) or "").strip()
            published = entry.findtext("atom:published", default="", namespaces=ns) or ""
            link_el = entry.find("atom:link[@type='text/html']", ns)
            link = link_el.attrib.get("href") if link_el is not None else ""

            papers.append(
                {
                    "title": title,
                    "summary": summary,
                    "published": published,
                    "link": link,
                }
            )

        return {"papers": papers[:n]}

    # ------------------------------------------------------------------
    # Schema helpers
    # ------------------------------------------------------------------
    @classmethod
    def get_input_schema(cls) -> dict:  # noqa: D401 – simple function name
        return cls.model_json_schema()

    @classmethod
    def get_output_schema(cls) -> dict:  # noqa: D401 – simple function name
        return cls.model_json_schema() 