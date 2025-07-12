"""Simple in-memory registry for :pyclass:`~ice_sdk.capabilities.card.CapabilityCard` objects.

The registry is NOT a singleton by design; callers create an instance, add
cards (or pull them from *ToolService.cards()*) and then perform look-ups.
If we need a process-wide default we can wire it later via *ice_sdk.cache*.
"""

from __future__ import annotations

import fnmatch
import re
from typing import Iterable, List

from .card import CapabilityCard

__all__ = ["CapabilityRegistry"]


class CapabilityRegistry:  # noqa: D101 – simple data holder
    def __init__(self) -> None:
        self._cards: dict[str, CapabilityCard] = {}

    # ------------------------------------------------------------------
    # Mutation helpers --------------------------------------------------
    # ------------------------------------------------------------------
    def add(
        self, card: CapabilityCard, *, overwrite: bool = False
    ) -> None:  # noqa: D401 – verb clause
        """Register *card* keyed by its ``id``.

        Args
        -----
        card
            The :class:`CapabilityCard` instance to store.
        overwrite
            If *False* (default) a ``ValueError`` is raised when a card with the
            same *id* already exists.  When *True* the existing entry is
            replaced (used when re-loading updated metadata).
        """
        if card.id in self._cards and not overwrite:  # noqa: R504
            raise ValueError(f"Capability '{card.id}' already registered")
        self._cards[card.id] = card

    def extend(
        self, cards: Iterable[CapabilityCard], *, overwrite: bool = False
    ) -> None:
        """Bulk-add *cards* (helper around :py:meth:`add`)."""
        for card in cards:
            self.add(card, overwrite=overwrite)

    # ------------------------------------------------------------------
    # Query helpers -----------------------------------------------------
    # ------------------------------------------------------------------
    def get(self, id_: str) -> CapabilityCard | None:  # noqa: D401 – getter
        """Return a card by *id* or **None** when missing."""
        return self._cards.get(id_)

    def list(self) -> List[CapabilityCard]:  # noqa: D401 – list helper
        """Return **all** cards in insertion order."""
        return list(self._cards.values())

    # ------------------------------------------------- search ----------
    def search(self, query: str) -> List[CapabilityCard]:  # noqa: D401
        """Very small search util.

        Matching strategy (quick & dirty):
        1. Case-insensitive substring against *id*, *name* and *description*.
        2. Wild-cards via :pymod:`fnmatch` (``web*``).
        3. Tag match if *query* exactly equals a tag.
        """
        query_low = query.lower()
        pattern = re.escape(query_low).replace("\\*", ".*")  # allow '*' wild-card
        regex = re.compile(pattern)

        def _match(card: CapabilityCard) -> bool:
            if regex.search(card.id.lower()):
                return True
            if regex.search(card.name.lower()):
                return True
            if regex.search(card.description.lower()):
                return True
            if card.purpose and regex.search(card.purpose.lower()):
                return True
            if card.examples and any(
                regex.search(str(sample).lower()) for sample in card.examples
            ):
                return True
            if any(tag.lower() == query_low for tag in card.tags):
                return True
            # fallback to fnmatch on id & tags --------------------------
            if fnmatch.fnmatch(card.id.lower(), query_low):
                return True
            if any(fnmatch.fnmatch(tag.lower(), query_low) for tag in card.tags):
                return True
            return False

        return [card for card in self._cards.values() if _match(card)]

    # ------------------------------------------------------------------
    # Representation ----------------------------------------------------
    # ------------------------------------------------------------------
    def __len__(self) -> int:  # noqa: D401 – dunder
        return len(self._cards)

    def __iter__(self) -> Iterable[CapabilityCard]:  # noqa: D401 – dunder
        return iter(self._cards.values())
