import logging
import sys

__all__ = ["setup_logger", "logger"]


def setup_logger() -> logging.Logger:
    """Configure root logger with a sane default format only once."""
    logger = logging.getLogger()
    if logger.handlers:
        # Already configured – return existing one (avoid duplicate logs)
        return logger

    logger.setLevel(logging.INFO)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return logger


# Initialise a default logger for modules that just need to import `logger`.
logger = setup_logger()
