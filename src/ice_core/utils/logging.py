from __future__ import annotations

import logging
import os
import sys

__all__ = ["setup_logger", "logger"]


def setup_logger() -> logging.Logger:
    """Configure root logger with a sane default format only once."""
    logger = logging.getLogger()
    if logger.handlers:
        return logger

    # ------------------------------------------------------------------
    # Log level detection ---------------------------------------------
    # ------------------------------------------------------------------
    # Allow environment override via ``ICE_LOG_LEVEL``.  This enables
    # integration tests and CLI demos to enable verbose output without
    # changing application code.

    level_name: str = os.getenv("ICE_LOG_LEVEL", "INFO").upper()
    log_level: int = getattr(logging, level_name, logging.INFO)

    logger.setLevel(log_level)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(log_level)
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    # ------------------------------------------------------------------
    # Optional JSON log file handler -----------------------------------
    # ------------------------------------------------------------------
    json_path = os.getenv("ICE_LOG_JSON")
    if json_path:
        import json
        from pathlib import Path

        class _JSONFormatter(logging.Formatter):
            """Very small JSON-lines formatter (one object per line)."""

            def format(self, record: logging.LogRecord) -> str:  # noqa: D401
                # Base dict with common attributes -----------------------
                rec_dict: dict[str, str] = {
                    "timestamp": self.formatTime(record, self.datefmt),
                    "level": record.levelname,
                    "logger": record.name,
                    "message": record.getMessage(),
                }

                # Merge *extra* mapping when provided ------------------
                for key, value in record.__dict__.items():
                    if key not in rec_dict and not key.startswith("_"):
                        try:
                            json.dumps(value)  # ensure serialisable
                            rec_dict[key] = value  # type: ignore[assignment]
                        except TypeError:
                            rec_dict[key] = str(value)

                return json.dumps(rec_dict, ensure_ascii=False)

        json_file = Path(json_path).expanduser().resolve()
        json_file.parent.mkdir(parents=True, exist_ok=True)

        json_handler = logging.FileHandler(json_file, encoding="utf-8")
        json_handler.setLevel(log_level)
        json_handler.setFormatter(_JSONFormatter())
        logger.addHandler(json_handler)

    return logger


logger = setup_logger()
