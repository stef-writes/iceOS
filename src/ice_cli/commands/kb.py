"""`ice kb` – knowledge-base ingestion helpers.

Phase-1 CLI wrapping the *KnowledgeService* so users can ingest documents
from the command-line.  Side-effects (filesystem IO, vector upserts) live in
KnowledgeService which is already an allowed layer.
"""

from __future__ import annotations

from pathlib import Path
from typing import List

import typer  # type: ignore
from rich import print as rprint  # type: ignore

from iceos.services.knowledge_service import KnowledgeConfig, KnowledgeService

kb_app = typer.Typer(add_completion=False, help="Knowledge-base utilities")

__all__: list[str] = ["kb_app"]


@kb_app.command("ingest", help="Ingest files or directories into the KB vector store")
def kb_ingest(
    paths: List[Path] = typer.Argument(
        ..., exists=True, readable=True, help="One or more files/directories to ingest"
    ),
    label: str = typer.Option(
        "default",
        "--label",
        "-l",
        help="Logical label / namespace for the uploaded docs (future filtering)",
    ),
    chunk_size: int = typer.Option(
        1000,
        "--chunk-size",
        "-c",
        min=100,
        help="Chunk size in tokens/words (>=100)",
    ),
    overlap: int = typer.Option(
        200,
        "--overlap",
        "-o",
        min=0,
        help="Overlap between chunks (must be < chunk-size)",
    ),
    watch: bool = typer.Option(
        False,
        "--watch/--no-watch",
        help="Watch directories for changes and ingest incrementally",
    ),
):
    """Ingest *paths* into the vector index.

    Example::

        ice kb ingest docs/support_faq --label support-faq -c 800 -o 120
    """

    # Validate overlap < chunk_size explicitly (typer's min check can't compare)
    if overlap >= chunk_size:
        rprint("[red]Error:[/] --overlap must be smaller than --chunk-size")
        raise typer.Exit(1)

    # Convert all paths to absolute, ensure they exist
    abs_dirs: list[str] = []
    for p in paths:
        if p.is_dir():
            abs_dirs.append(str(p.resolve()))
        else:
            # Treat files by using their parent directory for watcher simplicity
            abs_dirs.append(str(p.parent.resolve()))

    cfg = KnowledgeConfig(
        watch_dirs=abs_dirs,
        auto_parse=not watch,  # instant ingest unless watch mode
        chunk_size=chunk_size,
        chunk_overlap=overlap,
        label=label,
    )

    svc = KnowledgeService(cfg)

    # NOTE: KnowledgeService auto-parses when *auto_parse* is True.
    if watch:
        import signal

        from iceos.services.document_processor import DocumentProcessor

        rprint(
            f"[green]Watching {', '.join(abs_dirs)} for changes[/] – press Ctrl+C to stop"
        )

        processor = DocumentProcessor(svc)
        processor.start_watching()

        def _stop(sig, _frame):  # noqa: D401 – signal handler
            rprint("\n[cyan]Stopping watcher…[/]")
            processor.stop_watching()
            raise typer.Exit()

        signal.signal(signal.SIGINT, _stop)  # graceful Ctrl+C
        signal.pause()
    else:
        # One-off ingest path – just give feedback
        rprint(f"[green]✔ Ingested documents under:[/] {', '.join(abs_dirs)}")
        rprint("Chunks stored in the vector index. Use them via EnterpriseKBNode.")
