from __future__ import annotations

import logging
import os
import sys
from typing import Any, Dict, Optional

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

    # ------------------------------------------------------------------
    # Handler selection ------------------------------------------------
    # ------------------------------------------------------------------
    def _build_plain_handler() -> logging.Handler:
        h = logging.StreamHandler(sys.stdout)
        h.setLevel(log_level)
        h.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
        return h

    def _build_json_formatter() -> logging.Formatter:  # noqa: D401
        import json

        try:
            from opentelemetry import trace  # type: ignore
        except ImportError:  # pragma: no cover – OTEL optional
            trace = None  # type: ignore

        class _JSONFormatter(logging.Formatter):
            """Very small JSON-lines formatter (one object per line).

            Adds *trace_id* and *span_id* when OpenTelemetry context is present, and
            propagates a best-effort request_id if attached to the record by middleware.
            """

            def _trace_context(self) -> Dict[str, Optional[str]]:  # noqa: D401
                if trace is None:
                    return {"trace_id": None, "span_id": None}
                span = trace.get_current_span()
                if span is None:
                    return {"trace_id": None, "span_id": None}
                ctx = span.get_span_context()
                if ctx is None or not ctx.is_valid:
                    return {"trace_id": None, "span_id": None}
                return {
                    "trace_id": format(ctx.trace_id, "032x"),
                    "span_id": format(ctx.span_id, "016x"),
                }

            def format(self, record: logging.LogRecord) -> str:  # noqa: D401
                rec_dict: Dict[str, Any] = {
                    "timestamp": self.formatTime(record, self.datefmt),
                    "level": record.levelname,
                    "logger": record.name,
                    "message": record.getMessage(),
                }
                rec_dict.update(self._trace_context())

                # Correlation/request id if present
                req_id = getattr(record, "request_id", None)
                if isinstance(req_id, str) and req_id:
                    rec_dict["request_id"] = req_id

                # Merge any extra attributes --------------------------
                for key, value in record.__dict__.items():
                    if key not in rec_dict and not key.startswith("_"):
                        try:
                            json.dumps(value)
                            rec_dict[key] = value  # type: ignore[assignment]
                        except TypeError:
                            rec_dict[key] = str(value)

                return json.dumps(rec_dict, ensure_ascii=False)

        return _JSONFormatter()

    ice_log_json = os.getenv("ICE_LOG_JSON")
    env_profile = os.getenv("ICE_ENV", "dev").lower()

    if ice_log_json and ice_log_json.lower() in {"stdout", "1", "true"}:
        json_handler: logging.Handler = logging.StreamHandler(sys.stdout)
        json_handler.setLevel(log_level)
        json_handler.setFormatter(_build_json_formatter())
        logger.addHandler(json_handler)
    elif ice_log_json:  # treat value as file path
        from pathlib import Path

        json_file = Path(ice_log_json).expanduser().resolve()
        json_file.parent.mkdir(parents=True, exist_ok=True)
        json_handler = logging.FileHandler(json_file, encoding="utf-8")
        json_handler.setLevel(log_level)
        json_handler.setFormatter(_build_json_formatter())
        logger.addHandler(json_handler)
    elif env_profile == "prod":
        # Default to JSON to stdout in production profile even without env override
        json_handler = logging.StreamHandler(sys.stdout)
        json_handler.setLevel(log_level)
        json_handler.setFormatter(_build_json_formatter())
        logger.addHandler(json_handler)
    else:
        # Plain text stdout (default for dev/tests)
        logger.addHandler(_build_plain_handler())

    return logger


logger = setup_logger()
