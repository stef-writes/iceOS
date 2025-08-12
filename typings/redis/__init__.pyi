# Re-export asyncio submodule for import-as-redis usage
from . import asyncio as asyncio
from .asyncio import Redis
from .asyncio import from_url as from_url  # noqa: F401

__all__: list[str] = ["Redis", "from_url", "asyncio"]
