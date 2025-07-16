# mypy: ignore-errors
"""Filesystem watcher that triggers *incremental* ingestion on file updates."""

from __future__ import annotations

from pathlib import Path

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from iceos.services.knowledge_service import KnowledgeService

__all__ = ["DocumentProcessor"]


class _DocEventHandler(FileSystemEventHandler):
    """Internal handler delegating *all* file changes to :class:`KnowledgeService`."""

    def __init__(self, knowledge_service: KnowledgeService):
        self._kb_service = knowledge_service

    def on_modified(self, event):  # noqa: D401 – watchdog callback
        if not event.is_directory:
            self._kb_service._process_file(
                Path(event.src_path)
            )  # noqa: SLF001 – internal call

    # Also handle new files via *created* event -------------------------
    def on_created(self, event):  # noqa: D401 – watchdog callback
        if not event.is_directory:
            self._kb_service._process_file(
                Path(event.src_path)
            )  # noqa: SLF001 – internal call


class DocumentProcessor:
    """Thin wrapper around watchdog's :class:`Observer`."""

    def __init__(self, knowledge_service: KnowledgeService):
        self._observer = Observer()
        self._kb_service = knowledge_service

    # ------------------------------------------------------------------
    # Public control ----------------------------------------------------
    # ------------------------------------------------------------------
    def start_watching(self) -> None:  # noqa: D401
        """Begin monitoring the configured watch directories."""

        handler = _DocEventHandler(self._kb_service)
        for path in self._kb_service.config.watch_dirs:
            self._observer.schedule(handler, path, recursive=True)
        self._observer.start()

    def stop_watching(self) -> None:  # noqa: D401
        """Stop the filesystem observer and wait for thread shutdown."""

        self._observer.stop()
        self._observer.join()
