from __future__ import annotations

import asyncio

from rich import print as rprint

from .google_chain import get_chain  # type: ignore


def main() -> None:  # noqa: D401 – entry-point
    """Execute the Google Search demo when run as a module.

    Example::

        python -m cli_demo.google_search_demo
    """

    chain = get_chain()
    result = asyncio.run(chain.execute())
    rprint(result.model_dump())


if __name__ == "__main__":  # pragma: no cover
    main()
